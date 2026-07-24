# fn-130 fleet result

Closure record for the reached-path prompt optimization program. Measurements
below are deterministic source characters under the frozen LF/full-file-on-
activation/once-per-path+hash algorithm. They are not billed-token, cache, or
wall-time claims.

## Baseline lineage

| Stage | Commit | Proof |
|---|---|---|
| Immutable original baseline `B0` | `1e8d3a95cf12cf1f33fa5c6c7ee50e0998e04e4b` | 117 commit-sourced manifests validate |
| Version-only baseline `V1/B1` | `8ed71a73ccc593a8a018dcdb805a86f396dcf76f` | 117 manifests validate; structural input hashes frozen |
| Structural candidates | task commits through `97e9793a93bcad8c2bf18bdb1b8d28d3ae80b2ff` | every cluster ledger names `B1`, records its input check, and compares no structural candidate directly to `B0` |

`python3 optimization/reached-path/run_eval.py --self-test`,
`--validate-b0`, and `--validate-b1` pass. The tracked candidate ledgers and
focused tests fail closed on a prompt-input mismatch.

## Fleet result

| Cluster | `B0` / `B1` → candidate reached path | Accuracy and model cells | Kept / discarded |
|---|---|---|---|
| Version contract | `B0 53,931 → B1 50,243` on all 10 version fixtures: `−3,688` (`−6.84%`) | deterministic 10-state contract matrix; canonical + Codex question/warning parity; no backend telemetry claim | **kept:** Plan-only copy-mode check. Removed fleet ceremony. No hook/helper/ack write. |
| Setup | `B1 103,688 → 69,591–74,854` across 16 routes: `−27.81%` to `−32.88%` | 16 route fixtures plus 72 Setup/model/template checks; host branches for Claude, Codex, Cursor, Droid, Grok; deterministic only | **kept:** one-level host/model/Ralph routing. No discarded Setup mutation. |
| Tracker Sync | `B1 452,552 → 228,459–302,354`: `−33.2%` to `−49.5%` | 15/15 frozen fixtures; fake Linear MCP/GraphQL, GitHub, GitLab, Jira transports; zero external writes; deterministic only | **kept:** common spine + exactly one adapter. No-transport/malformed remain cold and safe. |
| Prime | classify-only `96,190 → 32,759` (`−65.94%`); report/full routes `−0.68%` to `−1.09%` | tracked authenticated Claude `sonnet` B1 and candidate: 7/7 each; 6/6 synthetic plus negative control; nonzero usage and clean isolation in [`optimization/prime/evidence/fn130/`](../prime/evidence/fn130/README.md) | **kept:** classify-only direct route and remediation gating. |
| Plan Review | `B1 48,486 → 10,347–18,366`: `−62.12%` to `−78.66%` after fn-131 transport-accounting guidance | Codex `gpt-5.6-sol` high B1/candidate real-backend corpus: risky 10/10 + NEEDS_WORK, clean SHIP, user-edited 37 grounded, nonzero usage; production reviewer prompt byte-identical | **kept:** common router + selected backend. No backend split discarded. Evidence: [`plan-review-real-backend.json`](evidence/fn130/plan-review-real-backend.json). |
| Plan | default `61,420 → 54,314` (`−11.57%`); optional routes `−4.58%` to `−12.24%` | paired Claude `sonnet` B1/candidate emissions: P1–P4 `N=2`, subjective P5 `N=3`; independent Codex `gpt-5.6-sol` high scorer; 58→59 checks, zero regressions, nonzero usage; scorer-only oracle excluded from subject prompts | **kept:** optional-route gating and independent examples trim. Prior unguarded examples trim remains superseded by the sealed holdout. Evidence: [`paired-emissions.json`](../plan/evidence/fn130/paired-emissions.json). |
| Work | default `54,358 → 50,628` (`−6.86%`); delegation-active `100,851 → 100,424` (`−0.42%`) | 20 route contracts; serial/parallel/conflict/failure/review/tracker/plan-sync/delegation rails; deterministic only | **kept:** exact selection contract + active machinery gating. **discarded:** circular summary-first consent router. |
| Strategy | absent/generated `33,798 → 31,898`; husk `30,029 → 28,129`; update `30,029 → 28,567`; foreign `17,772 → 11,657` | 6/6 frozen route/safety checks; non-clobber/read-back preserved; deterministic only | **kept:** first-run/update split. **discarded:** moving foreign confirmation and nested shared read-back. |
| Make PR | HTML-off/create/finalize routes `−7,262`; HTML-on `+450` selected-route overhead | frozen dry-run/body/create/finalize/existing/push corpora and B1 unchanged slices; deterministic only | **kept:** cold HTML lens because the predeclared default route improves with zero loss. **discarded:** flat inline HTML, moving action-site safety, combining HTML with forge routing. |
| Pilot | ready `63,302 → 61,293` (`−2,009`, `−3.17%`); backlog `90,422 → 90,135` | workflow and QA hashes byte-identical to B1; verdict/strike/receipt/failure/tracker contracts pinned; deterministic only | **kept:** backlog-only `ASKED`/`TRIAGED` grammar routing. No discarded Pilot mutation. |

Model output was used only where the ratchet required judgment or a live host
smoke. Deterministic source metrics remain separate from backend-reported input,
output, cache, reasoning, cost, and duration fields. No result substitutes a
directory total or cache counter for reached-path size.

## Current-source host smokes

Run 2026-07-23/24 in a clean disposable git repository. The subject was
`Prime --classify-only`: read-only, terminal after classification, and capable
of proving selected-reference discovery. The fixture carried a complete copied
`.flow/bin/flowctl`; no product repository or tracker was touched.

| Host | Version / model | Activation | Result |
|---|---|---|---|
| Claude Code | `2.1.218`, Sonnet 5 | `/flow-next:prime --classify-only`, current canonical plugin via `--plugin-dir` | **PASS** — terminal classification; no full scorecard/fixes |
| Claude Code | `2.1.218`, Sonnet 5 | natural language: invoke Flow-Next Prime in classify-only mode | **PASS** — skill selected; terminal classification; no scouts/fixes/writes |
| Codex | `0.145.0`, `gpt-5.6-terra` | `$flow-next-prime --classify-only`, temporary `CODEX_HOME` containing the regenerated mirror | **PASS** — visibly read mirror `flow-next-prime/classification.md`; terminal classification |
| Cursor CLI | `2026.07.23-e383d2b`, Grok 4.5 | `/flow-next:prime --classify-only`, current canonical plugin via `--plugin-dir`, Ask/read-only mode | **PASS** — visibly loaded Prime + classification workflow; bounded fallback classification because Ask mode blocks shell |
| Factory Droid | `0.178.0`, Grok 4.5 high | `/flow-next:prime --classify-only`, temporary project-scoped marketplace sourced from current commit | **PASS** — terminal classification; existing released user plugin untouched |
| Grok Build | `0.2.111`, Grok 4.5 high | `/flow-next:prime --classify-only`, current local canonical plugin | **PASS** — terminal `EndTurn` classification after the complete fixture allowed the emitter |

Harness corrections retained in the record:

- Claude plan mode correctly stopped before execution; the terminal retries used
  the normal plugin toolset. A deliberately over-restrictive `--allowedTools`
  retry was stopped after the command shim could not invoke its skill.
- Grok's first headless call used the wrong `-p` shape; the next read-only
  attempts proved skill/reference discovery but ended `Cancelled` when the
  emitter could not run. The final complete-fixture run ended `EndTurn`.
- Cursor GUI was not reinstalled from this branch. Earlier interactive GUI
  discovery probes established its flattened skill naming, while this closure's
  current-source CLI run proves the changed canonical references. A current-
  branch GUI/TUI interaction remains a visible pre-release manual gate, as do
  optional interactive Droid/Grok menu inspections; no loader-trace claim is
  made for Cursor.

Temporary Grok and Droid installations/marketplace registrations were removed
after the run. The pre-existing released Droid user plugin and pre-existing
inactive skill-only probe records were not changed.

## Canonical Claude fleet smoke

Run 2026-07-24 through Claude Code `2.1.218`, Sonnet, using the actual
`/flow-next:*` commands and `--plugin-dir`. Each disposable repository loaded
exactly one inline Flow-Next plugin, used nonzero model tokens, allowed no MCP
servers, and constrained Flow-Next reads to the expected immutable B1 or current
candidate root. Tracker Sync had no live transport; Make PR used `--dry-run`;
Plan Review exported beneath its fixture instead of opening Desktop.

| Workflow | B1 | Candidate | Observable contract |
|---|---:|---:|---|
| Setup | PASS | PASS | initialized Flow and reached or completed configuration |
| Tracker Sync | PASS | PASS | inactive bridge exited without tracker receipt |
| Prime | PASS | PASS | classify-only emitted terminal classification |
| Plan | **MISS** | PASS | task created; candidate additionally read both manifests and surfaced autonomous copy-version drift before planning |
| Plan Review | **MISS** | PASS | B1 returned while export work remained in the background; candidate completed the export terminally without a review subprocess |
| Work | PASS | PASS | exact marker written, task completed, implementation committed |
| Strategy | PASS | PASS | foreign strategy preserved; user choice surfaced |
| Make PR | PASS | PASS | complete dry-run body rendered; no `gh pr create` |
| Pilot | PASS | PASS | terminal dry-run verdict; repository unchanged |

Candidate result: **9/9 PASS**. B1 result: **7/9 PASS**. Every B1 pass remains
a candidate pass; the two visible baseline misses are retained rather than
normalized away. The Plan miss caused one proximity repair: the concise
copy-mode contract now explicitly tells Plan to read `.flow/meta.json` and the
plugin manifest before Step 0. Full sanitized transcripts, tool calls, usage,
plugin hashes, repository state, and per-check verdicts:
[`claude-plugin-fleet-smoke.json`](evidence/fn130/claude-plugin-fleet-smoke.json).

The subsequent completion review found that the first Codex transform targeted
`$HOME/.codex/.codex-plugin/plugin.json` while the official installer flattens
that manifest to `$HOME/.codex/plugin.json`. The generator was fixed and pinned
against the installer target. A temporary official install plus actual
`$flow-next-plan` invocation then read the installed manifest, emitted
`Local Flow-Next copy v0.0.1 differs from plugin v3.4.1`, completed planning,
and exited zero. Evidence:
[`codex-copy-drift-smoke.json`](evidence/fn130/codex-copy-drift-smoke.json).

## Final gates

- `./scripts/sync-codex.sh` twice: 28 skills, 22 agents; second run idempotent.
- Focused integrated suites: 276 tests plus 63 Work tests passed.
- `python3 scripts/run_tests_parallel.py`: 2,286 run, 3 skipped, 0 failures,
  0 errors.
- Plugin smoke from outside the repository: 136 passed, 0 failed, including
  live Codex Plan/implementation-review and Copilot paths.
- Prime authenticated Claude baseline and candidate: 7/7 each; 6/6 synthetic
  plus negative control; all 14 retained fixture runs report nonzero usage.
- Plan paired Claude `sonnet` B1/candidate emissions: P1–P4 `N=2`, subjective
  P5 `N=3`; independent Codex `gpt-5.6-sol` high scoring produced 58→59
  passing checks with zero regressions. The sealed scorer oracle was absent
  from all subject prompts.
- Plan Review B1/candidate risky, clean, and user-edited corpora ran through
  Codex `gpt-5.6-sol` high: both risky variants caught 10/10 planted gaps,
  both clean variants shipped, and both user-edited variants preserved 37
  without restoring 50.
- Actual canonical Claude plugin fleet: candidate 9/9; B1 7/9; no candidate
  regression and two observed baseline misses repaired.
- Actual installed Codex copy-mode mismatch: manifest read, exact `0.0.1 →
  3.4.1` warning, plan completed, exit zero.
- flow-next.dev: Astro check 0 errors/warnings/hints; 74 pages built. Existing
  highlighter/chunk-size warnings are non-blocking.
- `git diff --check`, changed-reference existence, B0/B1 validation, fixture
  hash recomputation, answer-key separation, and evidence privacy grep passed.
- README/repo/site truth scan: copy-mode guidance consistently says Plan detects
  a known mismatch and directs the user to rerun Setup. No behavior-neutral
  routing change required public-site churn.
- No version manifest, tag, release, deployment, live tracker, or production
  repository was changed.

## Deferrals and rollback

Every non-target skill remains structurally untouched as recorded in
[`deferrals.md`](deferrals.md). Closure rechecked the overlaps: fn-129 remains
deferred/open; the flowctl-hardening fn-122 is done while the separate
verdict-graduation fn-122 remains open; fn-61 and fn-73 remain open. No
invocation naming/frontmatter, Audit verdict graduation, Pilot/Land terminal
grammar, or forge semantics were taken over here.

Rollback is atomic per cluster: restore that cluster's canonical router and
references from `V1/B1`, run `scripts/sync-codex.sh` twice, and rerun its
focused ratchet plus the full gate. Reverting the version contract additionally
restores the Plan-only docs in the same commit. Retain candidate and discard
evidence even after rollback so a failed experiment is not repeated.
