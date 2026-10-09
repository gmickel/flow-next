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
The spec close commits as `chore(flow): close <spec-id>`. When the project instructions set
commit-message rules, set `CLOSE_COMMIT_MESSAGE` to a close message that follows them. Leave it
unset when the rules need a value you cannot find, such as a work-item id; the default applies.

```bash
source "$(dirname "$FLOWCTL")/make-pr-preflight.sh"
```

Exit 1 is failure; exit 2 needs human intervention; exit 3 carries `NEED_INPUT:`; exit 4 (`NO_SPEC`)
means the branch carries no spec: take the no-spec path in [no-spec-path.md](no-spec-path.md) and skip
every later phase. A repo
without `.flow/` takes that path without running the script.
Under `FLOW_AUTONOMOUS=1`, `AUTONOMOUS=1`, or `mode:autonomous`, never prompt: preserve the exit outcome. Attended, resolve
only the named missing input and rerun.

Already-closed specs stay untouched. Otherwise completed specs close on the head branch before Phase 1. Incomplete or
task-less specs have no close commit and still compose interactively. For `OPEN_COUNT > 0`,
autonomous hard-errors (exit 2). Dry-run and body-only updates never close. Under `--update` an
existing OPEN PR is REQUIRED; closed/merged PRs do not prevent a create. Preserve `PHASE0_CONTEXT.head`.

## Phase 1: Gather inputs

Capture `EXPORT_PAYLOAD` from `$FLOWCTL spec export-cognitive-aid "$SPEC_ID"
--base "$BASE_REF" --json` once, after close. Refresh `HEAD_SHA` and `MERGE_BASE`
from this head and base. For each entry in `specs` (otherwise the host), stop for empty goal/context AND
empty task summaries. Only the host aborts for nonempty criteria ALL in `tasks_summary.undeclared_r_ids`
(`Undeclared R-ID coverage`); siblings render those requirements as uncovered. No requirements is valid.
## Phase 1.5: Structured PR cognitive-aid

Read [pr-cognitive-aid.md](pr-cognitive-aid.md) and execute it on every entry path, including dry-run and
update, before body delivery.
## Phase 2: Deliver the briefing

Use rendered `BODY_FILE` unchanged, before `Ref` / Stack lines.
The renderer's numbered groups and linked file lists supply the structural sketch.

For dry-run, print `BODY_FILE` and stop. Otherwise read [create-and-finalize.md](create-and-finalize.md) and
complete it.

