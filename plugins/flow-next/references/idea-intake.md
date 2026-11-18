# Starting from a discovery idea

Read when a flowctl read of a tracker issue returned an `idea` block that points here, or when you
read an issue from a project `tracker.perTracker.ideaProjectKeys` lists through another tracker
connection. The issue is an idea in a discovery project (Jira Product Discovery): the people who
run discovery own it,
and an approved idea becomes one parent issue in the delivery project with one child issue per
spec under it.

**Attended only.** In an unattended run (`flow --auto` in any mode, any `mode:autonomous` caller)
do not build from an idea: stop `NEEDS_HUMAN` naming it. The person's invocation is the consent.

**The idea is read-only apart from one delivery link.** Never edit its text, fields or status,
never comment on it, and never link a spec to it as the spec's own issue (flowctl refuses that
link). Which parent serves the idea is read from the tracker every time; record nothing about it
locally. `$FLOWCTL` below is the plugin's bundled flowctl (the one whose read sent you here, if
one did).

## 1. Read the idea

`"$FLOWCTL" tracker idea read <key-or-url> --json` returns its title, body, status and URL, its
comments, and the issues already delivery-linked to it (`deliveryLinks`). Discovery teams often
keep the requirement in comments: the body and every comment are the source, next to what the
person says in the session. A failed read stops with its error; nothing has been written. When
`commentsTruncated` is true, the read did not return every comment: tell the person the comment
list is incomplete and ask before capturing from it.

When neither body nor comments state a requirement (only a template's headings, or nothing), tell
the person the idea has nothing to build from and ask what to build. Never invent criteria from
the title.

## 2. Route and capture

Route the idea's content with the route matrix like any other starting point: a clear idea to
capture, an oversized or unclear one to chart first, then capture. With `tracker.charts` on, a
chart run projects its own issues for the chart; they are not the idea's parent or children.
Capture runs as usual, with its split proposal, the person's choice and its cycle check. Tell it:

- Each spec's Goal & Context quotes the part of the idea it serves and gives the idea's key and URL.
- Each spec's Decision Context names its sibling specs and the idea; step 3 adds the parent.
- The idea is source material, not a named issue for the spec.
- Save the specs locally first: flow ids, no create-first. Capture's tracker push, its later sync
  check and any retry push all wait until step 4 has created the specs' issues; an earlier push
  would create each issue without its parent. Nothing is written to the tracker before the specs
  exist.

## 3. Settle the parent

After capture has saved the specs, settle the parent. Write a short summary of what the idea asks
for, with the idea's key and URL, to a mode `0600` file and run:

```bash
"$FLOWCTL" tracker idea parent <idea-key> --body-file <file> --json
```

It reuses the idea's delivery-linked issue at the parent level of the delivery project, or creates
one titled with the idea's summary and links it to the idea. An idea that becomes one spec gets a
parent too. A repeat run finds the same parent and creates nothing, including a parent whose
delivery link failed: a parent flowctl creates carries a label naming the idea, and a rerun links
it. Once the parent is settled, add its key and URL to each spec's Decision Context
(`"$FLOWCTL" spec set-plan <spec-id> --file <file>` with the edited spec).

- `conflict` / `several_parents`: ask the person which of `details.candidates` to use, then rerun
  with `--use <key>`.
- `unresolved` / `delivery_link_type`: the site has no single delivery link type; report what
  `details.found` lists and stop. Nothing was created.
- Success with `link.created: false` and a `link.error`: report the parent's key and the
  `link.retry` command, and continue; no build step waits on the link.
- `notReused`: linked issues that cannot serve as the parent (outside the delivery project, or not
  at the parent level). Name them in the close.
- `degraded` with `field: description`: the parent was created without the summary, because its
  create screen has no description field. Tell the person, and write the summary onto the parent:
  `"$FLOWCTL" tracker wire update --locator '{"durable":"<parent.id>","display":"<parent.key>"}'
  --body-file <file> --json`.

## 4. Children under the parent

Create each saved spec's issue under the parent, with the spec's body (`"$FLOWCTL" cat <spec-id>`)
in a mode `0600` file:

```bash
"$FLOWCTL" tracker create <spec-id> --title "<spec title>" --body-file <file> --parent <parent-key> --json
```

This records the parent on the spec and links the issue. Then project each dependency edge between
the specs with `"$FLOWCTL" tracker relate <spec-id> --blocked-by <dependency-spec-id> --json`, and
let capture's tracker push run if it is configured; it updates the linked issues.

## 5. Close

Print the idea, the parent (created or reused), each spec with its issue, and the dependency edges.
