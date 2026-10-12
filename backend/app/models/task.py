"""阶段与任务数据模型。

一个项目拆解为 4-6 个学习阶段（Stage），每个阶段包含 3-5 个具体任务（Task）。
两种项目来源（GitHub / 定制）复用同一套数据模型。
"""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TaskStatus, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.project import Project


class Stage(Base, TimestampMixin):
    """项目学习阶段（对应一个关键里程碑）。"""

    __tablename__ = "stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_milestone: Mapped[bool] = mapped_column(default=True, comment="是否为关键里程碑")

    project: Mapped["Project"] = relationship(back_populates="stages")
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="stage",
        cascade="all, delete-orphan",
        order_by="Task.order_index",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Stage id={self.id} order={self.order_index} name={self.name!r}>"


class Task(Base, TimestampMixin):
    """具体学习任务，带 DDL 与交付标准。"""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 任务在项目内的全局顺序，保证阶段化时间线唯一有序
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    knowledge_points: Mapped[list] = mapped_column(JSON, default=list, comment="需掌握知识点")
    deliverable_criteria: Mapped[str] = mapped_column(Text, default="", comment="交付标准")
    ddl_days: Mapped[int] = mapped_column(Integer, default=1, comment="建议 DDL 天数")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="DDL 截止日期")

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TaskStatus.TODO)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="tasks")
    stage: Mapped["Stage"] = relationship(back_populates="tasks")

    @property
    def locked(self) -> bool:
        """顺序门禁：前面的任务尚未完成时，该任务处于未解锁状态。

        对应 PRD 模块 2「用户标记任务完成后，自动解锁下一阶段任务」。
        已完成 / 进行中的任务永远不算锁定，避免状态回退时出现死锁。
        """
        if self.status != TaskStatus.TODO:
            return False
        return any(
            other.order_index < self.order_index and other.status != TaskStatus.DONE
            for other in self.project.tasks
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Task id={self.id} name={self.name!r} status={self.status}>"
