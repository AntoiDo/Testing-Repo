"""
集成测试：数据库层验证

测试覆盖：
  - SQLite 数据库初始化（建表）
  - Provider/Model/VideoTask CRUD 操作
  - 数据一致性
"""

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

# --- stub 重型依赖 ---
_ffmpeg_mod = types.ModuleType("ffmpeg")
_ffmpeg_mod.probe = lambda *_args, **_kwargs: {"format": {"duration": "0"}}
sys.modules["ffmpeg"] = _ffmpeg_mod

_fastapi_mod = types.ModuleType("fastapi")
_fastapi_mod.FastAPI = type("FakeFastAPI", (), {})
sys.modules["fastapi"] = _fastapi_mod

_routers = types.ModuleType("app.routers")
for _name in ("note", "provider", "model", "config", "chat"):
    _mod = types.ModuleType(f"app.routers.{_name}")
    _mod.router = object()
    sys.modules[f"app.routers.{_name}"] = _mod
    setattr(_routers, _name, _mod)
sys.modules["app.routers"] = _routers

_logger_mod = types.ModuleType("app.utils.logger")
_logger_mod.get_logger = lambda _n: type("_Logger", (), {
    "info": lambda *a, **kw: None,
    "warning": lambda *a, **kw: None,
    "error": lambda *a, **kw: None,
})()
sys.modules["app.utils.logger"] = _logger_mod

# 测试专用数据库
TEST_BASE = tempfile.mkdtemp(prefix="bilinote_int_db_")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_BASE}/test.db"
os.environ["DATA_DIR"] = os.path.join(TEST_BASE, "data")
os.environ["OUT_DIR"] = os.path.join(TEST_BASE, "screenshots")
os.environ["NOTE_OUTPUT_DIR"] = os.path.join(TEST_BASE, "notes")
for _d in ["DATA_DIR", "OUT_DIR", "NOTE_OUTPUT_DIR"]:
    os.makedirs(os.environ[_d], exist_ok=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.engine import get_engine, Base
from app.db.init_db import init_db
from app.db.models.models import Model as ModelTable
from app.db.models.providers import Provider
from app.db.models.video_tasks import VideoTask
from app.db.provider_dao import (
    insert_provider, get_all_providers, get_provider_by_id,
    get_provider_by_name, update_provider, delete_provider,
    seed_default_providers,
)
from app.db.model_dao import insert_model, get_models_by_provider, delete_model, get_all_models
from app.db.video_task_dao import insert_video_task, get_task_by_video, delete_task_by_video


def setUpModule():
    init_db()


def tearDownModule():
    import shutil
    shutil.rmtree(TEST_BASE, ignore_errors=True)


class TestDatabaseInit(unittest.TestCase):
    """数据库初始化验证"""

    def test_engine_created(self):
        self.assertIsNotNone(get_engine())

    def test_tables_created(self):
        from sqlalchemy import inspect
        inspector = inspect(get_engine())
        tables = inspector.get_table_names()
        for expected in ["providers", "models", "video_tasks"]:
            self.assertIn(expected, tables)

    def test_database_file_exists(self):
        # engine URL 中的路径（兼容 conftest 共享临时目录或模块自身 TEST_BASE）
        engine_url = str(get_engine().url)
        self.assertTrue(
            engine_url.startswith("sqlite:///"),
            f"Expected SQLite URL, got {engine_url}",
        )
        # sqlite:///path → path
        db_path = engine_url[len("sqlite:///"):]
        if os.name == "nt" and db_path.startswith("/"):
            db_path = db_path[1:]  # Windows: /C:/... → C:/...
        self.assertTrue(os.path.exists(db_path), f"DB file not found: {db_path}")

    def test_base_metadata_tables(self):
        for name in ["providers", "models", "video_tasks"]:
            self.assertIn(name, Base.metadata.tables)


class TestProviderCRUD(unittest.TestCase):
    """Provider CRUD 集成测试"""

    @classmethod
    def setUpClass(cls):
        # 清空 providers
        from app.db.engine import get_db
        db = next(get_db())
        try:
            db.query(Provider).delete()
            db.commit()
        finally:
            db.close()

    def test_insert_provider(self):
        pid = insert_provider(
            id="test-prov-1", name="TestProvider", api_key="sk-test",
            base_url="https://api.openai.com/v1", logo="openai.png", type_="openai",
        )
        self.assertEqual(pid, "test-prov-1")

    def test_get_all_providers(self):
        insert_provider("p1", "P1", "k1", "u1", "l1", "openai")
        insert_provider("p2", "P2", "k2", "u2", "l2", "deepseek")
        providers = get_all_providers()
        self.assertGreaterEqual(len(providers), 2)

    def test_get_provider_by_id(self):
        insert_provider("find-me", "FindMe", "key", "url", "logo", "openai")
        found = get_provider_by_id("find-me")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "FindMe")

    def test_get_provider_by_nonexistent_id(self):
        found = get_provider_by_id("no-such-id")
        self.assertIsNone(found)

    def test_get_provider_by_name(self):
        insert_provider("pn1", "ByNameTest", "key", "url", "logo", "openai")
        found = get_provider_by_name("ByNameTest")
        self.assertIsNotNone(found)
        self.assertEqual(found.id, "pn1")

    def test_update_provider(self):
        insert_provider("up1", "OldName", "key", "url", "logo", "openai")
        update_provider("up1", name="NewName", api_key="new-key")
        found = get_provider_by_id("up1")
        self.assertEqual(found.name, "NewName")
        self.assertEqual(found.api_key, "new-key")

    def test_delete_provider(self):
        insert_provider("del-me", "ToDelete", "key", "url", "logo", "openai")
        delete_provider("del-me")
        self.assertIsNone(get_provider_by_id("del-me"))

    def test_seed_default_providers(self):
        """种子数据填充（幂等——已有数据时跳过）"""
        seed_default_providers()
        providers = get_all_providers()
        self.assertGreater(len(providers), 0)
        for p in providers:
            self.assertIsNotNone(p.name)
            self.assertIsNotNone(p.type)


class TestModelCRUD(unittest.TestCase):
    """Model CRUD 集成测试"""

    @classmethod
    def setUpClass(cls):
        from app.db.engine import get_db
        db = next(get_db())
        try:
            db.query(ModelTable).delete()
            db.query(Provider).delete()
            db.commit()
        finally:
            db.close()
        insert_provider("mp1", "ModelProvider", "sk-test", "https://api.test.com/v1", "logo", "openai")

    def test_insert_model(self):
        result = insert_model(provider_id="mp1", model_name="gpt-4o")
        self.assertIsNotNone(result)
        self.assertEqual(result["model_name"], "gpt-4o")
        self.assertEqual(result["provider_id"], "mp1")

    def test_get_models_by_provider(self):
        insert_model("mp1", "gpt-4o-mini")
        insert_model("mp1", "gpt-4-turbo")
        models = get_models_by_provider("mp1")
        self.assertGreaterEqual(len(models), 2)

    def test_get_models_empty_provider(self):
        models = get_models_by_provider("no-such-provider")
        self.assertEqual(len(models), 0)

    def test_delete_model(self):
        result = insert_model("mp1", "to-delete-model")
        delete_model(result["id"])
        all_models = get_all_models()
        names = [m["model_name"] for m in all_models]
        self.assertNotIn("to-delete-model", names)


class TestVideoTaskCRUD(unittest.TestCase):
    """VideoTask CRUD 集成测试"""

    def setUp(self):
        # 清空
        from app.db.engine import get_db
        db = next(get_db())
        try:
            db.query(VideoTask).delete()
            db.commit()
        finally:
            db.close()

    def test_insert_and_query(self):
        insert_video_task("BV123", "bilibili", "task-uuid-001")
        task_id = get_task_by_video("BV123", "bilibili")
        self.assertEqual(task_id, "task-uuid-001")

    def test_get_nonexistent_task(self):
        self.assertIsNone(get_task_by_video("NONEXIST", "bilibili"))

    def test_delete_task(self):
        insert_video_task("BV456", "bilibili", "task-uuid-456")
        delete_task_by_video("BV456", "bilibili")
        self.assertIsNone(get_task_by_video("BV456", "bilibili"))

    def test_same_video_different_platform(self):
        insert_video_task("test123", "bilibili", "uuid-b")
        insert_video_task("test123", "youtube", "uuid-y")
        self.assertEqual(get_task_by_video("test123", "bilibili"), "uuid-b")
        self.assertEqual(get_task_by_video("test123", "youtube"), "uuid-y")


if __name__ == "__main__":
    unittest.main()
