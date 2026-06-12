---
satisfies: [R5, R8, R10]
---

## Description
The PR lens: make-pr emits a read-only review-instrument artifact derived from the diff + the spec's R-ID export, and links it from the PR body. Never enters the annotate loop. Side effects are tightly disciplined against make-pr's existing invariants (--dry-run, Ralph stdout contract).

**Size:** M
**Files:** plugins/flow-next/skills/flow-next-make-pr/SKILL.md, plugins/flow-next/skills/flow-next-make-pr/phases.md, plugins/flow-next/skills/flow-next-make-pr/workflow.md

## Approach
- Same config gate (bash block, not prose). Off ⇒ no reference load, no artifact, no body line, no output change.
- Hook after Phase 1's `flowctl spec export-cognitive-aid` call (workflow.md:285): the payload (R-IDs, tasks, evidence, diff stats) + `gh pr diff`/diffstat feed the artifact — diff-derived, never commit messages.
- Generate `.flow/artifacts/<spec-id>/pr.html` per the reference file's PR-lens guidance (dials, churn-by-review-intent, R-ID→evidence, where-to-look checklist, risk register). R-ID verification: payload vs diff mismatches render as flagged rows — warn-in-artifact, never block the PR.
- **Side-effect discipline (review-mandated):**
  - `--dry-run`: writes NO artifact (or temp-only under $TMPDIR, discarded) — the existing no-state-change promise holds.
  - Committed-mode: stage ONLY `.flow/artifacts/<spec-id>/pr.html` (never `git add -A` — R10 forbidden-behaviors), fixed commit message `chore(flow): pr artifact <spec-id>`, committed BEFORE `gh pr create` so the blob link resolves. Dirty-tree: the narrow add/commit touches nothing else; other working-tree changes are not make-pr's concern.
  - Failure is non-fatal: generation/commit failure ⇒ skip the body link, one stderr note, PR proceeds.
  - Ralph/stdout contract: `PR_URL=<url>` remains the ONLY stdout line in Ralph mode; all artifact messaging goes to stderr; receipts untouched.
- Inject the artifact link into the PR body before Phase 4's `gh pr create` (phases.md:11): committed artifacts → absolute blob URL (workflow.md:420-435 rule) + "GitHub renders this as source — open locally" note; gitignored → local-open guidance only. Never a 404 blob link.
- Lavish: NEVER open/poll for the PR lens (read-only instrument), interactive or not.

## Investigation targets
**Required:**
- plugins/flow-next/skills/flow-next-make-pr/workflow.md:270-340 (Phase 1 export + body assembly) and :410-440 (URL rules)
- plugins/flow-next/skills/flow-next-make-pr/phases.md (phase map, Phase 4, --dry-run + Ralph stdout invariants)
- plugins/flow-next/scripts/flowctl.py:14234 — export-cognitive-aid payload shape (confirm diff/evidence fields the lens needs; recompute via gh only what is missing)
**Optional:**
- ~/Documents/flow-next-artifact-smoke/pr-171-pilot.html — validated PR-lens shape

## Acceptance
- [ ] Mode off: make-pr unchanged (no reference load, no artifact, no body line)
- [ ] Mode on: pr.html generated at fixed path from export payload + real diff; zero external requests; staleness stamp present
- [ ] `--dry-run` writes no persistent artifact and makes no commit
- [ ] Committed-mode: exactly one narrow commit (`chore(flow): pr artifact <spec-id>`) staging only the artifact file, landing before gh pr create; blob link resolves on the remote branch
- [ ] Gitignored-artifacts repo: local-open guidance, no blob link
- [ ] R-ID mismatch case renders a visible flagged row; make-pr still completes
- [ ] Artifact failure path: PR still created, link skipped, single stderr note
- [ ] No lavish session/poll ever opened by make-pr (interactive AND autonomous transcripts)
- [ ] Ralph/autonomous draft-PR path: stdout still exactly `PR_URL=<url>`; receipts untouched (fn-59 R4/R11 regression)

## Done summary
Wired the PR render lens into /flow-next:make-pr: new Phase 1.5 (gated on artifacts.html.enabled, forced off under --dry-run) generates .flow/artifacts/<spec-id>/pr.html from the export payload + real diff per the shared disclosure reference §5, renders R-ID payload-vs-diff mismatches as flagged rows (warn-never-block), commits the artifact via a LENS_OK-guarded narrow pathspec commit (chore(flow): pr artifact <spec-id>) before HEAD_SHA capture/push so the blob link resolves, and injects a render-lens line into the PR body (blob URL when tracked, local-open guidance when the exact file is gitignored, no line on failure). No Lavish ever; Ralph PR_URL stdout contract untouched; Codex mirror regenerated.
## Evidence
- Commits: 3975a0f669317fa67b7729371e39a1135be57a68, 74a4ecdf957b77708442b3151b8130cd16bd96b7
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (1071 tests OK), scripts/sync-codex.sh validators green, RP impl-review: NEEDS_WORK -> SHIP (2 findings fixed)
- PRs: