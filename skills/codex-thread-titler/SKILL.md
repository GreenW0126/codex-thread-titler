---
name: codex-thread-titler
description: Generate or apply concise Codex task-title candidates that preserve why a conversation began and what problem the user wanted to resolve. Use when the user asks to title, rename, retitle, or regenerate title choices for the current Codex conversation.
---

# Codex Thread Titler

Create titles that help the user recognize why a conversation was started weeks later.

## Generate title choices

Use the initial user intent and, when available, the first assistant response to infer the original motivation and problem. Return exactly three candidates:

```text
A. <title>
B. <title>
C. <title>

请回复 A、B 或 C。
```

Each candidate must:

- preserve the conversation's starting point and the problem the user wanted to understand or solve;
- expose both the specific core object and the original intent, so the task remains recognizable weeks later;
- be a compact Chinese phrase or direct question, normally 8–20 Chinese characters;
- remove expendable lead-in verbs such as “让”“弄清”“找出”“解决”“减少”“讨论” when the meaning remains clear;
- describe the problem, desired result, or concrete artifact instead of the route taken through the discussion;
- rewrite process frames such as “从……寻找……”“从……延伸……”“基于……探索……” and “围绕……讨论……”;
- avoid colons, dashes, task-type labels, implementation steps, and temporary solution details;
- differ by emphasizing the core problem, desired result, or key object relationship—not by swapping synonymous process verbs.

Prefer forms such as:

- `保留准确的 Codex 对话标题`
- `免费方案是否限制了用户转化`
- `清晰辨认多项目中的不同对话`
- `《信条》影评中的佳作推荐`
- `《奥德赛》关联电影书单`

Reject forms such as:

- `从《信条》影评寻找佳作`
- `从奥德赛评论延伸作品`
- `基于评论探索更多作品`

Do not prematurely turn an exploratory discussion into a concrete implementation title.

## Apply a choice

Treat A, B, or C as a title selection only when three pending candidates were presented immediately beforehand or when hook-provided context explicitly identifies the pending candidates. Accept exact forms such as `A`, `选 A`, or `选择A`.

Use the current task-title operation (`set_thread_title` when available) to apply the selected title. Do not edit transcript files or internal state databases. If no task-title operation is available, state the selected title and tell the user it must be applied manually.

If the user asks to regenerate, return three new candidates. If the user says to skip, acknowledge briefly and do not rename the task.

Do not alter unrelated turns merely because this skill is installed. The bundled lifecycle hook owns automatic first-turn prompting: it asks Codex to answer normally and append the three choices to the same first response, while the Stop hook only captures those choices without continuing the turn.
