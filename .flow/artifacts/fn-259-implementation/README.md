# fn-259 implementation handoff

Implementation checkpoint: `988ebf95`. Starting commit: `fc93b0a4`.
Scope: task `fn-259-flowctl-renders-what-agents-hand.1`, R1–R31.
No push, rebase, amend, task completion, or review verdict was issued.
This is implementation evidence, not a completion-review receipt.

## Requirements and inherited work

| Requirement | Implementation / evidence |
|---|---|
| R1 | Additive CLI flags and commands, canonical skills and generated Codex consumers, updated installer helper inventory. Local suite, Ruff, mirror freshness and offline smokes pass. Cross-OS acceptance remains outstanding. |
| R2 | Live route lifecycle and PR observations survive external-judge unavailability; failed PR observations do not produce a lifecycle guess. |
| R3 | Pilot snapshot bundles selection, guards, config, per-candidate routes/backends, branch/PR/QA facts and task snapshots; one PR listing. |
| R4 | Locked cumulative strike recording; unready at two; clear shares the lock. |
| R5 | Tail wait uses bounded CI watch/patience/interval and defers after two unchanged human-review ticks. |
| R6 | Backlog reads use tracker wire; reconcile and questions retain the tracker skill. |
| R7 | Make-pr preflight/close and create/update/stack plumbing extracted to bundled scripts, with behavioral tests and installed-script parity. Measurement below: tokens down 7.5%, median tool calls +1. |
| R8 | Green rolling quiesce emits reusable gate receipts; focused integrated verification remains task Quick commands. |
| R9 | Baseline permits intervening Flow-only commits; initial rolling batch receives a baseline and reusable full-gate receipts. |
| R10 | Ready metadata and mechanical admission cover dependencies, Touches, serial surfaces and cap; host retains holds. |
| R11 | Done range derives commit/base evidence, accepts repeated tests and stdin; rolling retains explicit interleaved commit evidence. |
| R12 | Task-backed tier rendering and resolved tracker event operation map replace repeated assembly. |
| R13 | Named parse failures, per-draw status, middle-dot labels and zero-introduced SHIP lineage coverage. Six representative shapes tested; literal audit fixtures unavailable. |
| R14 | Shared host prompt rendering, record/attach, in-process diff identity and fanout metadata derivation. Plan/completion default receipts were already supplied by `e5535836`; wave-one record derivation from `b4c980af` preserved. |
| R15 | Completion terminal re-entry command preserves the shell state matrix, including MAJOR_RETHINK continuation; unknown persisted states fail. |
| R16 | Coordinator keep/collapse plan renders findings and counts survivors, with missing-item validation. |
| R17 | Deterministic tracker push body, optional explicit body override, body-free status-only push. Legacy spec headings accepted. |
| R18 | Four-provider push call-count matrix at most four calls; transaction reads/readbacks reused; Linear comment identity folded into its page. Linear parent state fields already existed in `e6a860184`. |
| R19 | Private prepare snapshots, pre-reduction class, stripped tracker body, paired bases and deduped genuine comments; consume/expiry cleanup. |
| R20 | Unchanged chart child skips update; relation setup shared with bounded probes and serialized mutations; HTTP connections reused. |
| R21 | Bulk task validation reports all items/allowed keys; Touches and JSON-relative content files supported. |
| R22 | Unknown and uncovered satisfies warnings; coverage table rendered from actual task ownership. |
| R23 | Independent preflight probe envelopes consumed by plan/capture/refine with existing failure behavior. |
| R24 | Nonblocking scout scheduling overlaps gap analysis with web research; SHORT docs charter folded into repo scout; GitHub search has one owner. |
| R25 | Prospect payload skeleton, ID/count/rate derivation, validation and atomic rendering/writing. |
| R26 | QA payload writer retains prior findings and coverage; unattended target/account prerequisites precede scenarios. |
| R27 | Memory audit snapshot and host-authored per-entry atomic apply, including reference updates. |
| R28 | Read-only overlap probe; rediscoveries update existing memory directly. |
| R29 | Read-only setup snapshot and remembered optional answers, without new config keys. |
| R30 | Map wrapper owns parsing/version/init/invocation; skill retains interpretation. |
| R31 | Six imports localized and eleven rarely used regexes deferred. Import-time improvement measured; whole-command improvement was not demonstrated. |

No other assigned R-ID was already fully satisfied at the starting commit.
Existing validators, renderers, locks, gate receipts and transaction machinery
were reused rather than reimplemented.

## Verification

All work used `TMPDIR=/home/gordon/.cache/fn-tmp`.

- `python3 scripts/run_tests_parallel.py`: 258 files, 5,194 tests, zero failures/errors, six skipped, 106.86 seconds. The first run found stale inline-workflow assertions and exposed the pilot review-argument omission; both were corrected before the green run.
- Final pilot candidate-specific review/QA selection was then checked by 14 affected executable tests, including a new regression proving a selected candidate's false QA freshness cannot fall back to another spec's true value.
- `uvx ruff@0.16.0 check .`: passed after final edits.
- `python3 scripts/check_doc_anchors.py` and `git diff --check`: passed.
- Tracker manifest regenerated; Codex regeneration repeated; `sync-codex.sh --check` confirmed byte-fresh mirror and manifest.
- Linux offline smoke matrix passed: interpreter picker, CLI integration, resolve-pr, strategy, audit, glossary, prospect, make-pr, map, impl-review, and general CLI smoke. Make-pr: 63 checks. General offline smoke: 128 checks.
- Consumer-layout installer tests passed in the full suite, including new bundled helper parity. All new CLI leaves are covered by the command-surface inventory.

The general smoke script auto-detected installed Codex/Copilot and unexpectedly
invoked four live backend checks. The Codex checks passed; both Copilot checks
failed on monthly quota. This was not an intentional delegation or review of
this branch. The general smoke was rerun with `PATH=/usr/bin:/bin`, excluding
those live CLIs: 128 checks passed. No further live backend calls were made.

## Startup measurement

Python 3.12.14; eleven alternating fresh-process samples per arm, one warmup
pair excluded. Common current templates and tracker package were held fixed.
Module import uses cached bytecode; direct script `--help` includes source
compilation and parser construction. No task tests or sync jobs overlapped the
isolated run. Raw samples are in `startup-isolated.json`.

| Median milliseconds | Before | After | Change |
|---|---:|---:|---:|
| Module import | 64.304 | 49.211 | -23.5% |
| Direct script --help | 441.795 | 446.528 | +1.1% |

Import startup improved; end-to-end CLI startup did not show an improvement.
The preliminary run overlapped mirror generation; its raw samples remain in
`startup-overlapped.json`, excluded from the result above. No agent-efficiency
claim is inferred from these mechanical timings.

## Outstanding acceptance evidence and scope boundaries

- R1: macOS and Windows OS smoke/unit legs were not available locally. No push
  was authorized, so CI for this branch was not triggered.
- R7: measured by the host after the bridge returned, with the fn-249 harness
  (`measure.sh`, `make-pr --dry-run` on the pr449 fixture, `claude-fable-5-1`),
  six runs per arm, before = `fc93b0a4` plugin, after = this branch. Raw rows are
  in `make-pr-measurement/`.

  | Point | Median output tokens | Median tool calls | Median wall s |
  |---|---:|---:|---:|
  | p5 before (`fc93b0a4`) | 13,097 | 13.5 | 169.8 |
  | p6 after, as bridged | 17,698.5 | 16.5 | 242.8 |
  | p7 after, dry-run SHA base fixed (`68e0aec8`) | 12,117 | 14.5 | 175.6 |

  The fixture passes `--base <sha>`. The preflight rewrote every non-`refs/` base
  to `origin/<base>`, so the bundled script failed on a SHA and every p6 run spent
  extra turns reading it; the inline-era agent had worked around the same defect
  by hand. With the dry-run SHA base accepted (p7), output tokens fall 7.5%. The
  median tool count is one call higher (mean 14.0 vs 15.2, lower); on six noisy
  samples this half of the criterion is not demonstrated.
- R13: the six literal audit draw artifacts were absent from this checkout;
  representative parser regressions are green, exact corpus replay is pending.
- R31: import-time evidence is positive, whole-command startup evidence is not.
- Public downstream properties outside this worktree were not edited. Runtime
  docs and the Unreleased changelog in this repository were updated; downstream
  site/release propagation belongs to the conductor's broader authorized scope.

## Delegation and rendering parity

Twelve native subagents were dispatched: seven direct owners and five nested
agents. All were awaited and reconciled before parent verification or staging;
one completed child was reused for setup without creating another agent.
The parent was the sole committer. Rejected spawn attempts created no agents.

The extracted make-pr shell logic and exit mapping are retained. Its retry
error now says to repeat the same make-pr invocation instead of printing a
Claude-only command spelling; host-specific recovery spelling remains in the
transformed workflow. Other intended differences are the additive helpers,
derived metadata, consolidated validation errors and diagnostics specified by
R1–R31. Skills keep judgment, consent and semantic merge decisions.
