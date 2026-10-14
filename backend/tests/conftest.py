"""pytest 公共夹具。

设计原则：
1. **完全离线** —— 任何用例都不得触发 LLM 或 GitHub 网络请求，
   因此全部测试在没有 DEEPSEEK_API_KEY 的环境（如 CI）下也能通过。
2. **互不干扰** —— 每个用例独享一个内存 SQLite 库。
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  导入以触发模型注册
from app.database import Base


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
