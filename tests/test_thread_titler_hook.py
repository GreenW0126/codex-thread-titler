from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "thread_titler_hook.py"
SPEC = importlib.util.spec_from_file_location("thread_titler_hook", SCRIPT_PATH)
assert SPEC and SPEC.loader
HOOK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOOK)


class ThreadTitlerHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "state.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def capture(self, function, *args):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            function(*args)
        return stream.getvalue()

    def test_first_prompt_injects_inline_title_requirement(self) -> None:
        output = self.capture(
            HOOK.handle_user_prompt,
            {"prompt": "Does the free plan limit user conversion?"},
            self.path,
            None,
        )

        payload = json.loads(output)
        context = payload["hookSpecificOutput"]["additionalContext"]
        state = HOOK.load_state(self.path)

        self.assertIn("先完整、自然地回答用户当前请求", context)
        self.assertIn("同一条回答的最末尾", context)
        self.assertIn("Language mode is auto", context)
        self.assertIn("primary language of the user's initial request", context)
        self.assertIn("Do not default to Chinese", context)
        self.assertIn("<localized title-section heading>", context)
        self.assertIn("Does the free plan limit user conversion?", context)
        self.assertEqual(state["phase"], "awaiting_first_response")

    def test_regeneration_uses_same_title_quality_rules(self) -> None:
        context = HOOK.regeneration_context(
            "从《信条》的评论继续寻找类似佳作",
            "正文",
        )

        self.assertIn("Language mode is auto", context)
        self.assertIn("Core object", context)
        self.assertIn("Free Plan Impact on Conversion", context)
        self.assertIn("Make the three candidates emphasize", context)
        self.assertIn("用户最初诉求的主要语言", context)

    def test_multilingual_controls_are_recognized(self) -> None:
        for value in ("choose B", "Aを選択", "C 선택", "选 A"):
            self.assertIsNotNone(HOOK.CHOICE_RE.fullmatch(value), value)

        for value in ("regenerate titles", "タイトルを再生成", "제목 재생성", "重新生成标题"):
            self.assertIsNotNone(HOOK.REGENERATE_RE.fullmatch(value), value)

        for value in ("skip", "スキップ", "건너뛰기", "跳过"):
            self.assertIsNotNone(HOOK.SKIP_RE.fullmatch(value), value)

    def test_parser_accepts_multilingual_titles(self) -> None:
        answer = """Conversation titles
A. Free Plan Conversion Limits
B. 無料プランと転換率
C. 무료 요금제의 전환 제한

Reply with A, B, or C."""

        candidates = HOOK.parse_candidates(answer)

        self.assertEqual(candidates["A"], "Free Plan Conversion Limits")
        self.assertEqual(candidates["B"], "無料プランと転換率")
        self.assertEqual(candidates["C"], "무료 요금제의 전환 제한")

    def test_stop_captures_candidates_without_continuation(self) -> None:
        state = {
            "phase": "awaiting_first_response",
            "initial_prompt": "讨论免费方案是否限制用户转化",
        }
        answer = """这里是完整正文。

对话标题

A. 免费方案是否限制用户转化
B. 免费用户的转化阻力
C. 免费策略与用户转化

请回复 A、B 或 C。"""

        output = self.capture(
            HOOK.handle_stop,
            {"last_assistant_message": answer},
            self.path,
            state,
        )
        saved = HOOK.load_state(self.path)

        self.assertEqual(output, "")
        self.assertNotIn("decision", output)
        self.assertEqual(saved["phase"], "awaiting_choice")
        self.assertEqual(saved["candidates"]["A"], "免费方案是否限制用户转化")

    def test_parser_prefers_appended_candidate_list(self) -> None:
        answer = """正文中的旧列表：
A. 旧选项甲
B. 旧选项乙
C. 旧选项丙

对话标题
A. 保留准确的 Codex 对话标题
B. 清晰辨认多项目中的不同对话
C. 首轮回复自然附带标题选项"""

        candidates = HOOK.parse_candidates(answer)

        self.assertEqual(candidates["A"], "保留准确的 Codex 对话标题")
        self.assertEqual(candidates["C"], "首轮回复自然附带标题选项")

    def test_explicit_choice_keeps_rename_flow(self) -> None:
        state = {
            "phase": "awaiting_choice",
            "initial_prompt": "讨论标题",
            "first_assistant_message": "正文",
            "candidates": {"A": "标题甲", "B": "标题乙", "C": "标题丙"},
        }

        output = self.capture(
            HOOK.handle_user_prompt,
            {"prompt": "B"},
            self.path,
            state,
        )
        payload = json.loads(output)
        context = payload["hookSpecificOutput"]["additionalContext"]

        self.assertIn("标题乙", context)
        self.assertEqual(HOOK.load_state(self.path)["phase"], "done")


if __name__ == "__main__":
    unittest.main()
