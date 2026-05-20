---
satisfies: [R4]
---

## Description

Audit canonical skills for destructive / irreversible / external actions (`.flow/epics` → `.flow/specs` migration; capture rewrite/supersede; make-pr push + `gh pr create`; interview rewrite; audit cleanup). Verify each surfaces an explicit `abort` option in its `AskUserQuestion` call AND that the post-sync Codex mirror surfaces the same option as a numbered choice. Skill must exit cleanly on `abort`; no default action without explicit user reply.

**Size:** S

**Files:**
- `plugins/flow-next/skills/flow-next-setup/workflow.md` (migration consent prompt)
- `plugins/flow-next/skills/flow-next-capture/workflow.md` (rewrite/supersede/override prompts)
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md` + `phases.md` (push + PR create prompts)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` (rewrite confirmation)
- `plugins/flow-next/skills/flow-next-audit/SKILL.md` + `workflow.md` (cleanup confirmation)
- `plugins/flow-next/codex/skills/**` (regenerated mirror — verify abort option appears in numbered prompts)

## Approach

- For each affected skill, locate the destructive `AskUserQuestion` call sites.
- Verify the canonical options list includes `abort` (or equivalent — `cancel`, `no`, `skip`) as one frozen option.
- Verify the skill code-path exits cleanly when the user picks `abort` (no fallthrough to the destructive action).
- After fn-45.1's sync regen, read the Codex mirror counterparts and confirm `abort` appears as one of the numbered options (e.g. `3. abort — exit cleanly, no write`).
- If a canonical site lacks `abort` (or the skill defaults to destructive action on missing reply), add `abort` to the option set in canonical.

## Investigation targets

**Required**:
- `plugins/flow-next/skills/flow-next-setup/workflow.md:55-100` — migration consent for `.flow/epics → .flow/specs` (when `PRE_1_0_LAYOUT=1`)
- `plugins/flow-next/skills/flow-next-capture/workflow.md:140-200` — Phase 0.5 duplicate-detection branch (extend/supersede/proceed-anyway/abort)
- `plugins/flow-next/skills/flow-next-capture/workflow.md:480-625` — Phase 4 read-back (approve/edit/abort) + Phase 5.0 strategy-override prompts
- `plugins/flow-next/skills/flow-next-make-pr/phases.md:127` — Phase 4 preview (`create / dry-run / edit-body / abort`) before push + `gh pr create`
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md` — search for `git push` / `gh pr create` invocation sites
- `plugins/flow-next/skills/flow-next-audit/workflow.md:473` — cleanup confirmation site

**Optional**:
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` — search for rewrite confirmation prompts
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md:393` — `needs-human` decision points

## Key context

- The spec Boundaries explicitly disallow touching canonical Claude Code prose unrelated to abort-option completeness. This task only *adds* `abort` to option sets where missing; does not refactor prompt wording.
- Verify by reading the post-sync mirror (after fn-45.1 lands). The transform should already preserve `abort` from canonical option lists — this task confirms that's true and patches gaps.
- "Star repo" action mentioned in spec R4: search canonical for `gh repo star` / "star" prompts; may not exist as an interactive prompt (likely a one-shot in a setup variant). If absent, no work needed.

## Acceptance

- [ ] All destructive-action sites listed above audited; `abort` (or equivalent) option present in canonical option lists.
- [ ] Skill exit-paths on `abort` choice verified by reading the skill workflow (no fallthrough to destructive action).
- [ ] Post-sync Codex mirror surfaces `abort` as one of the numbered options for each destructive site.
- [ ] Any canonical gaps closed: minimal edits to add `abort` where missing. Edits surface in `git diff` only on the affected workflow.md / SKILL.md files; no incidental refactors.
- [ ] Re-run `./scripts/sync-codex.sh`; mirror regenerates cleanly (no new validation-guard failures introduced by canonical edits).

## Done summary
Audited destructive-action sites listed in fn-45.2 acceptance R4 across canonical skills (flow-next-setup, flow-next-capture, flow-next-make-pr, flow-next-audit, flow-next-interview, flow-next-resolve-pr) and their post-fn-45.1 Codex mirrors. Found one gap: `flow-next-setup/workflow.md` Step 1b pre-1.0 migration consent prompt lacked an explicit `abort` option (`Migrate now` / `Defer` / `Suppress permanently` only). Added `abort` as the 4th option + explicit exit-path routing that acknowledges Step 1's `flowctl init` may already have run (idempotent — not rolled back); regenerated the Codex mirror via `./scripts/sync-codex.sh`. Codex impl-review cycled through 2 NEEDS_WORK iterations (option-label vs routing-text drift on what "abort" actually preserves vs discards) before SHIP. All other destructive sites (capture Phase 0.5/0.6/4, make-pr Phase 4.5, audit Phase 3/5.4/6, interview decision-record gate) already had abort or abort-equivalent options (`skip`, `Don't commit`, `no`) — no further canonical edits needed.
## Evidence
- Commits: 5b69147, 9adbceb, 28b498a, 041e51c
- Tests: ./scripts/sync-codex.sh (regenerated codex mirror cleanly; all 12 validation guards passed including the R6 request_user_input guard), grep -rE 'request_user_input(...)' plugins/flow-next/codex/skills/ → PASS (no surviving refs), sync-codex.sh idempotency check (find ... md5sum twice) → IDENTICAL, flowctl codex impl-review fn-45-codex-plain-text-fallback-for.2 --base 5eccbe9 → VERDICT=SHIP (cycle 3, after 2 NEEDS_WORK fixes)
- PRs: