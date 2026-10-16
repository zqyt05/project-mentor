"""每日 AI 调用配额。

## 为什么需要它

DeepSeek 平台**不提供消费上限**功能。把演示环境分享给朋友时，
后端持有的 API Key 会为所有访客的调用付费 —— 一旦链接外泄被陌生人刷，
损失不可控。既然平台不提供，就在自己的代码里加一道闸。

## 设计取舍

- **按「实际 LLM 调用次数」计数**，而不是按接口请求数。
  一次「项目匹配」会触发 2–3 次 LLM 调用，一次答疑只有 1 次，
  按接口计数会严重低估真实消耗。
- **全局共享一个额度**，不按访客分配。目标是保护分享者的钱包；
  若按访客分配，10 个朋友就能各用满一份额度，等于没有上限。
- **按「尝试次数」计数**（发起即 +1），不区分成功失败。
  失败重试同样可能产生费用，且这样计数简单、可预期。
- **默认不限制**（上限为 0），保证本地单用户使用行为完全不变。
"""

from datetime import date

from sqlalchemy.orm import Session

from app.config import settings
from app.models.usage import DailyUsage
from app.utils.response import CODE_BAD_REQUEST, BusinessError


def _today() -> str:
    """取本地日期字符串。

    按自然日重置，用本地时区而非 UTC —— 使用者看到「今天额度用完了」
    应该和他手表上的日期一致。
    """
    return date.today().isoformat()


def get_limit() -> int:
    """配置的每日上限。0 表示不限制。"""
    return max(0, settings.DAILY_LLM_CALL_LIMIT)


def get_used(db: Session) -> int:
    """查询今日已用次数。"""
    row = db.get(DailyUsage, _today())
    return row.llm_calls if row else 0


def snapshot(db: Session) -> dict:
    """用量快照，供接口返回与运维查看。"""
    limit = get_limit()
    used = get_used(db)
    return {
        "day": _today(),
        "used": used,
        "limit": limit,
        "remaining": None if limit == 0 else max(0, limit - used),
        "unlimited": limit == 0,
    }


def consume_or_raise(db: Session) -> None:
    """AI 调用前的配额检查：未超限则计数 +1，超限则抛业务异常。

    **注意这里会 commit()。** 前提是调用方在发起 LLM 请求时，
    会话中没有未提交的写入，否则会把半成品提前提交。
    当前四个调用点（项目匹配 / 任务拆解 / 答疑 / 复盘）都满足此前提，
    已逐一确认：
      - 项目匹配：纯 LLM 调用，无 DB 写入
      - 任务拆解：先拆解（LLM）再落库
      - 答疑：用户提问已先行 commit，之后才调用 LLM
      - 复盘：LLM 调用在写入 Review 之前
    后续若在 LLM 调用之前新增 DB 写入，需要重新评估这一点。
    """
    limit = get_limit()
    if limit == 0:  # 未配置上限 → 不限制（本地单用户模式）
        return

    day = _today()
    row = db.get(DailyUsage, day)
    if row is None:
        row = DailyUsage(day=day, llm_calls=0)
        db.add(row)

    if row.llm_calls >= limit:
        raise BusinessError(
            f"今日 AI 试用额度已用完（上限 {limit} 次），请明天再试，"
            "或联系分享者调整额度",
            CODE_BAD_REQUEST,
        )

    row.llm_calls += 1
    db.commit()
