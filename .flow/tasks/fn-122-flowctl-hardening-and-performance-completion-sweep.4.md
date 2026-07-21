---
satisfies: [R5, R9, R10, R17, R18]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.4 Python 3.11 runtime contract and startup acceleration proof

## Description
Raise the supported runtime to Python 3.11 and make every 3.1.0 launcher enforce it before loading flowctl.py. Cover plugin-bin, copied .flow/bin, canonical Unix/Windows launchers, Ralph copies, and embedded constants. Preserve the fn-77 Windows Store-stub functionality probe and return a distinct actionable error for a working but too-old interpreter. CI already runs 3.11; expand it to latest stable and lightweight intermediate-version smokes.

Prove a source-first, hash/version-validated cached-module or bytecode execution path. Missing, stale, corrupt, or unwritable cache must safely execute source. Cached execution must preserve the logical source/plugin root: cmd_usage must still find plugins/flow-next/templates/usage.md first and .flow/usage.md in copy mode; setup-mode and all other path discovery must remain exact even if __file__ would otherwise point into a cache directory.

Treat flowctl usage as a first-class performance target. fn-121 intentionally makes plugin-mode rails invoke it, but 3.1.0 spends ~0.224s loading the whole CLI to print static Markdown. Optimize it through the common startup path or a parity-tested launcher fast path across plugin/copy/Windows modes. Evaluate interpreter-choice caching and demand-driven argparse/template construction only after the primary proof.

Complexity: 86/100.

Quick commands:
- cd plugins/flow-next/tests && python3 -m unittest test_init_stamp_launchers test_bin_launcher_parity test_cmd_usage test_setup_mode_stamp test_precheck_mode_contract test_dogfood_template_parity -q
- ./scripts/sync-codex.sh && ./scripts/sync-codex.sh
## Acceptance
- [ ] Plugin-bin/copy/Ralph/Unix/Windows launch paths reject Python 3.10 before source import and accept Python 3.11/latest with precise errors.
- [ ] README/platform/install/update docs and CI state Python 3.11+ consistently; 3.11/latest full gates and intermediate smokes are defined.
- [ ] Cached startup artifacts are source-hash/runtime-version validated, recoverable, gitignored, and never authoritative.
- [ ] Cached execution preserves canonical/fallback usage resolution, setup-mode invariants, and every logical source/plugin path.
- [ ] Same-machine evidence targets >=35% warm improvement for help/usage/simple commands and >=20% for list/status, or records why no safe design can meet both benefit and correctness.
- [ ] Root/family help, aliases, error text/exit codes, scope rewriting, plugin/copy mode, Store-stub defense, usage/setup-mode, and source fallback remain covered.
- [ ] Canonical/generated launchers and Codex mirror remain twice-idempotent with fn-121 guards green.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
