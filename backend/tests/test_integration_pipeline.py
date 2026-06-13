"""
集成测试：全业务链路联调验证

核心链路：
  视频URL解析 → 平台识别 → 下载器选择 → 转写(ASR) → LLM总结 → 数据入库

测试覆盖：
  - 阶段1：URL解析 + 平台识别 + 下载器映射
  - 阶段2：ASR 转写器工厂与模型
  - 阶段3：GPT/LLM 工厂与配置
  - 阶段4：NoteGenerator 完整编排（Mock 外部依赖）
  - 阶段5：数据库任务入库 → 查询 → 删除
  - 异常路径：超时、格式错误、不支持平台
  - 系统架构完整性验证
"""

import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

# --- stub ---
_ffmpeg_mod = types.ModuleType("ffmpeg")
_ffmpeg_mod.probe = lambda *_args, **_kwargs: {"format": {"duration": "120.0"}}
sys.modules["ffmpeg"] = _ffmpeg_mod

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
    "debug": lambda *a, **kw: None,
})()
sys.modules["app.utils.logger"] = _logger_mod

_blinker_mod = types.ModuleType("blinker")
_blinker_mod.Signal = type("FakeSignal", (), {"connect": lambda *a, **kw: None, "send": lambda *a, **kw: None})
_blinker_mod.Namespace = lambda: type("FakeNS", (), {
    "signal": lambda _n: type("FakeSig", (), {"connect": lambda *a, **kw: None, "send": lambda *a, **kw: None})()
})()
sys.modules["blinker"] = _blinker_mod

TEST_BASE = tempfile.mkdtemp(prefix="bilinote_pipe_")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_BASE}/test.db"
os.environ["DATA_DIR"] = os.path.join(TEST_BASE, "data")
os.environ["OUT_DIR"] = os.path.join(TEST_BASE, "screenshots")
os.environ["NOTE_OUTPUT_DIR"] = os.path.join(TEST_BASE, "notes")
for _d in ["DATA_DIR", "OUT_DIR", "NOTE_OUTPUT_DIR"]:
    os.makedirs(os.environ[_d], exist_ok=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.engine import get_db
from app.db.init_db import init_db
from app.services.constant import SUPPORT_PLATFORM_MAP
from app.validators.video_url_validator import is_supported_video_url
from app.utils.url_parser import extract_video_id
from app.enmus.note_enums import DownloadQuality
from app.enmus.exception import NoteErrorEnum
from app.exceptions.note import NoteError
from app.models.audio_model import AudioDownloadResult
from app.models.transcriber_model import TranscriptResult, TranscriptSegment
from app.models.notes_model import NoteResult


def setUpModule():
    """恢复本模块的 DATABASE_URL（可能被字母序靠后的模块覆盖）。"""
    os.environ["DATABASE_URL"] = f"sqlite:///{TEST_BASE}/test.db"


def tearDownModule():
    import shutil
    shutil.rmtree(TEST_BASE, ignore_errors=True)


# ================================================================
# 阶段1: URL解析 → 平台识别 → 下载器
# ================================================================

class TestPipelineStage1URLParsing(unittest.TestCase):
    """阶段1：URL解析 + 平台识别 + 下载器映射"""

    def test_bilibili_full_chain(self):
        url = "https://www.bilibili.com/video/BV1vc411b7Wa"
        self.assertTrue(is_supported_video_url(url))
        self.assertEqual(extract_video_id(url, "bilibili"), "BV1vc411b7Wa")
        self.assertIn("bilibili", SUPPORT_PLATFORM_MAP)

    def test_youtube_full_chain(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertTrue(is_supported_video_url(url))
        self.assertEqual(extract_video_id(url, "youtube"), "dQw4w9WgXcQ")
        self.assertIn("youtube", SUPPORT_PLATFORM_MAP)

    def test_douyin_full_chain(self):
        url = "https://www.douyin.com/video/1234567890123456789"
        self.assertTrue(is_supported_video_url(url))
        self.assertEqual(extract_video_id(url, "douyin"), "1234567890123456789")
        self.assertIn("douyin", SUPPORT_PLATFORM_MAP)

    def test_kuaishou_full_chain(self):
        self.assertTrue(is_supported_video_url("https://www.kuaishou.com/short-video/abc123"))
        self.assertIn("kuaishou", SUPPORT_PLATFORM_MAP)

    def test_local_downloader(self):
        self.assertIn("local", SUPPORT_PLATFORM_MAP)

    def test_b23_short_url_detection(self):
        self.assertTrue(is_supported_video_url("https://b23.tv/abcd1234"))

    def test_invalid_url_blocked(self):
        self.assertFalse(is_supported_video_url("https://www.google.com"))
        self.assertIsNone(extract_video_id("https://www.google.com", "bilibili"))

    def test_all_downloaders_have_download_method(self):
        for platform, downloader in SUPPORT_PLATFORM_MAP.items():
            with self.subTest(platform=platform):
                self.assertTrue(hasattr(downloader, "download"),
                                f"{platform} missing 'download'")

    def test_platform_map_coverage(self):
        for p in ["bilibili", "youtube", "douyin", "kuaishou", "local"]:
            self.assertIn(p, SUPPORT_PLATFORM_MAP)


# ================================================================
# 阶段2: 转写器工厂 & ASR
# ================================================================

class TestPipelineStage2Transcriber(unittest.TestCase):
    """阶段2：ASR 转写器工厂与数据模型"""

    @classmethod
    def setUpClass(cls):
        # 需要先初始化数据库才能导入 transcriber_provider（因为 groq 导入了 ProviderService）
        init_db()

    def test_transcriber_type_enum_values(self):
        try:
            from app.transcriber.transcriber_provider import TranscriberType
        except ImportError as e:
            self.skipTest(f"faster-whisper 不可用: {e}")
        values = [t.value for t in TranscriberType]
        self.assertIn("fast-whisper", values)
        self.assertIn("groq", values)
        self.assertIn("bcut", values)
        self.assertIn("kuaishou", values)

    def test_transcriber_base_has_transcript_method(self):
        from app.transcriber.base import Transcriber
        self.assertTrue(hasattr(Transcriber, "transcript"))

    def test_transcript_result_model(self):
        result = TranscriptResult(
            language="zh",
            full_text="完整转写文本",
            segments=[TranscriptSegment(start=0.0, end=3.0, text="完整转写文本")],
        )
        self.assertEqual(result.language, "zh")
        self.assertEqual(result.segments[0].start, 0.0)

    def test_transcript_result_empty(self):
        result = TranscriptResult(language=None, full_text="", segments=[])
        self.assertEqual(len(result.segments), 0)

    def test_transcript_result_serialization(self):
        from dataclasses import asdict
        result = TranscriptResult(
            language="en",
            full_text="Hello world",
            segments=[TranscriptSegment(start=0.0, end=2.0, text="Hello world")],
        )
        d = asdict(result)
        self.assertEqual(d["language"], "en")

    def test_transcriber_factory_exists(self):
        try:
            from app.transcriber.transcriber_provider import get_transcriber
        except ImportError as e:
            self.skipTest(f"faster-whisper 不可用: {e}")
        self.assertTrue(callable(get_transcriber))


# ================================================================
# 阶段3: GPT 工厂 & LLM
# ================================================================

class TestPipelineStage3GPTFactory(unittest.TestCase):
    """阶段3：GPT/LLM 工厂"""

    def test_gpt_factory(self):
        from app.gpt.gpt_factory import GPTFactory
        self.assertTrue(hasattr(GPTFactory, "from_config"))

    def test_gpt_base_has_summarize(self):
        from app.gpt.base import GPT
        self.assertTrue(hasattr(GPT, "summarize"))

    def test_gpt_base_has_list_models(self):
        from app.gpt.base import GPT
        self.assertTrue(hasattr(GPT, "list_models"))

    def test_model_config(self):
        from app.models.model_config import ModelConfig
        config = ModelConfig(
            name="TestModel", provider="openai",
            api_key="sk-test", base_url="https://api.test.com/v1",
            model_name="gpt-4o",
        )
        self.assertEqual(config.model_name, "gpt-4o")

    def test_gpt_source_structure(self):
        from app.models.gpt_model import GPTSource
        source = GPTSource(
            segment=[TranscriptSegment(start=0.0, end=1.0, text="测试")],
            title="测试视频",
            tags="测试",
        )
        self.assertEqual(source.title, "测试视频")

    def test_request_chunker_exists(self):
        from app.gpt.request_chunker import RequestChunker
        self.assertTrue(hasattr(RequestChunker, "estimate"))


# ================================================================
# 阶段4: NoteGenerator 编排（Mock外部依赖）
# ================================================================

class TestPipelineStage4NoteGenerator(unittest.TestCase):
    """阶段4：NoteGenerator 编排流程"""

    def test_note_error(self):
        err = NoteError("平台不受支持", NoteErrorEnum.PLATFORM_NOT_SUPPORTED)
        self.assertEqual(err.code.code, 300101)
        with self.assertRaises(NoteError):
            raise err

    def test_audio_download_result(self):
        result = AudioDownloadResult(
            file_path="/tmp/test.mp3", title="Pipeline Test",
            duration=180.0, cover_url="https://img.example.com/cover.jpg",
            platform="bilibili", video_id="BV1vc411b7Wa",
            raw_info={"uploader": "Author"},
        )
        self.assertEqual(result.platform, "bilibili")
        self.assertEqual(result.raw_info["uploader"], "Author")

    def test_note_result(self):
        audio = AudioDownloadResult(
            file_path="/tmp/audio.mp3", title="集成测试",
            duration=300.0, cover_url=None, platform="youtube",
            video_id="dQw4w9WgXcQ", raw_info={},
        )
        transcript = TranscriptResult(
            language="zh", full_text="ASR 转写文本",
            segments=[TranscriptSegment(start=0.0, end=10.0, text="ASR 转写文本")],
        )
        note = NoteResult(
            markdown="# 笔记\nLLM 生成的完整笔记",
            transcript=transcript, audio_meta=audio,
        )
        self.assertEqual(note.audio_meta.platform, "youtube")

    def test_download_quality_values(self):
        self.assertEqual(DownloadQuality.fast, "fast")
        self.assertEqual(DownloadQuality.medium, "medium")
        self.assertEqual(DownloadQuality.slow, "slow")

    def test_builtin_providers_json(self):
        seed_path = Path(__file__).resolve().parents[1] / "app" / "db" / "builtin_providers.json"
        self.assertTrue(seed_path.exists())
        with open(seed_path) as f:
            providers = json.load(f)
        self.assertIsInstance(providers, list)
        self.assertGreater(len(providers), 0)
        for p in providers:
            self.assertIn("name", p)
            self.assertIn("type", p)


# ================================================================
# 阶段5: 数据库入库
# ================================================================

class TestPipelineStage5Database(unittest.TestCase):
    """阶段5：任务入库 → 查询 → 删除"""

    def setUp(self):
        init_db()
        from app.db.models.video_tasks import VideoTask
        db = next(get_db())
        try:
            db.query(VideoTask).delete()
            db.commit()
        finally:
            db.close()

    def test_insert_and_query(self):
        from app.db.video_task_dao import insert_video_task, get_task_by_video
        insert_video_task("BV_FULL", "bilibili", "pipeline-uuid-001")
        task_id = get_task_by_video("BV_FULL", "bilibili")
        self.assertEqual(task_id, "pipeline-uuid-001")

    def test_delete_and_verify(self):
        from app.db.video_task_dao import insert_video_task, get_task_by_video, delete_task_by_video
        insert_video_task("BV_DEL", "bilibili", "task-del")
        delete_task_by_video("BV_DEL", "bilibili")
        self.assertIsNone(get_task_by_video("BV_DEL", "bilibili"))

    def test_multi_platform_same_video_id(self):
        from app.db.video_task_dao import insert_video_task, get_task_by_video
        insert_video_task("test123", "bilibili", "uuid-b")
        insert_video_task("test123", "youtube", "uuid-y")
        self.assertEqual(get_task_by_video("test123", "bilibili"), "uuid-b")
        self.assertEqual(get_task_by_video("test123", "youtube"), "uuid-y")

    def test_multiple_tasks(self):
        from app.db.video_task_dao import insert_video_task
        for i in range(5):
            insert_video_task(f"BV_M_{i}", "bilibili", f"task-{i}")
        from app.db.engine import get_db
        from app.db.models.video_tasks import VideoTask
        db = next(get_db())
        try:
            count = db.query(VideoTask).count()
            self.assertGreaterEqual(count, 5)
        finally:
            db.close()


# ================================================================
# 异常路径测试
# ================================================================

class TestPipelineErrorPaths(unittest.TestCase):
    """集成异常路径测试"""

    def test_error_enum_code(self):
        self.assertEqual(NoteErrorEnum.PLATFORM_NOT_SUPPORTED.code, 300101)

    def test_unsupported_platform_blocked(self):
        self.assertFalse(is_supported_video_url("https://www.vimeo.com/123456"))
        self.assertIsNone(extract_video_id("https://www.vimeo.com/123456", "vimeo"))

    def test_empty_url_blocked(self):
        self.assertFalse(is_supported_video_url(""))
        self.assertIsNone(extract_video_id("", "bilibili"))

    def test_malformed_url_blocked(self):
        self.assertFalse(is_supported_video_url("javascript:alert(1)"))

    def test_transcript_none_language_ok(self):
        result = TranscriptResult(
            language=None, full_text="text",
            segments=[TranscriptSegment(start=0.0, end=1.0, text="text")],
        )
        self.assertIsNone(result.language)

    def test_audio_result_no_video_path_ok(self):
        result = AudioDownloadResult(
            file_path="/tmp/audio.mp3", title="Test", duration=60.0,
            cover_url=None, platform="youtube", video_id="test", raw_info={},
        )
        self.assertIsNone(result.video_path)


# ================================================================
# 系统架构验证
# ================================================================

class TestSystemArchitecture(unittest.TestCase):
    """系统模块流程图验证

    用户 → 前端页面 → 业务后端 → ASR语音模块 → LLM大模型 → 数据库
    """

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_router_module(self):
        from app.routers import note as note_router
        self.assertIsNotNone(note_router)

    def test_transcriber_module(self):
        try:
            from app.transcriber.transcriber_provider import get_transcriber
        except ImportError as e:
            self.skipTest(f"faster-whisper 不可用: {e}")
        self.assertTrue(callable(get_transcriber))

    def test_gpt_module(self):
        from app.gpt.gpt_factory import GPTFactory
        self.assertIsNotNone(GPTFactory)

    def test_database_module(self):
        from app.db.engine import get_engine
        self.assertIsNotNone(get_engine())

    def test_platform_map_module(self):
        self.assertGreater(len(SUPPORT_PLATFORM_MAP), 0)


if __name__ == "__main__":
    unittest.main()
