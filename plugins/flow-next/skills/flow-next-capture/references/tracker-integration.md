# capture — tracker integration (loaded on demand)

> Loaded ONLY when a `flowctl sync active` gate fires (bridge active, or the probe errored). With no
> tracker configured, capture behaves exactly as it always has: `spec create` mints `fn-N` locally,
> no lifecycle push happens, and Phase 6's mandatory `Tracker sync:` slot reads
> `n/a (bridge inactive)` — the sync check itself stays inline in workflow.md and always runs.

Contents:

- [5.2 — Tracker-first mint](#52--tracker-first-mint) — the distributed id allocator branch
- [5.7 — Tracker sync touchpoint](#57--tracker-sync-opt-in--spec-pushpull--merge)
- [Phase 6 — retro-fire on MISSING](#phase-6--retro-fire-on-missing)

---

## 5.2 — Tracker-first mint

**Tracker-first is the recommended team default** when a tracker is configured (`tracker.specIds=tracker`): the tracker is the distributed allocator, so parallel captures stop colliding on `fn-N`. Route from the preamble root config snapshot (fn-110) — **no new `config get`**. Explicit user override in the invocation always wins. Do **not** nag about the id scheme at this mint site (withdrawn R10).

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
SPEC_TITLE="<chosen title from Phase 3 or Phase 1.3>"

# From the preamble root snapshot (literal path; no new config get).
SPEC_IDS=$(jq -r '.value.tracker.specIds // "flow"' "${TMPDIR:-/tmp}/flow-capture-config-<suffix>.json" 2>/dev/null)
BRIDGE_ACTIVE=$("$FLOWCTL" sync active --json 2>/dev/null | jq -r '.active // false')

if [ "$SPEC_IDS" = "tracker" ] && [ "$BRIDGE_ACTIVE" = "true" ]; then
  # Named existing issue in the request → mint from that key, THEN attach + seed.
  #   SPEC_OUTPUT=$("$FLOWCTL" spec create --tracker-first --tracker-identifier "<KEY|#N|project#iid>" --title "$SPEC_TITLE" --json)
  #   Minting stores the identifier but NOT the durable tracker.id, so this branch
  #   MUST also run the fetch/attach/seed ceremony (tracker-sync steps.md Phase 2b)
  #   exactly like the fresh-idea branch below. Skipping it leaves the spec
  #   effectively unlinked: a later lifecycle touchpoint sees no tracker.id, takes
  #   the Phase 3 create-if-unlinked path, and creates a SECOND remote issue
  #   instead of linking the one the user named.
  # Fresh idea → create-first first (tracker-sync steps.md Phase 2d), then mint + attach + seed:
  #   skill: flow-next-tracker-sync (operation: create-first, title: "$SPEC_TITLE", body: "<draft seed>")
  #   → {id, identifier, url}; on noop / no transport → SILENT fall-through to flow-first below
  #   SPEC_OUTPUT=$("$FLOWCTL" spec create --tracker-first --tracker-identifier "$IDENTIFIER" --title "$SPEC_TITLE" --json)
  #   then attach + seed merge base per tracker-sync steps.md Phase 2d "Enabled caller sequence"
  # Network cost (honest, conditional): when tracker.perEvent.capture is already active,
  # tracker-first REORDERS that existing remote write; when the leaf is off (default — a
  # bridge-active repo can have every lifecycle event disabled), tracker-first adds an
  # EARLIER remote write that flow-first would not have made.
  :
fi
```

The flow-first `spec create` in workflow.md §5.2 is the **silent degrade** post-check for this branch — deliberately outside the `if` above. A create-first noop / unreachable transport / failed mint leaves `SPEC_OUTPUT` unset inside the tracker branch, and an `else` arm can never run in that case, so the promised fall-through has to be an unconditional post-check. Its guard also stands: degrade ONLY when nothing was created remotely; if create-first already made and recorded an issue and the tracker-keyed MINT then failed (e.g. preflight found a mixed-history collision), surface identifier + url + retryKey and STOP rather than stranding an orphan issue.

---

## 5.7 — Tracker sync (opt-in) — spec push/pull + merge

**Optional. Runs only when the tracker bridge is active AND `capture` is opted in. With no tracker configured this is a no-op — capture behaves exactly as today.** After the spec is on disk, project the captured/enriched body to the linked (or freshly linked) tracker issue and reconcile two-way (R6): a flow-first capture pushes the body out; a tracker-first spec (one already linked) reconciles the new capture content against the issue via the agentic 3-way merge.

```bash
LEAF="$("$FLOWCTL" config get tracker.perEvent.capture --json | jq -r '.value')"
case "$LEAF" in
  pull)      OP="pull" ;;
  push)      OP="push" ;;
  reconcile) OP="reconcile" ;;
  comment)   OP="comment" ;;
  off|null)  OP="off" ;;
  *)         OP="off" ;; # malformed config stays silent
esac
if [ "$("$FLOWCTL" sync active --json | jq -r '.active')" = "true" ] \
   && [ "$OP" != "off" ]; then
  # Invoke the inline flow-next-tracker-sync wrapper. It prepares the approved
  # operation-specific 0600 input files, then makes exactly one lifecycle call:
  #   "$FLOWCTL" tracker sync "$SPEC_ID" --op "$OP" --event capture <legal file flags>
  # For OP=comment, Capture synthesizes the comment content by name: a compact
  # created/updated-spec summary plus the captured context. The 0600
  # --body-file FIRST line is `evidence=<sha256-of-current-spec-file>`; delete
  # the file after the call. No content travels in argv.
  # No reachable transport is best-effort; genuine body conflicts surface scoped
  # (interactive) or queue (Ralph, though capture itself is Ralph-blocked).
  :
fi
```

Best-effort — a tracker failure never blocks the capture. The skill emits its own receipt, event-tagged `--event capture` — the tag Phase 6's end-of-run `sync check` audits.

---

## Phase 6 — retro-fire on MISSING

**Exactly ONE cycle, never blocking:**

1. Record the retro-fire start anchor and echo it (the re-check needs it as `--since`): `date -u +%Y-%m-%dT%H:%M:%SZ`
2. Invoke the **inline flow-next-tracker-sync wrapper directly**. Re-resolve the operation with 5.7's complete `off | pull | push | reconcile | comment` mapping. For `comment`, Capture re-synthesizes the created/updated-spec summary plus captured context in a mode `0600` body file. The wrapper prepares the other legal operation inputs, makes exactly one `flowctl tracker sync <spec-id> --op <op> --event capture <legal file flags>` call, and deletes the temporary files. NEVER invoke the Phase 6 check block as a wrapper.
3. Re-check with `--since` = the step-1 anchor:
   `"$FLOWCTL" sync check "$SPEC_ID" --events capture --since "<retro-fire-start>" --json`
4. Record the final state in the footer slot. Still MISSING after the one cycle is a recorded, visible outcome — never a second retro-fire, never a block (the spec is already on disk; a tracker hiccup must not become a hard stop). Recovery guidance lives in the receipt note + `docs/tracker-sync.md`.
