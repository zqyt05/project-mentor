#!/usr/bin/env bash
# ============================================================================
# 通过 Cloudflare 快速隧道把本机演示服务暴露到公网
#
# 为什么用隧道而不是云平台：
#   本项目的 /api/project/start 实测约 51 秒（LLM 生成 ~14 个任务的 JSON），
#   Vercel(10-60s)、Netlify(10-26s) 这类 Serverless 平台必然超时；
#   Cloudflare 隧道是普通 TCP 代理（上游超时 100s），能跑通。
#
# 前置：
#   1. 已安装 cloudflared：brew install cloudflared
#   2. 已在另一个终端启动演示服务：DEMO_PASSWORD='xxx' ./scripts/serve-demo.sh
#
# 用法：./scripts/share-tunnel.sh
# ============================================================================
set -euo pipefail

PORT="${PORT:-8000}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "❌ 未安装 cloudflared"
  echo "   macOS 安装：brew install cloudflared"
  exit 1
fi

if ! curl -sf -m 5 "http://127.0.0.1:$PORT/api/health" >/dev/null; then
  echo "❌ 本机 $PORT 端口没有可用的演示服务"
  echo "   请先在另一个终端执行：DEMO_PASSWORD='你的口令' ./scripts/serve-demo.sh"
  exit 1
fi

echo "🌐 正在建立 Cloudflare 隧道 → http://127.0.0.1:$PORT"
echo
echo "   稍后终端会打印一个 https://xxxx.trycloudflare.com 地址，"
echo "   把它和你的 DEMO_PASSWORD 一起发给朋友即可。"
echo
echo "   ⚠️  及时把链接和口令分开告知；关闭本终端即断开公网访问。"
echo "   ⚠️  请确认已在 DeepSeek 控制台设置消费上限。"
echo

exec cloudflared tunnel --url "http://127.0.0.1:$PORT"
