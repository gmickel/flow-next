# Model routing: Claude Code, Droid, and Codex

Read this reference only after the Model Routing answer is `Scaffold` or
`Scaffold + enable codex delegation` and `PLATFORM` is `claude-code`, `droid`,
or `codex`. The question has already been answered. Re-read target files from
disk after the Docs write; never reuse an in-memory copy.

## Resolve targets

Use this deterministic ladder, first match wins:

1. Docs answered this run: mirror `CLAUDE.md only`, `AGENTS.md only`, or `Both`.
   `Skip` falls through.
2. Otherwise use files already carrying `<!-- BEGIN FLOW-NEXT -->` (both means
   both).
3. Otherwise use Codex → `AGENTS.md`; Claude Code/Droid → `CLAUDE.md`.

Apply the shim guard per target. Exactly one non-empty line matching
`@<path>.md` or `See[:] <path>.md` (case-insensitive) is a shim: retarget to an
existing in-repo file and apply the guard again. Missing pointer target drops
that target with:
`Model-routing scaffold: <file> is a shim pointing at a missing <path>.md — skipping`.
Never turn a shim into a mixed file. If all targets drop,
`ROUTING_OUTCOME="skipped (shim)"`, then continue to delegation below.

For multiple targets, run composition, comparison, read-back, and write
separately. A per-file terminal ends only that file. Join outcomes in the
summary.

## Compose per target

Read [../templates/model-routing-snippet.md](../templates/model-routing-snippet.md)
verbatim. Deterministically transform every probe-sentinel line:

- Passing probe: strip the `<!-- probe:<cli> --> ` prefix.
- Failed probe: comment the full route as
  `<!-- not detected on this machine — install <binary>, then uncomment: TEXT -->`.
- Map `codex` → `codex`, `cursor` → `cursor-agent`, `grok` → `grok`.

After transformation no `<!-- probe:` sentinel and no active route for a failed
probe may remain. With all probes absent, all probe-gated routes are inert
install notes; still honor the user's scaffold choice.

Then substitute invocation syntax per target: only AGENTS.md on Codex rewrites
every `/flow-next:<cmd>` to `$flow-next-<cmd>`. CLAUDE.md on every platform and
AGENTS.md on Claude Code/Droid keep slash syntax.

## Compare, ask, and write

Inspect the target before read-back:

- Existing well-formed model-routing marker block: byte-compare against this
  target's composed block.
  - identical: silent no-op, no mtime change,
    `ROUTING_OUTCOME="unchanged (already current)"`.
  - different: ask `Keep mine (Recommended)` / `Overwrite with canonical` /
    `Skip`. Keep prints the canonical template path and records
    `kept (customized)`; Skip records `skipped`; Overwrite continues.
- No marker: scan outside markers for a model-routing-shaped heading. If found,
  ask `Add the flow-next block below yours` / `Skip`; never duplicate silently.

On a would-write path, show the complete composed block, then ask `write` /
`skip`. Only `write` appends or marker-replaces the whole block. Confirm:
`Model-routing section written to <file> — this section is yours now; edit the scores/rules freely, or re-run /flow-next:setup to regenerate.`

## Delegation opt-in

This branch runs even when the block was unchanged/kept if the answer was
`Scaffold + enable codex delegation`:

```bash
"${PLUGIN_ROOT}/scripts/flowctl" config set work.delegate codex --json
DELEGATE_SET=$("${PLUGIN_ROOT}/scripts/flowctl" config get work.delegate --raw --json 2>/dev/null | jq -r 'if .value == null then "" else (.value | tostring) end')
```

NEVER set or touch `work.delegateConsent`. Persisted `codex` sets
`ROUTING_DELEGATE="enabled"`; otherwise warn and set `failed`.

## Review-backend switch offer

Ask once only when all hold: scaffold answer accepted, `HAVE_CODEX=1`,
`PLATFORM` is not `codex`, and `CURRENT_BACKEND` is nonempty and neither bare
`codex` nor a `codex:...` spec. Ask `Keep current (Recommended)` or
`Switch to codex`; never silently overwrite. On Switch, set
`review.backend codex`, then read persisted config back and warn on failure.
