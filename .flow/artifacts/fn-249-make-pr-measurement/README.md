# make-pr measurement record

Measurement record for fn-249 R8 and fn-252 R11. Three points on one fixed pull
request, same model, same method:

| Point | make-pr under test | Status |
|---|---|---|
| p0-baseline | main at `7ce9dcdd` (5.6.1), before either spec | recorded 2026-09-20 |
| p1-after-input | after fn-249 (sparse aid input) | pending |
| p2-after-briefing | after fn-252 (briefing body) | pending |

## Method

- **Fixture:** pull request #449 (fn-248, capture template gate), merged. 23 changed
  files, +331 / -25, one spec, one task, seven requirement ids. Head
  `81990b699b4f352fdb31af5a7da98095311973a2`, base
  `07905c2c36b6f96eea815e120e117fff6d2bc8dc`. A scratch worktree is checked out at
  the head on a local branch named after the spec, so make-pr sees the state it
  saw when the pull request was opened: spec open, task done.
- **Invocation:** one headless run of `/flow-next:make-pr <spec> --dry-run --base <base sha>`
  per sample. `--dry-run` executes the whole authoring path (gather, compose the
  aid artifact, validate, render the body) and stops before push and create, so
  the network cost of `gh pr create` is excluded and the run is repeatable.
- **Model held constant:** `claude-fable-5-1` for every run at every point.
- **Plugin under test:** loaded from the repository path with `--plugin-dir`; user
  settings are excluded (`--setting-sources project,local`), so the installed
  plugin copy never serves the skill. The session's init event is checked for the
  plugin path.
- **Cold start each run:** the fixture is hard-reset to the head, `.flow/artifacts`
  and `.flow/tmp` are cleaned, and any scratch directory a previous run left
  under the user cache is parked. No run can reuse a prior run's artifact. This
  means the reuse-at-unchanged-head rule of fn-249 R7 is deliberately not what is
  measured; every sample pays for one full authoring pass.
- **Runs are sequential**, nothing else heavy running on the machine.
- **Metrics:** `output_tokens` is the session total from the final result event;
  `tool_calls` counts `tool_use` blocks in the stream; `wall_clock_s` is measured
  around the process. Three runs per point, medians reported.
- **Harness:** [`measure.sh`](measure.sh). Raw per-run lines: `<point>/runs.jsonl`.
  Stream logs are not committed.

## p0-baseline (2026-09-20)

| Run | Output tokens | Tool calls | Wall clock (s) |
|---|---|---|---|
| 1 | 31,698 | 22 | 325.3 |
| 2 | 21,389 | 22 | 251.1 |
| 3 | 21,627 | 18 | 249.6 |
| **Median** | **21,627** | **22** | **251.1** |

Notes, negative findings included:

- Run 1 repeated the whole rendered body (28 KB) in its final message; runs 2 and 3
  printed it once and summarized. That accounts for about 10,000 of run 1's output
  tokens. The spread is part of today's behavior and is kept.
- In all three runs the agent composed the aid artifact through shell heredocs or a
  throwaway script, never the Write tool, so authored bytes are not visible as file
  writes in the stream. Run 3's artifact was 25 KB of JSON and its body 27,457 bytes.
- Run 2 reported one self-correction after printing the body (a wrong count fixed
  and re-rendered).
- A dry run persists no aid artifact in the repository.

## Limits

- One fixture. A larger or chained pull request may behave differently.
- n = 3 per point: a difference smaller than the run-to-run spread above (about
  10,000 tokens, 75 s) is not evidence of a change.
- Headless print mode; an interactive session carries more context.

## Recomputed authored bytes (2026-09-20)

Strict, proven omissions save **40,957 bytes (2.5553%)** across the 39 tracked
artifacts in this clone. This is much smaller than the Goal's 57% mechanical
field estimate. That estimate described 111 artifacts; this measurement uses
only the 39 returned by the current index, with 2,236 file rows.

| Measure | Bytes |
|---|---:|
| Complete artifacts as stored | 1,602,803 |
| Sparse inputs plus unchanged artifacts without an identity solution | 1,561,846 |
| Proven reduction | 40,957 |

| Omitted field | Occurrences | Bytes saved |
|---|---:|---:|
| `changeType` | 155 | 5,687 |
| `additions` | 155 | 4,478 |
| `deletions` | 155 | 4,361 |
| `diffUrl` | 0 | 0 |
| `sourceRefs` | 0 | 0 |
| `rIds` | 118 | 5,148 |
| `taskIds` | 132 | 13,644 |
| `attentionClass` | 177 | 7,639 |
| Whole rows added by flowctl | 0 | 0 |

Method and limits:

- [`authored_bytes.py`](authored_bytes.py) selects JSON files beneath
  `*/pr-cognitive-aid/` from `git ls-files .flow/artifacts`, reads UTF-8, and
  compares complete and sparse inputs using flowctl's canonical serialization
  (sorted keys, two-space indentation, UTF-8, final newline). In this corpus,
  canonical complete bytes equal the actual stored bytes. Formatting changes
  earn no savings; every retained value and array order must remain identical.
- The script calls the branch's own expansion function for each proposed
  omission and for the final sparse input. It retains fields unless expansion
  reproduces the complete canonical bytes without errors. It tries whole empty
  rows first, then the fields in table order; byte attribution includes their
  JSON syntax and indentation and has no double counting. All 2,236 stored rows
  have non-empty summaries, so none can disappear. On these artifacts the
  remaining field omissions are independent, yielding the smallest input by
  omission of the supported fields wherever identity is possible. It does not
  rewrite groups, sources, judgments, or stored artifacts.
- Historical metadata comes from flowctl's own copy-aware diff reader and parser,
  substituting the recorded head for `HEAD` in its Git reads. There is no
  checkout, fetch, or invented metadata. Lazy fetching is disabled. Git cannot
  read 22 recorded ranges in this clone. For those artifacts the script passes
  no metadata, retains additions/deletions/change type and whole rows, and still
  proves any independent reference or attention omission. The result is a
  conservative locally provable figure, not a prediction for a complete clone.
- **29 artifacts have no identical expansion even as complete input.** They
  omit `diffUrl` on 1,172 rows, and this branch's expansion adds it. No supported
  omission can suppress that addition. The script explicitly reports these as
  having no identity solution and carries their original size into the total
  with zero savings; it does not claim their unchanged inputs round-trip.
  This historical compatibility finding is retained for the host; product
  changes are outside this measurement unit.
- The other 10 artifacts shrink. Existing diff links differ from the derived
  anchors and must remain. No source-reference omission reproduces the stored
  arrays. This measures expansion identity, not full historical validation or
  current-head eligibility. It does not measure tokens, calls, or time.

Rerun from the repository root:

```bash
python3 .flow/artifacts/fn-249-make-pr-measurement/authored_bytes.py
```

The JSON output includes aggregate and per-artifact counts, unavailable-diff
errors, added fields/rows preventing identity, and the per-field breakdown.
The indexed corpus and locally available Git objects determine the result.
The baseline runs and `measure.sh` were neither changed nor executed for this
figure. The after-input timing measurement remains pending.
