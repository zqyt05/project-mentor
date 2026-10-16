#!/usr/bin/env bash
# ============================================================================
# 检查 DeepSeek API Key 是否可用
#
# 改完 backend/.env 里的 key 之后跑一下，确认真的能通，而不是等服务报错才发现。
# 会做两件事：① 检查格式；② 真的发一次极小的请求试探服务端。
# 全程不会打印你的 key。
#
# 用法：./scripts/check-key.sh
# ============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/backend/.env"
PYTHON="$ROOT/backend/.venv/bin/python"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ 找不到配置文件：$ENV_FILE"
  exit 1
fi

if [[ ! -x "$PYTHON" ]]; then
  echo "❌ 找不到 Python 环境：$PYTHON"
  exit 1
fi

"$PYTHON" - "$ENV_FILE" <<'PY'
"""读取 .env 中的 DeepSeek 配置并做一次真实的可用性探测。"""
import sys
from pathlib import Path

import httpx

env_path = Path(sys.argv[1])
values: dict[str, str] = {}
for raw in env_path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, _, value = line.partition("=")
    values[key.strip()] = value.strip()

api_key = values.get("DEEPSEEK_API_KEY", "")
base_url = values.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
model = values.get("DEEPSEEK_MODEL", "deepseek-flash")

print("① 格式检查")
if not api_key:
    print("   ❌ DEEPSEEK_API_KEY 是空的")
    print("      请在 backend/.env 里填写：DEEPSEEK_API_KEY=sk-你的新key")
    sys.exit(1)

problems = []
if not api_key.startswith("sk-"):
    problems.append("不是以 sk- 开头（可能复制错了）")
if api_key != api_key.strip():
    problems.append("首尾有多余空格")
if '"' in api_key or "'" in api_key:
    problems.append("被引号包住了（.env 里不要加引号）")
if len(api_key) < 20:
    problems.append(f"长度只有 {len(api_key)}，看起来不完整")

if problems:
    for problem in problems:
        print(f"   ❌ {problem}")
    print(f"      当前长度 {len(api_key)}，末四位 …{api_key[-4:]}")
    sys.exit(1)

print(f"   ✅ 格式正常（长度 {len(api_key)}，末四位 …{api_key[-4:]}）")
print(f"   ℹ️  接口地址：{base_url}")
print(f"   ℹ️  模型：{model}")

print()
print("② 实际连通性测试（会真实调用一次，消耗极少 token）")
try:
    response = httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": "回复 ok"}],
            "max_tokens": 16,
        },
        timeout=60,
    )
except httpx.RequestError as exc:
    print(f"   ❌ 连不上服务器：{exc}")
    print("      检查网络，或确认 DEEPSEEK_BASE_URL 填对了")
    sys.exit(1)

if response.status_code == 200:
    print("   ✅ 调用成功 —— 这个 key 可以用")
    sys.exit(0)

hints = {
    401: "key 无效或已被删除/过期，请到 DeepSeek 控制台重新生成",
    402: "账户余额不足，请先充值",
    403: "key 没有调用该模型的权限",
    429: "触发限流，稍后再试",
    500: "DeepSeek 服务端异常，稍后再试",
    503: "DeepSeek 服务暂时不可用，稍后再试",
}
detail = ""
try:
    body = response.json()
    detail = body.get("error", {}).get("message") or body.get("message") or ""
except Exception:
    detail = response.text[:120]

print(f"   ❌ 调用失败（HTTP {response.status_code}）")
if detail:
    print(f"      服务端说：{detail}")
hint = hints.get(response.status_code)
if hint:
    print(f"      → {hint}")
sys.exit(1)
PY
