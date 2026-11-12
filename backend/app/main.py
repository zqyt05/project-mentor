"""ProjectMentor 后端服务入口。

FastAPI 应用装配：
- 统一响应格式 `{code, message, data}` 与全局异常处理
- CORS（供 Vite 开发服务器跨域调用）
- 启动时自动建表
- 自动生成 OpenAPI 文档：http://127.0.0.1:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, chat, project, review, task
from app.config import BASE_DIR, settings
from app.database import init_db
from app.services.github_service import get_github_service
from app.utils.response import register_exception_handlers, success

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期：启动建表，关闭时释放 HTTP 连接池。"""
    init_db()
    logger.info("数据库初始化完成：%s", settings.DATABASE_URL)
    logger.info("DeepSeek 模型：%s", settings.DEEPSEEK_MODEL)
    if not settings.DEEPSEEK_API_KEY:
        logger.warning("未配置 DEEPSEEK_API_KEY，AI 相关接口将不可用")
    if not settings.GITHUB_TOKEN:
        logger.warning("未配置 GITHUB_TOKEN，GitHub 检索速率限制较低")
    if settings.DEMO_PASSWORD:
        logger.info("演示门禁：已开启（访客数据互相隔离）")
    else:
        logger.info("演示门禁：未开启（本地单用户模式）")
    if settings.DAILY_LLM_CALL_LIMIT > 0:
        logger.info("每日 AI 调用上限：%s 次（超出后拒绝新的 AI 请求）",
                    settings.DAILY_LLM_CALL_LIMIT)
    else:
        logger.info("每日 AI 调用上限：未设置（AI 调用不受限制）")
    yield
    await get_github_service().aclose()
    logger.info("服务已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ProjectMentor —— PBL 项目制 AI 实战导师后端服务",
    lifespan=lifespan,
)

# 跨域配置：允许本地前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 统一异常处理
register_exception_handlers(app)

# 注册业务路由
app.include_router(auth.router)
app.include_router(project.router)
app.include_router(task.router)
app.include_router(chat.router)
app.include_router(review.router)


@app.get("/api/health", tags=["系统"], summary="健康检查")
def health() -> dict:
    """供前端启动时探测后端是否可用。"""
    return success(
        {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "model": settings.DEEPSEEK_MODEL,
            "llm_configured": bool(settings.DEEPSEEK_API_KEY),
            "github_configured": bool(settings.GITHUB_TOKEN),
        }
    )


# ==========================================================================
# 前端静态托管（生产同源部署）
# ==========================================================================
# 开启后前后端同源：前端 `baseURL='/api'` 无需改动，也完全不涉及 CORS。
# 必须放在所有 API 路由之后注册，否则通配路由会抢走 /api 请求。
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

if settings.SERVE_FRONTEND:
    if not (FRONTEND_DIST / "index.html").exists():
        logger.warning(
            "已开启 SERVE_FRONTEND，但未找到前端构建产物：%s（请先执行 pnpm build）",
            FRONTEND_DIST,
        )
    else:
        app.mount(
            "/assets",
            StaticFiles(directory=FRONTEND_DIST / "assets"),
            name="assets",
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str) -> FileResponse:
            """SPA 回退：前端路由（如 /project/1/overview）刷新时仍返回 index.html。

            注意必须放行 /api —— 否则不存在的接口会返回 HTML，
            前端解析 JSON 失败会得到难以排查的报错。
            """
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="接口不存在")

            # 优先返回真实存在的静态文件（favicon 等）
            candidate = (FRONTEND_DIST / full_path).resolve()
            if (
                full_path
                and candidate.is_file()
                and candidate.is_relative_to(FRONTEND_DIST.resolve())
            ):
                return FileResponse(candidate)

            return FileResponse(FRONTEND_DIST / "index.html")

        logger.info("前端静态托管已开启：%s", FRONTEND_DIST)


if __name__ == "__main__":  # pragma: no cover - 本地调试入口
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
