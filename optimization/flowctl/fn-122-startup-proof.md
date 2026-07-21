# fn-122 startup proof

Date: 2026-07-21  
Machine: maintainer macOS workstation  
Runtime: CPython 3.14.5  
Method: 12 fresh processes per command, discard the first two, report the median and observed range of the remaining 10. Stdout discarded; stderr captured; 30 ms spacing between runs. Baseline and post-change runs use the same worktree and machine.

## Shipped result

| Path | 3.1.0 baseline | Safe post-change median | Change | Post-change range |
|---|---:|---:|---:|---:|
| copied launcher `--help` | 0.2008s | 0.0636s | -68.3% | 0.0619–0.0668s |
| plugin-bin launcher `--help` | 0.1971s | 0.0632s | -67.9% | 0.0627–0.0648s |
| plugin-bin `usage` | 0.2242s | 0.0633s | -71.8% | 0.0617–0.0645s |
| `config get "" --json` | 0.2197s | 0.2235s | +1.7% | 0.2213–0.2271s |
| `status --json` | 0.2772s | 0.2767s | -0.2% | 0.2739–0.2828s |
| `list --json` | 0.2764s | 0.2782s | +0.7% | 0.2748–0.2829s |

Exact static `usage` and root-help requests route through the tracked bootstrap. Every other launcher invocation continues directly to tracked `flowctl.py`, preserving the 3.1.0 performance envelope; no measured ordinary path regressed by 10%.

## Bytecode-cache proof and rejection

The checked-hash pyc prototype met the raw latency target: approximately 45% faster help, 72% faster usage, 44% faster config, 37% faster status, and 36% faster list on the same machine. It was not safe enough to ship.

Python's checked-hash pyc header proves which source hash a cache claims, but it does not authenticate that the marshalled executable payload was produced from that source. A writable ignored cache can therefore carry different executable code beneath the correct source hash. A runtime-generated sidecar cannot fix that trust problem because both files share the same writable trust domain. The spec explicitly rejects a risky cache merely to hit the target, so flow-next reads and executes no runtime bytecode cache.

The shipped bootstrap instead uses only tracked, non-executable fast-path data:

- `flowctl usage` resolves the canonical bundled guide first, then copy-mode `.flow/usage.md` with the same error contract.
- exact root `--help` reads tracked `flowctl-help.txt`; a parity test compares it byte-for-byte with live argparse output.
- all other commands execute tracked `flowctl.py` directly through the launcher.
- a regression test plants executable pyc content for the expected module path and proves the tracked source still runs.

Interpreter-choice caching was evaluated and rejected: safely invalidating command aliases, PATH changes, `PYTHON_BIN`, Windows `py -3`, and interpreter replacement would add a second mutable cache and more validation than the retained probe costs. Demand-driven argparse construction was also deferred because the safe static paths already remove the two high-frequency presentation costs, while lazy parser surgery would broaden compatibility risk across 140 command nodes.

## Verification

- `python3 -m unittest test_startup_bootstrap test_init_stamp_launchers test_bin_launcher_parity test_cmd_usage test_setup_mode_stamp test_precheck_mode_contract test_dogfood_template_parity test_ralph_docs_truth test_ralphctl test_install_cursor_parity -q`
- `bash plugins/flow-next/scripts/pick_python_test.sh`
- `bash -n` over canonical, plugin-bin, dogfood, Ralph, resolver, hook, and smoke launch scripts
- `./scripts/sync-codex.sh && ./scripts/sync-codex.sh`
- `claude plugin validate plugins/flow-next`
- `python3 -m py_compile` over canonical/dogfood source and bootstrap copies

CI defines full gates on Python 3.11 and latest stable (`3.x`), intermediate 3.12/3.13 runtime smokes, and Windows Git Bash/PowerShell cases for both Store-stub fallback and pre-source Python 3.10 rejection.
