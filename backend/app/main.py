"""ProjectMentor 后端服务入口。

FastAPI 应用装配：
- 统一响应格式 `{code, message, data}` 与全局异常处理
- CORS（供 Vite 开发服务器跨域调用）
- 启动时自动建表
- 自动生成 OpenAPI 文档：http://127.0.0.1:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, project, review, task
from app.config import settings
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


if __name__ == "__main__":  # pragma: no cover - 本地调试入口
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
