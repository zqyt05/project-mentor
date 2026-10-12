"""Pydantic 请求 / 响应模型公共定义。"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    """可直接由 SQLAlchemy 对象转换的响应模型基类。"""

    model_config = ConfigDict(from_attributes=True)


class ApiResponse(BaseModel, Generic[T]):
    """统一响应结构 `{code, message, data}`（用于 OpenAPI 文档描述）。"""

    code: int = 0
    message: str = "success"
    data: T | None = None


class PageResult(BaseModel):
    """分页结果占位结构，MVP 阶段数据量小，暂不做复杂分页。"""

    total: int = 0
    items: list[Any] = []
