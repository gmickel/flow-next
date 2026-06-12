---
satisfies: [R1, R9, R11]
---

## Description
Introduce the opt-in gate and the artifact filesystem layout, and wire the setup ceremony. NO generation logic here — just the deterministic substrate.

**Size:** M
**Files:** plugins/flow-next/scripts/flowctl.py, plugins/flow-next/tests/test_artifacts_config.py (new — follow test_land_config.py shape), plugins/flow-next/skills/flow-next-setup/workflow.md, plugins/flow-next/skills/flow-next-setup/templates/usage.md, .flow/usage.md, plugins/flow-next/docs/flowctl.md (config-key row only)

## Approach
- Add an `artifacts` block to `get_default_config` (flowctl.py:1124), following the `work`/`land` block precedent (:1145/:1164): `{"html": {"enabled": False}}`. Boolean knob — `flowctl config set artifacts.html.enabled true` (set_config :1342 and deep_merge :1200 already handle the rest; no new subcommand).
- Regression tests (new test_artifacts_config.py, mirror test_land_config.py): fresh-repo default `false` (present, not null); set/get round-trip; unknown sibling keys under `artifacts` survive re-set (deep_merge preservation).
- Artifact layout contract (documented, not code): `.flow/artifacts/<spec-id>/spec.html`, `.flow/artifacts/<spec-id>/pr.html` — fixed deterministic paths, never timestamped (Lavish keys sessions on the absolute path).
- Setup ceremony: add the HTML-mode question to Step 6d (workflow.md:378, include-only-if-unset via --raw read like flowctl.py:5401 precedent) + config write in Step 7 (:523). On "yes": one follow-up — commit artifacts (default) or gitignore `.flow/artifacts/` (append to .flow/.gitignore); then surface the lavish-axi offer: print install commands (`npm i -g lavish-axi` / zero-setup `npx lavish-axi`), the session-spanning feedback model (global ~/.lavish-axi/state.json, pull-only poll), and the ~30min idle-stop/resume behavior. NEVER auto-install (flow-next-map discipline, SKILL.md:76).
- usage.md + setup template: add `artifacts.html.enabled` to the Config section + `.flow/artifacts/` to the layout diagram. flowctl.md: add the config-key row (boolean — docs show `true`, the literal value; memory: docs-activation-command-for-string-enum).

## Investigation targets
**Required:**
- plugins/flow-next/scripts/flowctl.py:1124-1170 — default-config block precedents
- plugins/flow-next/tests/test_land_config.py — config-test shape to mirror
- plugins/flow-next/skills/flow-next-setup/workflow.md:370-545 — question-list + answer-processing patterns
- plugins/flow-next/skills/flow-next-map/SKILL.md:70-90 — detect-on-PATH + install-offer discipline
**Optional:**
- .gitignore + .flow/.gitignore — generated-dir precedent (.flow/receipts/, .flow/tmp/)

## Acceptance
- [ ] `flowctl config get artifacts.html.enabled --json` returns `false` on a fresh repo (default present, not null)
- [ ] `flowctl config set artifacts.html.enabled true` round-trips; unknown sibling keys under `artifacts` survive a re-set (deep_merge)
- [ ] test_artifacts_config.py covers default + round-trip + sibling preservation; suite green
- [ ] Setup asks the HTML question ONLY when the key is unset (raw read); writes config + gitignore choice on confirmation; never auto-installs lavish
- [ ] Lavish offer text covers: install commands, session-spanning pull-only model, idle-stop/resume
- [ ] usage.md (both copies) + flowctl.md document the key and the `.flow/artifacts/` layout
- [ ] With the key absent/false: no reference file loaded, no artifacts written, no Lavish session opened, no behavior-visible output anywhere (grep: no unconditional references to the artifacts dir)

## Done summary
Added the opt-in HTML artifact config gate: artifacts.html.enabled=false seeded in get_default_config (fresh-repo get returns false, raw returns null), 9 regression tests mirroring test_land_config.py, setup-ceremony wiring (include-only-if-unset question, commit-vs-gitignore follow-up, verbatim lavish-axi offer with never-auto-install discipline), and docs for the key + .flow/artifacts/<spec-id>/ layout in flowctl.md and both usage.md copies. Codex mirror regenerated; dogfood flowctl.py synced. RP review: SHIP (first pass, R1/R9/R11 met).
## Evidence
- Commits: 5597dd124f44df6ce66950826098ef88a554d91d
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (1071 tests OK), python3 -m unittest test_artifacts_config (9 tests OK)
- PRs: