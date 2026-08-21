# Reach pages

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts's own syntax and are quoted verbatim — do not convert them.


**Reach** is how the active harness obtains a model for a [tier](../orchestration.md#tiers--what-kind-of-model-a-job-wants): the in-session model, an in-host subagent, shelling out to another CLI, or not available at all. Tier names, the routing block, and the routing precedence are defined once in [`../orchestration.md`](../orchestration.md#tiers--what-kind-of-model-a-job-wants); these pages state only what each harness can and cannot do.

Skills never name a spawn primitive, a CLI flag, or a vendor path — they ask for a tier, and reach lives here.

| Harness | Page |
|---|---|
| Claude Code | [`claude-code.md`](claude-code.md) |
| OpenAI Codex | [`codex.md`](codex.md) |
| Factory Droid | [`droid.md`](droid.md) |
| Cursor | [`cursor.md`](cursor.md) |
| Grok Build | [`grok-build.md`](grok-build.md) |
| OpenCode | [`opencode.md`](opencode.md) |
| Anything else / undetectable | [`generic.md`](generic.md) |

**An undetectable harness resolves to [`generic.md`](generic.md) and says so once.** Guessing a harness is worse than naming the fallback: the generic page assumes the least reach and degrades cleanly.

Each page answers the same four questions: which mechanisms exist here, which do not, what the degradation is when one is missing, and how to discover what the harness offers instead of trusting a stored answer.
