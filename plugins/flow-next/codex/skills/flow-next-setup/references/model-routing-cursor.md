# Model routing: Cursor

Read only after the Model Routing answer is `Scaffold` or
`Scaffold + enable codex delegation` on `PLATFORM=cursor`.

1. Enumerate available Cursor model slugs from host knowledge; fallback to
 foreground, short-timeout `cursor-agent --list-models` (up to 200 lines)
 when `HAVE_CURSOR=1`. If unavailable, scaffold an explicit enumeration note.
2. The HOST AGENT picks `SCOUT_PIN` (cheap/fast read-only scout) and
 `REVIEW_PIN` (strongest different-family host-review slug). Never Python,
 flowctl ranking, or same-family self-review. If no cross-family slug exists,
 leave a clear TODO.
3. Compose this exact structure with today's ISO date, enumeration, and pins:

```markdown
<!-- flow-next:model-routing:start -->
## Picking models for flow-next workflows and subagents

_Scaffolded by `/flow-next:setup` on Cursor (<YYYY-MM-DD>). Model ids are volatile — re-run setup to refresh. Edit freely; this section is yours now._

### Available models (enumerated at setup)

- <bullet list of enumerated Cursor slugs>

### Dispatch pins (host agent picked)

| role | pin | rule |
|------|-----|------|
| read-only scouts | `<SCOUT_PIN>` | cheap / fast |
| host review | `<REVIEW_PIN>` | cross-family vs the writer |
| everything else | inherit | session model |

### Routing rules

- Read-only scouts (repo-scout, context-scout, and any read-only Explore-class subagent): pin `<SCOUT_PIN>` (cheap).
- Host review (`review.backend host`): pin `<REVIEW_PIN>` (cross-family; never same-family self-review).
- Implementation, plan, judgment, and all other work: **inherit** the session model unless the user pins otherwise.
- Reviews prefer a different family than the writer — uncorrelated blind spots.
- Graceful degrade: unavailable slug → fall back to the session model; never block. **EXCEPTION — host review:** the `REVIEW_PIN` never degrades to the session model. If unavailable, host review fails closed: interactive → ask for a replacement; autonomous → NEEDS_HUMAN. Re-run `/flow-next:setup` to refresh.
<!-- flow-next:model-routing:end -->
```

Always target AGENTS.md. When Docs also selected CLAUDE.md, write both; AGENTS.md
is load-bearing. Per target:

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

Confirm a write with:
`Model-routing section written to <file> — Cursor host-native pins; re-run /flow-next:setup to refresh volatile ids.`

If the answer included delegation, set `work.delegate=codex`, NEVER touch
`work.delegateConsent`, read persisted `work.delegate` back with
`flowctl config get work.delegate --raw --json`, and warn if it is not `codex`.
Skip the codex review-backend switch on Cursor regardless of `CURRENT_BACKEND`;
Host remains the recommended non-circular path.
