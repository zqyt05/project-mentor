"""ORM 模型公共基类与枚举定义。"""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """返回带时区的当前 UTC 时间，作为模型默认时间戳。"""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """为模型统一附加创建时间 / 更新时间字段。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


# ===== 枚举常量 =====
# 说明：为兼容 SQLite 并保持可读性，枚举以字符串形式落库，
# 取值统一在此处定义，业务层与 schema 层共同引用，避免魔法字符串。


class ProjectSource:
    """项目来源：GitHub 开源项目 / AI 定制项目。"""

    GITHUB = "github"
    CUSTOM = "custom"


class ProjectStatus:
    """项目学习状态。"""

    LEARNING = "learning"  # 学习中
    REVIEWING = "reviewing"  # 已进入复盘环节
    COMPLETED = "completed"  # 复盘完成，闭环结束


class TaskStatus:
    """任务状态：未开始 / 进行中 / 已完成。"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class MessageRole:
    """对话角色。"""

    USER = "user"
    ASSISTANT = "assistant"


class ConversationScope:
    """对话作用域：绑定单个任务 / 绑定项目复盘。"""

    TASK = "task"
    REVIEW = "review"


class ReviewForm:
    """费曼复盘输出形式。"""

    STRUCTURED = "structured"  # 结构化技术总结文档
    BLOG = "blog"  # 项目复盘博客
    INTERVIEW = "interview"  # 面试口述提纲


DIFFICULTY_LEVELS = ("入门", "初级", "中级")
