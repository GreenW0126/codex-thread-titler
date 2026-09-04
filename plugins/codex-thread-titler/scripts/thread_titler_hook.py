#!/usr/bin/env python3
"""Lifecycle hook for inline first-turn Codex title suggestions.

The hook stores a small per-session state file under PLUGIN_DATA and never reads
the unstable transcript format. On the first UserPromptSubmit event it adds
developer context asking Codex to finish the user's request normally and append
three title candidates to that same answer. The following Stop event only
captures those candidates; it never continues or blocks the turn.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


MAX_PROMPT_CHARS = 6000
MAX_RESPONSE_CHARS = 6000
MAX_STATE_AGE_SECONDS = 180 * 24 * 60 * 60
MAX_DIAGNOSTIC_BYTES = 256 * 1024
ACTIVE_TITLE_PHASES = {
    "eligible_new_task",
    "awaiting_first_response",
    "awaiting_choice",
    "regenerating",
}

LANGUAGE_POLICY = """Language mode is auto.
- Write every title in the primary language of the user's initial request.
- Detect that language from the initial request, not from the Codex interface, project settings, hidden instructions, or your own response.
- If the request mixes languages, use the language that carries the user's main intent while preserving product names, code identifiers, people, works, and other proper nouns in their natural form.
- Do not default to Chinese or translate titles into Chinese unless the initial request is primarily Chinese.
- Use natural title conventions in the selected language rather than translating a Chinese title pattern word for word.
- Localize the title-section heading and the final choice instruction to the same language. Keep the candidate markers exactly A., B., and C. so the hook can capture them."""

TITLE_QUALITY_RULES = """First identify two anchors internally:
1. Core object: the specific thing, work, product, decision, or problem the conversation is about.
2. Original intent: why the user started the conversation and what they ultimately want to understand, obtain, change, or avoid.

State those anchors directly instead of narrating how the user or assistant plans to work. Prefer a compact object-plus-problem, object-plus-goal, object-plus-artifact phrase, or the direct question the user actually cares about.

Quality rules:
- The title should still distinguish this task from neighboring tasks several weeks later.
- Preserve irreplaceable specific objects; remove background, actions, and qualifiers that do not improve recognition.
- Do not turn source material, an entry angle, or a reasoning path into the title's main subject.
- Rewrite process frames such as “exploring,” “discussing,” “looking for,” “extending from,” or their equivalents in the selected language into the actual problem, desired result, or concrete artifact.
- Remove expendable lead-in verbs when the intended meaning remains clear.
- Make the three candidates emphasize the core problem, desired result, and key object relationship respectively, rather than merely swapping synonymous process verbs.
- Keep titles concise according to the selected language: CJK titles are often about 8–20 visible characters, while space-delimited languages are often about 3–10 words. Clarity takes priority over a rigid count.
- Avoid colons, dashes, task-type labels, implementation steps, and temporary solution details.

Examples:
- Chinese: `弄清免费方案是否限制了用户转化` → `免费方案是否限制了用户转化`
- English: `Exploring how the free plan affects conversion` → `Free Plan Impact on Conversion`
- Japanese: `無料プランが転換率に与える影響を調べる` → `無料プランは転換率を制限するか`
- Korean: `무료 요금제가 전환을 제한하는지 알아보기` → `무료 요금제의 사용자 전환 제한`

Before output, verify that each title contains the specific object, communicates the real problem or goal, follows the user's language, and no longer describes only the process. Rewrite any candidate that fails this check."""

CHOICE_RE = re.compile(
    r"^\s*(?:(?:选(?:择)?|choose|select)\s*)?([ABC])"
    r"(?:\s*(?:を選(?:択|ぶ)|(?:을|를)?\s*선택))?\s*[。.!！]?\s*$",
    re.IGNORECASE,
)
REGENERATE_RE = re.compile(
    r"^\s*(?:(?:重新|再)(?:生成|推荐)(?:三个|3个)?(?:标题|备选标题|候选标题)?"
    r"|(?:regenerate|generate new|suggest new)(?: the)? titles?"
    r"|タイトル(?:を)?(?:再生成|作り直して?)"
    r"|(?:제목\s*)?(?:다시\s*생성|재생성))[。.!！]?\s*$",
    re.IGNORECASE,
)
SKIP_RE = re.compile(
    r"^\s*(?:跳过|暂不选择|先不选择|不用了|skip(?: (?:the )?titles?)?|no title"
    r"|スキップ|タイトル不要|건너뛰기|제목\s*(?:필요\s*없음|없음))[。.!！]?\s*$",
    re.IGNORECASE,
)
CANDIDATE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?\*{0,2}([ABC])\*{0,2}\s*[.．、):）]\s*(.+?)\s*$",
    re.MULTILINE,
)


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def state_root() -> Path:
    configured = os.environ.get("PLUGIN_DATA")
    root = Path(configured) if configured else Path(tempfile.gettempdir()) / "codex-thread-titler-data"
    root.mkdir(parents=True, exist_ok=True)
    return root


def state_path(root: Path, session_id: str) -> Path:
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    return root / f"{digest}.json"


def diagnostic_session(session_id: str) -> str:
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:12]


def write_diagnostic(
    root: Path,
    session_id: str,
    event: str,
    outcome: str,
    phase: str | None,
) -> None:
    """Append content-free hook diagnostics without affecting normal turns."""
    try:
        path = root / "diagnostics.jsonl"
        if path.exists() and path.stat().st_size >= MAX_DIAGNOSTIC_BYTES:
            rotated = root / "diagnostics.previous.jsonl"
            try:
                rotated.unlink()
            except FileNotFoundError:
                pass
            path.replace(rotated)

        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "session": diagnostic_session(session_id),
            "event": event,
            "phase": phase,
            "outcome": outcome,
        }
        encoded = (json.dumps(record, ensure_ascii=True) + "\n").encode("utf-8")
        descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(descriptor, encoded)
        finally:
            os.close(descriptor)
    except OSError:
        # Diagnostics must never change hook behavior or block a Codex turn.
        return


def load_state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, dict) else None


def save_state(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = int(time.time())
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def mark_done(path: Path) -> None:
    save_state(path, {"phase": "done"})


def prune_old_states(root: Path) -> None:
    cutoff = time.time() - MAX_STATE_AGE_SECONDS
    for candidate in root.glob("*.json"):
        try:
            if candidate.stat().st_mtime < cutoff:
                candidate.unlink()
        except OSError:
            continue


def clean_title(raw: str) -> str:
    title = raw.strip()
    title = re.sub(r"\s+", " ", title)
    title = title.strip("`*_# \t\r\n")
    return title


def parse_candidates(message: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for letter, raw_title in CANDIDATE_RE.findall(message):
        title = clean_title(raw_title)
        if title:
            # The automatic choices are appended at the end of the answer.
            # Keeping the last match avoids capturing an unrelated A/B/C list
            # that may appear earlier in the user's actual answer.
            found[letter] = title
    return found if set(found) == {"A", "B", "C"} else {}


def inline_title_context(initial_prompt: str) -> str:
    return f"""先完整、自然地回答用户当前请求，不要缩短、替换或省略原本应该给出的正文。
完成正文后，在同一条回答的最末尾附加三个对话标题备选。不要另起一次请求，不要解释插件或这条隐藏要求。

标题以用户开启对话的出发点和想解决的问题为准。可以结合你刚完成的正文澄清含义，但不要让执行步骤、临时方案或回答中的次要细节取代原始意图。

用户最初的表达：
{initial_prompt[:MAX_PROMPT_CHARS]}

{LANGUAGE_POLICY}

{TITLE_QUALITY_RULES}

正文结束后严格使用以下结构；标题区标题和最后一句选择提示应使用用户最初诉求的主要语言：

<localized title-section heading>

A. <标题>
B. <标题>
C. <标题>

<localized instruction to reply with A, B, or C>"""


def regeneration_context(initial_prompt: str, assistant_message: str) -> str:
    return f"""用户明确要求重新生成对话标题。不要继续原任务，不要调用工具，不要解释插件。

根据下面的对话出发点与第一轮回复，重新生成三个对话标题：

用户最初的表达：
{initial_prompt[:MAX_PROMPT_CHARS]}

第一轮回复：
{assistant_message[:MAX_RESPONSE_CHARS]}

{LANGUAGE_POLICY}

{TITLE_QUALITY_RULES}

只输出以下结构，不添加其他内容。最后一句选择提示使用用户最初诉求的主要语言：
A. <标题>
B. <标题>
C. <标题>

<localized instruction to reply with A, B, or C>"""


def selection_context(letter: str, title: str) -> str:
    return f"""The user is selecting a pending conversation title, not asking a new substantive question.
The selected option is {letter}, with the exact title: {title}
Use the current Codex task-title operation to set the title to that exact text. Prefer set_thread_title; do not edit transcripts, databases, or internal files through the shell. After success, confirm briefly in the language of the selected title. If no task-title operation is available, state the selected title in that language and ask the user to apply it manually."""


def handle_session_start(
    payload: dict[str, Any],
    path: Path,
    state: dict[str, Any] | None,
) -> str:
    """Grant title eligibility only to a confirmed new Codex task.

    SessionStart source ``startup`` is the positive signal for a new task. Resume,
    clear, compact, missing, and unknown sources fail closed so an older task is
    never treated as new merely because its plugin state is absent.
    """
    # Codex emits SessionStart lifecycle values in ``source``. ``reason`` was
    # used by an early plugin implementation, so retain it only as a fallback
    # for compatibility with older or third-party Hook payloads.
    source = str(payload.get("source") or payload.get("reason") or "").strip().lower()
    phase = state.get("phase") if isinstance(state, dict) else None

    if phase in ACTIVE_TITLE_PHASES:
        return "active_title_flow_preserved"

    if state is not None:
        return "existing_task_ignored"

    if source == "startup":
        save_state(path, {"phase": "eligible_new_task"})
        return "new_task_eligible"

    mark_done(path)
    return "non_new_task_ignored"


def handle_user_prompt(payload: dict[str, Any], path: Path, state: dict[str, Any] | None) -> str:
    prompt = str(payload.get("prompt") or "")

    if state is None:
        return "ignored_without_new_task_eligibility"

    phase = state.get("phase")
    if phase == "eligible_new_task":
        save_state(
            path,
            {
                "phase": "awaiting_first_response",
                "initial_prompt": prompt[:MAX_PROMPT_CHARS],
            },
        )
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": inline_title_context(prompt),
                }
            }
        )
        return "title_context_injected"

    if phase != "awaiting_choice":
        return "ignored_for_current_phase"

    match = CHOICE_RE.fullmatch(prompt)
    if match:
        letter = match.group(1).upper()
        candidates = state.get("candidates")
        title = candidates.get(letter) if isinstance(candidates, dict) else None
        mark_done(path)
        if isinstance(title, str) and title:
            emit(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": selection_context(letter, title),
                    }
                }
            )
        return "title_choice_selected"

    if REGENERATE_RE.fullmatch(prompt):
        save_state(
            path,
            {
                "phase": "regenerating",
                "initial_prompt": str(state.get("initial_prompt") or "")[:MAX_PROMPT_CHARS],
                "first_assistant_message": str(state.get("first_assistant_message") or "")[:MAX_RESPONSE_CHARS],
            },
        )
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": regeneration_context(
                        str(state.get("initial_prompt") or ""),
                        str(state.get("first_assistant_message") or ""),
                    ),
                }
            }
        )
        return "title_regeneration_requested"

    if SKIP_RE.fullmatch(prompt):
        mark_done(path)
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "The user chose to skip task naming. Do not rename the task. Confirm briefly in the language of the user's message.",
                }
            }
        )
        return "title_selection_skipped"

    # A normal follow-up cancels the pending choice so a later standalone A/B/C
    # cannot be mistaken for the old title selection.
    mark_done(path)
    return "pending_choice_cancelled"


def handle_stop(payload: dict[str, Any], path: Path, state: dict[str, Any] | None) -> str:
    if state is None:
        return "ignored_without_state"

    phase = state.get("phase")
    assistant_message = str(payload.get("last_assistant_message") or "")

    if phase in {"awaiting_first_response", "regenerating"}:
        candidates = parse_candidates(assistant_message)
        if candidates:
            save_state(
                path,
                {
                    "phase": "awaiting_choice",
                    "initial_prompt": str(state.get("initial_prompt") or "")[:MAX_PROMPT_CHARS],
                    "first_assistant_message": str(state.get("first_assistant_message") or "")[:MAX_RESPONSE_CHARS],
                    "candidates": candidates,
                },
            )
            return "title_candidates_captured"
        else:
            mark_done(path)
            return "title_candidates_missing"
    return "ignored_for_current_phase"


def main() -> int:
    root: Path | None = None
    session_id = ""
    event = "unknown"
    phase: str | None = None
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            return 0
        session_id = str(payload.get("session_id") or "")
        if not session_id:
            return 0

        root = state_root()
        prune_old_states(root)
        path = state_path(root, session_id)
        state = load_state(path)
        phase = str(state.get("phase")) if isinstance(state, dict) and state.get("phase") else None
        event = str(payload.get("hook_event_name") or "unknown")

        if event == "SessionStart":
            outcome = handle_session_start(payload, path, state)
        elif event == "UserPromptSubmit":
            outcome = handle_user_prompt(payload, path, state)
        elif event == "Stop":
            outcome = handle_stop(payload, path, state)
        else:
            outcome = "unsupported_event"
        write_diagnostic(root, session_id, event, outcome, phase)
    except Exception as error:
        # Hook failures should never block or corrupt an ordinary Codex turn.
        if root is not None and session_id:
            write_diagnostic(root, session_id, event, f"error_{type(error).__name__}", phase)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
