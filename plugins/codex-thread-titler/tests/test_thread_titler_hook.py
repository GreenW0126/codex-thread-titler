from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
        start_outcome = HOOK.handle_session_start(
            {"source": "startup"},
            self.path,
            None,
        )
        output = self.capture(
            HOOK.handle_user_prompt,
            {"prompt": "Does the free plan limit user conversion?"},
            self.path,
            HOOK.load_state(self.path),
        )

        payload = json.loads(output)
        context = payload["hookSpecificOutput"]["additionalContext"]
        state = HOOK.load_state(self.path)

        self.assertEqual(start_outcome, "new_task_eligible")
        self.assertIn("先完整、自然地回答用户当前请求", context)
        self.assertIn("同一条回答的最末尾", context)
        self.assertIn("Language mode is auto", context)
        self.assertIn("primary language of the user's initial request", context)
        self.assertIn("Do not default to Chinese", context)
        self.assertIn("<localized title-section heading>", context)
        self.assertIn("Does the free plan limit user conversion?", context)
        self.assertEqual(state["phase"], "awaiting_first_response")

    def test_prompt_without_session_start_fails_closed(self) -> None:
        output = self.capture(
            HOOK.handle_user_prompt,
            {"prompt": "Continue an older task"},
            self.path,
            None,
        )

        self.assertEqual(output, "")
        self.assertIsNone(HOOK.load_state(self.path))

    def test_resume_without_state_marks_old_task_done(self) -> None:
        outcome = HOOK.handle_session_start(
            {"source": "resume"},
            self.path,
            None,
        )
        output = self.capture(
            HOOK.handle_user_prompt,
            {"prompt": "Continue after reconnecting"},
            self.path,
            HOOK.load_state(self.path),
        )

        self.assertEqual(outcome, "non_new_task_ignored")
        self.assertEqual(output, "")
        self.assertEqual(HOOK.load_state(self.path)["phase"], "done")

    def test_resume_preserves_pending_title_choice(self) -> None:
        HOOK.save_state(
            self.path,
            {
                "phase": "awaiting_choice",
                "initial_prompt": "Name a new task",
                "candidates": {"A": "Title A", "B": "Title B", "C": "Title C"},
            },
        )

        outcome = HOOK.handle_session_start(
            {"source": "resume"},
            self.path,
            HOOK.load_state(self.path),
        )

        self.assertEqual(outcome, "active_title_flow_preserved")
        self.assertEqual(HOOK.load_state(self.path)["phase"], "awaiting_choice")

    def test_compact_and_unknown_start_reasons_fail_closed(self) -> None:
        for source in ("compact", "clear", "", "unexpected"):
            path = Path(self.tempdir.name) / f"{source or 'missing'}.json"
            outcome = HOOK.handle_session_start({"source": source}, path, None)

            self.assertEqual(outcome, "non_new_task_ignored")
            self.assertEqual(HOOK.load_state(path)["phase"], "done")

    def test_legacy_reason_is_only_a_fallback(self) -> None:
        fallback_path = Path(self.tempdir.name) / "fallback.json"
        fallback_outcome = HOOK.handle_session_start(
            {"reason": "startup"},
            fallback_path,
            None,
        )
        precedence_path = Path(self.tempdir.name) / "precedence.json"
        precedence_outcome = HOOK.handle_session_start(
            {"source": "resume", "reason": "startup"},
            precedence_path,
            None,
        )

        self.assertEqual(fallback_outcome, "new_task_eligible")
        self.assertEqual(precedence_outcome, "non_new_task_ignored")
        self.assertEqual(HOOK.load_state(precedence_path)["phase"], "done")

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

    def test_diagnostics_exclude_conversation_content(self) -> None:
        root = Path(self.tempdir.name)
        secret_prompt = "private conversation text"
        secret_title = "private selected title"

        first_event = {
            "session_id": "session-containing-sensitive-id",
            "hook_event_name": "UserPromptSubmit",
            "prompt": secret_prompt,
        }
        start_event = {
            "session_id": "session-containing-sensitive-id",
            "hook_event_name": "SessionStart",
            "source": "startup",
        }
        stop_event = {
            "session_id": "session-containing-sensitive-id",
            "hook_event_name": "Stop",
            "last_assistant_message": (
                f"A. {secret_title} A\nB. {secret_title} B\nC. {secret_title} C"
            ),
        }
        with mock.patch.dict(os.environ, {"PLUGIN_DATA": str(root)}):
            with mock.patch.object(HOOK.sys, "stdin", io.StringIO(json.dumps(start_event))):
                self.capture(HOOK.main)
            with mock.patch.object(HOOK.sys, "stdin", io.StringIO(json.dumps(first_event))):
                self.capture(HOOK.main)
            with mock.patch.object(HOOK.sys, "stdin", io.StringIO(json.dumps(stop_event))):
                self.capture(HOOK.main)

        diagnostic = (root / "diagnostics.jsonl").read_text(encoding="utf-8")
        records = [json.loads(line) for line in diagnostic.splitlines()]
        self.assertNotIn(secret_prompt, diagnostic)
        self.assertNotIn(secret_title, diagnostic)
        self.assertNotIn("session-containing-sensitive-id", diagnostic)
        self.assertEqual(records[0]["event"], "SessionStart")
        self.assertEqual(records[0]["outcome"], "new_task_eligible")
        self.assertEqual(records[1]["outcome"], "title_context_injected")
        self.assertEqual(records[2]["outcome"], "title_candidates_captured")
        self.assertTrue(all(len(record["session"]) == 12 for record in records))

    def test_diagnostics_rotate_without_interrupting_hooks(self) -> None:
        root = Path(self.tempdir.name)
        path = root / "diagnostics.jsonl"
        path.write_bytes(b"x" * HOOK.MAX_DIAGNOSTIC_BYTES)

        HOOK.write_diagnostic(root, "session", "Stop", "title_candidates_captured", None)

        self.assertTrue((root / "diagnostics.previous.jsonl").exists())
        self.assertLess(path.stat().st_size, HOOK.MAX_DIAGNOSTIC_BYTES)
        if os.name != "nt":
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
