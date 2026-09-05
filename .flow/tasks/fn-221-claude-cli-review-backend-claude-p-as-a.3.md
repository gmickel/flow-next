---
satisfies: [R4, R5]
---
# fn-221-claude-cli-review-backend-claude-p-as-a.3 workflow-claude.md in the three review skills, setup menu, enumeration sweep

## Description
Give the three review skills a `workflow-claude.md`, add `claude` to every backend enumeration in skill prose, extend the setup review-backend menu, and regenerate the codex mirror (R4 and the skill half of R5). Split from the docs task so the skill-prose review runs against the conduct checklists on its own.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-impl-review/{SKILL.md,workflow-claude.md,workflow-common.md,references/backend-specs.md}`, `plugins/flow-next/skills/flow-next-plan-review/{SKILL.md,workflow-claude.md}`, `plugins/flow-next/skills/flow-next-spec-completion-review/{SKILL.md,workflow-claude.md,references/backend-at-a-glance.md}`, `plugins/flow-next/skills/flow-next-setup/workflow.md`, `plugins/flow-next/codex/**` (regenerated)
**Touches:** [plugins/flow-next/skills/**, plugins/flow-next/agents/**, plugins/flow-next/codex/**, scripts/sync-codex.sh]

### Approach
- `workflow-claude.md` in each skill: copy the sibling `workflow-cursor.md` (101 / 40 / 71 lines), swap backend name, argv notes (stdin prompt, `dontAsk`, `--tools Read Grep Glob` as the whole tool set with `--strict-mcp-config`, the diff delivered by path under `.flow/tmp/claude-review/`, `--effort` present), session notes (sessions persist in the CLI's store; re-review, deep pass and validate resume via `--resume <session_id>` from the receipt, the cursor shape), and add one advisory line: on Claude Code hosts the verdict is same-family; prefer `codex` or `host` there when family independence matters.
- Routing tables: impl-review `SKILL.md:11-15`, plan-review `SKILL.md:13-17`, completion-review `SKILL.md:11-15` gain `BACKEND=claude → workflow-claude.md`.
- Enumeration sweep (every line, not a sample): impl-review `SKILL.md` ~23-24, 37-38, 48, 65, 251; plan-review `SKILL.md` ~28, 40, 47, 53; completion-review `SKILL.md` ~23-24, 37-38, 48, 64, 83, 123, 194 (the `codex|copilot|cursor|host) RECEIPT_REQUIRED=true` case); `workflow-common.md:54,79-85` runnable examples; `references/backend-specs.md:15,19`; `references/backend-at-a-glance.md:13,17` with the grammar `claude[:<model>[:<effort>]]`. Executable dispatch arms inside the review skills that the literal-pipe grep does not catch: `flow-next-impl-review/optional-phases.md` (~160 and ~301) switch on the backend in separate case arms for the deep and validator passes; each needs a `claude` arm that resumes via the receipt like the cursor arm. The codex-mirror generator `scripts/sync-codex.sh` (~555) emits the work skill's `REVIEW_MODE` enum from its own hardcoded heredoc (`SECTION3C`), so the canonical `phases.md` edit must ALSO land in that heredoc or the mirror silently regenerates without `claude` at exit 0; verify the generated `codex/` output names `claude`, not just that the sync is idempotent. Operational consumers outside the review skills (these route or parse the backend, not just describe it): `flow-next-work/SKILL.md:113` backend list, `flow-next-work/phases.md:305` `REVIEW_MODE: none|rp|codex|copilot|cursor|host-deferred` enum and every branch that switches on it, `flow-next-plan/SKILL.md:144,147` configured-backend sentence and tip, `flow-next-pilot/SKILL.md` "Unattended runs" `--review=` list, and any `agents/*.md` prompt that names the backend set. Finish with `grep -rn 'codex|copilot|cursor' plugins/flow-next/skills plugins/flow-next/agents` (excluding `codex/`) and read every hit.
- Setup `workflow.md`: `HAVE_CLAUDE=$(command -v claude ...)` beside the cursor probe (~289-296), a Claude CLI row in each AskUserQuestion variant (~498-539) with the same-family note, the case mapping (~754-762), the status line (~925), the fallback note (~668).
- Run `./scripts/sync-codex.sh` twice; the mirror must be clean and the guards green. Review the diff against `agent_docs/conduct/impl-review.md`, `plan-review.md`, `spec-completion-review.md`, `setup.md` items.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-impl-review/workflow-cursor.md` — copy source
- `plugins/flow-next/skills/flow-next-impl-review/workflow-codex.md` — how effort is documented
- `plugins/flow-next/skills/flow-next-setup/workflow.md:280-300,490-545,750-765` — menu plumbing
- `scripts/sync-codex.sh` — guards that read skill prose
**Optional:**
- `agent_docs/conduct/README.md` — checklist index
- `.flow/memory/bug/integration/adding-a-review-backend-sweep-all-2026-06-29.md`

### Key context
- Canonical prose uses Claude-native tool names; the mirror rewrites them. `claude` as a backend value is not a tool dispatch, so no new transform is expected, but a guard failure is load-bearing: fix the content, never relax the guard.
- Cursor, Droid, Grok and OpenCode read canonical prose as-is: the setup menu row needs no host-specific clause beyond "when the `claude` CLI is on PATH".

### Acceptance
- [ ] Three `workflow-claude.md` files exist and are routed from their `SKILL.md`; each carries the same-family advisory line
- [ ] `grep -rn 'rp|codex|copilot|cursor' plugins/flow-next/skills plugins/flow-next/agents` (excluding the mirror) shows no backend enumeration or parse branch missing `claude`; the work skill's `REVIEW_MODE` enum and the plan skill's configured-backend sentence accept `claude`
- [ ] Setup offers Claude CLI when `claude` is on PATH and maps the choice to `review.backend claude`
- [ ] `./scripts/sync-codex.sh` twice: idempotent, guards green, mirror committed, and `grep -n claude plugins/flow-next/codex/skills/flow-next-work/phases.md` shows the regenerated `REVIEW_MODE` enum carrying `claude`
- [ ] `optional-phases.md` deep and validator arms dispatch `flowctl claude deep-pass` / `flowctl claude validate` with the receipt
- [ ] Skill-shape suites green: `cd plugins/flow-next/tests && python3 -m unittest test_skill_frontmatter test_sync_codex -q` (or the nearest existing suites named in the repo)
## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
