# Refine — research scope (loaded when `SCOPE == research`)

> Read at the Setup routing line in SKILL.md. A business, technical, or both pass never reads this file.

**Decision record**

- Source: fn-238 R16, the read-first signal on the route matrix's ready-spec row.
- Trigger: a spec or task names a library or API the repo does not already use, and nobody has read its current docs yet.
- Purpose: resolve library versions, changed APIs, gotchas, the docs that must change, and the project memory that applies, once, into one section both refine and plan recognise, before work starts on either route.
- Evidence: a worker that meets an unfamiliar API mid-task either guesses from training data or stops to research inside its implementation context; plan already runs the same scouts and used to keep their findings only in task bodies, where a no-plan spec never sees them.
- Disposition: keep. One artifact (`## Resolved via Research`), one skip rule shared with plan, never run by default.

## Contract

- **No questions.** The research pass asks nothing and runs no interview rounds. It reads the target, decides whether to run, dispatches the read-only scouts, and writes one section back through the shared read-back contract.
- **Four scouts, plus one gated.** `docs-scout` (official docs, version anchored on the repo's manifest scan), `practice-scout` (current best practices and pitfalls), `docs-gap-scout` (the repo's own docs that must change), and `memory-scout` (the bug and knowledge entries that apply). `github-scout` joins only when `scouts.github` is on, as in plan. Not `repo-scout` (the technical pass's fact scouts and plan's decomposition already cover repo patterns), not `spec-scout`, not `flow-gap-analyst`.
- **The section is the artifact.** `## Resolved via Research` on the spec (or the task body for a task target): one sub-block per scout that ran, one bullet per finding, a source on every line. Plan writes the same section when its Step 1 runs the same scouts, so the two never produce two copies.
- **Where research lands.** Research lands in the spec when a human should see it before ratifying and when it must survive the route choice (direct or planned); what only the implementer needs stays with the worker, in the task body or the worker's own investigation.
- **Never by default.** Flow routes here only on the read-first signal from `route-matrix.md`; the manual user names the scope. `flow --auto` (fn-239) never runs it.

## Setup

`flowctl scope resolve` returns `research` and passes every other token through in `remaining_args`. Strip the one research-only flag before input detection:

```bash
FORCE=0
case " $ARGUMENTS " in *" --force "*) FORCE=1 ;; esac
ARGUMENTS="$(printf '%s' "$ARGUMENTS" | sed -E 's/(^| )--force( |$)/ /g' | xargs)"
```

Then Detect Input Type exactly as SKILL.md states it. A file-path target is out of scope for this pass: print `research: skipped(policy: research writes a spec or task section; give a spec or task id)` and stop.

## Skip rule (observable)

Decide from what already exists, and say which case applied in the summary:

- **The section is present.** The target body carries `## Resolved via Research`: skip, write nothing, and name the section as the reason.
- **Plan already ran the scouts.** A spec target whose tasks (`$FLOWCTL tasks --spec <id> --json`, then `$FLOWCTL cat <task-id>`) carry plan's scout findings: skip, write nothing, and name the task that holds them.
- **Delta rerun.** When either case above would skip but the spec now names a library or API that neither the section nor the task findings mention, run the pass for that delta only. New bullets append under their scout's sub-block; existing bullets come back byte-for-byte.
- **`--force`.** Rerun the whole pass and replace the section.

Otherwise run the pass and say which scouts are being dispatched.

## Dispatch

Dispatch the scouts in parallel as read-only subagents (`Task` with `subagent_type: flow-next:docs-scout`, `flow-next:practice-scout`, `flow-next:docs-gap-scout`, `flow-next:memory-scout`, and `flow-next:github-scout` when gated on; on hosts without those agents, the host's generic read-only dispatch with Edit/Write disallowed, or inline WebFetch and `flowctl memory search` on the same brief). The brief per scout: the target's title, the sections that name the library or API, the repo's manifest files, and the instruction to return one line per doc, API signature, gotcha, doc-to-change, or memory entry with its source. `memory-scout` is a **fast scout** dispatch; the others are **thinking scout** dispatches under the routing precedence in `flow-next-plan/steps.md` Step 1. A scout that returns nothing is recorded as `<scout>: no findings`, never invented.

## Section shape

```markdown
## Resolved via Research
<!-- provenance: refine --scope=research (docs-scout, practice-scout, docs-gap-scout, memory-scout) on <YYYY-MM-DD>; plan writes the same section when its Step 1 runs the same scouts -->

### docs-scout
- **<library> <version>** — <what the docs settle: the API signature, the changed behaviour, the constraint>. Source: <url>

### practice-scout
- **Gotcha:** <the pitfall that bites at implementation time and its workaround>. Source: <url>

### docs-gap-scout
- **Docs that must change:** <repo doc path> — <what changes and why>. Source: <path:line>

### memory-scout
- **<entry title>** — <the rule or pitfall that applies here>. Source: <memory entry id>
```

One sub-block per scout that ran (omit a scout's block when it returned nothing, and say so in the summary), one bullet per finding, every bullet with a `Source:`. Version numbers come from the manifest scan (docs-scout's version anchor), never from memory. docs-gap-scout's findings read as "docs that must change" so the worker and the reviewer both see them. No fenced code, no pasted excerpts: the link carries the depth, the bullet carries the decision.

## Write-back

Compute the write policy with `scope write-policy research` (it lists every canonical section as preserved and only this section as writable), then follow `write-back.md`'s single-emission write pattern and the print-then-ask approval in [docs/read-back.md](../../../docs/read-back.md): summary first (target, bullet count per scout, sources, the skip or rerun line), then one ask with approve and write, open in editor, abort. The section is appended after the last auxiliary section for a spec (`flowctl spec set-plan --file`) or the task body (`flowctl task set-spec --file`); every other section comes back byte-for-byte. Under `--force` the old section is replaced in full; under a delta rerun, new bullets append below the existing ones in their scout's sub-block.

Done when: either nothing was written and the summary names the skip reason, or the target carries one `## Resolved via Research` section with one sub-block per scout that returned findings, a source on every bullet, every other section byte-identical to the copy read at Detect Input Type, and the summary reports the bullet count per scout.
