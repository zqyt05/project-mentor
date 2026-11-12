# ============================================================================
# ProjectMentor 生产镜像
#
# 两阶段构建：
#   1. node 阶段构建前端静态产物
#   2. python 阶段装后端依赖，并把前端产物一并带上，由后端同源托管
#      （前后端同源 ⇒ 前端 baseURL='/api' 无需改动，也不涉及 CORS）
#
# 用法：
#   docker compose up -d --build
#
# 注意：镜像内**不含 .env**。密钥通过 compose 的 env_file / environment
# 在运行时注入，避免把 API Key 烘进镜像层（镜像层可被任何拿到镜像的人读取）。
# ============================================================================

# ---------------------------------------------------------------------------
# 阶段 1：构建前端
# ---------------------------------------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /build

# 先只拷贝依赖清单，让依赖安装单独成层 —— 只要依赖没变，改代码时无需重装
COPY frontend/package.json frontend/pnpm-lock.yaml* frontend/pnpm-workspace.yaml ./

# 启用 corepack 以使用与开发环境一致的 pnpm 版本
RUN corepack enable \
    && corepack prepare pnpm@11 --activate

# 注意：pnpm-workspace.yaml 里把 rollup 换成了 wasm 版本，
# 那原本是为规避 macOS Hardened Runtime 的限制。Linux 上不需要，
# 但 wasm 版本是可移植的等价实现，保留它可以保证各环境行为一致。
RUN pnpm install --frozen-lockfile || pnpm install

COPY frontend/ ./
RUN pnpm build


# ---------------------------------------------------------------------------
# 阶段 2：运行时（后端 + 前端产物）
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# 不生成 .pyc、不缓冲输出（日志能立刻出现在 docker logs 里）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////data/projectmentor.db \
    SERVE_FRONTEND=1 \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

# 先装依赖，利用镜像层缓存
COPY backend/requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# 后端代码（.dockerignore 已排除 .venv / .env / *.db）
COPY backend/app ./app

# 前端产物：放在后端期望的位置（backend 的上一级 frontend/dist）
COPY --from=frontend /build/dist /frontend/dist

# 数据目录：SQLite 落在这里，compose 把它挂成命名卷
RUN mkdir -p /data \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app /data /frontend

USER appuser

EXPOSE 8000

# 用 Python 做健康检查（slim 镜像不带 curl）
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"

# 生产不用 --reload
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
