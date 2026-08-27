---
satisfies: [R2, R3, R7]
---
# fn-205-issue-sweep-skipped-review-status-land.1 Persist an excused completion-review member behind one shared satisfying-member predicate

## Description
Add the `not_required` member to the completion-review status vocabulary and route the two flowctl-side gates (merge-evidence projection, `--require-completion-review` scheduler) through a single declared satisfying-member set. Implements R2, R3 and the flowctl half of R7. First task by necessity: the CLI must accept the token before any skill prose writes it (spec Edge Cases, ordering rule).

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/scripts/flowctl_tracker/status/policy.py`, `plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json` (regenerated), `plugins/flow-next/tests/test_tracker_status.py`, `plugins/flow-next/tests/test_task_inventory.py`, `plugins/flow-next/tests/test_review_convergence_journal.py`
**Touches:** [plugins/flow-next/scripts/flowctl.py, plugins/flow-next/scripts/flowctl_tracker/**, plugins/flow-next/tests/test_tracker_status.py, plugins/flow-next/tests/test_task_inventory.py, plugins/flow-next/tests/test_review_convergence_journal.py]

### Approach
- Declaration home RESOLVED at plan-review (spec early proof point, verified 2026-08-27): a module-scope import from `flowctl_tracker` is unsafe — flowctl.py treats the tracker package as optionally absent everywhere (all imports lazy, inside functions, with a `sys.path.insert` fallback and graceful degrade: `flowctl.py:1903-1913`, `:39155-39166`), while argparse `choices` builds at parse time. So: keep the canonical known-member set + satisfying-set predicate in `flowctl.py`, mirror the declaration in `flowctl_tracker/status/policy.py` (next to its existing `SLOTS`/`TERMINAL`/`PR_EVIDENCE` constants), and add a parity test pinning the two equal. Do not leave two unpinned copies, and do not import across the boundary at module scope.
- Widen only the completion-review status `choices` at `flowctl.py:49928`. The plan-review list at `:49906` is a different command and stays as-is.
- Add an optional `--if-current <status>` compare-and-set flag to `spec set-completion-review-status` (review P1): evaluated inside the existing `_review_sidecar_lock` block in `cmd_spec_set_completion_review_status` (`flowctl.py:29895`), so the check and the write are one critical section. On mismatch: no write, visible machine-readable outcome (JSON `written: false` + current value, non-error exit) — a skipped CAS is a normal outcome for the 3g caller, not a failure. Regression test: a `needs_work` written between read and CAS is never clobbered by `--if-current unknown`.
- Projection: `flowctl_tracker/status/policy.py:210-216`. Row 2 currently returns `done` on `review == "ship"` and row 3 falls through to `in_review`. Row 2 becomes the allow-set membership test. Rows 4-8 and the `pr_evidence` ordering are untouched — terminal stays reachable only from `merged`.
- Leave the `verified`-vs-`done` label selector `ship`-only (it is a separate reader in `flowctl_tracker/status/verb.py:376-380`; `flow-next-land/workflow.md:776` already documents `verified` as ship-evidence). R2 requires the label stay `done`.
- Scheduler: `flowctl.py:34049-34065` — the `!= "ship"` condition becomes a not-in-allow-set test. Keep the emitted `needs_completion_review` reason string unchanged for `unknown` / `needs_work` / `needs_human`.
- Do not touch the three verdict->status maps (`flowctl.py:10231`, `:11070`, `:41059`) — the skip writes through the CLI, not through a verdict, and the dedup is fn-190's (spec Boundaries).
- Regenerate `plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json` via `python3 scripts/gen_tracker_manifest.py` in this task — the manifest pins every shipped member and `test_tracker_distribution` fails unhelpfully otherwise.
- Do NOT run `./scripts/sync-codex.sh` here. The single authoritative mirror regen is the finalization task, so parallel siblings never conflict in `plugins/flow-next/codex/`.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl_tracker/status/policy.py:190-220` — the 8-row projection and the docstring claiming it ports the doctrine table faithfully
- `plugins/flow-next/scripts/flowctl.py:34049-34065` — `next --require-completion-review` predicate and emission
- `plugins/flow-next/scripts/flowctl.py:29895-29930` — the writer command; note `completion_reviewed_at` is stamped unconditionally
- `plugins/flow-next/scripts/flowctl.py:3841-3842` — `normalize_epic` backfills absent -> `unknown`, so key-absence can never be a signal

**Optional** (reference as needed):
- `plugins/flow-next/tests/test_review_convergence_journal.py:1240-1243` — where the four members are exercised through the CLI today

### Key context
- Measured forward-compat: an older reader meeting `not_required` degrades to `in_review` / re-requests the review — non-terminal, the safe direction. Old spec JSON needs no migration; do not write one.
- The allow-set must be an explicit membership test, not a widened `!=` chain: `!= "ship"` is an implicit deny-list, and the next member added would silently classify itself.
- `flowctl.py:42606` echoes the written status in the `<backend> completion-review` JSON envelope — no change needed, but include it when enumerating members in the R7 test so a consumer-facing surface is never surprised by the new token.

### Acceptance
- [ ] `flowctl spec set-completion-review-status <id> --status not_required` is accepted; plan-review status choices are unchanged
- [ ] `--if-current <status>` performs an atomic compare-and-set under the sidecar lock; mismatch is a visible no-write (JSON reports it), and a concurrent `needs_work` survives a `--if-current unknown` attempt (regression test)
- [ ] The known-member set and the satisfying-member predicate are declared exactly once (or, if the import direction forbids sharing, mirrored with a parity test that fails on divergence)
- [ ] Projection: merged + spec `done` + `not_required` + review configured -> `done`; `unknown`, `needs_work`, `needs_human` -> `in_review`; non-merged PR evidence still never reaches terminal (R2)
- [ ] The `verified` vs `done` label selection is unchanged and still requires `ship` (R2)
- [ ] `flowctl next --require-completion-review` emits no `needs_completion_review` for a `not_required` spec, and still emits it for `unknown`, `needs_work`, `needs_human` (R3)
- [ ] A test enumerates every known member and pins each flowctl-side gate's classification, so an added member cannot silently default (R7)
- [ ] An unrecognized or absent persisted value reads as `unknown` and satisfies no gate
- [ ] `python3 scripts/gen_tracker_manifest.py` re-run and the manifest committed
- [ ] `cd plugins/flow-next/tests && python3 -m unittest test_tracker_status test_task_inventory test_review_convergence_journal -q` green

## Acceptance
- [ ] TBD

## Done summary
Added the `not_required` completion-review member behind one shared satisfying-member predicate: canonical declaration (`COMPLETION_REVIEW_STATUSES` / `COMPLETION_REVIEW_SATISFYING` / `completion_review_satisfied()`) in `flowctl.py`, mirrored in `flowctl_tracker/status/policy.py` with a parity test (import direction forbids sharing — tracker package is optionally absent). Projection row 2 and the `next --require-completion-review` scheduler now consume the allow-set instead of `==`/`!=` ship chains; `spec set-completion-review-status` gained an atomic `--if-current` compare-and-set under the sidecar lock (mismatch = visible no-write, `written:false`, non-error exit; regression test pins that a concurrent `needs_work` survives `--if-current unknown`). Plan-review choices and the verified-vs-done label selector are unchanged; unrecognized/absent values read as `unknown` and satisfy nothing. Member-enumeration tests pin every flowctl-side gate classification (R7). MANIFEST.json regenerated. Mirror regen (sync-codex.sh) deliberately deferred to the finalization task per task spec.

baseline: green (focused suite, 212 tests pre-edit)
implementer route: bridged both chunks to grok 4.6 via cursor-agent as instructed; both bridge outputs matched the specified diffs exactly, no fallback needed.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: d5e8d0b2b34078f9a42ee79fb8e4926cc5ee1d44
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_status test_task_inventory test_review_convergence_journal -q, cd plugins/flow-next/tests && python3 -m unittest test_tracker_distribution test_flowctl_surface -q, uvx ruff@0.16.0 check <changed files>, python3 scripts/gen_tracker_manifest.py
- PRs: