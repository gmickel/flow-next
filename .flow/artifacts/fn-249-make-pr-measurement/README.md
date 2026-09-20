# make-pr measurement record

Measurement record for fn-249 R8 and fn-252 R11. Three points on one fixed pull
request, same model, same method:

| Point | make-pr under test | Status |
|---|---|---|
| p0-baseline | main at `7ce9dcdd` (5.6.1), before either spec | recorded 2026-09-20 |
| p1-after-input | after fn-249 (sparse aid input), branch head `3fc36c96` | recorded 2026-09-20 |
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

## p1-after-input (2026-09-20)

Same fixture, model, harness and cold start. Plugin under test: the fn-249
branch at `3fc36c96`, after its review fixes (all four aid entry points expand
sparse input, so the dry run renders the walkthrough; checked in every stream).

| Run | Output tokens | Tool calls | Wall clock (s) |
|---|---|---|---|
| 1 | 25,653 | 18 | 273.3 |
| 2 | 18,031 | 22 | 212.3 |
| 3 | 29,223 | 20 | 309.8 |
| **Median** | **25,653** | **20** | **273.3** |

| Median | p0 | p1 | Change |
|---|---|---|---|
| Output tokens | 21,627 | 25,653 | +18.6% |
| Tool calls | 22 | 20 | -2 |
| Wall clock (s) | 251.1 | 273.3 | +8.8% |

**Result: no measurable improvement; the medians moved the wrong way, inside the
run-to-run spread.** This is a null result and is kept as one.

What the streams show:

- The spread is dominated by whether a run repeats the whole rendered body in its
  final message. One of three runs did at p0 (28 KB final message); two of three
  did at p1 (25 KB and 28 KB). Each repeat costs roughly 6,000 to 7,000 output
  tokens. Subtracting an estimate of the final message (characters / 4) gives
  medians of about 20,600 tokens at p0 and 19,500 at p1: equal within noise. That
  subtraction is an estimate made after seeing the data and is not a finding.
- The characters the agent spent authoring the aid artifact did not shrink:
  12,349 / 13,793 / 13,919 at p0 and 12,560 / 13,420 / 12,333 at p1. At p0 the
  agents were already avoiding the transcription this spec removes: every run
  composed the artifact with a throwaway script that read the mechanical fields
  out of the export, so they were never typed. On this 23-file fixture the
  judgment text (thesis, groups, per-file summaries) is nearly all of what is
  authored, which matches the recomputed strict figure below (3.2%).
- p1 runs split the authoring across more, smaller tool calls (5 to 7 against 2
  to 3) with the same total.

What this does and does not license: sparse input removes a failure class (a
first write rejected over a value an agent cannot know, corrected one error per
attempt) and that is covered by tests, not by this timing. It does not make an
ordinary make-pr run on a mid-sized pull request cheaper. The cost sits in the
instructions read and the body rendered, which the sibling briefing spec changes;
p2 is where a difference should show if there is one.

## Limits

- One fixture. A larger or chained pull request may behave differently.
- n = 3 per point: a difference smaller than the run-to-run spread above (about
  10,000 tokens, 75 s) is not evidence of a change.
- Headless print mode; an interactive session carries more context.

## Recomputed authored bytes (2026-09-20)

Strict, proven omissions save **51,595 bytes (3.2190%)** across the 39 tracked
artifacts in this clone. This is much smaller than the Goal's 57% mechanical
field estimate. That estimate described 111 artifacts; this measurement uses
only the 39 returned by the current index, with 2,236 file rows.

| Measure | Bytes |
|---|---:|
| Complete artifacts as stored | 1,602,803 |
| Sparse inputs plus unchanged artifacts without an identity solution | 1,551,208 |
| Proven reduction | 51,595 |

| Omitted field | Occurrences | Bytes saved |
|---|---:|---:|
| `changeType` | 155 | 5,687 |
| `additions` | 155 | 4,478 |
| `deletions` | 155 | 4,361 |
| `diffUrl` | 0 | 0 |
| `sourceRefs` | 0 | 0 |
| `rIds` | 191 | 7,644 |
| `taskIds` | 257 | 19,608 |
| `attentionClass` | 227 | 9,817 |
| Whole rows added by flowctl | 0 | 0 |

The pre-review expansion saved 40,957 bytes (2.5553%). It always added a
path-hash fragment, even without bound metadata, preventing identity for 29
artifacts (1,172 missing links). That result remains a negative baseline. After
the review fix, links use `/<owner>/<repo>/blob/<headSha>/<path>` and require
both local origin identity and bound metadata. This clone resolves
`gmickel/flow-next`; unavailable historical ranges now leave omitted links
absent, allowing more independent reference and attention omissions. The
conditional figure below is unchanged. Neither result approaches the original
57% estimate.

**Conditional figure under assumptions A and B**

| Measure | Bytes |
|---|---:|
| Complete artifacts as stored | 1,602,803 |
| Sparse inputs under assumptions A and B | 1,335,726 |
| Conditional reduction (16.6631%) | 267,077 |

Assumption A uses each row's stored `changeType`, `additions` and `deletions`
when Git cannot read its recorded range; verification against the live diff
when the artifact was written is assumed, not re-proven here.
Assumption B judges expansion identity modulo `diffUrl` values added to rows
whose stored form had none; every other leaf still matches byte for byte,
and a stored `diffUrl` differing from the derived head-bound blob link stays in the sparse input.
Neither figure counts rows an agent would now simply not write, since every
stored row has a summary, so the input-side saving from unlisted paths is not
measurable from stored artifacts.

Strict-mode method and limits:

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
- **14 artifacts have no identical expansion even as complete input.** They
  omit `diffUrl` on 843 rows, and this branch's expansion adds it. No supported
  omission can suppress that addition. The script explicitly reports these as
  having no identity solution and carries their original size into the total
  with zero savings; it does not claim their unchanged inputs round-trip.
  This historical compatibility limit remains part of the result.
- The other 25 artifacts shrink. Existing diff links differ from the derived
  head-bound blob links and must remain. No source-reference omission reproduces the stored
  arrays. This measures expansion identity, not full historical validation or
  current-head eligibility. It does not measure tokens, calls, or time.

Rerun from the repository root:

```bash
python3 .flow/artifacts/fn-249-make-pr-measurement/authored_bytes.py
```

The single JSON output reports both `strict` and `assumptionsAB` modes, each
with aggregate and per-artifact counts, unavailable-diff errors, added fields/rows
preventing identity, and the per-field breakdown.
The indexed corpus and locally available Git objects determine the result.
The baseline runs and `measure.sh` were neither changed nor executed for this
figure. The after-input timing measurement is recorded above under p1-after-input.
