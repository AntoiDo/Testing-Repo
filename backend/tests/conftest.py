"""
pytest 全局配置：确保 backend/ 在 sys.path 中，并为每个测试模块重置数据库引擎。
"""

import sys
from pathlib import Path

import pytest

# 将 backend/ 加入 sys.path
BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


@pytest.fixture(autouse=True, scope="module")
def _reset_db_per_module():
    """每个测试模块运行前重置数据库引擎，确保各模块使用自己的 DATABASE_URL。

    通过 sys.modules 直接访问已加载的 engine 模块，避免 import 触发
    app/__init__.py → routers → services 的完整导入链。
    """
    eng_mod = sys.modules.get("app.db.engine")
    if eng_mod is None:
        # engine 模块尚未被导入（当前模块不依赖数据库），无需重置
        yield
        return

    if eng_mod._engine is not None:
        eng_mod._engine.dispose()
    eng_mod._engine = None
    eng_mod._SessionLocal = None
    eng_mod._engine_url = None
    yield
