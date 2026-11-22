# Flow-Next Usage Guide

Task tracking for AI agents. All state lives in `.flow/`.

## CLI

```bash
flowctl --help              # All commands
flowctl <cmd> --help        # Command help
```

## IDs

- Specs: `fn-N-slug` where slug is derived from title (e.g., fn-1-add-oauth, fn-2-fix-login-bug)
- Tasks: `fn-N-slug.M` (e.g., fn-1-add-oauth.1, fn-2-fix-login-bug.2)
- Charts share the native `fn-N` domain with specs (never the same id)
- Tracker-keyed ids coexist and resolve (`wor-17-slug`, `gh-123-slug`, `gl-456-slug`). Default: `config set tracker.specIds tracker`.

**Backwards compatibility**: Legacy formats `fn-N`, `fn-N-xxx`, `fn-N.M`, and `fn-N-xxx.M` still work.

## Chart (optional pre-capture discovery)

One oversized/unclear idea whose **destination is nameable but route is not** (a direction like "make X more Y" is refused - narrow it or run prospect); one decision (`<chart-id>.D<n>`) per invocation; never a pilot stage. `chart frontier` is the sole work-mode selection input; `chart claim` then `chart resolve --answer-file` close it; every work invocation ends with one greppable `CHART_VERDICT=...` line. Chart never writes specs; capture ingests the briefing.

## Common Commands

The typical flow. Everything else (deps, block/reset, memory, glossary, config, tracker sync, checkpoints): `flowctl --help` and `flowctl <cmd> --help`.

```bash
flowctl list                          # all specs + tasks grouped
flowctl show fn-1-add-oauth.2         # spec or task detail (cat for raw markdown)
flowctl ready --spec fn-1-add-oauth   # tasks ready to work on
flowctl spec create --title "..." --plan-file plan.md --json
flowctl task create --spec fn-1-add-oauth --from-json tasks.json
# tasks.json: [{"title":"...","satisfies":["R1"]},{"title":"...","deps":[1]}]
# edit: set-description/set-acceptance/set-spec, set-plan
flowctl start fn-1-add-oauth.2        # claim task
flowctl done fn-1-add-oauth.2 --summary-file s.md --evidence-json e.json
flowctl task reset fn-1-add-oauth.2   # back to todo
flowctl validate --all                # check structure
```

## Orchestration & model steering

The multi-CLI bridge and model-steering recipes moved to their own guide. Run `flowctl usage --orchestration` now, before bridging work to another model or CLI or picking an implementation or review model, and follow it exactly.

## Workflow

1. `flowctl specs` - list all specs
2. `flowctl ready --spec fn-N-slug` - find available tasks
3. `flowctl start fn-N-slug.M` - claim task
4. Implement the task, then `git commit` the work (the evidence JSON cites this commit)
5. `flowctl done fn-N-slug.M --summary-file ... --evidence-json ...` - complete
6. Stage the receipt: `done` writes the summary into the tracked task file AFTER your commit - include it in your next commit (it lists the path under `modified_paths` and prints a note when the file is left dirty)

If a sandbox denies `git commit`, still complete `done` with the evidence you have and record the restriction in the summary - never block the task on a commit you cannot make; the receipt then needs a later commit by whoever can make one.

## Verification scoping

Per-task Quick commands list FOCUSED suites for the files you touch - that is what workers baseline and verify per task. The FULL suite runs only when the repository's instructions or the person ask for it; prefer the repo's parallel test entrypoint when one exists (see the project instruction file for the canonical command).

## Evidence JSON Format

```json
{"commits": ["<sha>"], "tests": ["<command>"], "prs": []}
```

## Parallel Worktrees

Runtime state (status, assignee, etc.) is stored in `.git/flow-state/` (or `$FLOW_STATE_DIR` when set), shared across worktrees.

## Pre-1.0 layout porting

Rename `.flow/epics/` to `.flow/specs/` (merge JSON into an existing `specs/` if present). Rewrite keys: `meta.json` `next_epic` -> `next_spec` and `schema_version` -> 3; each task JSON `epic`/`epic_id` -> `spec`/`spec_id`; write `.flow/.flow_version` with payload `1.0.0`. Run `flowctl validate --all`.

## More Info

- Human docs: https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/docs/flowctl.md
- CLI reference: `flowctl --help`
