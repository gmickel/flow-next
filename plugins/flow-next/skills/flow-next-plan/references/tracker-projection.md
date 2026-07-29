# Plan tracker projection

Load this reference only after Step 6.5 confirms both that the tracker bridge is
active and that `tracker.perEvent.plan` selected an operation.

Planning projects the spec to the tracker issue. Invoke the inline
`flow-next-tracker-sync` wrapper with the resolved `<OP>` and `<spec-id>`. The
wrapper prepares only the legal mode `0600` inputs, then makes exactly one
lifecycle call:

```bash
"$FLOWCTL" tracker sync "$SPEC_ID" --op "$OP" --event plan <legal file flags>
```

For `OP=comment`, Plan synthesizes the comment content by name: a compact
planning summary, task count, and execution-wave outline. Write it to the mode
`0600` `--body-file`, never argv, and delete it after the call. If the spec is
not yet linked (for example, planning started without `/flow-next:capture`),
the facade creates and links the issue before applying the selected operation.
No reachable transport is a best-effort no-op; tracker failure never blocks
planning.

Never create one tracker issue per task. The grain is one spec ↔ one issue and
tasks remain Flow-local. The only optional task-level effect is a task checklist
inside the issue body, owned by the merge engine and off by default.
