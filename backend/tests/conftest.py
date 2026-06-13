"""
Pytest 配置：集成测试数据库隔离

解决 test_integration_*.py 之间的 DATABASE_URL 冲突问题。
每个测试会话使用独立的临时数据库目录，确保测试隔离性。

使用方式：
  pytest backend/tests/test_integration_*.py  # 自动隔离
  pytest backend/tests/test_integration_*.py -v  # 详细输出
"""

import os
import sys
import tempfile
import shutil
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ============================================================
# 全局 stub 模块（必须在导入任何 app 模块之前设置）
# 注意：fastapi 和 routers 不在这里 stub，由各个测试文件自己管理
# ============================================================

def _create_stubs():
    """创建所有必要的 stub 模块（除了 fastapi 和 routers）"""
    
    # stub ffmpeg
    _ffmpeg_mod = types.ModuleType("ffmpeg")
    _ffmpeg_mod.probe = lambda *_args, **_kwargs: {"format": {"duration": "0"}}
    sys.modules["ffmpeg"] = _ffmpeg_mod
    
    # stub logger
    _logger_mod = types.ModuleType("app.utils.logger")
    _logger_mod.get_logger = lambda _n: type("_Logger", (), {
        "info": lambda *a, **kw: None,
        "warning": lambda *a, **kw: None,
        "error": lambda *a, **kw: None,
        "debug": lambda *a, **kw: None,
    })()
    sys.modules["app.utils.logger"] = _logger_mod
    
    # stub blinker
    _blinker_mod = types.ModuleType("blinker")
    _fake_sig = type("FakeSig", (), {"connect": lambda *a, **kw: None, "send": lambda *a, **kw: None})
    _blinker_mod.Signal = type("FakeSignal", (), {"connect": lambda *a, **kw: None, "send": lambda *a, **kw: None})
    _blinker_mod.Namespace = lambda: type("FakeNS", (), {
        "signal": lambda _n: type("FakeSig", (), {"connect": lambda *a, **kw: None, "send": lambda *a, **kw: None})()
    })()
    sys.modules["blinker"] = _blinker_mod
    
    # stub pkg_resources (for ctranslate2)
    _pkg = types.ModuleType("pkg_resources")
    _pkg.get_distribution = lambda *a, **kw: None
    _pkg.require = lambda *a, **kw: None
    _pkg.resource_filename = lambda *a: ""
    sys.modules["pkg_resources"] = _pkg
    
    # stub ctranslate2
    _ct2 = types.ModuleType("ctranslate2")
    _ct2.__file__ = None
    _ct2.__version__ = "0.0.0"
    _ct2.models = types.ModuleType("ctranslate2.models")
    sys.modules["ctranslate2"] = _ct2
    sys.modules["ctranslate2.models"] = _ct2.models
    
    # stub faster_whisper
    _fw = types.ModuleType("faster_whisper")
    
    class FakeWhisperModel:
        def __init__(self, model_size="base", device="cpu", **kwargs):
            self.model_size = model_size
            self.device = device
        
        def transcribe(self, audio, **kwargs):
            return [type("Seg", (), {"text": "fake", "start": 0.0, "end": 1.0})()], {"language": "zh"}
    
    _fw.WhisperModel = FakeWhisperModel
    _fw.BatchedInferencePipeline = type("FW2", (), {})
    sys.modules["faster_whisper"] = _fw
    sys.modules["faster_whisper.utils"] = types.ModuleType("faster_whisper.utils")
    _fw_trans = types.ModuleType("faster_whisper.transcribe")
    _fw_trans.WhisperModel = FakeWhisperModel
    _fw_trans.BatchedInferencePipeline = _fw.BatchedInferencePipeline
    sys.modules["faster_whisper.transcribe"] = _fw_trans


# 立即创建 stubs（不包含 fastapi 和 routers）
_create_stubs()


# ============================================================
# 测试数据库管理
# ============================================================

@pytest.fixture(scope="session")
def test_db_base():
    """
    会话级 fixture：创建临时数据库目录
    
    所有集成测试共享同一个临时目录，避免模块级 setUpModule 冲突。
    """
    base = tempfile.mkdtemp(prefix="bilinote_test_db_")
    yield base
    shutil.rmtree(base, ignore_errors=True)


@pytest.fixture(scope="session")
def test_db_url(test_db_base):
    """会话级 fixture：测试数据库 URL"""
    url = f"sqlite:///{test_db_base}/test.db"
    yield url


@pytest.fixture(scope="session")
def test_env_vars(test_db_base):
    """
    会话级 fixture：设置测试环境变量
    
    在导入 app 模块之前设置 DATABASE_URL 等环境变量。
    """
    # 设置环境变量
    os.environ["ENV"] = "testing"
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db_base}/test.db"
    os.environ["DATA_DIR"] = os.path.join(test_db_base, "data")
    os.environ["OUT_DIR"] = os.path.join(test_db_base, "screenshots")
    os.environ["NOTE_OUTPUT_DIR"] = os.path.join(test_db_base, "notes")
    os.environ["STATIC"] = "/static"
    
    # 创建目录
    for d in ["DATA_DIR", "OUT_DIR", "NOTE_OUTPUT_DIR"]:
        os.makedirs(os.environ[d], exist_ok=True)
    
    yield os.environ.copy()
    
    # 清理（不删除目录，让 test_db_base fixture 处理）


@pytest.fixture(scope="function")
def clean_db(test_env_vars):
    """
    函数级 fixture：为每个测试提供干净的数据库
    
    在测试前初始化数据库，测试后清理数据。
    适用于需要独立数据库状态的测试。
    """
    from app.db.init_db import init_db
    from app.db.engine import get_engine
    from sqlalchemy import inspect
    
    # 初始化数据库
    init_db()
    
    yield
    
    # 清理所有表数据（不删除表）
    engine = get_engine()
    with engine.connect() as conn:
        from sqlalchemy import text
        # 按依赖顺序删除
        conn.execute(text("DELETE FROM video_tasks"))
        conn.execute(text("DELETE FROM models"))
        conn.execute(text("DELETE FROM providers"))
        conn.commit()


@pytest.fixture(scope="function")
def test_client():
    """
    函数级 fixture：FastAPI TestClient
    
    为每个测试创建独立的 TestClient 实例。
    适用于 API 集成测试。
    """
    from main import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app, raise_server_exceptions=False)
    yield client


# ============================================================
# 自动注入环境变量（避免重复设置）
# ============================================================

def pytest_configure(config):
    """Pytest 配置钩子：自动添加 backend 路径并设置测试环境"""
    backend_path = str(Path(__file__).resolve().parents[1])
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    # 设置测试环境变量（只在第一次调用时设置）
    if not os.environ.get("_BILINOTE_TEST_ENV_SET"):
        test_base = tempfile.mkdtemp(prefix="bilinote_test_db_")
        os.environ["_BILINOTE_TEST_ENV_SET"] = "true"
        os.environ["TEST_BASE"] = test_base
        os.environ["ENV"] = "testing"
        os.environ["DATABASE_URL"] = f"sqlite:///{test_base}/test.db"
        os.environ["DATA_DIR"] = os.path.join(test_base, "data")
        os.environ["OUT_DIR"] = os.path.join(test_base, "screenshots")
        os.environ["NOTE_OUTPUT_DIR"] = os.path.join(test_base, "notes")
        os.environ["STATIC"] = "/static"
        
        # 创建目录
        for d in ["DATA_DIR", "OUT_DIR", "NOTE_OUTPUT_DIR"]:
            os.makedirs(os.environ[d], exist_ok=True)


def pytest_collection_modifyitems(config, items):
    """
    收集后修改钩子：为集成测试自动添加标记
    
    方便后续按标记过滤测试：
      pytest -m "integration"  # 只运行集成测试
      pytest -m "not integration"  # 排除集成测试
    """
    for item in items:
        if "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
