# Security Policy

## Supported versions

Only the latest release of flow-next receives security fixes. The plugin runs locally inside your agent harness (Claude Code / Codex / Droid) with no hosted components — the attack surface is the bundled `flowctl` CLI, the shell scripts, and the skill/hook prompts.

| Version | Supported |
|---|---|
| latest release | ✅ |
| older releases | ❌ — upgrade first |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

- Preferred: [GitHub private vulnerability reporting](https://github.com/gmickel/flow-next/security/advisories/new)
- Or email: [gordon@mickel.tech](mailto:gordon@mickel.tech)

Include reproduction steps and the affected version (`flowctl --version` or the README badge). You'll get an acknowledgment within a few days; fixes ship as a normal release with credit unless you prefer otherwise.

## Scope notes

- Prompt-injection hardening of skills (e.g. Ralph guardrails, review gates) is in scope — flow-next's autonomous loops are designed to be gated and receipted, and bypasses are bugs.
- Vulnerabilities in host platforms (Claude Code, Codex, Droid, Cursor, Grok) or optional third-party tools (`clawpatch`, `lavish-axi`, RepoPrompt) belong upstream — but if flow-next's integration makes them worse, report here too.
