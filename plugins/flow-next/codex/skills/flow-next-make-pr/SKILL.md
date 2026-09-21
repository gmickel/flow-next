---
name: flow-next-make-pr
description: Open a PR with a cognitive-aid body rendered from flow-next spec state via gh. Use whenever asked to make or open a PR in a flow-next repo.
user-invocable: false
allowed-tools: Read, Bash, Grep, Glob, Write, Edit, Task
---
# /flow-next:make-pr

The host authors one grounded aid object; flowctl validates, stores and renders the briefing. Read
[workflow.md](workflow.md), then its reached references. No extra model call or hand-assembled sections.
Invocation authorizes push and PR creation; `--dry-run` previews without repository writes, push, PR edits
or memory writes. The opt-in [html-lens.md](html-lens.md) loads only behind its config gate.

Define `FLOWCTL` from `${CODEX_HOME:-$HOME/.codex}/scripts/flowctl`, then
`<plugin-root>/scripts/flowctl` (two levels above this SKILL.md), then `.flow/bin/flowctl`, choosing the first
executable. Never assume a global install. Parse `$ARGUMENTS`: the positional token is `SPEC_ID`; reject
unknown flags and missing base values. Carry these values between prompt turns:

| Argument | Variable / effect |
| --- | --- |
| `--draft`, `--ready` | `DRAFT_FORCE=draft|ready`; default `auto`; last wins, note conflicts |
| `--base <ref>` or `--base=<ref>` | `BASE_REF`; default empty |
| `--memory` | `WRITE_MEMORY=1`; default 0 |
| `--dry-run` | `DRY_RUN=1`; default 0 |
| `--update` | `UPDATE_MODE=1`; default 0; refresh an existing open PR |
| `mode:autonomous` or `FLOW_AUTONOMOUS=1` | `AUTONOMOUS=1`; default 0; never sets `RALPH` |

Keep this skill inline so `plain-text numbered prompt` remains available. Resolve only missing information, one question
at a time with a recommended option; use a numbered prompt if the tool is unavailable. `NEED_INPUT:` means ask
outside Bash and rerun with the answer. Ralph/autonomous gaps hard-error instead. Ralph alone owns `PR_URL=`
stdout and harness semantics. Draft rules live in create-and-finalize; a complete chained layer can be ready
under autonomy. Never merge here. Evidence, paths and requirement attribution must be grounded in the export
and receipts, with unknowns explicit rather than invented.
