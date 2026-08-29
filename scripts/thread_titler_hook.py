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

TITLE_QUALITY_RULES = """先在心里提炼两个锚点：
1. 核心对象：这次对话究竟在谈什么具体事物、作品、产品或问题；
2. 原始意图：用户为什么开启对话，最终想判断、获得、改变或避免什么。

标题应直接呈现这两个锚点，而不是复述用户或助手准备怎样展开工作。优先使用“具体对象＋关键问题/目标/产物”的名词短语，或用户真正关心的直接问题。

质量规则：
- 数周后只看标题，仍能辨认这次对话与同一项目里的其他对话有何不同；
- 保留不可替换的具体对象，删除不增加辨识度的对象、动作和背景；
- 不要把阅读材料、切入角度或推理路径误写成标题主干；
- 避免“从……寻找……”“从……延伸……”“基于……探索……”“围绕……讨论……”等过程性句式；
- “寻找、延伸、探索、梳理、分析、研究、讨论、优化”等词如果只描述过程，应改写为问题、目标或明确产物；
- 三个备选应分别突出核心问题、目标结果或关键对象关系，而不是只替换近义动词。

改写示例：
- 差：从《信条》影评寻找佳作
  好：《信条》影评中的佳作推荐
- 差：从奥德赛评论延伸作品
  好：奥德赛评论关联作品
- 差：从《奥德赛》延伸的电影书单
  好：《奥德赛》关联电影书单
- 差：减少项目对话增多后难以辨认内容的问题
  好：清晰辨认多项目中的不同对话
- 差：弄清免费方案是否限制了用户转化
  好：免费方案是否限制了用户转化

输出前逐项自检：是否包含具体对象，是否说清真正问题或目标，是否仍在描述过程。若答案不理想，先重写再输出。"""

CHOICE_RE = re.compile(
    r"^\s*(?:选(?:择)?\s*)?([ABCabc])\s*[。.!！]?\s*$"
)
REGENERATE_RE = re.compile(
    r"^\s*(?:重新|再)(?:生成|推荐)(?:三个|3个)?(?:标题|备选标题|候选标题)?[。.!！]?\s*$"
)
SKIP_RE = re.compile(r"^\s*(?:跳过|暂不选择|先不选择|不用了)[。.!！]?\s*$")
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
完成正文后，在同一条回答的最末尾附加三个中文对话标题备选。不要另起一次请求，不要解释插件或这条隐藏要求。

标题以用户开启对话的出发点和想解决的问题为准。可以结合你刚完成的正文澄清含义，但不要让执行步骤、临时方案或回答中的次要细节取代原始意图。

用户最初的表达：
{initial_prompt[:MAX_PROMPT_CHARS]}

{TITLE_QUALITY_RULES}

形式要求：使用紧凑的名词短语、目标短语或直接问题，通常为 8–20 个中文字符。删去“让、弄清、找出、解决、减少、讨论”等不必要的引导动词。不要使用冒号、破折号、任务类型标签、执行步骤或临时方案。三个标题不能偏离原始意图。

正文结束后严格使用以下结尾格式：

对话标题

A. <标题>
B. <标题>
C. <标题>

请回复 A、B 或 C。"""


def regeneration_context(initial_prompt: str, assistant_message: str) -> str:
    return f"""用户明确要求重新生成对话标题。不要继续原任务，不要调用工具，不要解释插件。

根据下面的对话出发点与第一轮回复，重新生成三个中文对话标题：

用户最初的表达：
{initial_prompt[:MAX_PROMPT_CHARS]}

第一轮回复：
{assistant_message[:MAX_RESPONSE_CHARS]}

{TITLE_QUALITY_RULES}

形式要求：使用紧凑的名词短语、目标短语或直接问题，通常为 8–20 个中文字符。删去“让、弄清、找出、解决、减少、讨论”等不必要的引导动词。不要使用冒号、破折号、任务类型标签、执行步骤或临时方案。三个标题不能偏离原始意图。

只输出以下格式，不添加其他内容：
A. <标题>
B. <标题>
C. <标题>

请回复 A、B 或 C。"""


def selection_context(letter: str, title: str) -> str:
    return f"""用户正在选择刚才的对话标题，而不是提出新的业务问题。
所选项为 {letter}，对应标题是“{title}”。
请使用当前 Codex 任务的重命名工具将当前任务标题设置为这个精确文本。优先使用 set_thread_title；不要通过 shell 修改 transcript、数据库或内部文件。成功后只需简短确认。如果当前环境没有任务重命名工具，明确告诉用户所选标题并请其手动应用。"""


def handle_user_prompt(payload: dict[str, Any], path: Path, state: dict[str, Any] | None) -> None:
    prompt = str(payload.get("prompt") or "")

    if state is None:
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
        return

    phase = state.get("phase")
    if phase != "awaiting_choice":
        return

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
        return

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
        return

    if SKIP_RE.fullmatch(prompt):
        mark_done(path)
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "用户选择跳过本次对话命名。不要重命名任务，只需简短确认。",
                }
            }
        )
        return

    # A normal follow-up cancels the pending choice so a later standalone A/B/C
    # cannot be mistaken for the old title selection.
    mark_done(path)


def handle_stop(payload: dict[str, Any], path: Path, state: dict[str, Any] | None) -> None:
    if state is None:
        return

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
        else:
            mark_done(path)


def main() -> int:
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
        event = payload.get("hook_event_name")

        if event == "UserPromptSubmit":
            handle_user_prompt(payload, path, state)
        elif event == "Stop":
            handle_stop(payload, path, state)
    except Exception:
        # Hook failures should never block or corrupt an ordinary Codex turn.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
