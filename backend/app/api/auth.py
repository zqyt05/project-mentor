"""演示门禁接口。

路径前缀：/api/auth

门禁未开启（未配置 DEMO_PASSWORD）时，`/me` 返回 `required=false`，
前端据此直接进入应用，行为与本地单用户模式完全一致。
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel, Field

from app.services import auth_service
from app.utils.response import BusinessError, success

router = APIRouter(prefix="/api/auth", tags=["演示门禁"])


class LoginRequest(BaseModel):
    """口令登录请求。"""

    password: str = Field(..., description="演示访问口令")


@router.get("/me", summary="查询当前访客状态")
def me(
    pm_visitor: Annotated[str | None, Cookie()] = None,
) -> dict:
    """前端启动时调用：判断是否需要登录、当前是否已登录。

    刻意不抛 401 —— 这是「探测状态」的接口，未登录是正常返回值之一，
    抛错会让前端难以区分「门禁未开启」和「未登录」。
    """
    required = auth_service.is_gate_enabled()
    visitor_id = auth_service.parse_token(pm_visitor) if required else None
    return success(
        {
            "required": required,
            "authenticated": (not required) or visitor_id is not None,
            # 只回传短标识用于界面展示，不暴露完整 ID
            "visitor_label": visitor_id[:6] if visitor_id else None,
        }
    )


@router.post("/login", summary="使用演示口令登录")
def login(payload: LoginRequest, response: Response) -> dict:
    """校验口令并签发访客身份 Cookie。"""
    if not auth_service.is_gate_enabled():
        # 门禁未开启时不做任何事，保持本地模式的可用性
        return success({"required": False}, message="当前未开启演示门禁")

    if not auth_service.verify_password(payload.password):
        raise BusinessError("口令不正确", code=401)

    visitor_id = auth_service.issue_visitor(response)
    return success(
        {
            "required": True,
            "authenticated": True,
            "visitor_label": visitor_id[:6],
        },
        message="验证通过",
    )


@router.post("/logout", summary="退出演示身份")
def logout(response: Response) -> dict:
    """清除访客 Cookie。注意：清除后将失去对自己项目的访问（详见 README）。"""
    auth_service.clear_visitor(response)
    return success({"authenticated": False}, message="已退出")
