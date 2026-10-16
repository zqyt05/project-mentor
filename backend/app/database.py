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
    """SQLite 连接建立时设置 PRAGMA。

    1. `foreign_keys=ON`：SQLite 默认关闭外键约束，不开启则级联删除不生效。
    2. `journal_mode=WAL`：写前日志模式。默认的 DELETE 模式下写操作会阻塞读，
       演示场景中多个朋友同时点击（例如同时打开项目总览）容易撞出
       「database is locked」。WAL 允许读写并发，显著降低锁冲突。
    3. `busy_timeout`：遇到锁时等待 5 秒再报错，而不是立刻失败。
    """
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        # WAL 下适当放宽同步频率，换取并发写入时的吞吐
        cursor.execute("PRAGMA synchronous=NORMAL")
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
