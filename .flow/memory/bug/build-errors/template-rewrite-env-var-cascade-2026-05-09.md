---
title: "Env-var cascade in templates + canonical config.env knob alignment"
date: "2026-05-09"
track: bug
category: build-errors
module: "plugins/flow-next/skills/flow-next-ralph-init/templates, config.env, ralph.sh"
tags: [template, ralph, config-env, env-var-cascade, review-feedback]
problem_type: build-error
symptoms: "Template scripts discarded externally-set env vars before resolving cascade; config.env exposed convenience-only knobs and missed canonical file-path knobs spec required"
root_cause: "Naive variable-init cleared user-set env vars before cascade resolution; templates retained pre-spec convention shapes (list-style) when spec required canonical file-path knobs"
resolution_type: fix
audit_refocused_from: "fn-43 ralph.sh / config.env rewrite during epic→spec rename; refocused 2026-05-21 to extract reusable env-cascade discipline"
---

## Lesson 1 — Resolve cascade BEFORE clearing

When a script derives one variable from another, walk the precedence chain explicitly:

```bash
SPECS_FILE="${SPECS_FILE:-${EPICS_FILE:-}}"   # honor caller env first
if [[ -z "$SPECS_FILE" && -n "${SPECS// }" ]]; then
  SPECS_FILE="$RUN_DIR/run.json"               # then derive from list
  write_specs_file "$SPECS" > "$SPECS_FILE"
fi
EPICS_FILE="$SPECS_FILE"                       # then mirror legacy alias
```

Unconditional `SPECS_FILE=""` before cascade silently discards what the caller exported. Precedence order to honor: CLI flag → env var (canonical name) → env var (legacy alias) → config file → default.

## Lesson 2 — config.env exposes canonical knobs, not just convenience

When the spec acceptance criterion says "config.env exposes `$CANONICAL_KNOB=`", expose `$CANONICAL_KNOB=` literally — even if the codebase historically used a different shape (e.g. list-style convenience knob). The literal acceptance text is the contract.

When a feature has both a file-path knob and a list-derived convenience knob:
- Expose BOTH in config.env.
- File knob is canonical: `SPECS_FILE=/path/to/run.json`.
- List knob is convenience: `SPECS=fn-1,fn-2` — derives to a JSON file under `$RUN_DIR`.
- Resolver order: file knob > legacy file knob > list-derived > none.

## Prevention

- **Read spec acceptance literally, not aspirationally.** If the spec says `KNOB_A`, the template exposes `KNOB_A`. Don't substitute a near-equivalent because the existing codebase uses that shape — the reviewer is enforcing the spec, not the legacy.
- **Shell cascade idiom:** `VAR="${VAR:-${LEGACY_VAR:-}}"` is the cleanest precedence-preserving form. Use consistently across templates.
- **Each tier of the cascade gets a concrete test.** CLI flag set, env var set, config file set, default fallback — one test per tier so the chain can't silently rot.

## See also

- `[[detectvalidate-must-require-specs-dir]]` — analogous discipline for dual-location JSON-vs-markdown reads during canonical migrations
- `plugins/flow-next/skills/flow-next-ralph-init/templates/config.env` — current canonical example exposing both `SPECS_FILE=` and `SPECS=`
- `[[fn-44-review-cycle-lessons]]` — related review-cycle lessons including "honor every contract surface end-to-end"
