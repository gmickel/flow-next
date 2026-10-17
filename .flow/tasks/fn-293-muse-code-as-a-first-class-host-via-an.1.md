---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-293-muse-code-as-a-first-class-host-via-an.1 Implement Muse Code as a first-class host via an installer

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Muse Code support via `scripts/install-muse.sh`: a bundle builder (`scripts/lib/muse_bundle.py`) translates agent `disallowedTools` to Muse tool names, rewrites `flow-next:<agent>` to `flow-next/<agent>`, adds a dispatch note and a detection marker, then installs and approves with Muse's CLI. Setup detects the marker ahead of inherited host signals (AGENTS.md docs target, Grok-style review menu). Shared fixes: flowctl `main()` disables bytecode writes so commands never modify their install (Muse disables agents on package changes); agent colors use Claude Code's named values. Docs: platforms Muse section, roster, adding-skills, releasing, changelog.

Verified live on Muse Code 1.4.6 (Claude Code and Codex installed on the same machine): installer, agents spawning as their own definitions with read-only scouts refused writes, setup detection, capture, plan with scouts, work with workers, codex review, `flow --auto` to a PR and land to a merge, with `--disable-sandbox`; review inside Muse's sandbox fails honestly (documented).

stage: impl-review - ran [8e3d7b80..eed90c0d] NEEDS_WORK (2 findings: launcher path still wrote __pycache__; bundle did not rewrite agent references) then SHIP on re-review (model: codex gpt-6-astra)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 173552638d3460b81cb1e606e8844e4d035e63e5, eed90c0d4c5fab3e21734945f83a5cf925d6bf3e, d29714868cc100a7d118e13fee331ce685a21d5a, c6c543a5e4a1d9fa87c76ca92384392b01b59978
- Tests: python3 scripts/run_tests_parallel.py (4015 ok, before review fixes); focused: test_install_muse test_startup_bootstrap test_setup_grok_host test_tracker_package_import test_install_opencode test_sync_codex_check; uvx ruff@0.16.0 check .
- PRs: