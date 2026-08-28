---
name: flow-next-prose
description: "Apply the artifact prose contract while drafting substantial replies, reports, review walkthroughs, and summaries. Triggers on /flow-next:prose, 'apply the prose contract', and 'tighten this reply'. Do not trigger on short conversational turns, tool-call narration, the visual digest, or any output that lands in a file, PR, or tracker (those artifact surfaces carry their own pointers to the contract)."
user-invocable: false
allowed-tools: Read
---

# Flow Prose

Ambient triggering is host-discretionary. On Codex the host loads it on explicit invocation only.

The agent reads the prose contract at [`../../docs/prose.md`](../../docs/prose.md), resolved relative to this SKILL.md file's own location. If the doc is absent, the skill proceeds without it and never blocks the reply.

The agent applies the contract's rules 1-10 at draft time and writes the reply under them from the first draft.

The reply-dormant parts of the doc are the precedence section's dedup-marker and projection bullets, which stay idle for replies. Rule 8 (user-outcome-first ordering) softens to lead with the answer. Rule 10 (honesty) stays fully active.

The agent never rewrites quoted material, code, command output, or the user's own words.

Pass the identity (the path above). Never copy rule text from the doc into this skill.
