#!/usr/bin/env bash
# ============================================================================
# 停止演示服务（以及可选的开发服务）
#
# 什么时候用：
#   - 启动时提示「端口已被占用」，想先把旧的关掉
#   - 朋友试完了，想收工
#   - 服务卡住了，想干净重启
#
# 用法：
#   ./scripts/stop-demo.sh          只停演示服务（8000）
#   ./scripts/stop-demo.sh --all    连开发服务（5173）一起停
# ============================================================================
set -uo pipefail

STOP_FRONTEND=0
[[ "${1:-}" == "--all" ]] && STOP_FRONTEND=1

stop_port() {
  local port="$1" label="$2"
  local pids
  pids="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"

  if [[ -z "$pids" ]]; then
    echo "⚪ ${label}（端口 ${port}）：本来就没在运行"
    return 0
  fi

  local count
  count="$(echo "$pids" | wc -l | tr -d ' ')"
  echo "🛑 ${label}（端口 ${port}）：发现 ${count} 个进程，正在停止…"

  # 先礼后兵：SIGTERM 让程序自己收尾（关数据库连接、写日志）
  echo "$pids" | xargs kill 2>/dev/null || true
  sleep 3

  # 3 秒后还没退，再强制结束
  local remain
  remain="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [[ -n "$remain" ]]; then
    echo "   进程没有响应，强制结束…"
    echo "$remain" | xargs kill -9 2>/dev/null || true
    sleep 1
  fi

  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "   ❌ 端口 ${port} 仍被占用，请手动检查：lsof -nP -iTCP:${port} -sTCP:LISTEN"
    return 1
  fi
  echo "   ✅ 端口 ${port} 已释放"
}

echo "=== 停止服务 ==="
echo

failed=0
stop_port 8000 "演示/后端服务" || failed=1
if [[ "$STOP_FRONTEND" == "1" ]]; then
  stop_port 5173 "前端开发服务器" || failed=1
fi

echo
if [[ "$failed" == "1" ]]; then
  echo "⚠️  有端口未能释放，请按上面的提示手动处理"
  exit 1
fi

echo "✅ 已全部停止"
echo
echo "   隧道（cloudflared）不受本脚本影响 —— 请到它所在的终端窗口按 Control + C，"
echo "   或直接关掉那个窗口。"
