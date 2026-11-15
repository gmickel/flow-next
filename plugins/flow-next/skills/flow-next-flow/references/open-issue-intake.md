# Open-issue intake

Read from [route-matrix-more.md](route-matrix-more.md) when the person asks to triage the open
tracker issues that no spec covers. Attended only: under an autonomy marker, flow's attended
refusal has already stopped the run.

## Read

```bash
"$FLOWCTL" tracker wire list-open --any-lane --unlinked --json
```

Each row is `{id, identifier, title, url, labels, excerpt}`: an open issue no spec in this
checkout links. When the envelope is not a success (the bridge is inactive, the tracker is
unreachable), report its reason and stop with no table. When `truncated` is true, say the list
was cut and how many issues the table covers, even when that is none: the cap counts linked
issues too. When `issues` is empty and the list was not cut, say there is nothing to triage and
stop.

Read the open specs (`"$FLOWCTL" specs --json`, then `"$FLOWCTL" cat <spec-id>` where a title
alone does not settle it) so each issue can be matched. Which spec an issue belongs to is your
judgment from titles and excerpts; flowctl never decides it.

## One table, one question

Show one table, one row per issue:

| Issue | Title | Proposed action | Reason |
|---|---|---|---|
| `#42` | ... | new spec | one line |
| `#43` | ... | fold into `fn-N` | one line |
| `#44` | ... | dependency: new spec, blocked by `fn-N` | one line |
| `#45` | ... | leave | covered by `fn-N` |

The actions are `new spec`, `fold into <spec>`, `dependency` (a new spec, depending on or
depended on by an existing one) and `leave`. An issue folded into a spec on an earlier run comes
back unlinked; propose `leave` with `covered by <spec>`.

Then ask one confirming question: accept the table as proposed, or let the person name the rows
to change or skip. Do not ask per row.

## Run what was picked

The excerpt only proposes. Before acting on a picked row, read the whole issue:
`"$FLOWCTL" tracker wire read --locator '{"durable":"<id>","display":"<identifier>"}' --json`
and `"$FLOWCTL" tracker wire comment-list` with the same locator. That body and those comments are
the source a capture receives and what a fold adds to the spec.

Run the existing stages only, one picked row at a time:

- **New spec:** `flow-next:flow-next-capture from:flow`, naming the issue, so capture links the
  spec to it. A spec captured earlier in this run for another confirmed row is not a prior
  capture of this one: the confirmation already answers capture's rewrite-or-proceed question
  with `proceed`, so do not ask it again.
- **Fold into a spec:** amend that spec's body with what the issue adds, push it through
  `flow-next:flow-next-tracker-sync push <spec-id>` when the spec is linked, and comment on the
  issue pointing at the spec (`"$FLOWCTL" tracker wire comment-add --locator
  '{"durable":"<id>","display":"<identifier>"}' --body-file <file> --json`).
- **Dependency:** capture the new spec as above, then `"$FLOWCTL" spec add-dep <dependent>
  <dependency> --json` in the direction the table named.
- **Leave:** nothing.

Never close, relabel or unready an issue, and never start work: a captured spec waits for the
person, as any capture does. End with Step 5's report, one line per row that ran.
