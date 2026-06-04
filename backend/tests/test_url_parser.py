"""
M1 模块单元测试：视频ID提取与短链接解析

测试覆盖：
  - Bilibili BV号提取（标准URL + 短链接Mock）
  - YouTube视频ID提取（watch?v= + youtu.be）
  - Douyin视频ID提取
  - 无效/不完整URL返回None
  - b23.tv短链接解析（Mock网络请求）
  - 网络异常处理（连接错误、超时等）
"""

import pathlib
import sys
import types
import unittest
from unittest.mock import patch, MagicMock


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

from app.utils.url_parser import extract_video_id, resolve_bilibili_short_url


class TestExtractVideoIdBilibili(unittest.TestCase):
    """Bilibili平台视频ID提取测试"""

    def test_extract_bv_id_standard_url(self):
        bv = extract_video_id(
            "https://www.bilibili.com/video/BV1vc411b7Wa", "bilibili"
        )
        self.assertEqual(bv, "BV1vc411b7Wa")

    def test_extract_bv_id_without_www(self):
        bv = extract_video_id(
            "https://bilibili.com/video/BV1vc411b7Wa", "bilibili"
        )
        self.assertEqual(bv, "BV1vc411b7Wa")

    def test_extract_bv_id_with_query_params(self):
        bv = extract_video_id(
            "https://www.bilibili.com/video/BV1vc411b7Wa?t=120&p=1", "bilibili"
        )
        self.assertEqual(bv, "BV1vc411b7Wa")

    def test_extract_bv_id_lowercase_bv_prefix(self):
        """正则 r'BV([0-9A-Za-z]+)' 区分大小写，小写bv不匹配，返回None"""
        bv = extract_video_id(
            "https://www.bilibili.com/video/Bv1Vc411B7Wa", "bilibili"
        )
        self.assertIsNone(bv)

    def test_extract_bv_id_long_number(self):
        bv = extract_video_id(
            "https://www.bilibili.com/video/BV1Z1234y7h8P", "bilibili"
        )
        self.assertEqual(bv, "BV1Z1234y7h8P")

    def test_extract_bv_id_av_format_unsupported(self):
        bv = extract_video_id(
            "https://www.bilibili.com/video/av12345678", "bilibili"
        )
        self.assertIsNone(bv)

    def test_extract_bv_id_no_video_path(self):
        bv = extract_video_id(
            "https://www.bilibili.com/bangumi/play/ss12345", "bilibili"
        )
        self.assertIsNone(bv)

    def test_extract_bv_id_empty_url(self):
        bv = extract_video_id("", "bilibili")
        self.assertIsNone(bv)

    def test_extract_bv_id_b23_in_url_but_not_short_link(self):
        """URL中包含b23.tv字样但并非短链接格式"""
        bv = extract_video_id(
            "https://www.bilibili.com/video/BV1vc411b7Wa?ref=b23.tv", "bilibili"
        )
        self.assertEqual(bv, "BV1vc411b7Wa")

    @patch("app.utils.url_parser.resolve_bilibili_short_url")
    def test_extract_bv_id_from_short_url(self, mock_resolve):
        mock_resolve.return_value = "https://www.bilibili.com/video/BV1vc411b7Wa"
        bv = extract_video_id("https://b23.tv/abcd1234", "bilibili")
        self.assertEqual(bv, "BV1vc411b7Wa")
        mock_resolve.assert_called_once_with("https://b23.tv/abcd1234")

    @patch("app.utils.url_parser.resolve_bilibili_short_url")
    def test_extract_bv_id_from_short_url_resolve_failed(self, mock_resolve):
        mock_resolve.return_value = None
        bv = extract_video_id("https://b23.tv/abcd1234", "bilibili")
        self.assertIsNone(bv)

    @patch("app.utils.url_parser.resolve_bilibili_short_url")
    def test_extract_bv_id_from_short_url_resolved_to_non_video(self, mock_resolve):
        mock_resolve.return_value = "https://www.bilibili.com/"
        bv = extract_video_id("https://b23.tv/abcd1234", "bilibili")
        self.assertIsNone(bv)


class TestExtractVideoIdYoutube(unittest.TestCase):
    """YouTube平台视频ID提取测试"""

    def test_extract_yt_id_standard_watch(self):
        vid = extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"
        )
        self.assertEqual(vid, "dQw4w9WgXcQ")

    def test_extract_yt_id_without_www(self):
        vid = extract_video_id(
            "https://youtube.com/watch?v=dQw4w9WgXcQ", "youtube"
        )
        self.assertEqual(vid, "dQw4w9WgXcQ")

    def test_extract_yt_id_short_url(self):
        vid = extract_video_id(
            "https://youtu.be/dQw4w9WgXcQ", "youtube"
        )
        self.assertEqual(vid, "dQw4w9WgXcQ")

    def test_extract_yt_id_with_extra_params(self):
        vid = extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxxx&t=30s",
            "youtube"
        )
        self.assertEqual(vid, "dQw4w9WgXcQ")

    def test_extract_yt_id_with_underscore(self):
        vid = extract_video_id(
            "https://www.youtube.com/watch?v=aBc_12-3XyZ", "youtube"
        )
        self.assertEqual(vid, "aBc_12-3XyZ")

    def test_extract_yt_id_short_url_with_underscore(self):
        vid = extract_video_id(
            "https://youtu.be/aBc_12-3XyZ", "youtube"
        )
        self.assertEqual(vid, "aBc_12-3XyZ")

    def test_extract_yt_id_http(self):
        vid = extract_video_id(
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"
        )
        self.assertEqual(vid, "dQw4w9WgXcQ")

    def test_extract_yt_id_not_a_watch_url(self):
        vid = extract_video_id(
            "https://www.youtube.com/playlist?list=PLxxxx", "youtube"
        )
        self.assertIsNone(vid)

    def test_extract_yt_id_empty_url(self):
        vid = extract_video_id("", "youtube")
        self.assertIsNone(vid)

    def test_extract_yt_id_incomplete_v_param(self):
        vid = extract_video_id(
            "https://www.youtube.com/watch?v=abc", "youtube"
        )
        self.assertIsNone(vid)


class TestExtractVideoIdDouyin(unittest.TestCase):
    """Douyin平台视频ID提取测试"""

    def test_extract_douyin_id_standard(self):
        vid = extract_video_id(
            "https://www.douyin.com/video/1234567890123456789", "douyin"
        )
        self.assertEqual(vid, "1234567890123456789")

    def test_extract_douyin_id_without_www(self):
        vid = extract_video_id(
            "https://douyin.com/video/1234567890123456789", "douyin"
        )
        self.assertEqual(vid, "1234567890123456789")

    def test_extract_douyin_id_with_query(self):
        vid = extract_video_id(
            "https://www.douyin.com/video/1234567890123456789?previous_page=xxx",
            "douyin"
        )
        self.assertEqual(vid, "1234567890123456789")

    def test_extract_douyin_id_short_url(self):
        vid = extract_video_id(
            "https://v.douyin.com/abc123/", "douyin"
        )
        self.assertIsNone(vid)

    def test_extract_douyin_id_not_video_page(self):
        vid = extract_video_id(
            "https://www.douyin.com/user/abc123", "douyin"
        )
        self.assertIsNone(vid)

    def test_extract_douyin_id_empty_url(self):
        vid = extract_video_id("", "douyin")
        self.assertIsNone(vid)


class TestExtractVideoIdEdgeCases(unittest.TestCase):
    """视频ID提取边界条件测试"""

    def test_unknown_platform_returns_none(self):
        vid = extract_video_id(
            "https://www.example.com/video/123", "unknown_platform"
        )
        self.assertIsNone(vid)

    def test_empty_platform_returns_none(self):
        vid = extract_video_id(
            "https://www.bilibili.com/video/BV1vc411b7Wa", ""
        )
        self.assertIsNone(vid)

    def test_very_long_url(self):
        long_url = "https://www.bilibili.com/video/BV1vc411b7Wa?" + "x" * 10000
        bv = extract_video_id(long_url, "bilibili")
        self.assertEqual(bv, "BV1vc411b7Wa")

    def test_bilibili_multiple_bv_in_url(self):
        bv = extract_video_id(
            "https://www.bilibili.com/video/BV11111111111?ref=BV22222222222",
            "bilibili"
        )
        self.assertEqual(bv, "BV11111111111")

    def test_youtube_v_param_last_when_multiple(self):
        vid = extract_video_id(
            "https://www.youtube.com/watch?v=first123456&v=second23456",
            "youtube"
        )
        self.assertEqual(vid, "first123456")


class TestResolveBilibiliShortUrl(unittest.TestCase):
    """b23.tv短链接解析测试（Mock网络请求）"""

    @patch("app.utils.url_parser.requests.head")
    def test_resolve_success(self, mock_head):
        mock_response = MagicMock()
        mock_response.url = "https://www.bilibili.com/video/BV1vc411b7Wa"
        mock_head.return_value = mock_response

        result = resolve_bilibili_short_url("https://b23.tv/abcd1234")
        self.assertEqual(result, "https://www.bilibili.com/video/BV1vc411b7Wa")
        mock_head.assert_called_once_with(
            "https://b23.tv/abcd1234", allow_redirects=True
        )

    @patch("app.utils.url_parser.requests.head")
    def test_resolve_success_with_params(self, mock_head):
        mock_response = MagicMock()
        mock_response.url = "https://www.bilibili.com/video/BV1vc411b7Wa?t=60"
        mock_head.return_value = mock_response

        result = resolve_bilibili_short_url("https://b23.tv/abcd1234")
        self.assertEqual(result, "https://www.bilibili.com/video/BV1vc411b7Wa?t=60")

    @patch("app.utils.url_parser.requests.head")
    def test_resolve_connection_error(self, mock_head):
        import requests as req_mod
        mock_head.side_effect = req_mod.ConnectionError("Network unreachable")

        result = resolve_bilibili_short_url("https://b23.tv/abcd1234")
        self.assertIsNone(result)

    @patch("app.utils.url_parser.requests.head")
    def test_resolve_timeout(self, mock_head):
        import requests as req_mod
        mock_head.side_effect = req_mod.Timeout("Request timed out")

        result = resolve_bilibili_short_url("https://b23.tv/abcd1234")
        self.assertIsNone(result)

    @patch("app.utils.url_parser.requests.head")
    def test_resolve_general_request_exception(self, mock_head):
        import requests as req_mod
        mock_head.side_effect = req_mod.RequestException("Generic error")

        result = resolve_bilibili_short_url("https://b23.tv/abcd1234")
        self.assertIsNone(result)

    @patch("app.utils.url_parser.requests.head")
    def test_resolve_redirect_to_non_bilibili(self, mock_head):
        mock_response = MagicMock()
        mock_response.url = "https://www.example.com/some-page"
        mock_head.return_value = mock_response

        result = resolve_bilibili_short_url("https://b23.tv/abcd1234")
        self.assertEqual(result, "https://www.example.com/some-page")


if __name__ == "__main__":
    unittest.main()
