---
satisfies: [R5]
---
# fn-169-review-subsystem-agentic-first-pass.2 Eval fixture with scope traps + baseline measurement of current behavior

## Description
Extend the existing harness so it can measure what the current corpus structurally cannot, then record the BASELINE before anything changes.

**Size:** L
**Files:** `optimization/review-prompt/` (new git-fixture corpus + scope metrics; reuse `reveval.py`'s runner/scorer/summary), `agent_docs/optimization-log.md`

### Approach
- Reuse the scaffold, do not rebuild it: backend-in-the-loop runner, deterministic OR-matched answer key, clean-corpus over-flag check, cross-backend confirmation, both-axes accounting. The README says the point of the directory is the reusable scaffold.
- **The gap:** `orders.py` is a single file reviewed as content — no git history, no base/head, no multi-file surface. It cannot fail on scope, so every metric would pass while the real risk went unmeasured.
- **New corpus: a git fixture where the diff IS the artifact.** Commits from `base` to `head`, planted issues across several files, plus deliberate traps:
  - a planted bug in a file changed **before** `base` (must NOT be reviewed)
  - a planted bug in a file changed **after** `head` (must NOT be reviewed)
  - a bug in an **unchanged region of a changed file** (over/under-read)
  - a **rename** (git shows a rename; embedding showed content — the likeliest divergence)
- **New metrics:**
  - `verdict_delivered` — the "114 turns / no verdict" failure embedding was originally added to prevent. Primary safety metric.
  - `range_correct` — read from the reviewer's OWN `command_execution` stream (the codex JSON events name the range it actually ran). Directly observable, not inferred.
  - turns-to-verdict (count `command_execution` items)
  - scope precision — any finding naming an out-of-range file is a failure
  - resumed re-review **per-ordinal grammar compliance**, scored by feeding the reply to the production `_review_finding_prior_items` and comparing against the known resolution map
- **Measure the baseline now**, against as-shipped behavior, and log it. Without this the post-change numbers mean nothing.
- Keep the existing keyword scorer as-is so results stay comparable to fn-74's logged numbers; do not invent a new scoring scheme mid-study.
- Backends: codex (project default) + cursor (the argv/truncation case). Cursor's default model is quota-blocked on this account — use `grok-4.5` or `composer-2.5`.

### Investigation targets
**Required:**
- `optimization/review-prompt/README.md` — the method and the four rigor techniques
- `optimization/review-prompt/reveval.py` — runner, `GROUND` answer key, `detect()`, metrics
- `agent_docs/optimizing-skills.md` — the repo's eval methodology
- `agent_docs/optimization-log.md` — where every experiment, kept or discarded, is recorded

**Optional:**
- `reveval_clean.py` / `orders_clean.py` — the over-flag pattern to mirror for the new corpus

### Key context
- **Do not re-verify the spec's settled facts** (§ Already established): backend availability, resume working, the 50 KB cap, the 10%-visible number, codex-on-stdin. This task builds NEW instrumentation — the scope-trap corpus and its metrics — and records a baseline for comparison. It is not a re-audit.
- Pre-register the decision gate in this task, before any post-change numbers exist, so it cannot be rationalised later.
- fn-74 proved no-embed for file CONTENTS. The diff is the SCOPE signal — a different claim, which is why the traps exist.
- Record discarded experiments too; that is the harness's stated discipline.

## Acceptance
- [ ] Git-fixture corpus exists with all four trap classes (pre-base decoy, post-head decoy, unchanged-region bug, rename)
- [ ] Metrics implemented: `verdict_delivered`, `range_correct` (from the reviewer's own command stream), turns-to-verdict, scope precision, resumed per-ordinal grammar compliance via the production parser
- [ ] Existing detection scorer and clean-corpus over-flag check reused unchanged (results stay comparable to fn-74)
- [ ] BASELINE measured on as-shipped behavior, codex + cursor, >=3 runs, recorded in `agent_docs/optimization-log.md`
- [ ] The ship gate is written down BEFORE any post-change run: verdict_delivered 100%, range_correct 100%, scope precision 1.0, correctness detection >= baseline, prior-ordinal compliance >= baseline, prompt tokens down; wall-clock recorded not gated
- [ ] Harness runs offline-clean where it can (no live model needed to validate corpus structure)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
