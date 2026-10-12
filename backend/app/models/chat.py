"""答疑对话数据模型（双窗口隔离的持久化基础）。

隔离规则（对应 PRD 模块 3）：
- 每个任务独立保存一份会话（scope=task），切换任务时上下文天然隔离；
- 复盘环节另有一份会话（scope=review），可继续就复盘内容提问；
- 会话仅服务于右侧答疑窗口，不会影响左侧主窗口的任何状态。
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import ConversationScope, MessageRole, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.project import Project


class Conversation(Base, TimestampMixin):
    """一次会话：绑定某个任务的答疑，或绑定项目复盘。"""

    __tablename__ = "conversations"
    __table_args__ = (
        # 同一项目下，同一任务 / 同一复盘作用域只允许一条会话，避免历史分散
        UniqueConstraint("project_id", "scope", "task_id", name="uq_conversation_scope"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default=ConversationScope.TASK)
    title: Mapped[str] = mapped_column(String(200), default="")

    project: Mapped["Project"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Conversation id={self.id} scope={self.scope} task_id={self.task_id}>"


class Message(Base, TimestampMixin):
    """单条对话消息。"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=MessageRole.USER)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Message id={self.id} role={self.role}>"
