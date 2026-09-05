# Flow-Next Claude Code development entry point

Read [the shared development policy](agent_docs/project.md) before repository
work. It owns architecture, source ownership, verification, and delivery rules.
This file owns host guidance only; keep common rules in that policy.

Canonical spec scaffold: [templates/spec.md](plugins/flow-next/templates/spec.md).
For skill/platform changes also read [cross-platform patterns](agent_docs/adding-skills.md#cross-platform-patterns).

## Host guidance

On Claude Code, invoke skills as `/flow-next:<name>`. Other consumers of this
file use their supported native equivalent. Distinguish Claude-native product
source examples from the tools available to the current development session.

<!-- BEGIN FLOW-NEXT -->
<!-- flow-next:snippet:v2 -->
## Flow-Next

This repo tracks implementation specs/tasks through Flow-Next. See
[repository work and delivery](agent_docs/project.md#repository-work-and-delivery)
for state, templates, and command discovery. Invoke the selected skill with
`/flow-next:<name>` on Claude Code; follow its task-specific contract.
This is a repo-customized block. Keep maintainer additions outside its markers.
<!-- END FLOW-NEXT -->

<!-- flow-next:model-routing:start -->
## Model routing

These are preferences, not facts about this session's model or available tools.
Explicit user routing wins, then this block, agent defaults, and the session
model. Planning, judgment, user-facing design, and native workers otherwise
inherit the actual session model. Read `flowctl usage` before model steering.

For a Claude-family writer, the maintainer's preferred tiers are:

```text
reviewer: gpt-6-astra at high
implementer: gpt-6-astra at medium
fast scout: haiku-4.5
thinking scout: sonnet-5
```

Verify availability through the active harness. If this file is read by an
OpenAI-family writer, the reviewer preference is not independent-family review;
choose a reachable reviewer from another family through the configured backend.

For ordinary implementation/scouting, an unreachable preference falls back to
the session model with one notice. Host review is the exception: preserve its
fresh-context, tool-enforced read-only, cross-family requirement and fail closed
if unavailable. Reviews through other backends retain their existing contracts.
Escalate an inadequate cheaper implementation within the authorized scope.
Unattended bridge calls use the thin-wrapper recipe in `flowctl usage`; the host
keeps git, judgment, and verdict ownership.
<!-- flow-next:model-routing:end -->
