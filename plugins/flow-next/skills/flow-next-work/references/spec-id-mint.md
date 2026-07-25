# Spec-id mint gate (tracker-first vs flow-first)

Read this ONLY when actually minting a brand-new spec (the spec-file and spec-less starts in phases.md Phase 1). Work on an existing spec id never mints, so this stays off the default reached path.

**Tracker-first is the recommended team default** when a tracker is configured (`tracker.specIds=tracker`): the tracker is the distributed allocator, so parallel agents and worktrees stop colliding on `fn-N`.

Network cost is conditional: when the matching `tracker.perEvent.*` touchpoint is already active, tracker-first REORDERS an existing remote write; when it is off (the default, and a bridge-active repo can have every lifecycle event disabled) it adds an EARLIER remote write that flow-first would not make.

Explicit user override in the invocation always wins. No runtime nag here - setup owns the one-time question (withdrawn R10).

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
# REUSE the Phase 0 root snapshot - do NOT take another config read here (R7).
# Literal path; re-type it because variables die across tool calls.
WORK_CFG="${TMPDIR:-/tmp}/flow-work-config-<suffix>.json"
SPEC_IDS=$(jq -r '.value.tracker.specIds // "flow"' "$WORK_CFG" 2>/dev/null)
BRIDGE_ACTIVE=$($FLOWCTL sync active --json 2>/dev/null | jq -r '.active // false')

if [ "$SPEC_IDS" = "tracker" ] && [ "$BRIDGE_ACTIVE" = "true" ]; then
  # Named issue -> mint from its key. Fresh idea -> tracker-sync `create-first`
  # (tracker-sync steps.md Phase 2d) for {id,identifier,url}, then mint + attach + seed.
  # A noop / no-transport create-first falls through SILENTLY to flow-first -
  # via the unconditional post-check below, NOT an `else` arm (on a noop
  # SPEC_OUTPUT is unset inside THIS branch, which no `else` can reach).
  #   SPEC_OUTPUT=$($FLOWCTL spec create --tracker-first --tracker-identifier "<key>" --title "<title>" --json)
  :
fi

if [ -z "$SPEC_OUTPUT" ]; then
  SPEC_OUTPUT=$($FLOWCTL spec create --title "<title>" --json)   # silent flow-first degrade
fi
```
