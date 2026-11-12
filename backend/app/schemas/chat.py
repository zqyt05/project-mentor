"""答疑对话相关的 Pydantic 模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class MessageOut(ORMModel):
    """单条消息输出。"""

    id: int
    role: str
    content: str
    created_at: datetime


class ChatAskRequest(BaseModel):
    """答疑提问请求。

    - `task_id` 有值且 scope=task：绑定该任务的上下文答疑
    - `scope=review`：复盘环节答疑，绑定项目与最新复盘内容
    """

    project_id: int
    task_id: int | None = None
    scope: Literal["task", "review"] = "task"
    question: str = Field(min_length=1, max_length=4000)

    @property
    def clean_question(self) -> str:
        return self.question.strip()


class ChatHistoryOut(BaseModel):
    """会话历史：右侧答疑窗口切换任务时加载。"""

    conversation_id: int | None = None
    project_id: int
    task_id: int | None = None
    scope: str = "task"
    title: str = ""
    messages: list[MessageOut] = Field(default_factory=list)
    quick_prompts: list[str] = Field(default_factory=list)


class ChatSource(BaseModel):
    """回答引用的资料出处。"""

    filename: str
    chunk_index: int
    score: float
    # 片段摘要：让前端能展示「引用了哪一段」，而不只是文件名
    snippet: str


class ChatAskResponse(BaseModel):
    """答疑响应。"""

    conversation_id: int
    task_id: int | None = None
    answer: str
    messages: list[MessageOut] = Field(default_factory=list)
    # RAG 检索到的资料出处；未上传资料或未命中时为空
    sources: list[ChatSource] = Field(default_factory=list)
