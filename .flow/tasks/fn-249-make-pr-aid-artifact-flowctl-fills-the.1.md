---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-249-make-pr-aid-artifact-flowctl-fills-the.1 Implement make-pr aid artifact: flowctl fills the diff metadata

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Aid validate and write now accept sparse input and store the complete v1 object: flowctl fills change type, line counts and diff link from the bound diff, inherits group references per field, adds empty-summary rows for unlisted paths, derives the attention class only from zero-judgment path patterns, and reports every independent violation in one call. The managed ignore block keeps aid generations and write locks local, and the measurement record carries the recomputed authored-bytes figure.

Tier: implementer = gpt-6-astra at medium (explicit invocation; reached over the codex CLI bridge)

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: implement - ran (model: gpt-6-astra at medium, `codex exec --sandbox workspace-write`, 8 foreground runs, one per scope unit plus one R7 rework and one R8 addition; delegated: 3)

Baseline: none (the spec defines no Quick commands). The sandbox denied every child commit (`.git` read-only in a linked worktree); the worker committed each child tree with `git add -A` between runs.

### Per R-ID

- R1, R2, R5: `_expand_pr_cognitive_aid_input` in flowctl.py, tests in test_pr_cognitive_aid_sparse.py (all git statuses incl. copied/renamed, underivable field names row and field, supplied mismatch still rejected, sparse and complete input store identical bytes at the same path, per-field inheritance, ungrounded summary and unknown references still rejected).
- R3: validator collects violations in traversal order; tests in test_pr_cognitive_aid_violations.py (parse error alone in both formats, pathless row reported once, containers and bindings do not hide independent errors). `--json` carries the same lines in the existing `error` string; no new field.
- R4: unlisted paths get rows with `summary: ""`, the diff-metadata source only, empty rIds/taskIds. Attention is `mechanical` for `.flow/tasks/*.json`, `.flow/specs/*.json` and named lockfiles, `generated` for the codex mirror prefix, `canonical` otherwise; an authored row with no class and no pattern is rejected naming the row. make-pr aid instructions: 143 lines at the base, 143 now.
- R6: two managed patterns (`artifacts/*/pr-cognitive-aid/*.json`, `.../.write.lock`); tests in test_flow_gitignore.py cover fresh, existing and hand-edited blocks, preserved user patterns, a broad stage, and that tracked files are never untracked. CHANGELOG `## Unreleased` gives the one-time untracking step; docs/pr-cognitive-aid.md states the per-clone limit. The measurement directory is not ignored (`git check-ignore` rc 1). No aid file in this repo was untracked.
- R7: no write-side change (see finding). test_pr_cognitive_aid_reuse.py pins the seam make-pr's resolve step depends on: a generation written from sparse input resolves as `current` at the unchanged base and head; moved head, missing artifact and failed validation do not.
- R8: `.flow/artifacts/fn-249-make-pr-measurement/authored_bytes.py` plus a new README heading. The measurement harness was not run; the after-measurement is the conductor's.

### Findings for the PR body

R6, staging mechanism in repositories without a local ignore rule: no flow-next skill or flowctl command stages aids explicitly. The work skill and Ralph template use broad `git add -A`, which can sweep in unignored aid generations and locks. This repository's root `.gitignore` has ignored the aid directory since 2026-08-17; no aid file was added after that date. Its 69 tracked aid files are grandfathered, and the changelog's one-time untracking step addresses those paths. Managed ignore rules protect other repositories without a local rule; the regression test covers a broad stage. No tracked aid was untracked here.

R7, why same-head generations exist (first Parked unknown): neither a reuse miss nor a base change. Aid artifacts are per-clone, so the worktree (39 tracked generations, 30 specs, zero repeated heads) could not show them; the clone that holds them (78 generations, 56 specs, 11 multi-generation) has 3 same-head specs: fn-207, fn-224, fn-239. In each pair base and head are identical, the second explicitly supersedes the first and was written 0.5 to 3 minutes later inside one run. Beyond id, timestamp and supersedes, the pairs differ in one thesis, one proof cell value, and four diffUrl values; every other leaf (339 to 1233 per artifact) is identical. They are same-run corrections of authored content, forced to re-author the whole object because generations are immutable. make-pr's resolve step already reuses a current generation before composing, which predates this spec. The child's first R7 attempt (a write-side guard returning the existing generation at a matching base and head) would have silently dropped such corrections while reporting success, and it rewrote two existing tests that pin same-head supersession; it was reworked out before commit. The spec's count (5 of 76 specs) was not reproducible from either clone.

Second Parked unknown (which group carries added rows): existing step groups, last step first, moving to preceding steps only at the 200-file limit. No group is invented, so the one-to-seven step rule and the optional kept/verify groups are untouched; verified against a seven-step, 500-file fixture.

R8 figure, negative results kept: the review fix recomputes strict identity savings as 51,595 of 1,602,803 bytes (3.2190%) over the 39 tracked artifacts. The pre-review result was 40,957 bytes (2.5553%), with unconditional fragment addition blocking identity for 29 artifacts and 1,172 rows. Bound blob links now leave absent URLs alone when historical diff metadata is unavailable; 14 artifacts with 843 added links still have no identical expansion. Git cannot read 22 of 39 recorded ranges. Under the same assumptions (stored mechanics stand in for unreadable ranges; identity modulo added diffUrl), savings remain 267,077 bytes (16.6631%). Both remain far below the Goal's 57% estimate. Neither counts rows an agent would now omit, because every stored row has a summary.

### Surprises the reviewer should weigh

- diffUrl: R1 requires the diff link to be filled, but a forge URL is not derivable from the diff. flowctl now derives `/<owner>/<repo>/blob/<headSha>/<path>` from local origin identity and the artifact head, URL-encoding the path; without identity or a bound diff the optional link remains absent. diffUrl and the line counts were optional before and rendered as a dash; input that omitted them now renders a link and counts. The renderer itself is unchanged, but this is a visible effect next to the "no change to what the PR body renders" boundary.
- `summary: ""` on flowctl-added rows keeps the v1 key set, but a reader that vendored the old validator rejects an empty summary. The spec requires "no summary" on those rows, so some relaxation was unavoidable.
- Inherited sourceRefs mean a group must itself cite the diff-metadata source for its sparse rows to pass the existing "file cites diff_metadata" rule; the instructions say so.
- The `generated` pattern is this repository's mirror prefix, hardcoded in flowctl; it is inert elsewhere.
- Worker edits on top of the child's range: the reuse test used a repo-rooted scratch directory (now the default temp dir); a test the child added for the measurement script was left out of the suite (it coupled the product suite to a one-off script and needed `.flow/tmp` to exist); three ruff findings fixed in 281e2287.

Follow-up, not built: a way to correct one authored field of a current generation without re-authoring the whole object is the actual remedy for same-head generations.

### Gates (at 281e2287)

- `python3 scripts/run_tests_parallel.py`: suite_rc=0, 4961 ran, 0 failures, 0 errors, 6 skipped; green receipt written.
- `uvx ruff@0.16.0 check .`: rc=0.
- `bash scripts/make-pr_smoke_test.sh`: rc=0, 75 pass.
- `bash scripts/smoke_test.sh`: rc=1, 132 pass, 1 fail: `copilot plan-review re-review ... NOT_RETRYABLE`, the pre-existing local-environment case.
- sync-codex twice (second a no-op) and tracker manifest regenerated; tree clean.
## Evidence
- Commits: 11cb7be0937dd4e9c77b36e2ae1dc35933ee55ab, 3fc36c9651cccf83add3aa9c8fe7b19c8bfb5eb8, f04d11cae0e16c361405e436faeb0759f5db6be0, 281e2287027bfdc2317e09fed597f242875a602d, 7128a427c6ca96c8ac4f23492df51440d7b53a8e, 7620eb9ffcca5907f5f4aac9716d22de85e2a6cd, 785b4aebe5abf5ab451404494489c4d11e81e27b, 2798cfdec2c1aaa4a7212df3986a06b4a0345ac9, f632be745be42666e8bc747f63a2d4e4c56883b5, 95badbc43c318a27ec006bafd9bfa416bd26584d, 011bd82fc7d6ac571e5c21a54fdec255f527d297
- Tests: baseline: none (spec defines no Quick commands), python3 scripts/run_tests_parallel.py (at 281e2287: suite_rc=0, files=230 ran=4961 failures=0 errors=0 skipped=6; green receipt .flow/tmp/green-receipts/281e2287-unittest.json), uvx ruff@0.16.0 check . (rc=0 at 281e2287), bash scripts/make-pr_smoke_test.sh from plugins/flow-next (rc=0, PASS 75 FAIL 0), bash scripts/smoke_test.sh from plugins/flow-next (rc=1, passed 132 failed 1: 'copilot plan-review re-review ... NOT_RETRYABLE: artifact unchanged since last verdict', the pre-existing local-environment case named in the dispatch), ./scripts/sync-codex.sh twice (second run no-op) and python3 scripts/gen_tracker_manifest.py (tree clean afterwards), python3 .flow/artifacts/fn-249-make-pr-measurement/authored_bytes.py (rc=0; strict 2.5553%, assumptionsAB 16.6631%), python3 scripts/run_tests_parallel.py after review fixes (4966 ran, 0 failures, exit 0), uvx ruff@0.16.0 check . (exit 0), bash scripts/make-pr_smoke_test.sh (75 pass, exit 0), bash scripts/smoke_test.sh (132 pass, 1 pre-existing live-CLI failure), python3 scripts/check_doc_anchors.py (exit 0)
- PRs: