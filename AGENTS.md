# Flow-Next Agent development entry point

Read [the shared development policy](agent_docs/project.md) before repository
work. It owns architecture, source ownership, verification, and delivery rules.
This file owns host guidance only; keep common rules in that policy.

Canonical spec scaffold: [templates/spec.md](plugins/flow-next/templates/spec.md).
For skill/platform changes also read [cross-platform patterns](agent_docs/adding-skills.md#cross-platform-patterns).

## Host guidance

On Codex, invoke skills as `$flow-next-<name>` or through the skill picker.
Other hosts that read this file use their native Flow-Next invocation syntax;
do not apply Codex syntax to Claude, Cursor, Grok, or OpenCode commands.
Use the current harness's actual tool interfaces. Canonical product prose may
use Claude names because the Codex mirror is generated; that is not an
instruction to call unavailable tools in this development session.

<!-- BEGIN FLOW-NEXT -->
<!-- flow-next:snippet:v2 -->
## Flow-Next

This repo tracks implementation specs/tasks through Flow-Next. See
[repository work and delivery](agent_docs/project.md#repository-work-and-delivery)
for state, templates, and command discovery. Invoke the selected skill with
`$flow-next-<name>` on Codex; follow its task-specific contract.
This is a repo-customized block. Keep maintainer additions outside its markers.
<!-- END FLOW-NEXT -->

<!-- flow-next:model-routing:start -->
## Model routing

These are preferences, not facts about this session's model or available tools.
Explicit user routing wins, then this block, agent defaults, and the session
model. Planning, judgment, user-facing design, and native workers otherwise
inherit the actual session model. Read `flowctl usage` before model steering.

For an OpenAI-family writer, prefer a reachable Claude-family reviewer through
the configured review backend. Do not reuse the Claude entry point's Astra
reviewer preference as an independent-family reviewer here. No host-review
model is pinned in this entry point: when choosing `host`, resolve an explicit
reachable cross-family reviewer before dispatch; absence is a reported blocker,
not permission for self-review. Existing backend configuration remains in force.

For ordinary implementation/scouting, an unreachable preference falls back to
the session model with one notice. Host review is the exception: preserve its
fresh-context, tool-enforced read-only, cross-family requirement and fail closed
if unavailable. Reviews through other backends retain their existing contracts.
Escalate an inadequate cheaper implementation within the authorized scope.
Unattended bridge calls use the thin-wrapper recipe in `flowctl usage`; the host
keeps git, judgment, and verdict ownership.
<!-- flow-next:model-routing:end -->
