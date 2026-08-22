---
name: work-rolling
description: Rolling-frontier variant of /flow-next:work (experimental - can change or disappear) - per-task admission at every worker-return event, isolated workspaces, conductor-owned review, shared notes surface
argument-hint: "[spec-id | task-id | spec file | idea] [--branch=...] [--review=...] [mode:autonomous]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-work-rolling`

The ONLY purpose of this command is to call the `flow-next-work-rolling` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill verbatim. The skill accepts the same inputs as `/flow-next:work` (spec id, task id, spec file, idea text, branch/review options, `mode:autonomous`) and defers everything except its rolling Phase-3 scheduler to the canonical work skill by pointer.
