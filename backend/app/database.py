"""数据库连接与会话管理。

使用 SQLite + SQLAlchemy 2.0 ORM：
- SQLite 轻量、无需额外部署，适合单用户本地使用场景（MVP 范围）
- `check_same_thread=False` 允许 FastAPI 多线程访问同一连接
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的公共基类。"""


# SQLite 需要关闭同线程检查，才能被 FastAPI 的线程池安全使用
_connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    echo=False,
    future=True,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
    """开启 SQLite 外键约束（默认关闭），保证级联删除生效。"""
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：每个请求一个数据库会话，请求结束自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表。导入 models 包以确保所有模型已注册到 Base.metadata。"""
    from app import models  # noqa: F401  # 触发模型注册

    Base.metadata.create_all(bind=engine)
