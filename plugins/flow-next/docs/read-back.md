# Read-back contract

Refine (write-back) and plan (task set) use the pre-write ratification shape below. Interactive capture uses the saved-spec review at the end of this page: the capture request already authorizes saving. Each skill reads this file at its review step, never on every run.

## The shape

1. **Write the draft once** to a literal temporary file with the Write tool (`${TMPDIR:-/tmp}/flow-<skill>-draft-<slug>-<4-char suffix>.md`, or `.json` for plan's task set). The file is what the flowctl `--file` / `--from-json` call consumes; it is never re-authored into a heredoc.
2. **Print a compact summary**, never the draft: title, criteria count (plan: task count and sizes, execution waves, R-ID coverage tally), the inferred tally where source tags exist, the split proposal when one exists, and the recommended route from the routing reference (`skills/flow-next-flow/references/plan-vs-no-plan.md` for a captured spec).
3. **One ask** (`AskUserQuestion`; plain-text numbered fallback elsewhere) with exactly these options plus the built-in free-text answer for "change X":
   - `approve and write` - the file becomes the spec / write-back / task set.
   - `open in editor` - hand the draft file to the user's editor; how it is found is the agent's call (`$VISUAL`, `$EDITOR`, a host open command). After the editor round, **re-read the file before asking again**, so the write consumes what the user saw.
   - `abort` - nothing is written; the file stays for inspection.
4. **Edit cycles print only the diff** (unified style, changed sections in full) before the next ask. The full draft prints only when the user asks for it.

## What stays unchanged

- Ratification precedes plan/refine write-back. Capture's noninteractive autofix mode still requires `--yes`; without it only the temporary draft is written.
- The no-self-blessing rule: while unverified `[inferred]` items remain, the ask never recommends `approve and write`.
- Question bodies stay short and pointer-shaped; a draft, diff, or criteria list never rides inside the ask body.
- Each skill keeps its separate consent gates (glossary, mark-ready, tracker). Plan/refine keep their own edit-cycle caps.

## Summary payload

The summary carries these fields, one line each, and nothing that restates the draft:

```
Title: <title>
Criteria: <N> (plan: Tasks: <M> | Sizes: <n>s S, <m>m M | Waves: <...> | Coverage: <covered>/<total> R-IDs)
Source: [user] N · [paraphrase] M · [strategy] K · [inferred] L        (when source tags exist)
Split: <proposal one-liner>                                            (only when one exists)
Recommended next: /flow-next:<stage> <id> - <one-clause reason>
Draft: <path>
```

## Capture: saved-spec review

Interactive capture resolves material questions and any explicit split choice, writes the spec through flowctl, then prints the summary above with `Spec:` and the saved path in place of `Draft:`. Inferred content remains labeled for review. A rewrite also shows its diff. The full body prints only on request.

Offer `open in editor` or `continue` through a short `AskUserQuestion`, with free text for corrections. The question concerns editing the saved spec, not permission to write it. Skip an already-answered editor offer. An editor round opens the saved file and re-reads it before any further operation; corrections preserve user edits and print only their diff. There is no approve-and-write or re-approval loop, and stopping review never deletes the saved spec.

Capture retains its duplicate/rewrite checks, explicit split choice, chart-risk overrides, and separate glossary/readiness questions. Saving or continuing past the editor offer grants no implementation or external-write authority. Previously authorized work and configured tracker behavior keep their own scope.
