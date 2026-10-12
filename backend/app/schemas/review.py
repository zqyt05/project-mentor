"""费曼复盘相关的 Pydantic 模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

ReviewFormType = Literal["structured", "blog", "interview"]


class ReviewGuideOut(BaseModel):
    """复盘引导信息：3 种形式 + 引导性问题。"""

    forms: list[dict] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


class ReviewGenerateRequest(BaseModel):
    """提交用户复盘内容，请求 AI 纠错补全。"""

    project_id: int
    form: ReviewFormType = "structured"
    user_content: str = Field(min_length=1, max_length=20000)


class ReviewOut(ORMModel):
    """复盘结果输出。"""

    id: int
    project_id: int
    form: str
    user_content: str = ""
    final_content: str = ""
    corrections: list[str] = Field(default_factory=list)
    supplements: list[str] = Field(default_factory=list)
    structure_advice: str = ""
    next_steps: list[str] = Field(default_factory=list)
    created_at: datetime
