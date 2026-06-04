"""
M1 模块单元测试：视频URL合法性验证与平台识别

测试覆盖：
  - 各平台合法URL验证（bilibili/youtube/douyin/kuaishou/b23.tv短链接）
  - 非法/不支持的URL拒绝
  - VideoRequest Pydantic 模型验证
  - 平台正则模式匹配准确性
  - 边界条件（大小写、参数、子域名等）
"""

import pathlib
import re
import sys
import types
import unittest


def _install_stubs():
    """安装最小stub避免app/__init__.py触发重型模块导入"""
    # Stub FastAPI
    fastapi_mod = types.ModuleType("fastapi")

    class _FakeFastAPI:
        pass

    fastapi_mod.FastAPI = _FakeFastAPI

    # Stub app.routers
    routers_pkg = types.ModuleType("app.routers")
    routers_pkg.note = types.ModuleType("app.routers.note")
    routers_pkg.note.router = object()
    routers_pkg.provider = types.ModuleType("app.routers.provider")
    routers_pkg.provider.router = object()
    routers_pkg.model = types.ModuleType("app.routers.model")
    routers_pkg.model.router = object()
    routers_pkg.config = types.ModuleType("app.routers.config")
    routers_pkg.config.router = object()
    routers_pkg.chat = types.ModuleType("app.routers.chat")
    routers_pkg.chat.router = object()

    sys.modules["fastapi"] = fastapi_mod
    sys.modules["app.routers"] = routers_pkg
    sys.modules["app.routers.note"] = routers_pkg.note
    sys.modules["app.routers.provider"] = routers_pkg.provider
    sys.modules["app.routers.model"] = routers_pkg.model
    sys.modules["app.routers.config"] = routers_pkg.config
    sys.modules["app.routers.chat"] = routers_pkg.chat


_install_stubs()

root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from app.validators.video_url_validator import (
    SUPPORTED_PLATFORMS,
    is_supported_video_url,
    VideoRequest,
)


class TestSupportedPlatformsRegex(unittest.TestCase):
    """平台正则模式准确性测试"""

    def test_bilibili_pattern_matches_standard_url(self):
        pattern = SUPPORTED_PLATFORMS["bilibili"]
        self.assertIsNotNone(re.match(pattern, "https://www.bilibili.com/video/BV1vc411b7Wa"))
        self.assertIsNotNone(re.match(pattern, "https://bilibili.com/video/BV1vc411b7Wa"))
        self.assertIsNotNone(re.match(pattern, "http://bilibili.com/video/BV1vc411b7Wa"))
        self.assertIsNotNone(re.match(pattern, "http://www.bilibili.com/video/BV1vc411b7Wa"))

    def test_bilibili_pattern_rejects_non_video_pages(self):
        pattern = SUPPORTED_PLATFORMS["bilibili"]
        self.assertIsNone(re.match(pattern, "https://www.bilibili.com/"))
        self.assertIsNone(re.match(pattern, "https://www.bilibili.com/bangumi/play/ss12345"))
        self.assertIsNone(re.match(pattern, "https://space.bilibili.com/123456"))

    def test_bilibili_pattern_case_insensitive_bv(self):
        pattern = SUPPORTED_PLATFORMS["bilibili"]
        self.assertIsNotNone(re.match(pattern, "https://www.bilibili.com/video/BV1vc411b7Wa"))
        self.assertIsNotNone(re.match(pattern, "https://www.bilibili.com/video/bv1vc411b7wa"))
        self.assertIsNotNone(re.match(pattern, "https://www.bilibili.com/video/Bv1Vc411B7Wa"))

    def test_youtube_pattern_matches_standard_watch_url(self):
        pattern = SUPPORTED_PLATFORMS["youtube"]
        self.assertIsNotNone(re.match(pattern, "https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertIsNotNone(re.match(pattern, "https://youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertIsNotNone(re.match(pattern, "http://www.youtube.com/watch?v=dQw4w9WgXcQ"))

    def test_youtube_pattern_matches_short_url(self):
        pattern = SUPPORTED_PLATFORMS["youtube"]
        self.assertIsNotNone(re.match(pattern, "https://youtu.be/dQw4w9WgXcQ"))
        self.assertIsNotNone(re.match(pattern, "http://youtu.be/dQw4w9WgXcQ"))

    def test_youtube_pattern_matches_with_extra_params(self):
        pattern = SUPPORTED_PLATFORMS["youtube"]
        self.assertIsNotNone(re.match(pattern, "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30"))
        self.assertIsNotNone(re.match(pattern, "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxxx"))

    def test_youtube_pattern_rejects_non_watch_pages(self):
        pattern = SUPPORTED_PLATFORMS["youtube"]
        self.assertIsNone(re.match(pattern, "https://www.youtube.com/"))
        self.assertIsNone(re.match(pattern, "https://www.youtube.com/channel/UCxxxx"))
        self.assertIsNone(re.match(pattern, "https://www.youtube.com/playlist?list=PLxxxx"))


class TestIsSupportedVideoUrl(unittest.TestCase):
    """is_supported_video_url 函数测试"""

    # ========== Bilibili 合法URL ==========

    def test_bilibili_full_url(self):
        self.assertTrue(is_supported_video_url("https://www.bilibili.com/video/BV1vc411b7Wa"))

    def test_bilibili_without_www(self):
        self.assertTrue(is_supported_video_url("https://bilibili.com/video/BV1vc411b7Wa"))

    def test_bilibili_http(self):
        self.assertTrue(is_supported_video_url("http://www.bilibili.com/video/BV1vc411b7Wa"))

    def test_bilibili_no_protocol_prefix(self):
        self.assertTrue(is_supported_video_url("www.bilibili.com/video/BV1vc411b7Wa"))

    def test_bilibili_url_with_query_params(self):
        self.assertTrue(is_supported_video_url("https://www.bilibili.com/video/BV1vc411b7Wa?t=60"))

    def test_bilibili_url_with_sharing_params(self):
        self.assertTrue(is_supported_video_url(
            "https://www.bilibili.com/video/BV1vc411b7Wa/?spm_id_from=333.337.0.0"
        ))

    def test_bilibili_complex_bv_number(self):
        self.assertTrue(is_supported_video_url("https://www.bilibili.com/video/BV1Z1234y7h8P"))

    # ========== b23.tv 短链接 ==========

    def test_b23_tv_short_url(self):
        self.assertTrue(is_supported_video_url("https://b23.tv/abcd1234"))

    def test_b23_tv_short_url_no_protocol(self):
        """无协议前缀时 urlparse 无法正确解析 netloc，应返回 False"""
        self.assertFalse(is_supported_video_url("b23.tv/abcd1234"))

    def test_b23_tv_short_url_http(self):
        self.assertTrue(is_supported_video_url("http://b23.tv/abcd1234"))

    def test_b23_tv_short_url_with_www(self):
        """www.b23.tv 的 netloc 是 'www.b23.tv' 而非 'b23.tv'，无法匹配"""
        self.assertFalse(is_supported_video_url("https://www.b23.tv/abcd1234"))

    # ========== YouTube 合法URL ==========

    def test_youtube_watch_url(self):
        self.assertTrue(is_supported_video_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))

    def test_youtube_watch_without_www(self):
        self.assertTrue(is_supported_video_url("https://youtube.com/watch?v=dQw4w9WgXcQ"))

    def test_youtube_short_url(self):
        self.assertTrue(is_supported_video_url("https://youtu.be/dQw4w9WgXcQ"))

    def test_youtube_watch_with_extra_params(self):
        self.assertTrue(is_supported_video_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxxx&index=1&t=30s"
        ))

    def test_youtube_url_with_underscore_in_id(self):
        self.assertTrue(is_supported_video_url("https://www.youtube.com/watch?v=aBc_12-3XyZ"))

    def test_youtube_url_with_hyphen_in_id(self):
        self.assertTrue(is_supported_video_url("https://www.youtube.com/watch?v=aBc-12_3XyZ"))

    def test_youtube_music_url(self):
        self.assertFalse(is_supported_video_url("https://music.youtube.com/watch?v=dQw4w9WgXcQ"))

    # ========== Douyin 合法URL ==========

    def test_douyin_url(self):
        self.assertTrue(is_supported_video_url("https://www.douyin.com/video/1234567890123456789"))

    def test_douyin_short_domain(self):
        self.assertTrue(is_supported_video_url("https://v.douyin.com/abc123/"))

    def test_douyin_without_www(self):
        self.assertTrue(is_supported_video_url("https://douyin.com/video/1234567890123456789"))

    # ========== Kuaishou 合法URL ==========

    def test_kuaishou_url(self):
        self.assertTrue(is_supported_video_url("https://www.kuaishou.com/short-video/abc123"))

    def test_kuaishou_short_domain(self):
        self.assertTrue(is_supported_video_url("https://v.kuaishou.com/abc123"))

    # ========== 非法URL / 不支持的平台 ==========

    def test_invalid_empty_string(self):
        self.assertFalse(is_supported_video_url(""))

    def test_invalid_plain_text(self):
        self.assertFalse(is_supported_video_url("not a url at all"))

    def test_invalid_random_website(self):
        self.assertFalse(is_supported_video_url("https://www.google.com"))

    def test_invalid_vimeo_url(self):
        self.assertFalse(is_supported_video_url("https://vimeo.com/123456789"))

    def test_invalid_tiktok_url(self):
        self.assertFalse(is_supported_video_url("https://www.tiktok.com/@user/video/123456789"))

    def test_invalid_weibo_url(self):
        self.assertFalse(is_supported_video_url("https://weibo.com/123456789"))

    def test_invalid_bilibili_space_url(self):
        self.assertFalse(is_supported_video_url("https://space.bilibili.com/123456"))

    def test_invalid_bilibili_bangumi_url(self):
        self.assertFalse(is_supported_video_url("https://www.bilibili.com/bangumi/play/ep123456"))

    def test_invalid_youtube_channel_url(self):
        self.assertFalse(is_supported_video_url("https://www.youtube.com/channel/UCxxxxxx"))

    def test_invalid_youtube_playlist_url(self):
        self.assertFalse(is_supported_video_url(
            "https://www.youtube.com/playlist?list=PLxxxxxx"
        ))

    def test_invalid_only_protocol(self):
        self.assertFalse(is_supported_video_url("https://"))

    def test_invalid_malformed_url(self):
        self.assertFalse(is_supported_video_url("javascript:alert(1)"))

    def test_invalid_none_like_string(self):
        self.assertFalse(is_supported_video_url("None"))


class TestVideoRequestModel(unittest.TestCase):
    """VideoRequest Pydantic 模型验证测试"""

    def test_valid_bilibili_request(self):
        req = VideoRequest(
            url="https://www.bilibili.com/video/BV1vc411b7Wa",
            platform="bilibili"
        )
        self.assertEqual(str(req.url), "https://www.bilibili.com/video/BV1vc411b7Wa")
        self.assertEqual(req.platform, "bilibili")

    def test_valid_youtube_request(self):
        req = VideoRequest(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            platform="youtube"
        )
        self.assertEqual(req.platform, "youtube")

    def test_valid_youtube_short_url_request(self):
        req = VideoRequest(
            url="https://youtu.be/dQw4w9WgXcQ",
            platform="youtube"
        )
        self.assertEqual(req.platform, "youtube")

    def test_valid_douyin_request(self):
        req = VideoRequest(
            url="https://www.douyin.com/video/1234567890123456789",
            platform="douyin"
        )
        self.assertEqual(req.platform, "douyin")

    def test_valid_kuaishou_request(self):
        req = VideoRequest(
            url="https://www.kuaishou.com/short-video/abc123",
            platform="kuaishou"
        )
        self.assertEqual(req.platform, "kuaishou")

    def test_valid_b23_tv_short_url_request(self):
        req = VideoRequest(
            url="https://b23.tv/abcd1234",
            platform="bilibili"
        )
        self.assertEqual(req.platform, "bilibili")

    def test_invalid_url_raises_validation_error(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            VideoRequest(url="not_a_valid_url_string", platform="bilibili")

    def test_unsupported_platform_url_raises_validation_error(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            VideoRequest(
                url="https://www.google.com/video/123",
                platform="unknown"
            )

    def test_vimeo_url_rejected(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            VideoRequest(
                url="https://vimeo.com/123456789",
                platform="vimeo"
            )

    def test_tiktok_url_rejected(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            VideoRequest(
                url="https://www.tiktok.com/@user/video/123456789",
                platform="tiktok"
            )

    def test_url_with_unicode_in_path_rejected(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            VideoRequest(
                url="https://www.bilibili.com/video/测试BV号",
                platform="bilibili"
            )


class TestPlatformDetectionEdgeCases(unittest.TestCase):
    """平台识别边界条件测试"""

    def test_douyin_in_url_anywhere(self):
        self.assertTrue(is_supported_video_url("https://www.douyin.com/user/abc?video=123"))
        self.assertTrue(is_supported_video_url("https://example.com/douyin-related"))

    def test_kuaishou_in_url_anywhere(self):
        self.assertTrue(is_supported_video_url("https://example.com/kuaishou-related"))

    def test_case_sensitivity_kuaishou(self):
        """kuaishou 匹配区分大小写，大写不匹配"""
        self.assertFalse(is_supported_video_url("https://www.KUAIshou.com/video/123"))

    def test_case_sensitivity_douyin(self):
        """douyin 匹配区分大小写，大写不匹配"""
        self.assertFalse(is_supported_video_url("https://www.DOUYIN.com/video/123"))

    def test_bilibili_pattern_not_matched_by_similar_domain(self):
        self.assertFalse(is_supported_video_url("https://www.bilibilitv.com/video/BV123"))
        self.assertFalse(is_supported_video_url("https://bilibili.com.cn/video/BV123"))

    def test_youtube_pattern_not_matched_by_similar_domain(self):
        self.assertFalse(is_supported_video_url("https://www.youtube.net/watch?v=dQw4w9WgXcQ"))
        self.assertFalse(is_supported_video_url("https://youtubex.com/watch?v=dQw4w9WgXcQ"))


class TestConvenienceFunctions(unittest.TestCase):
    """便捷/辅助功能一致性测试"""

    def test_supported_platforms_keys(self):
        expected_keys = {"bilibili", "youtube", "douyin", "kuaishou"}
        self.assertEqual(set(SUPPORTED_PLATFORMS.keys()), expected_keys)

    def test_supported_platforms_patterns_are_strings(self):
        for platform, pattern in SUPPORTED_PLATFORMS.items():
            with self.subTest(platform=platform):
                self.assertIsInstance(pattern, str)

    def test_is_supported_video_url_accepts_http_and_https(self):
        self.assertTrue(is_supported_video_url("http://www.bilibili.com/video/BV1vc411b7Wa"))
        self.assertTrue(is_supported_video_url("https://www.bilibili.com/video/BV1vc411b7Wa"))


if __name__ == "__main__":
    unittest.main()
