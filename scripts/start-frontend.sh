#!/usr/bin/env bash
#
# 启动 ProjectMentor 前端（Vite 开发服务器）。
#
# 会依次完成：
#   1. 定位 Node.js（优先用系统 PATH，其次回退到 DSH 自带 Node）
#   2. 定位 pnpm（同上）
#   3. 首次运行时自动 pnpm install
#   4. 启动 vite，监听 127.0.0.1:5173
#
# 用法：
#   ./scripts/start-frontend.sh
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "==> ProjectMentor 前端启动中"

# ---------- 1. 定位 Node.js ----------
NODE_BIN=""
if command -v node >/dev/null 2>&1; then
  NODE_BIN="$(command -v node)"
  echo "    Node: $NODE_BIN (系统安装) $("$NODE_BIN" --version)"
else
  # 回退：使用 DeepSeek Harness 自带的 Node
  DSH_NODE_DIR="/Users/chloe/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/node/bin"
  if [[ -x "$DSH_NODE_DIR/node" ]]; then
    NODE_BIN="$DSH_NODE_DIR/node"
    echo "    Node: $NODE_BIN (DSH 自带) $("$NODE_BIN" --version)"
  fi
fi

if [[ -z "$NODE_BIN" ]]; then
  echo "❌ 未找到 Node.js"
  echo
  echo "请任选一种方式安装："
  echo "  brew install node                 # 推荐，你已安装 Homebrew"
  echo "  或到 https://nodejs.org 下载 LTS 版本"
  exit 1
fi

NODE_DIR="$(dirname "$NODE_BIN")"

# ---------- 2. 定位 pnpm ----------
# 说明：pnpm 本质是一个 JS 脚本，用 node 直接执行即可，不一定需要全局安装
PNPM_CMD=()
if command -v pnpm >/dev/null 2>&1; then
  PNPM_CMD=("$(command -v pnpm)")
  echo "    pnpm: $(command -v pnpm) (系统安装)"
else
  DSH_PNPM="/Users/chloe/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/pnpm/bin/pnpm.mjs"
  if [[ -f "$DSH_PNPM" ]]; then
    PNPM_CMD=("$NODE_BIN" "$DSH_PNPM")
    echo "    pnpm: $DSH_PNPM (DSH 自带)"
  else
    echo "⚠️  未找到 pnpm，尝试用 corepack 启用"
    if "$NODE_BIN" -e "require('corepack')" >/dev/null 2>&1; then
      PNPM_CMD=("$NODE_BIN" "$(command -v corepack)")
    else
      echo "❌ 未找到 pnpm。请执行：npm install -g pnpm"
      exit 1
    fi
  fi
fi

cd "$FRONTEND_DIR"

# ---------- 3. 安装依赖（首次运行） ----------
if [[ ! -d node_modules ]]; then
  echo "==> 首次运行，正在安装前端依赖（约 1-2 分钟）"
  # 说明：缓存目录指向仓库内，避免依赖用户主目录的可写权限
  "${PNPM_CMD[@]}" install \
    --config.store-dir="$ROOT_DIR/.pnpm-store" \
    --config.cache-dir="$ROOT_DIR/.npm-cache"
  echo "==> 依赖安装完成"
fi

# ---------- 4. 检查后端是否已启动 ----------
if ! curl -s -m 3 -o /dev/null http://127.0.0.1:8000/api/health 2>/dev/null; then
  echo "⚠️  后端 (127.0.0.1:8000) 似乎未启动，页面能打开但数据会加载失败。"
  echo "    请另开一个终端执行：./scripts/start-backend.sh"
  echo
fi

# ---------- 5. 启动 ----------
echo "==> 启动 Vite 开发服务器"
echo "    界面地址: http://127.0.0.1:5173"
echo "    按 Ctrl+C 停止"
echo

export PATH="$NODE_DIR:$PATH"
exec "${PNPM_CMD[@]}" dev
