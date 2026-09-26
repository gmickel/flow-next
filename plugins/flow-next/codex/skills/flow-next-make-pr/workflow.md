# /flow-next:make-pr workflow

Run in order; preserve variables. Require `.flow/`, git, jq and Python. Failed preflight, close, staging or close commit stops before export and PR creation; never skip close.
Use `set -e`, the resolved `FLOWCTL`, and `REPO_ROOT=$(git rev-parse --show-toplevel)`.
## Phase 0: Pre-flight

Run the fences; an information prompt may interrupt and rerun its fence. Dry-run skips installation/auth checks.
Explicit `--base <branch>` uses `origin/<branch>`, refreshed on real runs. Chain detection uses shared history; first match wins.
Merged-parent rewrites require create, a clean tree, ancestry and lease guards; dry-run reports and update never rewrites.
Resolve `SPEC_ID` from the argument or the first current-branch `branch_name` match in
`.flow/specs/*.json`; leave it empty if none. Source the bundled script in Bash
with the parsed argument variables (including `AUTONOMOUS`) set. It retains the
phase outputs in the same shell; do not print or reassemble its source.

```bash
source "$(dirname "$FLOWCTL")/make-pr-preflight.sh"
```

Exit 1 is failure; exit 2 needs human intervention; exit 3 carries `NEED_INPUT:`.
Under `FLOW_RALPH`, `REVIEW_RECEIPT_PATH`, `FLOW_AUTONOMOUS=1`, `AUTONOMOUS=1`,
or `mode:autonomous`, never prompt: preserve the exit outcome. Attended, resolve
only the named missing input and rerun.

Already-closed specs stay untouched. Otherwise completed specs close on the head branch before Phase 1. Incomplete or
task-less specs have no close commit and still compose interactively. For `OPEN_COUNT > 0`,
Ralph/autonomous hard-errors (exit 2). Dry-run and body-only updates never close. Under `--update` an
existing OPEN PR is REQUIRED; closed/merged PRs do not prevent a create. Preserve `PHASE0_CONTEXT.head`.
## Phase 1: Gather inputs

Capture `EXPORT_PAYLOAD` from `$FLOWCTL spec export-cognitive-aid "$SPEC_ID"
--base "$BASE_REF" --json` once, after close. Refresh `HEAD_SHA` and `MERGE_BASE`
from this head and base. For each entry in `specs` (otherwise the host), stop for empty goal/context AND
empty task summaries. Only the host aborts for nonempty criteria ALL in `tasks_summary.undeclared_r_ids`
(`Undeclared R-ID coverage`); siblings render those requirements as uncovered. No requirements is valid.
## Phase 1.5: Structured PR cognitive-aid

Read [pr-cognitive-aid.md](pr-cognitive-aid.md) and execute it on every entry path, including dry-run and
update, before optional HTML or body delivery.
## Phase 1.5b: HTML render lens (opt-in)

```bash
HTML_LENS=$("$FLOWCTL" config get artifacts.html.enabled --json | jq -r 'if .value == true then "true" else "false" end')
[[ "$DRY_RUN" == "1" ]] && HTML_LENS=false
```

When true, read [html-lens.md](html-lens.md) in full and execute it end-to-end. When false,
do not read `html-lens.md` or the shared disclosure reference; emit no artifact, commit, body line or output. The lens is
unchanged; retain its optional Render lens line when it succeeds.
## Phase 2: Deliver the briefing

Use rendered `BODY_FILE` unchanged; append the enabled lens line before `Ref` / Stack lines.
The renderer's numbered groups and linked file lists supply the structural sketch; the lens's old summary-block references mean this position.

For dry-run, print `BODY_FILE` and stop. Otherwise read [create-and-finalize.md](create-and-finalize.md) and
complete it.

[Manual smoke](references/manual-smoke.md) is a maintainer checklist, never loaded at runtime.
