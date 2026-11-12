"""pytest 公共夹具。

设计原则：
1. **完全离线** —— 任何用例都不得触发 LLM 或 GitHub 网络请求，
   因此全部测试在没有 DEEPSEEK_API_KEY 的环境（如 CI）下也能通过。
2. **互不干扰** —— 每个用例独享一个内存 SQLite 库。
3. **不受本地配置影响** —— 见 `_isolate_settings`。
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  导入以触发模型注册
from app.database import Base


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """把所有配置重置为**默认值**，让用例完全不依赖开发者本地的 .env。

    背景：`Settings` 会读取 backend/.env。开发者在本地配置演示相关开关后
    （分享给朋友试用时必然要配），这些值会漏进测试，导致用例莫名失败 ——
    测试结果被本地配置左右。

    这里刻意**逐字段重置为默认值**，而不是只把某几个开关设为空：
    早期版本只处理了 DEMO_PASSWORD，后来新增 DAILY_LLM_CALL_LIMIT 时
    就漏掉了，同样的坑又踩了一次。逐字段重置可以让新增字段自动被覆盖。

    需要开启门禁的用例用 `enable_gate` 夹具显式打开。
    """
    from app.config import Settings, settings

    defaults = Settings(_env_file=None)  # 不读 .env，拿到纯默认值
    for field in Settings.model_fields:
        monkeypatch.setattr(settings, field, getattr(defaults, field))


@pytest.fixture()
def enable_gate(monkeypatch: pytest.MonkeyPatch) -> str:
    """开启演示门禁并返回口令，供门禁相关用例使用。"""
    from app.config import settings

    password = "test-demo-password"
    monkeypatch.setattr(settings, "DEMO_PASSWORD", password)
    return password


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """提供一个内存 SQLite 会话，用例结束后自动销毁。

    使用 StaticPool 让同一内存库在多次连接间共享。
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    session = test_session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    """提供把数据库依赖指向测试库的 HTTP 客户端。

    注意：不使用 `with TestClient(app)`，以避免触发 lifespan 而在真实路径上建库。
    """
    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
