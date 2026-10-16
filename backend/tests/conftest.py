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
    """把演示开关固定为「关闭」，让用例不依赖开发者本地的 .env。

    背景：`Settings` 会读取 backend/.env。一旦开发者在本地配了
    DEMO_PASSWORD（分享给朋友试用时必然要配），门禁就会在测试里也生效，
    所有契约用例都会收到 401 而莫名失败 —— 测试结果被本地配置左右。

    需要测试门禁开启行为的用例，用 `enable_gate` 夹具显式打开。
    """
    from app.config import settings

    monkeypatch.setattr(settings, "DEMO_PASSWORD", "")
    monkeypatch.setattr(settings, "SERVE_FRONTEND", False)


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
