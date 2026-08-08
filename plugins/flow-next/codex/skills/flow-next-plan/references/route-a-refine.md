# Plan Route A — refine an existing Flow ID

Load this reference only when Step 5 took Route A: the input resolved to an
existing spec or task id (including a tracker handle resolved via R16). Route B
(new idea) never reaches this file.

The Step 5 efficiency note still binds: author with **Write**, revise with
**Edit** — never compose a document inside a bash heredoc or stdin pipe.

1. If spec ID (fn-N-slug or legacy fn-N/fn-N-xxx):
 Compose the revised plan as a FILE: `"$FLOWCTL" cat <id> > "${TMPDIR:-/tmp}/flow-plan-body-<suffix>.md"` (or Write it fresh), revise it with **Edit** (span edits, not re-emission), then:
 ```bash
 $FLOWCTL spec set-plan <id> --file "${TMPDIR:-/tmp}/flow-plan-body-<suffix>.md" --json
 rm -f "${TMPDIR:-/tmp}/flow-plan-body-<suffix>.md"
 ```
 - Create/update child tasks as needed

2. If task ID (fn-N-slug.M or legacy fn-N.M/fn-N-xxx.M):
 ```bash
 # Combined set-spec: description + acceptance in one call
 # Write to temp files only if content has single quotes — unique per-task paths
 # (path-persistence rule: literal agent-composed paths, never shared fixed names)
 $FLOWCTL task set-spec <id> --description "${TMPDIR:-/tmp}/flow-plan-desc-<task-id>.md" --acceptance "${TMPDIR:-/tmp}/flow-plan-acc-<task-id>.md" --json
 ```

**Source-tag consumption (Route A refine of a capture-authored spec):** `/flow-next:capture` tags each acceptance criterion with its provenance — `[user]` (verbatim), `[paraphrase]` (user-grounded), `[inferred]` (the agent filled a gap), `[strategy:<track>]`. capture invests real machinery in these *so plan can scrutinize them* — do not plan an `[inferred]` criterion as established fact. When the spec carries source tags:
- `[user]` / `[paraphrase]` / `[strategy:*]` → user- or strategy-grounded; plan normally.
- `[inferred]` → **unconfirmed**. Route it through the Step-1 scouts (does the codebase actually support/need it?). A scout-confirmed inference becomes a normal criterion (drop the tag); an **unconfirmed** one moves to `## Open Questions` (or renders as a `⚠️ unconfirmed inference` coverage-table row) rather than being silently planned as a requirement. This closes capture→plan: the provenance capture records is otherwise dropped at the one consumer built to read it.

Then return to Step 5 and apply the plan-content rules (spec scaffold, R-ID rule
including per-R error/boundary enumeration, source-tag consumption), the
task-spec content rules (artifact split, `**Touches:**`, `satisfies`), spec
dependencies (both directions), and task dependencies.
