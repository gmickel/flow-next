---
satisfies: [R3, R4]
---
# fn-201-opencode-install-path-from-canonical.2 Generate OpenCode agents and slash-command stubs at install time

## Description
Extend scripts/install-opencode.sh to GENERATE (not copy, not commit a mirror) OpenCode-format files at install time from canonical sources. Generated paths join the task-1 ownership manifest.

Agents: for every plugins/flow-next/agents/*.md write <dest>/agents/flow-next-<name>.md. Body after the closing --- fence is byte-identical. Frontmatter: keep description; set mode: subagent; represent every canonical disallowedTools denial via keys from the PINNED OpenCode agent frontmatter schema — pin the actual key set from OpenCode docs/source first and record it in the generator (OpenCode documents both tools: boolean maps and permission: allow/ask/deny with a narrower key set; prefer the representation that unambiguously covers edit/write/task/bash denial, expected tools:). The full canonical token set is Edit, Write, Task, Bash (plan-sync.md carries Bash — mapping only three tokens fails on the canonical tree). FAIL CLOSED with a named error on stderr, non-zero exit, no file written, in three cases: (a) a disallowedTools token without a mapping, (b) a denial with no representable key in the pinned schema (guard the OUTPUT side too — a silently-ignored emitted key is broader access than canonical intent), (c) readonly: true disagreeing with the file's disallowedTools (readonly is the Cursor-native write-denial marker, permission-relevant — cross-check, never drop as cosmetic). Drop canonical model: family aliases (session-model inherit, same degradation as Cursor). Genuinely non-permission keys (name, model, color, user-invocable) are dropped, not fatal.

Commands roster (single source of truth): canonical plugins/flow-next/commands/<name>.md files whose skill dir plugins/flow-next/skills/flow-next-<name>/SKILL.md exists — mapping rule exactly commands/<name>.md -> skills/flow-next-<name>/; stub filename flow-next-<name>.md (prefix added once, never doubled). Two named exceptions: commands/uninstall.md is command-only (no skill dir) — copy its body verbatim as commands/flow-next-uninstall.md; commands/setup.md is EXCLUDED by name (setup's platform cascade has no OpenCode rung and falls through to PLATFORM=codex, writing Codex-shaped instructions that contradict the installed stubs) — no stub, exclusion stated in the generator, docs (task 4) say setup is unsupported with the manual alternative. Every other stub: frontmatter description from the skill's own description; body tells the host to load and follow the installed skill's SKILL.md (absolute installed path) and forward $ARGUMENTS.

Extract the translators into a stdlib Python helper under plugins/flow-next/scripts/lib/ (same home as verify_tracker_manifest.py) so unittests drive fixtures without an OpenCode binary; the bash installer invokes it. Still no canonical prose edits and no committed OpenCode tree.

Touches: scripts/install-opencode.sh, plugins/flow-next/scripts/lib/opencode*.py
Files:
- scripts/install-opencode.sh (extend)
- plugins/flow-next/scripts/lib/opencode_generate.py (or similarly named helper)
- plugins/flow-next/agents/*.md (read-only)
- plugins/flow-next/commands/*.md (read-only roster)
- plugins/flow-next/skills/*/SKILL.md (read-only descriptions)

## Acceptance
R3: every canonical agents/*.md yields <dest>/agents/flow-next-<name>.md with byte-identical body, mode: subagent, and denials matching that file's disallowedTools via pinned-schema keys — including plan-sync's Bash; fixtures prove all three fail-closed cases (unmapped token, unrepresentable denial, readonly/disallowedTools disagreement) abort with a named error and emit nothing; model: dropped; generated frontmatter uses ONLY keys from the pinned schema. R4: every skill-backed command in the roster has a generated commands/flow-next-<name>.md whose description matches the skill and whose body forwards $ARGUMENTS to the installed SKILL.md absolute path; flow-next-uninstall.md is the verbatim command body; no setup stub exists and the generator names the exclusion; phrase-triggered skills get no stub. Re-run refreshes generated files in place; manifest lists them.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
