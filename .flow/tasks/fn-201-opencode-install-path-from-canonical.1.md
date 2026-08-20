---
satisfies: [R1, R2]
---
# fn-201-opencode-install-path-from-canonical.1 POSIX OpenCode installer: skills snapshot and plugin-root support dirs

## Description
Add scripts/install-opencode.sh (POSIX bash, set -e, snapshot-of-working-tree, idempotent re-run = update) following scripts/install-cursor.sh conventions (rsync -a --delete with tar fallback; no symlink; no Windows .ps1). Target: ${XDG_CONFIG_HOME:-$HOME/.config}/opencode — XDG ONLY, no OPENCODE_CONFIG_DIR probing; an explicit --dest <path> flag overrides the target (tests drive this). Scatter canonical files — do not commit a rewritten mirror and do not copy the whole plugin tree.

Install: recursively copy plugins/flow-next/skills/* as-is into <dest>/skills/<skill-name>/, EXCLUDING skills/flow-next-setup/ (OpenCode dispatches skills by description match, so an installed setup SKILL is phrase-reachable and lands in setup's else->codex platform fallback even with no command stub; docs in task 4 state setup unsupported + the manual alternative). Directory NAMES (skills/agents/commands) are the plan's working assumption - pin the actual names from OpenCode docs/source at build time and record the source reference in the installer (see the spec's pinned-directory-layout clause). Copy the PLUGIN-ROOT SUPPORT DIRS to the config root: scripts/ (flowctl + everything gen_tracker_manifest.py pins, including scripts/lib/), templates/, references/, and docs/ — everything canonical skill prose resolves plugin-root-relative (${PLUGIN_ROOT}/templates/spec.md tier-3 cascade, ${PLUGIN_ROOT}/templates/criteria.md, ../../references/*, docs cross-links). The support-dir list follows the spec's PRECISE derivation rule: grep-derived top-level segments MINUS the named, reason-annotated exclusion list (.claude-plugin/, .cursor-plugin/, .codex-plugin/, codex/, skills/ itself, non-filesystem matches) - pinned by a test in task 3 as derived - exclusions == installed. After copy, fail closed if flowctl_tracker/MANIFEST.json or scripts/lib/verify_tracker_manifest.py is missing; run that verifier against the installed scripts/ dir and abort loudly on mismatch (same contract as install-cursor.sh).

Ownership manifest: write ONE deterministic manifest (no timestamps, no host-varying absolute paths) at the config root listing EVERY installed path (skills dirs, support dirs; tasks 2-3 extend it with generated agents/commands). Install-time --delete semantics and re-runs read from the manifest, never the source tree. PRE-FLIGHT (fail closed): if a target support dir (e.g. <dest>/scripts/) exists WITHOUT the manifest claiming it, abort with a named error naming the colliding path; a documented --force flag overrides. A first install never deletes user-authored content to claim a path.

Never write into ~/.claude/. Never register Ralph/hooks. Re-run must update in place and drop paths removed upstream from manifest-owned paths only; user files outside manifest paths stay untouched.

Zero canonical skill/agent prose edits. No setup platform-detection branch.

CI: both paths: filter blocks already carry a blanket scripts/** entry, so the installer is covered from day one; add the explicit scripts/install-opencode.sh entry beside the other installers for parity/legibility only (both lists stay in step per test_push_and_pull_request_filters_stay_in_step).

Touches: scripts/install-opencode.sh, plugins/flow-next/scripts/lib/, .github/workflows/test-flow-next.yml
Files:
- scripts/install-opencode.sh (create)
- .github/workflows/test-flow-next.yml (paths: filters)
- plugins/flow-next/scripts/lib/ (read/verify only unless a tiny ownership helper is required)

## Acceptance
R1: running the installer with --dest at a temp dir plants every canonical plugins/flow-next/skills/*/ tree EXCEPT flow-next-setup/ as-is under <dest>/skills/ plus scripts/, templates/, references/, docs/ at the config root; a second run after editing a SKILL.md updates it in place; a path removed upstream disappears from manifest-owned paths and nowhere else; a pre-existing unclaimed <dest>/scripts/ aborts with a named error and survives untouched (--force overrides). R2 (CI-provable half): from any installed skills/<name>/SKILL.md, ../../scripts/flowctl is executable and verify_tracker_manifest.py passes on the installed scripts/; ../../templates/spec.md exists. The manifest is byte-deterministic across two fresh installs of the same tree. No writes under ~/.claude/. No hooks/ralph registration. The explicit CI paths: parity entry exists in both lists (coverage pre-exists via scripts/**).

## Done summary
scripts/install-opencode.sh created (grok-4.6 bridge draft, host-verified): XDG-only dest + --dest, skills minus flow-next-setup, support dirs scripts/templates/references/docs at config root, deterministic ownership manifest, pre-flight collision abort with --force, manifest-driven stale cleanup, tracker verifier fail-closed. CI paths parity entries added. Verified live: idempotent trees identical, manifest byte-deterministic across dests, unclaimed-dir abort leaves user file intact, two-levels-up rung resolves flowctl+templates, tracker manifest verifies (45 files).
## Evidence
- Commits: 5d24a384003067b5de4f18c1070808337e1c24e5
- Tests: bash -n scripts/install-opencode.sh, ./scripts/install-opencode.sh --dest /tmp/oc-dest1 (idempotency+determinism+preflight+rung smoke)
- PRs: