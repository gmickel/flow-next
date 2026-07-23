# Plan tracker projection

Load this reference only after Step 6.5 confirms both that the tracker bridge is
active and that `tracker.perEvent.plan` selected an operation.

Planning projects the spec to the tracker issue. If the spec is not yet linked
(for example, planning started without `/flow-next:capture`), invoke the
`flow-next-tracker-sync` skill with `<leaf> <spec-id>`: its flow-first push
creates and links the issue, then reconciles it. No reachable transport is a
best-effort no-op; tracker failure never blocks planning.

Never create one tracker issue per task. The grain is one spec ↔ one issue and
tasks remain Flow-local. The only optional task-level effect is a task checklist
inside the issue body, owned by the merge engine and off by default.

