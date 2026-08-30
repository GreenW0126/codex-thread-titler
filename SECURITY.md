# Security Policy

## Supported versions

Security fixes are provided for the latest published version of Codex Thread Titler.

| Version | Supported |
| --- | --- |
| Latest release | Yes |
| Older releases | No |

## Reporting a vulnerability

Please do not open a public issue for a suspected security vulnerability.

Use GitHub's private vulnerability reporting feature for this repository. Include the affected version, reproduction steps, potential impact, and any suggested mitigation. Reports will be reviewed as availability permits; no fixed response-time commitment is currently offered.

Codex Thread Titler runs local lifecycle Hooks. It does not intentionally access the network or transmit conversation data. Diagnostic logs contain only timestamps, Hook event names, state phases, outcomes, and shortened one-way session hashes; they do not contain prompts, assistant responses, or generated titles.
