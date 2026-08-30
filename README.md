# Codex Thread Titler

Codex Thread Titler is a local Codex plugin that adds three concise title choices to the end of the first response in a new task. After you reply with `A`, `B`, or `C`, the plugin applies the selected title to the current task.

It is designed for people who manage many Codex tasks and want titles that preserve why each conversation started—not generic summaries of what happened along the way.

## Features

- Appends title choices to the first response without hiding or collapsing the main answer.
- Preserves the conversation's original motivation and the problem to be resolved.
- Produces three distinct Chinese title candidates.
- Renames the task only after an explicit `A`, `B`, or `C` selection.
- Supports regenerating the candidates or skipping the title step.
- Runs locally and does not access the network.

## Title style

The plugin favors compact object, goal, or question phrases. A useful title should make the task recognizable at a glance when it appears beside many other conversations.

It avoids:

- Process-oriented wording such as “explore,” “discuss,” or “find out.”
- Redundant lead-in verbs such as “clarify,” “reduce,” or “solve.”
- Colons, dashes, task-type labels, implementation steps, and temporary solutions.
- Titles based only on the latest message when the original request provides better context.

Examples:

| Avoid | Prefer |
| --- | --- |
| Keep accurate titles for Codex conversations | Accurate Codex conversation titles |
| Find out whether the free plan limits user conversion | Whether the free plan limits user conversion |
| Reduce the difficulty of identifying conversations across growing projects | Distinguishing conversations across multiple projects |

## Installation

### Requirements

- Codex desktop or Codex CLI with plugin and hook support.
- Git and Python 3.
- The built-in `$plugin-creator` skill.

### Recommended installation

Open a new Codex task and paste the following prompt:

```text
Use $plugin-creator to install the public plugin from
https://github.com/GreenW0126/codex-thread-titler.

Clone it to ~/plugins/codex-thread-titler, add it to my personal
marketplace without overwriting any existing marketplace entries,
install and enable codex-thread-titler@personal, and ask for permission
as soon as it is needed. When finished, tell me to start a new task and
review the plugin hooks.
```

Codex will clone the source, register it in the personal marketplace, and install the plugin. Approve any filesystem or network permission requests required by the installation.

When installation finishes:

1. Start a new Codex task so the plugin is loaded.
2. Open `/hooks`.
3. Review, trust, and enable `UserPromptSubmit` and `Stop` for `codex-thread-titler`.
4. Start another new task and send a first message to verify that three title choices appear at the end of the response.

This repository contains the plugin source rather than a standalone marketplace. Do not run `codex plugin marketplace add GreenW0126/codex-thread-titler`; use the personal-marketplace installation flow above.

### Updating

Open a Codex task and paste:

```text
Use $plugin-creator to update the existing plugin at
~/plugins/codex-thread-titler from
https://github.com/GreenW0126/codex-thread-titler.

Pull the latest main branch, update the Codex cachebuster, reinstall
codex-thread-titler@personal, preserve all existing marketplace entries,
and ask for permission as soon as it is needed.
```

After an update, start a new task. If the hook definition changed, review and trust the hooks again.

## Usage

1. Start a new Codex task and send your first message normally.
2. Codex answers the request in full.
3. The same response ends with three choices:

```text
Conversation titles

A. <title>
B. <title>
C. <title>

Reply with A, B, or C.
```

4. Reply with `A`, `B`, or `C` to apply that title.

You can also ask to regenerate the candidates or reply with “skip.”

## Hook permissions

After the first installation—or whenever the hook definition changes—open `/hooks` in Codex and review, trust, and enable both hooks used by this plugin:

- `UserPromptSubmit`
- `Stop`

The title choices will not appear automatically if `UserPromptSubmit` is disabled. The plugin cannot capture the choices if `Stop` is disabled.

## How it works

- `UserPromptSubmit` injects the title-generation instruction when the first user message is submitted.
- Codex completes the original request and appends the three title choices to the same response.
- `Stop` captures those choices without blocking the response or starting a continuation request.
- Candidate state is stored in the Codex-provided `PLUGIN_DATA` directory.
- The plugin does not parse unstable conversation transcripts or make network requests.

## Project structure

```text
.codex-plugin/plugin.json                 Plugin manifest
hooks/hooks.json                          Hook definitions
scripts/thread_titler_hook.py             Hook implementation
skills/codex-thread-titler/SKILL.md       Manual title skill
tests/test_thread_titler_hook.py          Behavior tests
```

## Development

Run the behavior tests:

```bash
python3 -m unittest discover -s tests -v
```

If the Codex `plugin-creator` skill is available locally, validate the plugin structure with:

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

## 中文简介

Codex Thread Titler 会在新任务的第一轮完整回复末尾自然附上三个中文标题选项。标题优先保留用户开启对话的出发点与真正想解决的问题，而不是复述讨论过程。回复 `A`、`B` 或 `C` 后，插件会将所选标题应用到当前任务，方便在多个项目和大量对话中快速辨认内容。
