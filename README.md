# Codex Thread Titler

Codex Thread Titler adds three concise title choices to the end of the first response in a new Codex task. After you reply with `A`, `B`, or `C`, the plugin applies the selected title to the current task.

It is designed for people who manage many Codex tasks and want titles that preserve why each conversation started—not generic summaries of what happened along the way.

> [!NOTE]
> This is a community plugin distributed through a GitHub Marketplace. It is not currently listed in the official universal ChatGPT and Codex plugin directory.

## Features

- Keeps the full first response visible and appends title choices naturally at the end.
- Preserves the conversation's original motivation and the problem to be resolved.
- Uses the primary language of the user's initial request automatically.
- Produces three distinct candidates and renames only after an explicit selection.
- Supports regenerating the candidates or skipping the title step.
- Runs locally and does not access the network.

## Install from the Codex Marketplace

### Requirements

- Codex desktop or Codex CLI with plugin and hook support
- Git and Python 3.9 or later

### Support matrix

| Platform | Status | Verified environment |
| --- | --- | --- |
| macOS | Tested | macOS 15.6.1, Codex CLI 0.149.0-alpha.4, Python 3.14.6 |
| Linux | Not tested | Community testing is welcome |
| Windows | Not tested | No Windows-specific Hook command is currently provided |

The matrix describes environments actually verified by the maintainer; it does not prevent the plugin from working on other compatible versions.

Add this GitHub repository as a Marketplace:

```bash
codex plugin marketplace add GreenW0126/codex-thread-titler
```

Install the plugin:

```bash
codex plugin add codex-thread-titler@greenw0126
```

If you prefer a single shell line:

```bash
codex plugin marketplace add GreenW0126/codex-thread-titler && codex plugin add codex-thread-titler@greenw0126
```

Then:

1. Start a new Codex task so the plugin is loaded.
2. Open `/hooks`.
3. Review, trust, and enable `UserPromptSubmit` and `Stop` for `codex-thread-titler`.
4. Start another new task and send a first message.
5. Confirm that three title choices appear at the end of the first response.

The Marketplace needs to be added only once. Later installations or reinstalls use:

```bash
codex plugin add codex-thread-titler@greenw0126
```

## Update

Refresh the Marketplace snapshot and reinstall the plugin:

```bash
codex plugin marketplace upgrade greenw0126
codex plugin add codex-thread-titler@greenw0126
```

Then start a new task so Codex loads the updated plugin. If the hook definition changed, review and trust the hooks again.

To install a specific published version, add the Marketplace using a Git tag, for example:

```bash
codex plugin marketplace add GreenW0126/codex-thread-titler@v0.1.0
codex plugin add codex-thread-titler@greenw0126
```

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

## Automatic language mode

Language mode is `auto` by default. The plugin follows the language that carries the user's original intent rather than the Codex interface language or the assistant's reply.

- Chinese request → Chinese titles
- English request → English titles
- Japanese request → Japanese titles
- Korean request → Korean titles
- Mixed-language request → the main request language, with proper nouns preserved naturally

Candidate markers remain `A.`, `B.`, and `C.` in every language.

## Title quality

The plugin favors compact object, goal, or question phrases. A useful title should make the task recognizable at a glance beside many other conversations.

It avoids process-oriented wording, redundant lead-in verbs, task labels, temporary implementation details, and titles based only on the latest message.

| Avoid | Prefer |
| --- | --- |
| Keep accurate titles for Codex conversations | Accurate Codex conversation titles |
| Find out whether the free plan limits user conversion | Whether the free plan limits user conversion |
| Reduce the difficulty of identifying conversations across growing projects | Distinguishing conversations across multiple projects |

## Hook permissions

After the first installation—or whenever the hook definition changes—open `/hooks` in Codex and review, trust, and enable both hooks:

- `UserPromptSubmit`
- `Stop`

The title choices will not appear automatically if `UserPromptSubmit` is disabled. The plugin cannot capture the choices if `Stop` is disabled.

## Diagnostics

The Hook writes a small local diagnostic log to the Codex-provided `PLUGIN_DATA` directory:

```text
diagnostics.jsonl
```

Each record contains only:

- UTC timestamp
- shortened one-way session hash
- Hook event name
- state phase
- outcome code

It does not record prompts, assistant responses, generated titles, or selected title text. The active log rotates at approximately 256 KB, retaining at most one previous log file. Diagnostic failures never block a Codex response.

## Upgrading and older conversations

New tasks use the latest installed plugin version. An existing Codex task may continue referencing the absolute plugin-cache path that was active when the task started. If that cache directory is later removed, its hook can fail with an error such as:

```text
can't open file '.../old-version/scripts/thread_titler_hook.py'
```

The safest solution is to start a new task after updating the plugin.

If continuing the older task is necessary, restore the exact version directory shown in the error. From a clone of this repository, run:

```bash
python3 plugins/codex-thread-titler/scripts/restore_legacy_cache.py \
  "/absolute/path/from-the-error/to/the/old-version"
```

The helper accepts only a destination inside `~/.codex/plugins/cache`, copies only runtime files, leaves identical files untouched, and stops if any existing file has different contents. It never deletes or silently overwrites cache data.

This is a compatibility workaround for behavior observed in existing Codex tasks, not a guarantee that Codex will preserve old cache directories indefinitely.

## How it works

- `UserPromptSubmit` injects the title-generation instruction for the first user message.
- Codex completes the original request and appends three title choices to the same response.
- `Stop` captures those choices without blocking the response or starting a continuation request.
- Candidate state is stored in the Codex-provided `PLUGIN_DATA` directory.
- The plugin does not parse unstable conversation transcripts or make network requests.

## Repository structure

```text
.agents/plugins/marketplace.json                         Marketplace catalog
plugins/codex-thread-titler/.codex-plugin/plugin.json   Plugin manifest
plugins/codex-thread-titler/hooks/hooks.json            Hook definitions
plugins/codex-thread-titler/scripts/                    Runtime and compatibility tools
plugins/codex-thread-titler/skills/                     Manual title skill
plugins/codex-thread-titler/tests/                      Behavior tests
```

## Development

Run the behavior tests:

```bash
python3 -m unittest discover -s plugins/codex-thread-titler/tests -v
```

Validate the plugin structure when the built-in `plugin-creator` skill is available:

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/codex-thread-titler
```

## License

Codex Thread Titler is available under the [MIT License](LICENSE).

Security vulnerabilities should be reported privately according to [SECURITY.md](SECURITY.md).

## 中文简介

Codex Thread Titler 会在新任务的第一轮完整回复末尾自然附上三个标题选项，不会另外触发一轮请求或折叠正文。标题默认自动跟随用户最初诉求的主要语言，并优先保留对话的出发点、核心对象与真正想解决的问题。回复 `A`、`B` 或 `C` 后，插件会将所选标题应用到当前任务。

这是通过 GitHub Marketplace 分发的社区插件，目前没有进入 ChatGPT 与 Codex 的官方统一插件目录。当前已验证环境为 macOS 15.6.1、Codex CLI 0.149.0-alpha.4 和 Python 3.14.6；Linux 与 Windows 尚未测试。

首次安装时依次运行：

```bash
codex plugin marketplace add GreenW0126/codex-thread-titler
codex plugin add codex-thread-titler@greenw0126
```

安装后请新建任务，并在 `/hooks` 中检查、信任和启用 `UserPromptSubmit` 与 `Stop`。插件升级后，旧任务可能继续引用旧缓存路径；优先新建任务，如必须继续旧任务，可使用仓库内的 `restore_legacy_cache.py` 安全补齐旧缓存运行文件。
