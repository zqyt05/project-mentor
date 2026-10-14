"""任务与阶段相关的 Pydantic 模型。"""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class TaskOut(ORMModel):
    """任务输出模型。"""

    id: int
    project_id: int
    stage_id: int
    order_index: int
    name: str
    description: str = ""
    knowledge_points: list[str] = Field(default_factory=list)
    deliverable_criteria: str = ""
    ddl_days: int = 1
    due_date: date | None = None
    status: str = "todo"
    started_at: datetime | None = None
    completed_at: datetime | None = None


class StageOut(ORMModel):
    """阶段输出模型，内嵌任务列表。"""

    id: int
    project_id: int
    order_index: int
    name: str
    description: str = ""
    is_milestone: bool = True
    tasks: list[TaskOut] = Field(default_factory=list)


class TaskUpdateRequest(BaseModel):
    """任务更新请求（支持手动调整 DDL、任务名、描述）。"""

    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    due_date: date | None = None
    status: str | None = Field(default=None, pattern="^(todo|in_progress|done)$")
    knowledge_points: list[str] | None = None
    deliverable_criteria: str | None = None


class ProgressOut(BaseModel):
    """项目整体进度。"""

    total: int = 0
    done: int = 0
    in_progress: int = 0
    todo: int = 0
    percent: int = 0
    current_task_id: int | None = None
    all_completed: bool = False
