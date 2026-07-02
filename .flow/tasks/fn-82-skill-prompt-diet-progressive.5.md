---
satisfies: [R9, R10, R11, R12, R13]
---

## Description

Final gate: the ONE mirror regeneration + commit, full test sweep, gate-contract greps, the before/after token table, agent_docs target-map + log updates, CHANGELOG entry. Depends on fn-82.1-.4.

**Size:** S
**Files:** `plugins/flow-next/codex/` (regenerated, committed once), `agent_docs/optimizing-skills.md`, `agent_docs/optimization-log.md`, `CHANGELOG.md`, optionally `agent_docs/adding-skills.md`

## Approach

- `bash scripts/sync-codex.sh` ×2 (idempotent; parity guards green — includes the NEW references/*.md files) → commit mirror. Drop any mirror-only validation stashes left by tasks 1-4.
- Smoke from non-repo cwd + `python3 -m pytest plugins/flow-next/tests/ -q` green.
- **Gate-contract greps (R9):** for each new gate (work bridge, pilot qa), verify against the spec's exact skeleton: gated file exists + linked one level deep; sentinel text (`GATE ACTIVE — STOP. Read`) present; fail-open `|| ACTIVE=1` on both probe and parse; NO unguarded `| jq` pipeline inside any gate block; default branch contains NO Read of the reference. Record each check.
- **Token table (R12):** `wc -c` pre (fn-81 merge-base) vs post, chars/4, over these PINNED file sets — work `SKILL.md+phases.md`; pilot `SKILL.md+workflow.md`; tracker-sync `SKILL.md+steps.md`; impl-review core `SKILL.md+workflow-common.md` / active-backend scenario `+workflow-rp.md` (rp); spec-completion-review core `SKILL.md+workflow-common.md` / active-backend `+workflow-rp.md` (rp) — report core and backend-scenario columns separately; interview `SKILL.md`; audit `SKILL.md+workflow.md+phases.md`; qa `SKILL.md+workflow.md`; prospect `SKILL.md+workflow.md`; capture `SKILL.md+workflow.md+phases.md`; make-pr pre `SKILL.md+workflow.md+phases.md` / post `SKILL.md+workflow.md` (phases.md un-force-loaded). Table into the PR body and the summary.
- **agent_docs (R10):** optimizing-skills.md target map corrected (no uncapped free-form agents remain; prime scouts fixed-size; remaining prizes = always-loaded skill weight — edit the existing section in place); optimization-log.md: consolidate this spec's rows (gating wins, strips, dedupes, the two eval-guarded outcomes). Optional (implementer's judgment): adding-skills.md gains the "gated references/*.md" heuristic block (third landed instance — follow the existing heuristic-block shape).
- CHANGELOG: sibling bullet under the existing `## Unreleased` → `### Changed` (fn-81's entry is there); no version bump.

## Investigation targets

**Required:**
- `agent_docs/optimizing-skills.md:140-210` — target-map section to correct
- `CHANGELOG.md:1-40` — Unreleased section + house style
- `agent_docs/adding-skills.md` — heuristic-block shape (optional item)

## Acceptance

- [ ] Mirror regenerated once, ×2 idempotent, parity green, committed here only; validation stashes dropped
- [ ] Smoke (non-repo cwd) + pytest green — tails in summary
- [ ] Gate-contract checks recorded per gate (sentinel + fail-open + one-level link)
- [ ] Before/after token table (chars/4 per skill) in summary + staged for the PR body
- [ ] optimizing-skills target map corrected; optimization-log rows consolidated; CHANGELOG sibling entry; no version bump

## Done summary
Final gate for fn-82 (skill prompt diet): regenerated the Codex mirror once (idempotent x2, all parity guards green — new references/*.md mirrored, spike archive kept out of the plugin tree), ran the full test sweep (smoke 138/138 from non-repo cwd; pytest 1393 passed), verified the R9 gate contract for both new gates (work tracker-touchpoints x3, pilot qa-stage) via programmatic greps, produced the R12 before/after token table (~10.7k always-loaded tokens cut across 11 skills), corrected the optimizing-skills target map + consolidated the fn-82.1/.2/.3 optimization-log rows + added the gated-references heuristic to adding-skills, and landed the CHANGELOG Unreleased sibling entry (no version bump). Caught and fixed a real regression: fn-82.2's fn-strip archaeology over-stripped a test-pinned breadcrumb in tracker-sync steps.md (test_pilot_backlog_mirror_safety) — restored the canonical string and re-mirrored. rp impl-review returned a clean first-pass SHIP.
## Evidence
- Commits: 82f890ea, 6690e334, bb91d1ff
- Tests: bash smoke_test.sh (non-repo cwd): 138/138 passed, python3 -m pytest plugins/flow-next/tests/ (via uv): 1393 passed, 2 skipped, 164 subtests passed, sync-codex.sh: idempotent x2, all parity guards green, R9 gate-contract greps: work=3 sentinels + 6 fail-open, pilot=1 sentinel + 2 fail-open, one-level links, default no-op — all pass, rp impl-review: clean first-pass SHIP, 0 introduced findings
- PRs: