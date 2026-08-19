---
satisfies: [R1, R3]
---
# fn-200-land-request-human-reviewers-at.1 flowctl: seed land.requestReviewers + publish in config schema

## Description
Add the `land.requestReviewers` config key to flowctl's seeded defaults and the published config schema, following the fn-188 `land.mergeVerdictCommand` plumbing shape exactly. Pure plumbing — no land workflow prose in this task.

**Size:** S
**Files:** plugins/flow-next/scripts/flowctl.py, scripts/gen_flow_config_schema.py, plugins/flow-next/schema/flow-config.schema.json (regenerated), plugins/flow-next/tests/test_land_config.py
**Touches:** [plugins/flow-next/scripts/flowctl.py, scripts/gen_flow_config_schema.py, plugins/flow-next/schema/flow-config.schema.json, plugins/flow-next/tests/test_land_config.py]

### Approach
- `flowctl.py` land defaults dict (`"mergeVerdictCommand": ""` at ~l.1472): add `"requestReviewers": ""` with the same seeded-so-`config get`-returns-a-value comment style; extend the module docstring key inventory the tests assert on.
- `scripts/gen_flow_config_schema.py`: add the description entry beside `land.mergeVerdictCommand` (~l.335) naming the grammar — csv of GitHub logins / `org/team` slugs and/or the literal `codeowners`; unset, `null`, `""` = off; one-shot per PR per head SHA; never gates a merge — and the type tuple `("land.requestReviewers", {"type": ["string", "null"]})` beside ~l.636. Regenerate the artifact with `python3 scripts/gen_flow_config_schema.py`; never hand-edit the JSON.
- `tests/test_land_config.py`: mirror the fn-188 block (~l.306-363): default is `""`, `config get` CLI returns it, `config set` round-trips a csv value, explicit `""` resets, siblings are not clobbered, docstring names the key.
- Keep `test_flow_config_schema_drift` green.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:1460-1480` — land defaults dict
- `scripts/gen_flow_config_schema.py:300-340,625-640` — TABLE description + type entries for land.*
- `plugins/flow-next/tests/test_land_config.py:1-30,300-365` — key inventory docstring + fn-188 test block

**Optional:**
- `plugins/flow-next/tests/test_flow_config_schema_drift.py` — what the drift test enforces

### Key context
- Precedent memory: `.flow/memory/bug/integration/spec-named-config-keys-must-be-checked-2026-07-15.md` (new keys must hit the shipped schema surface) and `adding-a-review-backend-sweep-all-2026-06-29.md` (sweep every enumeration site).
- Do NOT touch `plugins/flow-next/codex/` by hand; the mirror regen is task .3.

### Acceptance
- [ ] `flowctl config get land.requestReviewers --json` returns `""` on a fresh `.flow/`
- [ ] `config set` round-trip + sibling-preservation + reset-to-empty tests pass
- [ ] `flow-config.schema.json` regenerated and contains `requestReviewers` under `land` with the grammar in its description
- [ ] `cd plugins/flow-next/tests && python3 -m unittest test_land_config test_flow_config_schema_drift -q` green

## Acceptance
- [ ] TBD

## Done summary
Seeded `land.requestReviewers` (default `""`; unset/null/"" = OFF) in flowctl's land defaults, published it in the config schema (`["string","null"]`, description names the csv logins / org/team / `codeowners` grammar, one-shot per head, never gates a merge) and regenerated `flow-config.schema.json`; `test_land_config.py` gained the fn-200 block (default, fresh CLI get, csv round-trip, reset-to-empty, sibling preservation both ways, docstring inventory) covering R1 + R3's default-unchanged half. Baseline green; verify green (132 tests, ruff clean, schema-drift green).

stage: impl-review - ran (codex gpt-5.6-sol high, SHIP first pass)
## Evidence
- Commits: 688650a0bc129b0b1029ee311137c6499f81c0b3
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_land_config test_flow_config_schema_drift test_skill_prose_diet -q, uvx ruff@0.16.0 check ., python3 scripts/gen_flow_config_schema.py
- PRs:
stage: plan-sync - ran (drift: no; cross-spec grep not run by agent, conductor checked: no other open spec references land.requestReviewers)
