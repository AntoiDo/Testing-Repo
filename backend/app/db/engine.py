import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

# 懒加载：不在模块 import 时创建 engine，而是在首次调用 get_engine() 时创建。
# 这样测试文件可以在 import 之后修改 DATABASE_URL，get_engine() 会使用最新的环境变量。
_engine = None
_SessionLocal = None
_engine_url = None  # 记录当前 engine 使用的 DATABASE_URL，用于检测变更


def _get_database_url():
    return os.getenv("DATABASE_URL", "sqlite:///bili_note.db")


def _build_engine(db_url):
    """根据数据库 URL 创建 engine 和 SessionLocal。"""
    global _engine, _SessionLocal, _engine_url

    engine_args = {}
    if db_url.startswith("sqlite"):
        engine_args["connect_args"] = {"check_same_thread": False}

    _pool_args = {}
    if not db_url.startswith("sqlite"):
        _pool_args = {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "pool_pre_ping": True,
        }

    _engine = create_engine(
        db_url,
        echo=os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true",
        **engine_args,
        **_pool_args,
    )
    _engine_url = db_url
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_engine():
    """返回数据库 engine。

    如果 DATABASE_URL 环境变量在 engine 创建后被修改（例如集成测试切换临时库），
    自动 dispose 旧 engine 并用新 URL 重建。
    """
    global _engine, _SessionLocal, _engine_url

    current_url = _get_database_url()
    if _engine is not None and current_url != _engine_url:
        # DATABASE_URL 已变更 → 释放旧连接并用新 URL 重建（测试隔离）
        _engine.dispose()
        _engine = None
        _SessionLocal = None
        _engine_url = None

    if _engine is None:
        _build_engine(current_url)

    return _engine


def get_db():
    """返回数据库会话（FastAPI 依赖注入用）。"""
    global _SessionLocal
    get_engine()  # 确保 engine 是最新的
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_engine():
    """显式重置 engine 单例（供测试 teardown 使用）。"""
    global _engine, _SessionLocal, _engine_url
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    _engine_url = None
