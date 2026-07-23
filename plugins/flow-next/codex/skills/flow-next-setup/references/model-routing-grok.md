# Model routing: Grok

Read only after the Model Routing answer is `Scaffold` or
`Scaffold + enable codex delegation` on `PLATFORM=grok`.

1. Enumerate available Grok models from host knowledge; fallback to foreground,
 short-timeout `grok models` when `HAVE_GROK=1`. If unavailable, list
 `grok-4.5` with a not-live-enumerated note.
2. The HOST AGENT picks `SCOUT_PIN`. Grok is single-native-family; leave
 `REVIEW_PIN` as an explicit TODO or bridge-model note unless a genuinely
 different-family pin exists. Never invent a fake native cross-family slug.
3. Compose this exact structure:

```markdown
<!-- flow-next:model-routing:start -->
## Picking models for flow-next workflows and subagents

_Scaffolded by `/flow-next:setup` on Grok (<YYYY-MM-DD>). Grok is single-native-family (grok-4.5); model ids may change — re-run setup to refresh. Edit freely; this section is yours now._

### Available models (enumerated at setup)

- <bullet list of enumerated Grok models — typically just grok-4.5>

### Dispatch pins (host agent picked)

| role | pin | rule |
|------|-----|------|
| read-only scouts | `<SCOUT_PIN>` | cheap / fast |
| host review | `<REVIEW_PIN or TODO>` | cross-family vs the writer — fails closed on same-family Grok |
| everything else | inherit | session model |

### Routing rules

- Read-only scouts (repo-scout, context-scout, and any read-only Explore-class subagent): pin `<SCOUT_PIN>` (cheap).
- Host review (`review.backend host`): pin `<REVIEW_PIN>` only when it is a **different family than the writer**. Grok's only native family is grok — native host review **fails closed** for a Grok writer (interactive → ask for a bridge/replacement pin; autonomous → NEEDS_HUMAN). Cross-family review comes through `codex` / `cursor` / `copilot`.
- Implementation, plan, judgment, and all other work: **inherit** the session model unless the user pins otherwise.
- Reviews prefer a different family than the writer — uncorrelated blind spots.
- Graceful degrade: unavailable slug → fall back to the session model; never block. **EXCEPTION — host review:** the `REVIEW_PIN` never degrades to the session model. If unavailable, host review fails closed. Re-run `/flow-next:setup` to refresh.
<!-- flow-next:model-routing:end -->
```

Always target AGENTS.md; optionally also CLAUDE.md when Docs selected it. Per
target:

- A file with exactly one non-empty `@<path>.md` or `See[:] <path>.md` line is
 a shim. Retarget to an existing in-repo pointer and re-apply the guard;
 missing targets are skipped. Never mix content into a shim.
- If a well-formed model-routing marker block exists, byte-compare it against
 the complete composed block. Identical means silent no-op and no mtime
 change. Different means ask `Keep mine (Recommended)` /
 `Overwrite with canonical` / `Skip`; never silently overwrite.
- Without markers, detect a user-authored model-routing heading and ask
 `Add the flow-next block below yours` / `Skip`; never duplicate silently.
- On a would-write path, show the complete block, ask `write` / `skip`, then
 append or marker-replace the whole block only on `write`.

Confirm:
`Model-routing section written to <file> — Grok host-native pins (single-family fail-closed for host review); re-run /flow-next:setup to refresh.`

If delegation was selected, set `work.delegate=codex`, NEVER touch
`work.delegateConsent`, read persisted `work.delegate` back with
`flowctl config get work.delegate --raw --json`, and warn if it is not `codex`.
The codex review-backend switch may run on Grok only when the scaffold was
accepted, `HAVE_CODEX=1`, and `CURRENT_BACKEND` is nonempty and not already
bare `codex` or `codex:...`: Codex is genuinely cross-family for a Grok writer.
