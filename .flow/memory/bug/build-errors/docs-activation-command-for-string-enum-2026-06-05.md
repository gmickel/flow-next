---
title: Docs activation command for string-enum config knob used bool true instead of th
date: "2026-06-05"
track: bug
category: build-errors
module: "plugins/flow-next/docs/flowctl.md, .flow/usage.md"
tags: [fn-55, work.delegate, config-enum, docs-drift, activation-predicate, codex-delegation, review-feedback]
problem_type: build-error
symptoms: Documented enable command (config set work.delegate true) silently never activates delegation; activation predicate is value=='codex'
root_cause: String-enum knob (codex|false) documented with the bool 'true' idiom used by every other flow knob; 'true' != 'codex' so resolves OFF
resolution_type: fix
related_to: [bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/env-marker-gate-must-scan-the-namespace-2026-06-04, bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
fn-55.6 documented the opt-in Codex delegation activation as `flowctl config set work.delegate true` in `.flow/usage.md` + the setup template, and typed `work.delegate` as `bool` in `flowctl.md`. But the activation predicate (SKILL.md / phases.md / `test_work_delegate_config.py`) is `config_value == "codex"` — ANYTHING else, including bool `true`, resolves OFF. So the documented command would persist and silently NEVER activate delegation. RP impl-review caught it at confidence 100.

## What Didn't Work
Reflexively writing the enable command in the boolean shape every other flow knob uses (`config set memory.enabled true`, `config set planSync.enabled true`). The delegation knob is deliberately a string-enum (`codex | false`), not a bool — the value carries the backend identity, mirroring `review.backend`. Copy-pasting the bool idiom produced a doc that "looks" right but is inert.

## Solution
- usage.md + setup template: `work.delegate true` → `work.delegate codex`, with inline "value MUST be `codex` to activate".
- flowctl.md: type `bool` → `codex | false`; note that the activation predicate is `value == "codex"` and any other value (incl. bool `true`) is OFF. Default stays `false`.
- Regenerate Codex mirror; parity guard green.
(README.md + canonical `codex-delegation.md` already said `work.delegate=codex` — only the usage/flowctl surfaces drifted.)

## Prevention
- When a config knob is a string-enum whose *value selects a mode* (review.backend, work.delegate), the enable-command in docs MUST use the literal activating value — never the bool `true` idiom. Grep new docs for `config set <knob> true` and cross-check against the resolution predicate in code/tests before shipping.
- The activation predicate is the source of truth — if `get_default_config` default is `False` (bool) but the predicate compares `== "codex"` (string), the type is `string|bool`, not `bool`. Document both the default AND the activating value.
