---
name: flow-next-prose
description: Use while drafting a substantial reply, report, or summary for the user - read the prose contract before writing and draft under its rules. Not for short turns or file/PR output.
user-invocable: false
allowed-tools: Read
---

# Flow Prose

Ambient triggering is host-discretionary on every host: the host matches this skill's description at the moment the agent begins drafting a substantial reply.

The agent reads the prose contract at [docs/prose.md](../../docs/flow-next/prose.md), resolved relative to this SKILL.md file's own location. If the doc is absent, the skill proceeds without it and never blocks the reply.

The agent applies the contract's rules 1-10 at draft time and writes the reply under them from the first draft.

The reply-dormant parts of the doc are the precedence section's dedup-marker and projection bullets, which stay idle for replies. Rule 8 (user-outcome-first ordering) softens to lead with the answer. Rule 10 (honesty) stays fully active.

The agent never rewrites quoted material, code, or command output, and never restyles the user's words where they are being quoted back. A draft the user hands the skill as the `/flow-next:prose <draft>` argument is submitted for tightening, so the agent rewrites it under the contract.

Pass the identity (the path above). Never copy rule text from the doc into this skill.
