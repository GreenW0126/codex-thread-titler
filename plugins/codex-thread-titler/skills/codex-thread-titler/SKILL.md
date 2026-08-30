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

<localized instruction to reply with A, B, or C>
```

Each candidate must:

- preserve the conversation's starting point and the problem the user wanted to understand or solve;
- expose both the specific core object and the original intent, so the task remains recognizable weeks later;
- use the primary language of the user's initial request; never default to Chinese because of the interface, project, hidden instructions, or the assistant's response;
- preserve product names, code identifiers, people, works, and other proper nouns in their natural form when the request mixes languages;
- use natural title conventions in the selected language instead of translating a Chinese title pattern word for word;
- be a compact phrase or direct question: CJK titles are often about 8–20 visible characters and space-delimited titles are often about 3–10 words, but clarity takes priority over a rigid count;
- remove expendable lead-in verbs such as “explore,” “discuss,” “find out,” and their equivalents in the selected language when the meaning remains clear;
- describe the problem, desired result, or concrete artifact instead of the route taken through the discussion;
- rewrite process frames such as “exploring,” “discussing,” “looking for,” “extending from,” and their equivalents in the selected language;
- avoid colons, dashes, task-type labels, implementation steps, and temporary solution details;
- differ by emphasizing the core problem, desired result, or key object relationship—not by swapping synonymous process verbs.

Language examples:

- Chinese: `弄清免费方案是否限制了用户转化` → `免费方案是否限制了用户转化`
- English: `Exploring how the free plan affects conversion` → `Free Plan Impact on Conversion`
- Japanese: `無料プランが転換率に与える影響を調べる` → `無料プランは転換率を制限するか`
- Korean: `무료 요금제가 전환을 제한하는지 알아보기` → `무료 요금제의 사용자 전환 제한`

Localize the final choice instruction to the same language as the titles, while keeping the candidate markers exactly `A.`, `B.`, and `C.`.

Do not prematurely turn an exploratory discussion into a concrete implementation title.

## Apply a choice

Treat A, B, or C as a title selection only when three pending candidates were presented immediately beforehand or when hook-provided context explicitly identifies the pending candidates. Accept a bare letter and concise equivalents such as `选 A`, `choose A`, `Aを選択`, or `A 선택`.

Use the current task-title operation (`set_thread_title` when available) to apply the selected title. Do not edit transcript files or internal state databases. If no task-title operation is available, state the selected title and tell the user it must be applied manually.

If the user asks to regenerate in their language, return three new candidates in the primary language of the initial request. If the user says to skip, acknowledge briefly in their language and do not rename the task.

Do not alter unrelated turns merely because this skill is installed. The bundled lifecycle hook owns automatic first-turn prompting: it asks Codex to answer normally and append the three choices to the same first response, while the Stop hook only captures those choices without continuing the turn.
