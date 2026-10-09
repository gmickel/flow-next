# Refine — write-back

Read at completion. Run the one branch that matches the input: [spec](#spec) below; for a task or a file path, read [write-back-task-file.md](write-back-task-file.md).

Spec prose follows the artifact prose contract in [docs/prose.md](../../../docs/prose.md) when that doc exists.

## Write pattern

Compose the body and Write it once, with the Write tool, to a literal unique path you choose in context, such as `${TMPDIR:-/tmp}/flow-refine-spec-<id>-<4-char suffix>.md`. Type that same path in the Write call and in the flowctl `--file` call; shell variables do not survive between tool calls, so never carry the path in one.

## Read-back approval

Follow the shared read-back contract in [docs/read-back.md](../../../docs/read-back.md):

1. **Print the summary** as an ordinary message, never the whole draft: the title, the criteria count, the existing → proposed diff (unified style, changed sections in full; the diff is what the person approves), a `Changed:` line naming every section this session changed, the source tally when this session added spec acceptance criteria (`Source: [user] N · [paraphrase] M · [strategy] K · [inferred] L`, where `[user]` counts the untagged lines in the person's own words), short warnings (such as the open-questions count), the `Recommended next:` line, and the draft path. Omit the tally for a task or file target; they carry no tags.
2. **Ask once** with `AskUserQuestion`: `Summary printed above; draft at <path>.`, your recommendation, and the options `approve and write` / `open in editor` / `abort` (plus `split as proposed` and a one-line note when [split.md](split.md) proposed a split). A free-text answer is an edit request. Never put the draft, diff or criteria list in the ask body.

An edit request is applied with the Edit tool; `open in editor` hands the draft file to `$VISUAL`, `$EDITOR` or the host's open command. After either, Read the full draft file again, print only the diff, and ask again. Loop until `approve and write` or `abort`.

## Source tags

Only a spec's `## Acceptance Criteria` bullets that this session adds are tagged. The tag is the last token on the bullet.

- **The person's own words stay untagged.** An untagged criterion claims to be what they said in this session, findable in their answers; trimming is fine, rewording is not.
- `[paraphrase]` — their intent in your wording, with no new constraint. A close restatement is a paraphrase, never untagged.
- `[inferred]` — your fill-in that nobody stated.
- `[strategy:<track>]` — derived from `STRATEGY.md`; the track's H3 heading copied literally, casing and spaces kept (`[strategy:Cross-platform parity]`).

```markdown
- **R6:** Rate limit rejects 3+ requests per second from a single client.
- **R7:** Errors include the request id for trace correlation. [inferred]
```

- Criteria an earlier session wrote keep their bullet exactly as read, tagged or not. Never add, change or remove a tag on them.
- Never ask about tagging.
- A criterion the person answered is untagged or `[paraphrase]`; only genuine gap-fill is `[inferred]`. If everything came out `[inferred]`, recheck which criteria came from answers.
- When an `[inferred]` criterion was covered by no question, do not recommend `approve and write`; state the count and let the person check those lines.
- When `.flow/criteria.md` exists, never restate a standing criterion (G-ID) as an R-ID; reference it in prose and add an R only for what this spec adds.

## Spec

Check for tasks with `$FLOWCTL tasks --spec <id> --json`. When tasks exist, change only the spec, never a task. Without tasks, judge the `Recommended next:` line from [plan-vs-no-plan.md](../../flow-next-flow/references/plan-vs-no-plan.md) (`/flow-next:plan-review fn-N` when design risk wants an independent look; `/flow-next:flow --explain fn-N` when the signals conflict).

Start from the body read when detecting the input; re-read only if this run already wrote the spec. Then add refine's own sections, only those that apply, below the rest:

```markdown
## Resolved via Codebase
Questions settled by reading the code, each with file:line evidence.

## Resolved via Project Docs
Questions settled from README / CHANGELOG / STRATEGY / GLOSSARY / decision entries / open specs / docs, each with path or path:line evidence.

## Resolved via Experiment
Per question: what ran, what was observed (numbers or output), and the decision it settled, or "inconclusive" with the question moved to the person. The experiment stays in .flow/tmp/experiments/.

## Glossary Conflicts
(doc-aware only) Per term: the person's wording, the canonical term, the resolution, and the canonical entry's file:line.

## Strategy Conflicts
(strategy-aware only) Per line: the person's wording, the strategy wording (track or approach), the STRATEGY.md path, and the resolution. Refine never edits STRATEGY.md.

## Parked unknowns
Genuine fog only, one bullet each, naming what would resolve it.

## Open Questions
Items left for planning, plus every skipped or handed-off question with its owner and leaning. After fill-assumptions, one entry points at the inline *(assumed — unconfirmed)* markers.
```

**Parked unknowns.** For each existing bullet: resolved this session → move the answer into the section that owns it and delete the bullet; still unknown → keep it byte-for-byte. Append new fog as a bullet naming what would resolve it (decidable now → decide it; resolvable by scheduled work → it is a task, not fog). Drop the heading when the list empties. Fog is a question nobody can answer yet; a skipped question belongs in `## Open Questions`.

Write the merged body per the write pattern, get approval, then:

```bash
$FLOWCTL spec set-plan <id> --file "${TMPDIR:-/tmp}/flow-refine-spec-<id>-<suffix>.md" --json
```
