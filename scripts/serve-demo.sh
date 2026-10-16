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

# 口令来源优先级：命令行环境变量 > backend/.env > 无门禁
#
# 注意：不能写 `DEMO_PASSWORD="${DEMO_PASSWORD:-}"` 去「兜底」——
# 那会在命令行未传时向子进程注入一个**空字符串**，
# 而环境变量的优先级高于 .env，结果反而把 .env 里配好的口令覆盖成空，
# 门禁静默关闭。因此这里只在命令行确实传了值时才 export。
if [[ -z "${DEMO_PASSWORD:-}" ]]; then
  DEMO_PASSWORD="$(grep -E '^DEMO_PASSWORD=' "$ROOT/backend/.env" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r' | sed 's/^["'"'"']//; s/["'"'"']$//')"
  if [[ -n "$DEMO_PASSWORD" ]]; then
    echo "🔐 演示门禁：从 backend/.env 读取到口令"
  fi
fi

if [[ -n "${DEMO_PASSWORD:-}" ]]; then
  export DEMO_PASSWORD
  echo "🔐 演示门禁：已开启（访客数据互相隔离）"
else
  echo "⚠️  演示门禁：未开启 —— 任何拿到链接的人都能使用，且共用同一份数据"
  echo "   如需对外分享，请在 backend/.env 设置 DEMO_PASSWORD，或直接传参："
  echo "   DEMO_PASSWORD='你的口令' ./scripts/serve-demo.sh"
fi

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "❌ 端口 $PORT 已被占用 —— 已经有一个服务在跑（可能是上次忘了关）。"
  echo
  echo "   当前占用者："
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | tail -n +2 | awk '{print "     PID " $2 "  " $1}' | sort -u
  echo
  echo "   如果那个服务就是你想要的（演示模式），直接用即可，不必重启。"
  echo "   想重新启动，先关掉旧的："
  echo "     ./scripts/stop-demo.sh"
  echo
  echo "   或者换个端口启动："
  echo "     PORT=8001 ./scripts/serve-demo.sh"
  exit 1
fi

echo "🚀 启动演示服务：http://0.0.0.0:$PORT"
echo "   接口文档：http://127.0.0.1:$PORT/docs"
echo "   按 Ctrl+C 停止"
echo

# SERVE_FRONTEND=1 让后端托管 frontend/dist（前后端同源 ⇒ 零 CORS）
# DEMO_PASSWORD 已在上面按优先级解析并 export，这里不再重复注入
export SERVE_FRONTEND=1
exec "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
