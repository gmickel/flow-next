# Harness & Permissions (HP)

The checked-in agent-**harness** configuration - the front-door layer that makes agents safe and effective in a repo, and the one no published rubric covers. Prime assesses the codebase everywhere else; this file is the check set for the harness config itself.

This file carries the **collection view**: for each HP criterion, how to probe it, which harness mechanism implements it, its evidence class, and the per-harness instantiation of the five function classes. The **pass conditions, the scored-core designation, the criterion-to-score map, and the N/A whitelist all live in [pillars.md](pillars.md)** and are pointed at here, never restated. Remediation safety rules for harness artifacts live at the bottom of this file (verbatim, hard) and feed [remediation.md](remediation.md).

**Two governing principles (from pillars.md, not re-argued here):**

1. **Score the FUNCTION, not the file.** Five function classes; each harness implements a different subset. Detect ACTIVE harnesses first, grade only those, map each criterion to the active harness's native mechanism, N/A otherwise. One deep harness + an AGENTS.md bridge outscores five shallow stubs.
2. **Zero harness config is today's normal** - the group reads as headroom, not shame. EXCEPT the two P0 findings below, which fire regardless of score.

**Scored core = HP1, HP2, HP5, HP7, HP9, HP12** (per pillars.md's landed criterion-to-score map); the rest are informational at first.

---

## The five function classes

| Class | What it governs |
|---|---|
| **(a) instructions** | the agent instruction file(s) - canonical + cross-harness bridge |
| **(b) permission/sandbox posture** | allow/deny/ask rules, access-scoping, sandbox + trust posture |
| **(c) lifecycle hooks** | edit-time / commit / task-end hook wiring and its content |
| **(d) MCP config** | MCP server declarations, secret handling, hygiene |
| **(e) cloud-agent/env bootstrap** | cloud-agent env config, devcontainer/setup parity |

---

## Active-harness detection (do this FIRST)

Grade only harnesses that are ACTIVE - a config dir/file present AND not stale by commit recency. Never fail a Codex-only repo for a missing `.claude/hooks`; never fail a Cursor repo for lacking `permissions.deny`. Detection signals per harness:

| Harness | Active if present | Instruction file |
|---|---|---|
| Claude Code | `.claude/` (settings.json, hooks, agents), `.mcp.json`, `CLAUDE.md` | `CLAUDE.md` |
| Codex | `.codex/config.toml`, `AGENTS.md` | `AGENTS.md` |
| Cursor | `.cursor/` (rules, hooks, mcp.json), `.cursorignore` | `.cursor/rules/*.mdc` or `AGENTS.md` |
| Copilot | `.github/copilot-instructions.md`, `copilot-setup-steps.yml` | `.github/copilot-instructions.md` |
| Droid (Factory) | `.factory/`, `AGENTS.md` | `AGENTS.md` |
| OpenCode | `opencode.json`, `AGENTS.md` | `AGENTS.md` |

A config dir present but untouched for months (commit recency) is treated as stale and its HP criteria fall to N/A via the pillars.md whitelist (HP1-HP16 inactive-harness row).

---

## HP criteria - probe + mechanism view

Pass conditions are in pillars.md; this table gives the **probe** (how evidence is collected, bounded), the harness **mechanism** it maps to, the **evidence class**, and the **scored-core** flag. Collection is HOST-INLINE with security-sensitive quoting (**key names only, never values**); hook-content classification inputs come from the emitter. **Hooks are READ, never executed, during assessment.**

| ID | Function class | Probe (bounded) | Evidence class | Scored-core |
|---|---|---|---|---|
| HP1 | (a) instructions | Resolve the symlink graph, then diff canonical vs bridge file | file diff summary | **scored** |
| HP2 | (b) posture | Parse the permissions file for the active harness | parse result | **scored** |
| HP3 | (b) posture | Cross-ref allow rules against Phase-2-verified commands | allow-rule list vs manifest | informational |
| HP4 | (b) posture | Flag allow rules naming a nonexistent command | dangling-rule list | informational |
| HP5 | (b) posture | Check `.env` family + repo-specific secret paths are deny-read; derive candidates from the repo's own `.gitignore` secret-shaped entries | deny-rule presence | **scored** |
| HP6 | (b) posture | Check curl/wget/`rm -rf` denied or sandbox-gated; push-class on ask | rule presence | informational |
| HP7 | (c) hooks | Enumerate configured hooks; READ each including the COMMAND STRINGS (never execute); classify real gate / stub / suspicious | hook content quoted | **scored** (+ P0) |
| HP8 | (c) hooks | Flag heavy whole-project checks wired to PostToolUse (fires per edit) | hook + trigger | informational |
| HP9 | (d) MCP | Check `.mcp.json`-family values use `${VAR}` indirection; flag inline literal secret shapes | key name only | **scored** (+ P0) |
| HP10 | (d) MCP | Check stdio commands resolve; versions pinned not `@latest`; server count sane | command + version | informational |
| HP11 | (d) MCP | Check each server has a when-to-use line in the agent file | doc presence | informational |
| HP12 | (b) posture | Check personal-scope files absent from the git index; if committed, feed content into HP3/HP5/HP7 | git-index membership | **scored** |
| HP13 | (e) bootstrap | Check cloud-agent env config parity with verified install commands | config vs commands | informational |
| HP14 | (b) posture | Sandbox/isolation posture ladder (none < deny-rules < sandbox/allowlist < devcontainer firewall) | posture tier | informational |
| HP15 | (b) posture | Flag dangling `paths:` / `applyTo:` globs matching zero tracked files | stale-glob list | informational |
| HP16 | (e) bootstrap | Check the PR template carries an agent-evidence section | template section | informational |

---

## Per-harness instantiation table

The criterion maps to a DIFFERENT native mechanism per harness. Grade the active harness against ITS mechanism (or N/A). File + syntax per function class:

| Function class | Claude Code | Codex | Cursor | Copilot | Droid | OpenCode |
|---|---|---|---|---|---|---|
| (a) instructions | `CLAUDE.md` | `AGENTS.md` | `.cursor/rules/*.mdc` / `AGENTS.md` | `.github/copilot-instructions.md` | `AGENTS.md` | `AGENTS.md` |
| (b) posture | `.claude/settings.json` `permissions` (allow/deny/ask) | `.codex/config.toml` (`approval_policy`, `sandbox`, trust) | `.cursorignore` (access-scoping, NOT allow/deny) | limited native posture (N/A most rows) | `.factory` config | `opencode.json` `permission` |
| (c) hooks | `.claude/settings.json` `hooks` (PreToolUse / PostToolUse / Stop) | no native lifecycle hooks (N/A) | `.cursor/hooks` (afterFileEdit / beforeShellExecution) | no native lifecycle hooks (N/A) | PostToolUse (Factory hooks) | plugin hooks |
| (d) MCP | `.mcp.json` | `.codex/config.toml` `[mcp_servers]` | `.cursor/mcp.json` | `.vscode/mcp.json` / repo MCP | (per platform) | `opencode.json` `mcp` |
| (e) cloud/env bootstrap | devcontainer / `.claude` env | `config.toml` | `.cursor/environment.json` | `copilot-setup-steps.yml` (`.github/workflows`) | `.factory` env | `opencode.json` |

A cell reading "N/A" means the harness has no native mechanism for that class; the criterion is N/A for that harness (never a fail), and the function is graded on whichever active harness DOES implement it. Cursor "permissions" are access-scoping via `.cursorignore`, not an allow/deny model - grade HP5 against `.cursorignore` carrying `.env*` / keys / secrets dirs.

---

## P0 rules (fire regardless of score)

Two findings surface as **P0 regardless of the group score** - they are safety-critical, not readiness headroom:

1. **Inline secrets in MCP config (HP9).** Any inline literal secret shape in an `.mcp.json`-family value = P0. Quote the **KEY NAME only, never the value**, with "rotate it - it is already in git history".
2. **Suspicious hook content (HP7).** A configured hook whose command strings make network calls, touch credential paths, or use obfuscation = P0 security finding. Committed hook config is an RCE vector (CVE-2025-59536 class) - it executes on teammates' machines at workspace trust. A stub hook (no real content) is a fail-with-quote, not a P0; a suspicious hook is the P0.

**Read-never-execute vs exercise-what-you-scaffold (gap 27).** During ASSESSMENT prime READS hook content (bounded) and NEVER executes it - the whole point of the P0 screen is that reading a hostile hook must not run it. During REMEDIATION the distinction inverts: any hook prime OFFERS is built from verified commands, read-back gated, and EXERCISED in the same pass (per the anti-stub rule - prime never scaffolds what would pass its own checks unexercised). Assessment does not run hooks; remediation runs the one it just wrote.

---

## Remediation safety rules (hard - verbatim into remediation.md)

Deny/ask rules are the ONLY permissions artifact safe to scaffold (they apply without workspace trust and only restrict; model on anthropics/claude-code examples/settings). Allow rules: propose only entries derived from commands prime itself executed successfully in Phase 2, and state that project allow rules are inert until the workspace-trust dialog is accepted. Never scaffold: defaultMode changes, bypassPermissions, danger-full-access, approval_policy never, additionalDirectories, HTTP hooks, MCP server installs. Hooks offered = built from verified commands + read-back gated + exercised in the same pass. Secret findings: key name only, never the value, always "rotate".

**Never report "allow rules present" as "prompts eliminated"** - project allow rules are inert until the workspace-trust dialog is accepted; remediation text must say so.
