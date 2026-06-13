import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import types
import unittest
from pathlib import Path


def _make_stubs():
    """构建 universal_gpt 测试所需的轻量 stub 模块，避免触发完整 import 链。"""
    app_mod = types.ModuleType("app")
    gpt_pkg = types.ModuleType("app.gpt")
    models_pkg = types.ModuleType("app.models")

    base_mod = types.ModuleType("app.gpt.base")

    class _GPT:
        pass

    base_mod.GPT = _GPT

    prompt_builder_mod = types.ModuleType("app.gpt.prompt_builder")

    def _generate_base_prompt(**_kwargs):
        return "prompt"

    prompt_builder_mod.generate_base_prompt = _generate_base_prompt

    prompt_mod = types.ModuleType("app.gpt.prompt")
    prompt_mod.BASE_PROMPT = ""
    prompt_mod.AI_SUM = ""
    prompt_mod.SCREENSHOT = ""
    prompt_mod.LINK = ""
    prompt_mod.MERGE_PROMPT = "merge"

    utils_mod = types.ModuleType("app.gpt.utils")

    def _fix_markdown(text):
        return text

    utils_mod.fix_markdown = _fix_markdown

    request_chunker_mod = types.ModuleType("app.gpt.request_chunker")

    class _RequestChunker:
        def __init__(self, *_args, **_kwargs):
            pass

        def group_texts_by_budget(self, texts, _builder, **_kwargs):
            return [texts]

    request_chunker_mod.RequestChunker = _RequestChunker

    gpt_model_mod = types.ModuleType("app.models.gpt_model")

    class _GPTSource:
        pass

    gpt_model_mod.GPTSource = _GPTSource

    transcriber_model_mod = types.ModuleType("app.models.transcriber_model")

    class _TranscriptSegment:
        def __init__(self, **kwargs):
            self.start = kwargs.get("start", 0)
            self.end = kwargs.get("end", 0)
            self.text = kwargs.get("text", "")

    transcriber_model_mod.TranscriptSegment = _TranscriptSegment

    return {
        "app": app_mod,
        "app.gpt": gpt_pkg,
        "app.models": models_pkg,
        "app.gpt.base": base_mod,
        "app.gpt.prompt_builder": prompt_builder_mod,
        "app.gpt.prompt": prompt_mod,
        "app.gpt.utils": utils_mod,
        "app.gpt.request_chunker": request_chunker_mod,
        "app.models.gpt_model": gpt_model_mod,
        "app.models.transcriber_model": transcriber_model_mod,
    }


class _FailingCompletions:
    def create(self, **_kwargs):
        raise Exception("Error code: 524 - bad_response_status_code")


class _DummyChat:
    def __init__(self):
        self.completions = _FailingCompletions()


class _DummyModels:
    @staticmethod
    def list():
        return []


class _DummyClient:
    def __init__(self):
        self.chat = _DummyChat()
        self.models = _DummyModels()


class TestUniversalGPTCheckpoint(unittest.TestCase):
    """测试 UniversalGPT 合并阶段的 checkpoint 持久化。

    使用 setUpClass / tearDownClass 安装和清理 sys.modules 中的 stub 模块，
    避免污染其他测试文件的 import 命名空间。
    """

    @classmethod
    def setUpClass(cls):
        # 保存原始模块引用，安装轻量 stub
        cls._originals = {}
        cls._stubs = _make_stubs()
        for name, stub_mod in cls._stubs.items():
            cls._originals[name] = sys.modules.get(name)
            sys.modules[name] = stub_mod

        # 在 stub 环境中加载 UniversalGPT
        root = pathlib.Path(__file__).resolve().parents[1]
        module_path = root / "app" / "gpt" / "universal_gpt.py"
        spec = importlib.util.spec_from_file_location("universal_gpt", module_path)
        if spec is None or spec.loader is None:
            raise ImportError("universal_gpt module spec not found")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.UniversalGPT = module.UniversalGPT

    @classmethod
    def tearDownClass(cls):
        # 还原 sys.modules，不影响后续测试文件
        for name, original in cls._originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    def test_merge_524_error_persists_checkpoint(self):
        original_attempts = os.environ.get("OPENAI_RETRY_ATTEMPTS")
        os.environ["OPENAI_RETRY_ATTEMPTS"] = "1"
        gpt = self.UniversalGPT(_DummyClient(), model="mock-model")
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                gpt.checkpoint_dir = Path(tmp_dir)

                with self.assertRaises(Exception):
                    gpt._merge_partials(["part-a", "part-b"], "task-1", "sig-1")

                checkpoint_path = gpt._checkpoint_path("task-1")
                self.assertTrue(checkpoint_path.exists())
                payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["phase"], "merge")
                self.assertEqual(payload["partials"], ["part-a", "part-b"])
        finally:
            if original_attempts is None:
                os.environ.pop("OPENAI_RETRY_ATTEMPTS", None)
            else:
                os.environ["OPENAI_RETRY_ATTEMPTS"] = original_attempts


if __name__ == "__main__":
    unittest.main()
