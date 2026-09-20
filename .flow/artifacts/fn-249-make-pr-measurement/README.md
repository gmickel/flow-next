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
