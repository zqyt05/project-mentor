"""项目匹配与生成相关的 Pydantic 模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.base import DIFFICULTY_LEVELS
from app.schemas.common import ORMModel
from app.schemas.task import ProgressOut, StageOut, TaskOut

Difficulty = Literal["入门", "初级", "中级"]


class ProjectMatchRequest(BaseModel):
    """项目匹配请求：学习方向 + 难度。"""

    domain: str = Field(min_length=1, max_length=100, description="学习方向/领域")
    difficulty: Difficulty = Field(default="入门", description="难度：入门/初级/中级")

    @field_validator("domain")
    @classmethod
    def _strip_domain(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("学习方向不能为空")
        return value

    @field_validator("difficulty")
    @classmethod
    def _check_difficulty(cls, value: str) -> str:
        if value not in DIFFICULTY_LEVELS:
            raise ValueError(f"难度必须是 {'/'.join(DIFFICULTY_LEVELS)} 之一")
        return value


class ProjectCandidate(BaseModel):
    """项目卡片：匹配结果中的单个候选项目。"""

    name: str = Field(description="项目名称")
    source: Literal["github", "custom"] = Field(description="项目来源标签")
    difficulty: str = "入门"
    summary: str = Field(default="", description="项目简介/推荐理由（2-3 句话）")
    background: str = Field(default="", description="项目背景")
    goals: list[str] = Field(default_factory=list, description="实战目标")
    core_points: list[str] = Field(default_factory=list, description="核心学习点（3-5 个关键词）")
    deliverables: list[str] = Field(default_factory=list, description="最终交付物清单")
    target_audience: str = Field(default="", description="适配人群")
    pitfalls: str = Field(default="", description="常见学习误区")
    match_reason: str = Field(default="", description="难度匹配度 / 排序依据")

    # GitHub 项目额外展示字段
    repo_url: str | None = None
    repo_full_name: str | None = None
    stars: int | None = None
    language: str | None = None


class ProjectMatchResponse(BaseModel):
    """项目匹配响应：命中路径 + 候选项目列表。"""

    path: Literal["github", "custom"]
    route_reason: str = Field(default="", description="领域路由说明")
    projects: list[ProjectCandidate] = Field(default_factory=list)


class ProjectStartRequest(BaseModel):
    """开始学习：把选中的候选项目落库并拆解为阶段任务。"""

    domain: str
    difficulty: Difficulty = "入门"
    project: ProjectCandidate


class ProjectBrief(ORMModel):
    """项目列表项。"""

    id: int
    name: str
    source: str
    domain: str
    difficulty: str
    status: str
    summary: str = ""
    deliverables: list[str] = Field(default_factory=list)
    repo_url: str | None = None
    repo_full_name: str | None = None
    stars: int | None = None
    language: str | None = None
    created_at: datetime
    progress: ProgressOut | None = None


class ProjectDetail(ProjectBrief):
    """项目详情：含完整内容与阶段任务时间线。"""

    background: str = ""
    readme_digest: str = Field(default="", description="GitHub 项目 README 摘要")
    goals: list[str] = Field(default_factory=list)
    core_points: list[str] = Field(default_factory=list)
    target_audience: str = ""
    pitfalls: str = ""
    stages: list[StageOut] = Field(default_factory=list)
    tasks: list[TaskOut] = Field(default_factory=list, description="按顺序展开的全部任务")


class TaskDecomposeRequest(BaseModel):
    """重新拆解项目（保留给后续迭代，MVP 主流程在 start 时自动拆解）。"""

    project_id: int
