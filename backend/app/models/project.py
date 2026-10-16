"""项目数据模型。

统一项目模型：GitHub 开源项目与 AI 定制项目共用同一张表，
通过 `source` 字段区分；GitHub 专有字段（repo_url/stars/language）对定制项目为空。
"""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import ProjectSource, ProjectStatus, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型检查，避免循环导入
    from app.models.chat import Conversation
    from app.models.review import Review
    from app.models.task import Stage, Task


class Project(Base, TimestampMixin):
    """学习项目。"""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ===== 访客归属（演示模式下的轻量隔离）=====
    # None 表示「本机所有者」—— 门禁关闭时创建的本地数据。
    # 门禁开启后，每个访客只能看到 owner_id 等于自己的项目。
    owner_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # ===== 基本信息 =====
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default=ProjectSource.CUSTOM)
    domain: Mapped[str] = mapped_column(String(200), nullable=False, comment="用户输入的学习方向")
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default="入门")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ProjectStatus.LEARNING)

    # ===== 内容字段 =====
    summary: Mapped[str] = mapped_column(Text, default="", comment="项目简介 / 推荐理由")
    background: Mapped[str] = mapped_column(Text, default="", comment="项目背景")
    goals: Mapped[list] = mapped_column(JSON, default=list, comment="实战目标列表")
    core_points: Mapped[list] = mapped_column(JSON, default=list, comment="核心学习知识点")
    # 最终交付物：分条存储，前端可直接渲染为列表（比一整段文字更直观）
    deliverables: Mapped[list] = mapped_column(JSON, default=list, comment="最终交付物清单")
    target_audience: Mapped[str] = mapped_column(Text, default="", comment="适配人群")
    pitfalls: Mapped[str] = mapped_column(Text, default="", comment="常见学习误区")
    # GitHub 项目的 README 摘要，单独存储以便前端折叠展示（展开时回链仓库地址）
    readme_digest: Mapped[str] = mapped_column(Text, default="", comment="README 摘要")

    # ===== GitHub 专有字段 =====
    repo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    repo_full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ===== 关联 =====
    stages: Mapped[list["Stage"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Stage.order_index",
        passive_deletes=True,
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Task.order_index",
        passive_deletes=True,
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Project id={self.id} name={self.name!r} source={self.source}>"
