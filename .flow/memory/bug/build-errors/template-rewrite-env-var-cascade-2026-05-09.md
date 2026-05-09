---
title: "Template rewrite: env-var cascade + canonical config.env knob alignment"
date: "2026-05-09"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-ralph-init/templates
tags: [fn-43, rename, template, ralph, config-env, env-var-cascade, review-feedback, codex-review]
problem_type: build-error
symptoms: ralph.sh discarded externally-set SPECS_FILE/EPICS_FILE; config.env exposed list knob but not file knob
root_cause: Naive variable-init cleared user-set env vars before cascade resolution; literal spec text required SPECS_FILE= but template kept the list-style SPECS= shape only
resolution_type: fix
related_to: [bug/build-errors/agent-rename-epic-id-prompt-key-changes-2026-05-08, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08]
---

## Problem

Two related issues during the Ralph init template rewrite (T9 of the epic→spec rename):

1. **Resolver dropped externally-set env vars.** The `SPECS_FILE` / `EPICS_FILE` resolver in `ralph.sh` unconditionally reset both to empty before deriving from the `SPECS` list. If a user/script set `SPECS_FILE=/path.json` in the environment before invoking ralph.sh, the script silently discarded it.

2. **config.env exposed only the convenience list, not the canonical file knob.** The template originally exposed `EPICS=` as a list-style scope knob. The rename to `SPECS=` preserved the convention, but the spec text explicitly required `config.env` to expose `SPECS_FILE=` (the canonical file-path knob). Reviewer pushed back twice on this, citing the literal acceptance text.

## What Didn't Work

- First fix only restored the env-var cascade in ralph.sh but kept config.env exposing only `SPECS=` (the list). Reviewer's second pass flagged that fresh `/flow-next:ralph-init` installs would not show the canonical `SPECS_FILE=` knob.

## Solution

For (1): Resolve the run-scope file via cascade BEFORE clearing for derivation:
```bash
SPECS_FILE="${SPECS_FILE:-${EPICS_FILE:-}}"
if [[ -z "$SPECS_FILE" && -n "${SPECS// }" ]]; then
  SPECS_FILE="$RUN_DIR/run.json"
  write_specs_file "$SPECS" > "$SPECS_FILE"
fi
EPICS_FILE="$SPECS_FILE"  # mirror canonical → legacy after resolution
```

For (2): Expose BOTH `SPECS_FILE=` (canonical, file-path) AND `SPECS=` (convenience list, derives a JSON file under `$RUN_DIR`) in config.env. The cascade resolves `SPECS_FILE > EPICS_FILE > SPECS-list-derived > none`.

## Prevention

When porting a config-knob rename across template files: read the spec acceptance criteria literally, not aspirationally. If the spec says `SPECS_FILE=`, expose `SPECS_FILE=` in the template — even if the codebase historically used a different shape (`SPECS=` list-style). The reviewer-as-spec-enforcer pattern catches this; trust it.

When updating a template that derives one variable from another: walk the precedence chain explicitly (CLI flag > env var > config.env > default) and verify each tier with a concrete test. The shell idiom `VAR="${VAR:-${LEGACY_VAR:-}}"` is the cleanest cascade form — use it consistently.
