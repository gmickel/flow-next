# Starting from a discovery idea

Read when a flowctl read of a tracker issue returned an `idea` block that points here. The issue
is an idea in a discovery project (Jira Product Discovery): the people who run discovery own it,
and an approved idea becomes one parent issue in the delivery project with one child issue per
spec under it.

**Attended only.** In an unattended run (`flow --auto` in any mode, any `mode:autonomous` caller)
do not build from an idea: stop `NEEDS_HUMAN` naming it. The person's invocation is the consent.

**The idea is read-only apart from one delivery link.** Never edit its text, fields or status,
never comment on it, and never link a spec to it as the spec's own issue (flowctl refuses that
link). Which parent serves the idea is read from its delivery links every time; record nothing
about it locally. `$FLOWCTL` below is the flowctl that made the read which sent you here.

## 1. Read the idea

`"$FLOWCTL" tracker idea read <key-or-url> --json` returns its title, body, status and URL, its
comments, and the issues already delivery-linked to it (`deliveryLinks`). Discovery teams often
keep the requirement in comments: the body and every comment are the source, next to what the
person says in the session. A failed read stops with its error; nothing has been written.

When neither body nor comments state a requirement (only a template's headings, or nothing), tell
the person the idea has nothing to build from and ask what to build. Never invent criteria from
the title.

## 2. Route and capture

Route the idea's content with the route matrix like any other starting point: a clear idea to
capture, an oversized or unclear one to chart first, then capture. Capture runs as usual, with its
split proposal, the person's choice and its cycle check. Tell it:

- Each spec's Goal & Context quotes the part of the idea it serves and gives the idea's key and URL.
- Each spec's Decision Context names its sibling specs, the idea and the parent issue.
- The idea is source material, not a named issue for the spec.

## 3. Settle the parent

Once the person has agreed what to write (the read-back, or the split choice) and before the first
spec is created, settle the parent. Write a short summary of what the idea asks for, with the
idea's key and URL, to a mode `0600` file and run:

```bash
"$FLOWCTL" tracker idea parent <idea-key> --body-file <file> --json
```

It reuses the idea's delivery-linked issue at the parent level of the delivery project, or creates
one titled with the idea's summary and links it to the idea. An idea that becomes one spec gets a
parent too. A repeat run finds the same parent and creates nothing.

- `conflict` / `several_parents`: ask the person which of `details.candidates` to use, then rerun
  with `--use <key>`.
- `unresolved` / `delivery_link_type`: the site has no single delivery link type; report what
  `details.found` lists and stop. Nothing was created.
- Success with `link.created: false` and a `link.error`: report the parent's key and the
  `link.retry` command, and continue; no build step waits on the link.
- `notReused`: linked issues that cannot serve as the parent (outside the delivery project, or not
  at the parent level). Name them in the close.

## 4. Children under the parent

Treat the parent's key as a parent the person named: every spec this capture creates records it
(`spec create --tracker-parent <parent-key>`, or `--parent` on create-first), so its issue is
created under the parent. Dependency edges between the specs are projected as usual.

## 5. Close

Print the idea, the parent (created or reused), each spec with its issue, and the dependency edges.
