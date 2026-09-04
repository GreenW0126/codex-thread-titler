# Changelog

All notable changes to Codex Thread Titler are documented here.

## 0.1.3 - 2026-09-04

- Read the Codex `SessionStart.source` field when distinguishing `startup` from resumed tasks.
- Keep the former `reason` field as a compatibility fallback only.
- Add regression tests using the real Codex Hook payload shape and source precedence.

## 0.1.2 - 2026-08-31

- Generate title choices only after `SessionStart` confirms a new task with the `startup` reason.
- Skip restored, reconnected, cleared, compacted, unknown, and state-less older tasks by default.
- Preserve an already active title-selection flow across a task resume.
- Add regression tests for reconnection and missing-state boundaries.

## 0.1.1 - 2026-08-30

- Clarify that the plugin is distributed through a community GitHub Marketplace and is not listed in the official universal plugin directory.
- Document the verified macOS environment and untested platforms.
- Add local, content-free Hook diagnostics with bounded log rotation.
- Change Hook status messages from Chinese to English.
- Add a security policy and private vulnerability reporting guidance.

## 0.1.0 - 2026-08-30

- Append three title candidates to the end of the first response without creating a continuation turn.
- Preserve the conversation's original motivation and core problem.
- Follow the primary language of the user's initial request automatically.
- Apply the selected title after an explicit A, B, or C reply.
- Publish the plugin through a repository-backed Codex Marketplace.
- Add a safe compatibility-cache restoration tool for older Codex tasks.
