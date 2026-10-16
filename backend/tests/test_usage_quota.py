"""每日 AI 调用配额的单元测试。

背景：DeepSeek 平台不提供消费上限，因此在后端自行加一道闸。
这些用例保证：默认不限制（本地模式不受影响）、超限拒绝、按天重置。
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.usage import DailyUsage
from app.services import usage_service


class TestUnlimitedByDefault:
    """未配置上限时完全放行 —— 本地单用户使用行为不能变。"""

    def test_limit_zero_means_unlimited(self, db: Session) -> None:
        assert usage_service.get_limit() == 0
        for _ in range(50):
            usage_service.consume_or_raise(db)  # 不应抛异常
        assert usage_service.get_used(db) == 0  # 不限制时不计数

    def test_snapshot_reports_unlimited(self, db: Session) -> None:
        snap = usage_service.snapshot(db)
        assert snap["unlimited"] is True
        assert snap["remaining"] is None


class TestQuotaEnforcement:
    """配置上限后：计数、拒绝、剩余量都正确。"""

    def test_consume_increments(self, db: Session, monkeypatch) -> None:
        from app.config import settings

        monkeypatch.setattr(settings, "DAILY_LLM_CALL_LIMIT", 5)
        usage_service.consume_or_raise(db)
        usage_service.consume_or_raise(db)
        assert usage_service.get_used(db) == 2

    def test_rejected_after_limit(self, db: Session, monkeypatch) -> None:
        from app.config import settings
        from app.utils.response import BusinessError

        monkeypatch.setattr(settings, "DAILY_LLM_CALL_LIMIT", 3)
        for _ in range(3):
            usage_service.consume_or_raise(db)

        try:
            usage_service.consume_or_raise(db)
            raise AssertionError("第 4 次调用本应被拒绝")
        except BusinessError as exc:
            assert "额度已用完" in exc.message
            assert "3" in exc.message  # 提示里应带上限数字

    def test_rejected_call_does_not_increment(self, db: Session, monkeypatch) -> None:
        """被拒绝的调用不能再累加计数，否则额度会被越顶越高。"""
        from app.config import settings
        from app.utils.response import BusinessError

        monkeypatch.setattr(settings, "DAILY_LLM_CALL_LIMIT", 2)
        usage_service.consume_or_raise(db)
        usage_service.consume_or_raise(db)
        for _ in range(5):
            try:
                usage_service.consume_or_raise(db)
            except BusinessError:
                pass
        assert usage_service.get_used(db) == 2

    def test_snapshot_remaining(self, db: Session, monkeypatch) -> None:
        from app.config import settings

        monkeypatch.setattr(settings, "DAILY_LLM_CALL_LIMIT", 10)
        usage_service.consume_or_raise(db)
        snap = usage_service.snapshot(db)
        assert snap["used"] == 1
        assert snap["limit"] == 10
        assert snap["remaining"] == 9
        assert snap["unlimited"] is False

    def test_remaining_never_negative(self, db: Session, monkeypatch) -> None:
        from app.config import settings

        monkeypatch.setattr(settings, "DAILY_LLM_CALL_LIMIT", 2)
        usage_service.consume_or_raise(db)
        usage_service.consume_or_raise(db)
        assert usage_service.snapshot(db)["remaining"] == 0


class TestDailyReset:
    """按自然日重置：新的一天额度重新计算。"""

    def test_yesterday_usage_does_not_count(self, db: Session, monkeypatch) -> None:
        from app.config import settings

        monkeypatch.setattr(settings, "DAILY_LLM_CALL_LIMIT", 3)
        # 手工塞一条「昨天」的记录
        db.add(DailyUsage(day="2000-01-01", llm_calls=999))
        db.commit()

        assert usage_service.get_used(db) == 0  # 今天还没用过
        usage_service.consume_or_raise(db)  # 不应因为昨天用满而被拒
        assert usage_service.get_used(db) == 1

    def test_one_row_per_day(self, db: Session, monkeypatch) -> None:
        from app.config import settings

        monkeypatch.setattr(settings, "DAILY_LLM_CALL_LIMIT", 10)
        usage_service.consume_or_raise(db)
        usage_service.consume_or_raise(db)
        rows = db.query(DailyUsage).all()
        assert len(rows) == 1  # 同一天只应有一行
        assert rows[0].llm_calls == 2


class TestUsageEndpoint:
    """用量查询接口。"""

    def test_usage_available_when_gate_disabled(self, client: TestClient) -> None:
        body = client.get("/api/auth/usage").json()
        assert body["code"] == 0
        assert body["data"]["unlimited"] is True

    def test_usage_requires_login_when_gate_enabled(
        self, client: TestClient, enable_gate: str
    ) -> None:
        assert client.get("/api/auth/usage").status_code == 401

    def test_usage_after_login(self, client: TestClient, enable_gate: str) -> None:
        client.post("/api/auth/login", json={"password": enable_gate})
        body = client.get("/api/auth/usage").json()
        assert body["code"] == 0
        assert "used" in body["data"]
