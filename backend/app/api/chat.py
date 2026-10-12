"""答疑接口（PRD 模块 3 · 双窗口隔离式场景化答疑）。

路径前缀：/api/chat

说明：本组接口只读写会话与消息，**不会修改任何项目 / 任务状态**，
从数据层保证「答疑窗口的操作不影响主任务窗口」。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chat import ChatAskRequest
from app.services import chat_service
from app.utils.response import success

router = APIRouter(prefix="/api/chat", tags=["场景化答疑"])


@router.post("/ask", summary="提问（自动绑定项目 + 任务上下文）")
async def ask(payload: ChatAskRequest, db: Session = Depends(get_db)) -> dict:
    """提交问题，返回导师回答。

    - `scope=task`：绑定 `task_id` 对应任务的上下文与历史对话
    - `scope=review`：绑定项目复盘内容的上下文
    """
    result = await chat_service.ask(
        db,
        project_id=payload.project_id,
        task_id=payload.task_id,
        scope=payload.scope,
        question=payload.clean_question,
    )
    return success(result.model_dump(), message="已回答")


@router.get("/history", summary="加载指定任务/复盘的对话历史")
def history(
    project_id: int = Query(..., description="项目 ID"),
    task_id: int | None = Query(default=None, description="任务 ID（scope=task 时必填）"),
    scope: str = Query(default="task", pattern="^(task|review)$", description="作用域"),
    db: Session = Depends(get_db),
) -> dict:
    """切换任务时，右侧答疑窗口调用本接口加载对应任务的独立对话记录。"""
    result = chat_service.get_history(db, project_id, task_id, scope)
    return success(result.model_dump())


@router.delete("/history", summary="清空当前任务的对话")
def clear_history(
    project_id: int = Query(..., description="项目 ID"),
    task_id: int | None = Query(default=None, description="任务 ID"),
    scope: str = Query(default="task", pattern="^(task|review)$"),
    db: Session = Depends(get_db),
) -> dict:
    """清空指定作用域的对话记录，不影响其他任务与主窗口内容。"""
    count = chat_service.clear_history(db, project_id, task_id, scope)
    return success({"deleted": count}, message=f"已清空 {count} 条对话记录")
