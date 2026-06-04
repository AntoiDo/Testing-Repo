"""
M1 模块单元测试：数据模型、枚举、异常类

测试覆盖：
  - AudioDownloadResult 数据类字段与默认值
  - NoteResult 数据类结构
  - TranscriptResult / TranscriptSegment 数据类
  - DownloadQuality 枚举值
  - NoteError / NoteErrorEnum 异常定义
  - QUALITY_MAP 质量映射正确性
"""

import pathlib
import sys
import types
import unittest


def _install_stubs():
    fastapi_mod = types.ModuleType("fastapi")
    fastapi_mod.FastAPI = type("FakeFastAPI", (), {})

    routers_pkg = types.ModuleType("app.routers")
    for name in ("note", "provider", "model", "config", "chat"):
        mod = types.ModuleType(f"app.routers.{name}")
        mod.router = object()
        sys.modules[f"app.routers.{name}"] = mod
        setattr(routers_pkg, name, mod)

    sys.modules["fastapi"] = fastapi_mod
    sys.modules["app.routers"] = routers_pkg


_install_stubs()

root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from app.models.audio_model import AudioDownloadResult
from app.models.notes_model import NoteResult
from app.models.transcriber_model import TranscriptResult, TranscriptSegment
from app.enmus.note_enums import DownloadQuality
from app.enmus.exception import NoteErrorEnum
from app.exceptions.note import NoteError
from app.downloaders.base import QUALITY_MAP


class TestAudioDownloadResult(unittest.TestCase):
    """AudioDownloadResult 数据类测试"""

    def test_create_with_all_fields(self):
        result = AudioDownloadResult(
            file_path="/data/audio/test.mp3",
            title="测试视频",
            duration=120.5,
            cover_url="https://example.com/cover.jpg",
            platform="bilibili",
            video_id="BV1vc411b7Wa",
            raw_info={"id": "BV1vc411b7Wa", "title": "测试视频"},
            video_path="/data/video/test.mp4",
        )
        self.assertEqual(result.file_path, "/data/audio/test.mp3")
        self.assertEqual(result.title, "测试视频")
        self.assertEqual(result.duration, 120.5)
        self.assertEqual(result.cover_url, "https://example.com/cover.jpg")
        self.assertEqual(result.platform, "bilibili")
        self.assertEqual(result.video_id, "BV1vc411b7Wa")
        self.assertEqual(result.raw_info["id"], "BV1vc411b7Wa")
        self.assertEqual(result.video_path, "/data/video/test.mp4")

    def test_create_with_optional_fields_none(self):
        result = AudioDownloadResult(
            file_path="/data/audio/test.mp3",
            title="测试视频",
            duration=60.0,
            cover_url=None,
            platform="youtube",
            video_id="dQw4w9WgXcQ",
            raw_info={},
        )
        self.assertIsNone(result.cover_url)
        self.assertIsNone(result.video_path)

    def test_create_without_video_path_defaults_to_none(self):
        result = AudioDownloadResult(
            file_path="/data/audio/test.mp3",
            title="测试视频",
            duration=60.0,
            cover_url=None,
            platform="youtube",
            video_id="dQw4w9WgXcQ",
            raw_info={},
        )
        self.assertIsNone(result.video_path)

    def test_duration_float_type(self):
        result = AudioDownloadResult(
            file_path="/data/audio/test.mp3",
            title="测试视频",
            duration=120.5,
            cover_url=None,
            platform="bilibili",
            video_id="BV123",
            raw_info={},
        )
        self.assertIsInstance(result.duration, float)

    def test_duration_int_auto_converted(self):
        result = AudioDownloadResult(
            file_path="/data/audio/test.mp3",
            title="测试视频",
            duration=120,
            cover_url=None,
            platform="bilibili",
            video_id="BV123",
            raw_info={},
        )
        self.assertEqual(result.duration, 120.0)

    def test_platform_values_for_all_supported(self):
        for platform in ["bilibili", "youtube", "douyin", "kuaishou"]:
            with self.subTest(platform=platform):
                result = AudioDownloadResult(
                    file_path="/data/audio/test.mp3",
                    title="test",
                    duration=0,
                    cover_url=None,
                    platform=platform,
                    video_id="test_id",
                    raw_info={},
                )
                self.assertEqual(result.platform, platform)

    def test_raw_info_empty_dict(self):
        result = AudioDownloadResult(
            file_path="/data/audio/test.mp3",
            title="test",
            duration=0,
            cover_url=None,
            platform="bilibili",
            video_id="BV123",
            raw_info={},
        )
        self.assertEqual(result.raw_info, {})

    def test_raw_info_complex(self):
        complex_info = {
            "id": "BV123",
            "title": "Title",
            "uploader": "Author",
            "duration": 120,
            "tags": ["tag1", "tag2"],
            "formats": [{"format_id": "mp3", "ext": "mp3"}],
        }
        result = AudioDownloadResult(
            file_path="/data/audio/test.mp3",
            title="Title",
            duration=120,
            cover_url=None,
            platform="bilibili",
            video_id="BV123",
            raw_info=complex_info,
        )
        self.assertEqual(result.raw_info["uploader"], "Author")
        self.assertEqual(len(result.raw_info["tags"]), 2)

    def test_equality_same_values(self):
        a = AudioDownloadResult(
            file_path="/data/a.mp3", title="T", duration=1.0,
            cover_url=None, platform="bilibili", video_id="BV1", raw_info={}
        )
        b = AudioDownloadResult(
            file_path="/data/a.mp3", title="T", duration=1.0,
            cover_url=None, platform="bilibili", video_id="BV1", raw_info={}
        )
        self.assertEqual(a, b)

    def test_inequality_different_values(self):
        a = AudioDownloadResult(
            file_path="/data/a.mp3", title="T", duration=1.0,
            cover_url=None, platform="bilibili", video_id="BV1", raw_info={}
        )
        b = AudioDownloadResult(
            file_path="/data/a.mp3", title="T", duration=1.0,
            cover_url=None, platform="bilibili", video_id="BV2", raw_info={}
        )
        self.assertNotEqual(a, b)


class TestTranscriptDataClasses(unittest.TestCase):
    """TranscriptSegment / TranscriptResult 数据类测试"""

    def test_transcript_segment_create(self):
        seg = TranscriptSegment(start=0.0, end=5.5, text="大家好")
        self.assertEqual(seg.start, 0.0)
        self.assertEqual(seg.end, 5.5)
        self.assertEqual(seg.text, "大家好")

    def test_transcript_result_create_with_full_text(self):
        segs = [
            TranscriptSegment(start=0.0, end=3.0, text="第一段"),
            TranscriptSegment(start=3.0, end=6.0, text="第二段"),
        ]
        result = TranscriptResult(
            language="zh",
            full_text="第一段 第二段",
            segments=segs,
            raw={"source": "whisper"},
        )
        self.assertEqual(result.language, "zh")
        self.assertEqual(result.full_text, "第一段 第二段")
        self.assertEqual(len(result.segments), 2)
        self.assertEqual(result.raw["source"], "whisper")

    def test_transcript_result_raw_defaults_to_none(self):
        result = TranscriptResult(
            language=None, full_text="text", segments=[]
        )
        self.assertIsNone(result.raw)

    def test_transcript_result_language_none(self):
        result = TranscriptResult(
            language=None, full_text="text", segments=[]
        )
        self.assertIsNone(result.language)


class TestNoteResult(unittest.TestCase):
    """NoteResult 数据类测试"""

    def test_create_note_result(self):
        audio = AudioDownloadResult(
            file_path="/data/audio/test.mp3",
            title="测试视频",
            duration=120.5,
            cover_url="https://example.com/cover.jpg",
            platform="bilibili",
            video_id="BV1vc411b7Wa",
            raw_info={},
        )
        transcript = TranscriptResult(
            language="zh",
            full_text="大家好 欢迎收看",
            segments=[
                TranscriptSegment(start=0.0, end=5.0, text="大家好"),
                TranscriptSegment(start=5.0, end=10.0, text="欢迎收看"),
            ],
        )
        note = NoteResult(
            markdown="# 笔记标题\n\n笔记内容...",
            transcript=transcript,
            audio_meta=audio,
        )
        self.assertEqual(note.markdown, "# 笔记标题\n\n笔记内容...")
        self.assertEqual(note.audio_meta.title, "测试视频")
        self.assertEqual(note.transcript.language, "zh")
        self.assertEqual(len(note.transcript.segments), 2)
        self.assertEqual(note.transcript.segments[0].text, "大家好")

    def test_note_result_empty_markdown(self):
        audio = AudioDownloadResult(
            file_path="/data/audio/test.mp3",
            title="test",
            duration=0,
            cover_url=None,
            platform="bilibili",
            video_id="BV123",
            raw_info={},
        )
        transcript = TranscriptResult(language="en", full_text="", segments=[])
        note = NoteResult(markdown="", transcript=transcript, audio_meta=audio)
        self.assertEqual(note.markdown, "")
        self.assertEqual(note.transcript.language, "en")
        self.assertEqual(len(note.transcript.segments), 0)


class TestDownloadQuality(unittest.TestCase):
    """DownloadQuality 枚举测试"""

    def test_enum_values(self):
        self.assertEqual(DownloadQuality.fast.value, "fast")
        self.assertEqual(DownloadQuality.medium.value, "medium")
        self.assertEqual(DownloadQuality.slow.value, "slow")

    def test_enum_is_string(self):
        self.assertEqual(DownloadQuality.fast, "fast")

    def test_enum_comparison(self):
        self.assertTrue(DownloadQuality.fast == "fast")
        self.assertFalse(DownloadQuality.fast == "medium")

    def test_enum_iteration(self):
        values = [q.value for q in DownloadQuality]
        self.assertIn("fast", values)
        self.assertIn("medium", values)
        self.assertIn("slow", values)


class TestQualitMap(unittest.TestCase):
    """QUALITY_MAP 质量映射测试"""

    def test_quality_map_keys(self):
        self.assertEqual(set(QUALITY_MAP.keys()), {"fast", "medium", "slow"})

    def test_quality_map_values_are_numeric_strings(self):
        for key, value in QUALITY_MAP.items():
            with self.subTest(key=key):
                self.assertIsInstance(value, str)
                int(value)

    def test_quality_map_value_order(self):
        fast_val = int(QUALITY_MAP["fast"])
        medium_val = int(QUALITY_MAP["medium"])
        slow_val = int(QUALITY_MAP["slow"])
        self.assertLess(fast_val, medium_val)
        self.assertLess(medium_val, slow_val)


class TestNoteError(unittest.TestCase):
    """NoteError 异常类测试"""

    def test_create_note_error(self):
        err = NoteError("选择的平台不受支持", NoteErrorEnum.PLATFORM_NOT_SUPPORTED)
        self.assertEqual(err.message, "选择的平台不受支持")
        self.assertEqual(err.code, NoteErrorEnum.PLATFORM_NOT_SUPPORTED)

    def test_note_error_is_exception(self):
        err = NoteError("test message", NoteErrorEnum.PLATFORM_NOT_SUPPORTED)
        self.assertIsInstance(err, Exception)

    def test_note_error_str(self):
        err = NoteError("选择的平台不受支持", NoteErrorEnum.PLATFORM_NOT_SUPPORTED)
        self.assertEqual(str(err), "选择的平台不受支持")

    def test_note_error_can_be_raised(self):
        with self.assertRaises(NoteError):
            raise NoteError("test", NoteErrorEnum.PLATFORM_NOT_SUPPORTED)

    def test_note_error_caught_as_exception(self):
        with self.assertRaises(Exception):
            raise NoteError("test", NoteErrorEnum.PLATFORM_NOT_SUPPORTED)


class TestNoteErrorEnum(unittest.TestCase):
    """NoteErrorEnum 枚举测试"""

    def test_platform_not_supported_code(self):
        self.assertEqual(NoteErrorEnum.PLATFORM_NOT_SUPPORTED.code, 300101)

    def test_platform_not_supported_message(self):
        self.assertEqual(NoteErrorEnum.PLATFORM_NOT_SUPPORTED.message, "选择的平台不受支持")


if __name__ == "__main__":
    unittest.main()
