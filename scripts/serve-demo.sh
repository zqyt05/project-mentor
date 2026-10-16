#!/usr/bin/env bash
# ============================================================================
# 演示模式启动脚本（生产同源：后端同时托管前端构建产物）
#
# 与 start-backend.sh 的区别：
#   - 关闭 --reload（生产不该用开发服务器）
#   - 开启 SERVE_FRONTEND，前后端同源 ⇒ 零 CORS、前端 baseURL 无需改动
#   - 监听 0.0.0.0，便于隧道/容器访问
#
# 前置：已构建前端（pnpm build）
# 用法：DEMO_PASSWORD='你的口令' ./scripts/serve-demo.sh
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

PYTHON="$ROOT/backend/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "❌ 未找到虚拟环境：$PYTHON"
  echo "   请先在 backend/ 下创建：uv venv && uv pip install -r requirements.txt"
  exit 1
fi

# 前端构建产物必须存在，否则页面会 404
if [[ ! -f "$ROOT/frontend/dist/index.html" ]]; then
  echo "❌ 未找到前端构建产物：frontend/dist/index.html"
  echo "   请先构建：cd frontend && pnpm build"
  exit 1
fi

PORT="${PORT:-8000}"

if [[ -n "${DEMO_PASSWORD:-}" ]]; then
  echo "🔐 演示门禁：已开启（访客数据互相隔离）"
else
  echo "⚠️  演示门禁：未开启 —— 任何拿到链接的人都能使用，且共用同一份数据"
  echo "   如需对外分享，请设置 DEMO_PASSWORD"
fi

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "❌ 端口 $PORT 已被占用，请先停止占用进程或改用 PORT=8001"
  exit 1
fi

echo "🚀 启动演示服务：http://0.0.0.0:$PORT"
echo "   接口文档：http://127.0.0.1:$PORT/docs"
echo "   按 Ctrl+C 停止"
echo

# SERVE_FRONTEND=1 让后端托管 frontend/dist
exec env SERVE_FRONTEND=1 DEMO_PASSWORD="${DEMO_PASSWORD:-}" \
  "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
