"""每日 AI 调用计数模型。

## 为什么需要它

DeepSeek 平台**不提供消费上限**功能。把演示环境分享给朋友时，
后端持有的 API Key 会为所有访客的调用付费，一旦链接外泄被陌生人刷，
损失不可控。

既然平台不提供，就在自己的代码里加一道闸：按天统计 AI 调用次数，
超过配置的上限就拒绝新的 AI 请求。相关逻辑见
`app/services/usage_service.py`。
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class DailyUsage(Base, TimestampMixin):
    """按天累计的 AI 调用计数。

    以日期字符串（YYYY-MM-DD）作为主键，每天一行。
    """

    __tablename__ = "daily_usage"

    day: Mapped[str] = mapped_column(
        String(10), primary_key=True, comment="统计日期，格式 YYYY-MM-DD"
    )
    llm_calls: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="当日已发起的 AI 调用次数"
    )
