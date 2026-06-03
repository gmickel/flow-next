---
satisfies: [R13]
---

## Description

The GitHub transport behind the .2 adapter interface, reusing the .4/.5 reconcile core unchanged — proving the reconciliation is transport-blind. GitHub-next per the staging decision. Parallelizes with .6 (different files).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-tracker-sync/references/github.md`.

## Approach

- **gh CLI, headless:** `GH_TOKEN` for non-interactive; `gh issue create/edit/comment/view --json`, `gh issue list --json`, `gh auth status --json` (discovery probe, also used by .2). Use `--body-file -` for large/markdown bodies (shell-quoting breaks on raw `--body`).
- **State fidelity (reduced vs Linear):** GitHub native = `open`/`closed` + `stateReason {completed|not_planned}`. Map the richer flow/Linear status DOWN; carry fine-grained status as a label (`status:in-progress`). Surface `deferred`/`wontfix`, don't auto-apply (R7 semantics). Document the reduced-fidelity mapping.
- **Comments:** same dedup-marker scheme as .5; GitHub comment ids are stable.
- **Normalized mapping:** map gh's JSON (open/closed+reason, labels, comments) to/from the .2 normalized `issue`/`comment`/`status` structs — same contract the Linear adapter satisfies.
- **Transport-blind proof:** the same reconcile path over gh fixtures yields merge output identical to the Linear path (the R13 guarantee).

## Investigation targets

**Required:**
- the .2 adapter interface (mirror .3's Linear implementation shape)
- the .3 Linear adapter — the ladder/structure to mirror
- the .4/.5 reconcile core (consumed unchanged)

**Optional:**
- `gh issue` / `gh auth` docs (headless flags, `--json` fields, `--reason`)

## Acceptance

- [ ] GitHub adapter: gh-based create/edit/comment/view, headless via `GH_TOKEN`, `--body-file` for bodies; no-op + receipt when gh is unauthenticated [R13]
- [ ] State mapping documented (open/closed + reason + `status:` label) — reduced fidelity vs Linear; `deferred`/`wontfix` surfaced not auto-applied [R13]
- [ ] Transport-blind: reconcile output identical across Linear and GitHub fixtures [R13]
- [ ] Error contract: a deleted/404 GitHub issue emits an `errored`/`queued` receipt + prompts/queues unlink — no crash, no state clear, no `lastSyncedAt` advance [R13]

## Done summary
Added the GitHub transport adapter as a skill reference (plugins/flow-next/skills/flow-next-tracker-sync/references/github.md): a gh-based implementation of the fn-52.2 six-method interface — single headless rung (GH_TOKEN) plus terminal no-op, mapping gh JSON to/from the normalized issue/comment/status structs and reusing the fn-52.4/.5 reconcile core unchanged. Documents reduced-fidelity status (normalized mapped DOWN to open/closed + stateReason, full status carried via a status: label; deferred/wontfix surfaced not auto-applied), the R13 transport-blind/cross-tracker parity proof + round-trip spike (live exec deferred to the post-PR smoke phase), and the non-destructive 404/rate-limit error contract; wired into SKILL.md and steps.md alongside the Linear ladder links.
## Evidence
- Commits: b8f10214a01e5a445e998d11fd653b0d7ecedc89
- Tests: impl-review rp backend: triage-skip docs-only -> SHIP (mode: triage_skip), link-integrity: github.md sibling .md links resolve; SKILL.md+steps.md cross-link github.md
- PRs: