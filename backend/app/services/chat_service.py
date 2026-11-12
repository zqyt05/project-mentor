"""答疑服务：双窗口隔离式场景化问答。

对应 PRD 模块 3。核心设计：
1. **会话隔离**：每个任务一份独立会话（scope=task），复盘一份会话（scope=review）。
   切换任务时天然加载各自的上下文与历史，互不干扰。
2. **上下文拼接**：每次提问都把「项目基本信息 + 当前任务 + 阶段总览」拼进 System Prompt，
   让模型锚定在具体场景，避免泛泛而谈。
3. **主窗口无感**：对话数据只写入 conversations / messages 表，
   完全不触碰项目与任务状态，从数据层面保证「答疑不影响主窗口」。
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Conversation,
    ConversationScope,
    Message,
    MessageRole,
    Project,
    Review,
    Task,
)
from app.schemas.chat import ChatAskResponse, ChatHistoryOut, MessageOut
from app.services.llm_service import get_llm_service, render_prompt
from app.services.project_service import build_project_context, get_project
from app.utils.response import CODE_NOT_FOUND, BusinessError

logger = logging.getLogger(__name__)

# 送入模型的历史对话轮数上限（超出则只保留最近若干条，控制 token 消耗）
_MAX_HISTORY_MESSAGES = 12

# 快速提问模板（前端答疑窗口底部的快捷按钮）
QUICK_PROMPTS = [
    "这一步具体该怎么做？",
    "我遇到报错了，帮我排查",
    "这个任务需要掌握哪些知识点？",
    "帮我检查我的实现思路对不对",
    "给我一个能验证完成的标准",
]


def _get_task(db: Session, task_id: int) -> Task:
    """读取任务，不存在则报错。"""
    task = db.get(Task, task_id)
    if task is None:
        raise BusinessError(f"任务不存在（id={task_id}）", CODE_NOT_FOUND)
    return task


def get_or_create_conversation(
    db: Session, project: Project, task: Task | None, scope: str
) -> Conversation:
    """获取（或创建）指定作用域下的会话。

    :param scope: `task` 表示任务答疑；`review` 表示复盘答疑
    :param task: scope=task 时必填
    """
    stmt = select(Conversation).where(
        Conversation.project_id == project.id,
        Conversation.scope == scope,
        Conversation.task_id == (task.id if task else None),
    )
    conversation = db.execute(stmt).scalars().first()
    if conversation is not None:
        return conversation

    title = task.name if task is not None else f"{project.name} · 复盘答疑"
    conversation = Conversation(
        project_id=project.id,
        task_id=task.id if task else None,
        scope=scope,
        title=title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def _load_history(db: Session, conversation: Conversation) -> list[Message]:
    """按时间顺序读取会话的全部消息。"""
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id.asc())
    )
    return list(db.execute(stmt).scalars().all())


def get_history(
    db: Session,
    project_id: int,
    task_id: int | None,
    scope: str,
    visitor_id: str | None = None,
) -> ChatHistoryOut:
    """加载某个任务 / 复盘作用域下的历史对话（切换任务时由右窗口调用）。"""
    project = get_project(db, project_id, visitor_id)

    if scope == ConversationScope.TASK:
        if task_id is None:
            raise BusinessError("task 作用域必须提供 task_id")
        task = _get_task(db, task_id)
        if task.project_id != project.id:
            raise BusinessError("任务不属于当前项目", CODE_NOT_FOUND)
        title = task.name
    else:
        task = None
        title = f"{project.name} · 复盘答疑"

    stmt = select(Conversation).where(
        Conversation.project_id == project.id,
        Conversation.scope == scope,
        Conversation.task_id == (task.id if task else None),
    )
    conversation = db.execute(stmt).scalars().first()

    messages = _load_history(db, conversation) if conversation else []
    return ChatHistoryOut(
        conversation_id=conversation.id if conversation else None,
        project_id=project.id,
        task_id=task.id if task else None,
        scope=scope,
        title=title,
        messages=[MessageOut.model_validate(message) for message in messages],
        quick_prompts=QUICK_PROMPTS,
    )


def clear_history(
    db: Session,
    project_id: int,
    task_id: int | None,
    scope: str,
    visitor_id: str | None = None,
) -> int:
    """清空当前作用域的对话记录，返回删除的消息条数。"""
    project = get_project(db, project_id, visitor_id)
    stmt = select(Conversation).where(
        Conversation.project_id == project.id,
        Conversation.scope == scope,
        Conversation.task_id == task_id,
    )
    conversation = db.execute(stmt).scalars().first()
    if conversation is None:
        return 0

    messages = _load_history(db, conversation)
    count = len(messages)
    for message in messages:
        db.delete(message)
    db.commit()
    return count


def _build_review_context(db: Session, project: Project) -> str:
    """复盘答疑的上下文：项目信息 + 用户的复盘内容与 AI 最终文档。"""
    context = build_project_context(project, task=None)
    review = db.execute(
        select(Review)
        .where(Review.project_id == project.id)
        .order_by(Review.id.desc())
        .limit(1)
    ).scalars().first()

    if review is not None:
        context += "\n\n【学习者已提交的复盘内容】\n" + (review.user_content or "（空）")
        if review.final_content:
            context += "\n\n【AI 已生成的复盘文档】\n" + review.final_content[:4000]
    return context


async def ask(
    db: Session,
    project_id: int,
    task_id: int | None,
    scope: str,
    question: str,
    visitor_id: str | None = None,
) -> ChatAskResponse:
    """答疑主流程：拼装上下文 → 调用 LLM → 落库 → 返回回答。"""
    project = get_project(db, project_id, visitor_id)
    question = question.strip()
    if not question:
        raise BusinessError("问题内容不能为空")

    task: Task | None = None
    if scope == ConversationScope.TASK:
        if task_id is None:
            raise BusinessError("task 作用域必须提供 task_id")
        task = _get_task(db, task_id)
        if task.project_id != project.id:
            raise BusinessError("任务不属于当前项目", CODE_NOT_FOUND)
        context = build_project_context(project, task)
    else:
        context = _build_review_context(db, project)

    conversation = get_or_create_conversation(db, project, task, scope)
    history = _load_history(db, conversation)

    # 保存用户提问（先落库，保证即使模型调用失败也不丢问题）
    user_message = Message(
        conversation_id=conversation.id, role=MessageRole.USER, content=question
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # 只取最近若干条历史，控制上下文长度
    recent = history[-_MAX_HISTORY_MESSAGES:]
    history_text = (
        "\n".join(
            f"{'学习者' if message.role == MessageRole.USER else '导师'}：{message.content}"
            for message in recent
        )
        or "（这是本任务的第一个问题）"
    )

    system_prompt = render_prompt("chat_answer", context=context)
    user_prompt = (
        f"## 本任务的历史对话\n{history_text}\n\n"
        f"## 学习者当前的问题\n{question}"
    )

    llm = get_llm_service()
    answer = await llm.acomplete(system_prompt, user_prompt, db=db)

    assistant_message = Message(
        conversation_id=conversation.id, role=MessageRole.ASSISTANT, content=answer
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return ChatAskResponse(
        conversation_id=conversation.id,
        task_id=task.id if task else None,
        answer=answer,
        messages=[
            MessageOut.model_validate(user_message),
            MessageOut.model_validate(assistant_message),
        ],
    )


__all__ = [
    "QUICK_PROMPTS",
    "ask",
    "get_history",
    "clear_history",
    "get_or_create_conversation",
]
