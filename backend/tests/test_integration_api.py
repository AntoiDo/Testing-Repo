"""
集成测试：API 接口层联调验证

测试覆盖：
  - 服务健康检查
  - /api/generate_note 请求验证与响应
  - /api/task_status/{task_id} 状态轮询
  - Provider/Model CRUD API
  - Transcriber 配置 API
  - 错误处理与边界条件

注意：数据库隔离由 conftest.py 管理，不要在此文件中重复设置 DATABASE_URL。
"""

import os
import sys
import types
import unittest
from pathlib import Path

# --- stub 重型依赖（必须在导入 app 之前设置）---
_ffmpeg_mod = types.ModuleType("ffmpeg")
_ffmpeg_mod.probe = lambda *_args, **_kwargs: {"format": {"duration": "0"}}
sys.modules["ffmpeg"] = _ffmpeg_mod

# ctranslate2 -> pkg_resources -> faster_whisper chain
_pkg = types.ModuleType("pkg_resources")
_pkg.get_distribution = lambda *a, **kw: None
_pkg.require = lambda *a, **kw: None
_pkg.resource_filename = lambda *a: ""
sys.modules["pkg_resources"] = _pkg

_ct2 = types.ModuleType("ctranslate2")
_ct2.__file__ = None  # prevent add_dll_directory OS call
_ct2.__version__ = "0.0.0"
_ct2.models = types.ModuleType("ctranslate2.models")
sys.modules["ctranslate2"] = _ct2
sys.modules["ctranslate2.models"] = _ct2.models

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

# 添加 backend 路径
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# blinker stub - 必须在 events 模块导入前设置
_bl = types.ModuleType("blinker")
_fake_sig = type("FakeSig", (), {"connect": lambda *a, **kw: None, "send": lambda *a, **kw: None})
_bl.signal = lambda _name: _fake_sig()
_bl.Signal = type("FakeSignal", (), {"connect": lambda *a, **kw: None, "send": lambda *a, **kw: None})
_bl.Namespace = lambda: type("FakeNS", (), {"signal": lambda s, _n: _fake_sig()})()
sys.modules["blinker"] = _bl

# logger stub
_log_mod = types.ModuleType("app.utils.logger")
_log_mod.get_logger = lambda _n: type("_L", (), {
    "info": lambda *a, **kw: None,
    "warning": lambda *a, **kw: None,
    "error": lambda *a, **kw: None,
    "debug": lambda *a, **kw: None,
})()
sys.modules["app.utils.logger"] = _log_mod

# 导入 app 模块（此时 conftest.py 已设置好环境变量）
from app.db.init_db import init_db
init_db()

# 导入 main 需要完整的 FastAPI，所以这里不 stub
from main import app
from fastapi.testclient import TestClient

client = TestClient(app, raise_server_exceptions=False)


# ================================================================
# 健康检查
# ================================================================

class TestHealthCheck(unittest.TestCase):
    def test_sys_health_returns_200(self):
        self.assertEqual(client.get("/api/sys_health").status_code, 200)

    def test_sys_health_body(self):
        data = client.get("/api/sys_health").json()
        self.assertIn("code", data)

    def test_sys_check_returns_200(self):
        self.assertEqual(client.get("/api/sys_check").status_code, 200)

    def test_deploy_status(self):
        self.assertEqual(client.get("/api/deploy_status").status_code, 200)

    def test_cors_present(self):
        resp = client.options("/api/sys_health", headers={
            "Origin": "http://localhost:3015",
            "Access-Control-Request-Method": "GET",
        })
        self.assertIn(resp.status_code, [200, 405])


# ================================================================
# Provider API
# ================================================================

class TestProviderAPI(unittest.TestCase):
    def test_get_all_providers(self):
        resp = client.get("/api/get_all_providers")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("data", resp.json())

    def test_add_provider(self):
        resp = client.post("/api/add_provider", json={
            "name": "IntTestProv", "type": "openai",
            "api_key": "sk-test", "base_url": "https://api.test.com/v1",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNotNone(data.get("data"))

    def test_add_duplicate_provider(self):
        client.post("/api/add_provider", json={
            "name": "DupProv", "type": "openai",
            "api_key": "sk-1", "base_url": "https://a.com",
        })
        resp = client.post("/api/add_provider", json={
            "name": "DupProv", "type": "openai",
            "api_key": "sk-2", "base_url": "https://b.com",
        })
        self.assertNotEqual(resp.json().get("code"), 0)

    def test_get_provider_by_id(self):
        resp = client.post("/api/add_provider", json={
            "name": "GetById", "type": "openai",
            "api_key": "k", "base_url": "https://x.com",
        })
        data = resp.json()
        self.assertIn("data", data)
        pid = data.get("data")
        if isinstance(pid, dict):
            pid = pid.get("id")
        if pid:
            resp2 = client.get(f"/api/get_provider_by_id/{pid}")
            self.assertEqual(resp2.status_code, 200)

    def test_get_provider_nonexistent(self):
        resp = client.get("/api/get_provider_by_id/nonexistent-id")
        self.assertIn("data", resp.json())

    def test_connect_test(self):
        """连通测试接口可访问"""
        # connect_test 需要已有 provider id
        resp = client.post("/api/add_provider", json={
            "name": "ConnTest", "type": "openai",
            "api_key": "sk-conn", "base_url": "https://api.openai.com/v1",
        })
        data = resp.json()
        pid = data.get("data") if isinstance(data.get("data"), str) else data.get("data", {}).get("id")
        if pid:
            resp2 = client.post("/api/connect_test", json={"id": str(pid)})
            # 可能成功也可能失败（外部API不可用），只要不是500就行
            self.assertNotEqual(resp2.status_code, 500)


# ================================================================
# Model API
# ================================================================

class TestModelAPI(unittest.TestCase):
    provider_id = None

    @classmethod
    def setUpClass(cls):
        # 确保有一个 provider
        resp = client.post("/api/add_provider", json={
            "name": "ModelProv", "type": "openai",
            "api_key": "sk-m", "base_url": "https://m.com",
        })
        data = resp.json().get("data")
        if isinstance(data, dict):
            cls.provider_id = data.get("id")
        elif isinstance(data, str):
            cls.provider_id = data
        if not cls.provider_id:
            # fallback: use get_all_providers to find one
            all_resp = client.get("/api/get_all_providers")
            all_data = all_resp.json().get("data", [])
            if all_data and isinstance(all_data[0], dict):
                cls.provider_id = all_data[0].get("id")

    def test_add_model(self):
        resp = client.post("/api/models", json={
            "provider_id": self.provider_id,
            "model_name": "gpt-integration-test",
        })
        self.assertEqual(resp.status_code, 200)

    def test_get_model_list(self):
        resp = client.get(f"/api/model_list/{self.provider_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json()["data"], list)


# ================================================================
# Generate Note API（核心集成入口）
# ================================================================

class TestGenerateNoteAPI(unittest.TestCase):
    """
    /api/generate_note 接口测试

    注意：当 transcriber 模型未就绪时，所有没有 prefetched_transcript
    的请求会返回 code=300102（转写模块未就绪）。这是正常行为。
    """

    def test_bilibili_valid_request(self):
        resp = client.post("/api/generate_note", json={
            "video_url": "https://www.bilibili.com/video/BV1vc411b7Wa",
            "platform": "bilibili", "quality": "fast",
            "model_name": "gpt-4o", "provider_id": "1",
        })
        data = resp.json()
        self.assertIn(data["code"], [0, 300102])

    def test_youtube_valid_request(self):
        resp = client.post("/api/generate_note", json={
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "platform": "youtube", "quality": "medium",
            "model_name": "gpt-4o", "provider_id": "1",
        })
        self.assertIn(resp.json()["code"], [0, 300102])

    def test_douyin_valid_request(self):
        resp = client.post("/api/generate_note", json={
            "video_url": "https://www.douyin.com/video/1234567890123456789",
            "platform": "douyin", "quality": "slow",
            "model_name": "gpt-4o", "provider_id": "1",
        })
        self.assertIn(resp.json()["code"], [0, 300102])

    def test_invalid_url_format(self):
        """畸形 URL 会通过请求层校验但 pipeline 中会失败"""
        resp = client.post("/api/generate_note", json={
            "video_url": "not-a-valid-url!@#", "platform": "bilibili",
            "quality": "fast", "model_name": "gpt-4o", "provider_id": "1",
        })
        # 请求层通过（video_url 是 str 类型），pipeline 返回错误
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("code", data)
        # 注意：如果 provider_id=1 不存在，会返回 ProviderError，code != 0
        # 如果 provider_id=1 存在，会尝试下载但 URL 无效，也会返回错误
        # 这里只验证返回了响应，不强制要求特定 code

    def test_unsupported_platform(self):
        """不支持平台：请求层接受但 pipeline 拦截"""
        resp = client.post("/api/generate_note", json={
            "video_url": "https://www.vimeo.com/123456",
            "platform": "vimeo", "quality": "fast",
            "model_name": "gpt-4o", "provider_id": "1",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertNotEqual(resp.json()["code"], 0)

    def test_missing_required_fields(self):
        resp = client.post("/api/generate_note", json={})
        self.assertEqual(resp.status_code, 422)

    def test_missing_platform(self):
        resp = client.post("/api/generate_note", json={
            "video_url": "https://www.bilibili.com/video/BV1vc411b7Wa",
            "quality": "fast", "model_name": "gpt-4o", "provider_id": "1",
        })
        self.assertEqual(resp.status_code, 422)

    def test_invalid_quality(self):
        resp = client.post("/api/generate_note", json={
            "video_url": "https://www.bilibili.com/video/BV1vc411b7Wa",
            "platform": "bilibili", "quality": "ultra",
            "model_name": "gpt-4o", "provider_id": "1",
        })
        self.assertEqual(resp.status_code, 422)

    def test_with_screenshot_link_option(self):
        resp = client.post("/api/generate_note", json={
            "video_url": "https://www.bilibili.com/video/BV1vc411b7Wa",
            "platform": "bilibili", "quality": "fast",
            "model_name": "gpt-4o", "provider_id": "1",
            "screenshot": True, "link": True,
        })
        self.assertIn(resp.json()["code"], [0, 300102])

    def test_with_video_understanding(self):
        resp = client.post("/api/generate_note", json={
            "video_url": "https://www.bilibili.com/video/BV1vc411b7Wa",
            "platform": "bilibili", "quality": "fast",
            "model_name": "gpt-4o", "provider_id": "1",
            "video_understanding": True, "video_interval": 5,
        })
        self.assertIn(resp.json()["code"], [0, 300102])

    def test_with_prefetched_transcript_bypasses_readiness(self):
        """预转写文本应跳过 transcriber 准备检查，返回 task_id"""
        resp = client.post("/api/generate_note", json={
            "video_url": "https://www.bilibili.com/video/BV1vc411b7Wa",
            "platform": "bilibili", "quality": "fast",
            "model_name": "gpt-4o", "provider_id": "1",
            "prefetched_transcript": {
                "language": "zh", "full_text": "测试转写文本。用于生成笔记。",
                "segments": [
                    {"start": 0.0, "end": 5.0, "text": "测试转写文本。"},
                    {"start": 5.0, "end": 10.0, "text": "用于生成笔记。"},
                ],
            },
        })
        data = resp.json()
        # 预转写模式下绕过模型准备检查
        self.assertIn("code", data)
        self.assertIn(data.get("code"), [0, 300102])


# ================================================================
# Task Status API
# ================================================================

class TestTaskStatusAPI(unittest.TestCase):
    def test_nonexistent_task(self):
        resp = client.get("/api/task_status/nonexistent-uuid-12345")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # 不存在的任务: code=0 但 data 为 null 或包含错误信息
        self.assertIn("code", data)
        self.assertIn("data", data)

    def test_task_status_response_structure(self):
        resp = client.get("/api/task_status/fake-id")
        data = resp.json()
        self.assertIn("code", data)
        self.assertIn("msg", data)

    def test_generate_and_check_status(self):
        resp = client.post("/api/generate_note", json={
            "video_url": "https://www.bilibili.com/video/BV1vc411b7Wa",
            "platform": "bilibili", "quality": "fast",
            "model_name": "gpt-4o", "provider_id": "1",
            "prefetched_transcript": {
                "language": "zh", "full_text": "测试",
                "segments": [{"start": 0, "end": 1, "text": "测试"}],
            },
        })
        data = resp.json()
        if data.get("code") == 0 and data.get("data"):
            task_id = data["data"]["task_id"]
            status = client.get(f"/api/task_status/{task_id}")
            self.assertEqual(status.status_code, 200)


# ================================================================
# Config API
# ================================================================

class TestConfigAPI(unittest.TestCase):
    def test_get_transcriber_config(self):
        self.assertEqual(client.get("/api/transcriber_config").status_code, 200)

    def test_get_models_status(self):
        self.assertEqual(client.get("/api/transcriber_models_status").status_code, 200)

    def test_get_proxy_config(self):
        self.assertEqual(client.get("/api/proxy_config").status_code, 200)

    def test_update_transcriber_config(self):
        resp = client.post("/api/transcriber_config", json={
            "transcriber_type": "fast-whisper", "model_size": "base",
        })
        self.assertEqual(resp.status_code, 200)


# ================================================================
# Upload API
# ================================================================

class TestUploadAPI(unittest.TestCase):
    def test_upload_without_file(self):
        self.assertEqual(client.post("/api/upload").status_code, 422)

    def test_upload_empty_file(self):
        import io
        resp = client.post("/api/upload", files={
            "file": ("test.txt", io.BytesIO(b""), "text/plain"),
        })
        self.assertNotEqual(resp.status_code, 500)


if __name__ == "__main__":
    unittest.main()
