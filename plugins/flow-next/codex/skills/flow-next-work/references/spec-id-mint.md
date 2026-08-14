# Spec-id mint gate (tracker-first vs flow-first)

Read this ONLY when actually minting a brand-new spec (the spec-file and spec-less starts in phases.md Phase 1). Work on an existing spec id never mints, so this stays off the default reached path.

**Tracker-first is the recommended team default** when a tracker is configured (`tracker.specIds=tracker`): the tracker is the distributed allocator, so parallel agents and worktrees stop colliding on `fn-N`.

Network cost is conditional: when the matching `tracker.perEvent.*` touchpoint is already active, tracker-first REORDERS an existing remote write; when it is off (the default, and a bridge-active repo can have every lifecycle event disabled) it adds an EARLIER remote write that flow-first would not make.

Explicit user override in the invocation always wins. No runtime nag here - setup owns the one-time question (withdrawn R10).

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
# REUSE the root snapshot the Phase 1 mint gate just took - do NOT take another
# config read here, and never a per-leaf `config get tracker.specIds` (R7).
# Literal path; re-type it because variables die across prompt turns.
WORK_CFG="${TMPDIR:-/tmp}/flow-work-config-<suffix>.json"
SPEC_IDS=$(jq -r '.value.tracker.specIds // "flow"' "$WORK_CFG" 2>/dev/null)
BRIDGE_ACTIVE=$($FLOWCTL sync active --json 2>/dev/null | jq -r '.active // false')

if [ "$SPEC_IDS" = "tracker" ] && [ "$BRIDGE_ACTIVE" = "true" ]; then
  # Named issue -> mint from its key, THEN attach + seed exactly like the fresh
  # idea route: minting stores tracker.identifier but NOT the durable tracker.id,
  # so without the Phase 2b fetch/attach/seed ceremony an enabled
  # work.firstClaim (or any later touchpoint) treats the spec as unlinked and
  # creates a SECOND remote issue instead of linking the named one.
  # Fresh idea -> tracker-sync `create-first`
  # (tracker-sync steps.md Phase 2d) for {id,identifier,url}, then mint + attach + seed.
  # A noop / no-transport create-first falls through SILENTLY to flow-first -
  # via the unconditional post-check below, NOT an `else` arm (on a noop
  # SPEC_OUTPUT is unset inside THIS branch, which no `else` can reach).
  #   SPEC_OUTPUT=$($FLOWCTL spec create --tracker-first --tracker-identifier "<key>" --title "<title>" --json)
  :
fi

# GUARD: degrade ONLY when nothing was created remotely - a failed mint AFTER
# create-first made an issue must surface identifier + url + retryKey and stop,
# never silently create an fn-N spec that leaves the issue orphaned.
if [ -z "$SPEC_OUTPUT" ] && [ -z "$IDENTIFIER" ]; then
  SPEC_OUTPUT=$($FLOWCTL spec create --title "<title>" --json)   # silent flow-first degrade
fi
```
