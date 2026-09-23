# Spec-id mint gate (tracker-first vs flow-first)

Read this ONLY when actually minting a brand-new spec (the spec-file and spec-less starts in phases.md Phase 1). Work on an existing spec id never mints, so this stays off the default reached path.

**Tracker-first is the recommended team default** when a tracker is configured (`tracker.specIds=tracker`): the tracker is the distributed allocator, so parallel agents and worktrees stop colliding on `fn-N`.

Network cost is conditional: when the matching `tracker.perEvent.*` touchpoint is already active, tracker-first REORDERS an existing remote write; when it is off (the default, and a bridge-active repo can have every lifecycle event disabled) it adds an EARLIER remote write that flow-first would not make.

Explicit user override in the invocation always wins. No runtime nag here - setup owns the one-time question (withdrawn R10).

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
# REUSE the root snapshot the Phase 1 mint gate just took - do NOT take another
# config read here, and never a per-leaf `config get tracker.specIds` (R7).
# Literal path; re-type it because variables die across prompt turns.
WORK_CFG="${TMPDIR:-/tmp}/flow-work-config-<suffix>.json"
SPEC_IDS=$(jq -r '.value.tracker.specIds // "flow"' "$WORK_CFG" 2>/dev/null)
BRIDGE_ACTIVE=$($FLOWCTL sync active --json 2>/dev/null | jq -r '.active // false')

if [ "$SPEC_IDS" = "tracker" ] && [ "$BRIDGE_ACTIVE" = "true" ]; then
  # Named issue -> pass its complete identity to the mint when available:
  #   spec create --tracker-first --tracker-identifier "<key>" --tracker-id "<id>" --tracker-url "<url>" ...
  #   This persists tracker.identifier, tracker.id, and tracker.url atomically,
  #   so the spec is linked before any later touchpoint. If only a key is known,
  #   fetch and use sync set-tracker-id as a compatibility fallback, then seed.
  # Fresh idea -> tracker-sync `create-first`
  # (tracker-sync steps.md Phase 2d) returns {id,identifier,url}; pass all three
  # to mint, then seed the merge base. Attach remains a partial-response fallback.
  # A noop / no-transport create-first falls through SILENTLY to flow-first -
  # via the unconditional post-check below, NOT an `else` arm (on a noop
  # SPEC_OUTPUT is unset inside THIS branch, which no `else` can reach).
  #   SPEC_OUTPUT=$($FLOWCTL spec create --tracker-first --tracker-identifier "<key>" --tracker-id "<id>" --tracker-url "<url>" --title "<title>" --json)
  :
fi

# GUARD: degrade ONLY when nothing was created remotely - a failed mint AFTER
# create-first made an issue must surface identifier + url + retryKey and stop,
# never silently create an fn-N spec that leaves the issue orphaned.
if [ -z "$SPEC_OUTPUT" ] && [ -z "$IDENTIFIER" ]; then
  SPEC_OUTPUT=$($FLOWCTL spec create --title "<title>" --json)   # silent flow-first degrade
fi
```
