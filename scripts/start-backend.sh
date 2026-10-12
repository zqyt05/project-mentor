#!/usr/bin/env bash
#
# 启动 ProjectMentor 后端（FastAPI）。
#
# 会依次完成：
#   1. 定位 Python 虚拟环境（backend/.venv）
#   2. 检查 backend/.env 是否存在且已填写 DEEPSEEK_API_KEY
#   3. 启动 uvicorn，监听 127.0.0.1:8000
#
# 用法：
#   ./scripts/start-backend.sh            # 带热重载（开发用）
#   ./scripts/start-backend.sh --no-reload # 关闭热重载
#
set -euo pipefail

# 项目根目录（脚本所在目录的上一级）
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"

RELOAD="--reload"
if [[ "${1:-}" == "--no-reload" ]]; then
  RELOAD=""
fi

echo "==> ProjectMentor 后端启动中"

# ---------- 1. 检查虚拟环境 ----------
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "❌ 未找到虚拟环境：$VENV_DIR"
  echo
  echo "请先创建虚拟环境并安装依赖："
  echo "  cd backend"
  echo "  python3.11 -m venv .venv          # 需要 Python 3.11"
  echo "  source .venv/bin/activate"
  echo "  pip install -r requirements.txt"
  exit 1
fi

PYTHON="$VENV_DIR/bin/python"
echo "    Python: $($PYTHON --version 2>&1)  ($VENV_DIR)"

# ---------- 2. 检查环境变量 ----------
if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  echo "❌ 未找到 $BACKEND_DIR/.env"
  echo
  echo "请先创建并填写："
  echo "  cp .env.example backend/.env"
  echo "  然后填入 DEEPSEEK_API_KEY"
  exit 1
fi

if ! grep -qE '^DEEPSEEK_API_KEY=.+' "$BACKEND_DIR/.env" \
   || grep -qE '^DEEPSEEK_API_KEY=your_' "$BACKEND_DIR/.env"; then
  echo "⚠️  backend/.env 中的 DEEPSEEK_API_KEY 似乎还没填写，AI 接口会不可用"
fi

# ---------- 3. 检查端口占用 ----------
if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "⚠️  端口 8000 已被占用，后端可能已经在运行。"
  echo "    查看或停止：lsof -nP -iTCP:8000 -sTCP:LISTEN"
  echo "    如需换端口：修改本脚本末尾的 --port，并同步修改 frontend/vite.config.ts"
  exit 1
fi

# ---------- 4. 启动 ----------
cd "$BACKEND_DIR"
echo "    接口文档: http://127.0.0.1:8000/docs"
echo "    健康检查: http://127.0.0.1:8000/api/health"
echo "    按 Ctrl+C 停止"
echo

exec "$PYTHON" -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  $RELOAD
