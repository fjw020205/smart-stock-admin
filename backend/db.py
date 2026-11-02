"""数据库引擎、会话与出入库专用事务。"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from .config import DB_PATH

Base = declarative_base()

engine = create_engine(
    f"sqlite:///{DB_PATH.as_posix()}",
    future=True,
    connect_args={"check_same_thread": False, "timeout": 15},
)


@event.listens_for(engine, "connect")
def _apply_pragmas(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=15000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
session = scoped_session(SessionLocal)


@contextmanager
def stock_conn():
    """出入库专用连接：显式 BEGIN IMMEDIATE，写事务串行化，避免并发超卖。"""
    conn = sqlite3.connect(str(DB_PATH), timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=15000")
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.close()


def init_db(seed: bool = True) -> None:
    from sqlalchemy import inspect

    from . import models  # noqa: F401  确保模型已注册

    first_run = not inspect(engine).has_table("users")
    Base.metadata.create_all(engine)
    if seed:
        from .seed import seed_all

        seed_session = SessionLocal()
        try:
            seed_all(seed_session, include_demo=first_run)
            seed_session.commit()
        finally:
            seed_session.close()
