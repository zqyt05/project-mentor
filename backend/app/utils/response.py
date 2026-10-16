"""统一响应格式与全局异常处理。

规范（PRD 第 8 节）：
- 所有接口统一返回 `{code, message, data}`
- `code == 0` 表示成功，非 0 表示业务/系统错误
- 统一错误处理，返回友好提示而非堆栈
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# ===== 业务错误码约定 =====
CODE_SUCCESS = 0
CODE_BAD_REQUEST = 400
CODE_NOT_FOUND = 404
CODE_LLM_ERROR = 1001  # LLM 调用失败
CODE_GITHUB_ERROR = 1002  # GitHub 接口失败
CODE_CONFIG_ERROR = 1003  # 配置缺失（如未配置 API Key）
CODE_INTERNAL_ERROR = 500


def success(data: Any = None, message: str = "success") -> dict[str, Any]:
    """构造成功响应体。"""
    return {"code": CODE_SUCCESS, "message": message, "data": data}


class BusinessError(Exception):
    """业务异常：由服务层主动抛出，携带用户可读的友好提示。"""

    def __init__(self, message: str, code: int = CODE_BAD_REQUEST) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _json(code: int, message: str, data: Any = None, http_status: int = 200) -> JSONResponse:
    """统一 JSON 响应构造。业务错误仍以 HTTP 200 返回，由 code 字段表达语义。"""
    return JSONResponse(
        status_code=http_status,
        content={"code": code, "message": message, "data": data},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """把所有异常收敛为统一响应格式，避免前端处理多种错误结构。"""

    @app.exception_handler(BusinessError)
    async def _business_error_handler(_request: Request, exc: BusinessError) -> JSONResponse:
        logger.warning("业务异常: %s", exc.message)
        return _json(exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """参数校验失败：提取首个错误，给出可读提示。"""
        errors = exc.errors()
        detail = "请求参数不合法"
        if errors:
            first = errors[0]
            location = ".".join(str(part) for part in first.get("loc", []) if part != "body")
            detail = f"参数校验失败：{location} {first.get('msg', '')}".strip()
        return _json(CODE_BAD_REQUEST, detail)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        code = CODE_NOT_FOUND if exc.status_code == status.HTTP_404_NOT_FOUND else exc.status_code
        # 401 必须回传真实的 HTTP 状态码：前端 axios 拦截器依赖 HTTP 层判断
        # 「演示门禁失效」并跳回登录页。其余错误仍以 HTTP 200 + code 表达，
        # 保持既有契约不变。
        http_status = (
            status.HTTP_401_UNAUTHORIZED
            if exc.status_code == status.HTTP_401_UNAUTHORIZED
            else 200
        )
        return _json(code, message, http_status=http_status)

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        """兜底：记录完整堆栈，但只向用户返回友好提示。"""
        logger.exception("未捕获异常: %s", exc)
        return _json(CODE_INTERNAL_ERROR, "服务内部错误，请稍后重试或查看后端日志")
