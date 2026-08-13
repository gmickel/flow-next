# flowctl module split: importable launcher, package extraction on the flowctl_tracker pattern

> **SUPERSEDED 2026-08-13 — split into two specs, closed without implementation.**
> Its two halves had different justifications (a measured startup number vs a
> parity/navigation bet), different risk profiles, and different verification, so
> bundling them meant the low-risk half waited on the high-risk one.
>
> - **R1 (importable launcher) + R3 (single verdict→status site)** →
>   `fn-190-flowctl-startup-importable-entry-for`
> - **R2 + R4/R5 (package extraction, distribution integrity)** →
>   `fn-191-flowctl-review-terminal-machinery` (depends on fn-190)
>
> Both successors carry this spec's research forward in their task files: the
> launcher artifact graph and `init` restamp trap, the authenticated-fast-path
> scoping, the `argv[0]`/`prog` parity trap, the injection-over-import rule that
> avoids `__main__` split-brain, and the symbol-list-not-coordinates boundary.
> Re-measured on main @ 9e111db4 (2026-08-13): 249ms as-script vs 109ms imported
> (−56%); the extraction region is ~2,633 lines (5.1% of the module) and its
> boundary had drifted 366 lines from the coordinates recorded below — which is
> why the successors state symbols, never line numbers.
>
> Nothing here was implemented. Read the successors, not this file.

## Goal & Context
<!-- scope: business -->

`flowctl.py` is a 48,283-line single file. Measured 2026-08-04 (macOS, M-series): every invocation costs ~250-400ms of pure parse/exec before any work (`show --json` ~290ms total; module import+exec alone ~390ms cold; a trivial script ~40ms) because Python does not bytecode-cache a file run as `python3 file.py` — only imported modules get `__pycache__`. A full spec run makes hundreds of flowctl calls, so aggregate startup overhead is roughly 1-3 minutes per run. [evidence: measured in-session]

The larger cost is parity and navigation, with fresh field evidence from fn-159 (PR #290): the verdict→status literal existed at multiple sites and fixes repeatedly landed on one path while missing a sibling (RP vs in-process vs host; plan vs completion — multiple bot rounds were exactly such parity misses); plan-sync spent three passes re-anchoring line numbers as the file shifted by hundreds of lines per task; agents never read the file in full (~1.4M tokens) and navigate exclusively by Grep + offset Reads. A monolith makes drift-class bugs likelier and every review slower. [evidence: fn-159 review ledger, plan-sync breadcrumbs]

**The extraction pattern is already proven in this repo:** `flowctl_tracker/` (fn-139-141) moved the tracker bridge's repeatable machinery into a deterministic package with a generated MANIFEST integrity contract, deleting per-provider prose and cutting reached-path size ~70%. STRATEGY.md's Tracker-determinism track explicitly calls it "the template for future 'prose that grew into plumbing' extractions". This spec applies that template to flowctl itself.

## Architecture & Data Models
<!-- scope: technical -->

Two independent improvements, ordered by risk:

1. **Importable launcher (perf, near-zero risk):** the `.flow/bin/flowctl` bash launcher and the plugin entry invoke flowctl as a MODULE (thin entry importing the real module, or an inline `python3 -c` import shape) so `__pycache__` kicks in. Expected ~3-5x startup cut after first invocation per checkout. Must respect: the 49-line bash launcher contract (fn-77 — never overwrite `.flow/bin/flowctl` with Python), `.flow/bin/` dual-copy distribution, `--ignore-user-config`-style env isolation unaffected, `sys.path` containment (no repo-module shadowing), and stale-pyc safety across copy-mode upgrades (Python's own source-mtime/size invalidation).
2. **Package extraction (parity surface, staged):** split cohesive subsystems out of flowctl.py into a package next to `flowctl_tracker/` (working name `flowctl_review/`), starting with the newest and most parity-sensitive region: the fn-159 review-terminal machinery (reservations, journal lifecycle, replay gate, supersession, epochs, digests, stall rules, ratchet rendering) plus the verdict→status map unified behind one function. Follow the flowctl_tracker contract exactly: deterministic package, generated MANIFEST, `.flow/bin/` rsync propagation, `test_tracker_distribution`-style integrity test. Later stages (separate follow-up specs, NOT this one): rp/backend dispatch, receipts/findings, gates. This spec proves the pattern on one subsystem; it does not boil the file.

### Plan-time research refinements (2026-08-04, verified file:line)

- **The recorded bytecode-cache rejection is scoped, not overturned.** `flowctl_bootstrap.py:98-176` deliberately compiles flowctl.py in memory via exec() and never reads/writes pyc — a fn-139.5 design, recorded at `docs/flowctl.md:125` ("a runtime-written ignored pyc can validate a source hash without proving its executable payload came from that source"). That rationale belongs to the **manifest-authenticated static-help fast path**, which KEEPS its no-cache exec design untouched. The **main CLI path** (`python3 flowctl.py ...`) never made a hash-authentication claim — it just runs the source; switching it to a thin entry that imports flowctl uses Python's standard pyc invalidation (source mtime/size embedded in the pyc header), the same trust model as any imported module, `flowctl_tracker/` included. `docs/flowctl.md:125` is REWRITTEN (not appended) to record this scoping.
- **Entry seam is half-built:** `main()` exists at `flowctl.py:46820`; the `__main__` guard sits at `:49735`; bootstrap already calls `module.main()`. The launcher's `FLOWCTL_ENTRY` mechanism (bash `:44-49`) points at the new entry.
- **Windows twin:** `plugins/flow-next/scripts/flowctl.cmd` mirrors the bash launcher (same bootstrap/main split) and changes in parallel. `test_tracker_distribution` RuntimeSmoke exercises the real launcher incl. `.cmd` on Windows CI.
- **Extraction region (defined by SYMBOLS, not line numbers):** from `get_max_review_iterations` through the COMPLETE `build_convergence_ratchet_block` function (currently `flowctl.py:9546` through `:11901`; the def starts at :11797 and its body ends at :11901). `build_rereview_preamble` (:11904) explicitly STAYS in flowctl.py. Line refs are orientation only — the boundary is the symbol list; re-grep at implementation time. The prompt-template loaders (:9425-9489) and `build_review_prompt` (:9489) also STAY in flowctl.py so `test_prompt_text_pinned` needs no changes; if a pinned constant moves, only the test's read location changes and hashes stay identical.
- **Import pattern (DECIDED — explicit injection + facade re-export):** flowctl.py loads the package via the flowctl_tracker-style lazy `sys.path.insert` guard + soft-fail message (patterns at `flowctl.py:1706-1709`, `:38576-38582`). For the reverse direction the package NEVER imports flowctl by name: under direct `python3 flowctl.py` the host module is `__main__`, so `import flowctl` would execute a SECOND module instance with separate lock/cache singletons (silent split-brain). Instead flowctl.py passes its own module object (or a narrow context object of the needed callables) into flowctl_review at wiring time — the seven listed helpers (`atomic_write_json`, `now_iso`, `get_flow_dir`, `find_spec_json_path`, `load_json_or_exit`, `normalize_epic`, `CrossProcessLockError`) are a starting list, NOT the full set: the region also reaches receipt-recovery paths (e.g. `_completion_review_receipt_recovery_path` ~:39672), receipt locking/preservation, findings validation, and criteria parsing. A mechanical cross-boundary symbol inventory (AST/pyflakes pass over the moved code) is required before the move. flowctl.py keeps facade re-exports of every extracted symbol name so the dozens of downstream flowctl.py call sites remain verbatim. Runtime tests must cover all three load identities: imported `flowctl` (new launcher), direct `python3 flowctl.py`, and the bootstrap static path.
- **Launcher artifact graph (R1 touches more than two files):** the launcher text exists at multiple drift-guarded sites: embedded `LAUNCHER_SH`/`LAUNCHER_CMD` constants inside flowctl.py (`:19101-19158` — byte-identical-to-disk drift guard; `flowctl init` RESTAMPS launchers from these constants), `plugins/flow-next/scripts/flowctl` + `flowctl.cmd`, `plugins/flow-next/bin/flowctl`, `.flow/bin/flowctl`, `scripts/install-codex.sh` copy lines (:245-251), setup workflow copy steps, ralph-init copies, and staged-layout smoke fixtures. Changing the invocation shape means updating the WHOLE graph together — otherwise `flowctl init` restamps the old launcher and `test_bin_launcher_parity` / `test_init_stamp_launchers` fail. A new entry file must ride every distribution channel that today carries `flowctl.py` (setup, install-codex, ralph-init, `.flow/bin`), plus an installed-layout smoke that invokes a non-static command.
- **R3 reality check:** site 1 (`_REVIEW_VERDICT_STATUS` + `_review_status_from_verdict`, `flowctl.py:9966-9976`) is ALREADY the canonical helper; sites 2 (`:10741-10745`, inline dict inside `_record_review_attempt_locked`) and 3 (`:40053-40057`, inline dict in `_self_write_review_status`) are duplicates to delete and route through it. Site 4 is the ralph.sh template's INVERSE status→VERDICT bash mapping (`skills/flow-next-ralph-init/templates/ralph.sh:1278-1285`) — different language and direction; it and `ralph-guard.py:128`'s verdict-set enum are documented independents (bash/hook contexts must not depend on importing flowctl internals), not consumers of the Python helper.

## Edge Cases & Constraints

- **Zero behavior change.** Byte-identical CLI surface, exit codes, markers, JSON shapes. The full suite is the contract; `test_flowctl_surface` must not change except import-path plumbing.
- **Zero-dep contract holds** (stdlib only; package lives in-repo, copied to `.flow/bin/`).
- **Prompt-text discipline:** extraction must not alter any embedded prompt constant — `test_prompt_text_pinned` + parity suites green with UNCHANGED hashes (a moved constant keeps its bytes).
- **Windows launcher + smoke matrix** (10 suites x 3 OS) must stay green; fn-120's concurrent-edit caution applies — coordinate if it activates.
- **Copy-mode upgrade path:** propagation gains package dirs — setup/installers already rsync `flowctl_tracker/`; extend the same mechanism, never a new one.
- **`__pycache__` hygiene:** importing flowctl writes `__pycache__/` next to the imported module (incl. under committed `.flow/bin/`) — `.gitignore` must cover the new dirs; propagation rsync already excludes `__pycache__`. Read-only checkouts: Python silently skips pyc writes — flowctl still works, just without the speedup (graceful; no error surface).
- **`test_no_per_command_hashing`** (`test_tracker_distribution.py:197-201`) asserts flowctl.py source never contains the literal string "MANIFEST.json" — the new package's manifest checks live in the generator/installer only, exactly like flowctl_tracker.
- **Stale-install soft-fail:** `.flow/bin` copies missing `flowctl_review/` after a partial upgrade must produce an actionable message naming the package (mirror flowctl_tracker's "package not installed alongside flowctl.py"), never a bare traceback.
- **Verdict-map parity precondition:** the three Python dicts must be verified equivalent (incl. unknown-verdict fallback semantics) BEFORE deleting duplicates — silent divergence would make unification a behavior change; divergence gets surfaced, not unified.
- **Line-anchor churn:** the extraction shifts every downstream doc/task anchor once — do it in one PR, run plan-sync after landing, note it in the CHANGELOG entry. Open specs fn-160 (`flowctl.py:17307+`, `:2737+`, `:42209+`) and fn-158 (`:13814-13872`, `:11376`) carry anchors that will churn (both self-note re-grep).

## Quick commands
```bash
# Focused suites (per-task baseline + verify)
cd plugins/flow-next/tests && python3 -m unittest test_tracker_distribution test_prompt_text_pinned test_flowctl_surface test_bin_launcher_parity test_startup_bootstrap -q
cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_review_receipt_schema test_review_json_tallies test_host_review_backend test_review_prompt_template_parity -q
# Warm-startup measurement (R1 evidence)
time (for i in 1 2 3 4 5; do .flow/bin/flowctl show fn-166-flowctl-module-split-importable --json >/dev/null; done)
```

## Acceptance Criteria
<!-- scope: both -->

- **R1:** flowctl invocations import a bytecode-cacheable module; measured warm startup for `flowctl show <spec> --json` drops >=2x vs the 2026-08-04 baseline (~290ms) on the same machine class, with the measurement method recorded in the spec/PR. The manifest-authenticated bootstrap fast path (`flowctl_bootstrap.py`) keeps its no-cache exec design; `docs/flowctl.md:125` is rewritten to scope its bytecode-rejection rationale to that authenticated path. Errors: read-only checkout → pyc write silently skipped, flowctl works without the speedup; stale pyc → Python's standard source-mtime/size invalidation; sys.path gains only the script's own directory (no repo-module shadowing).
- **R2:** the fn-159 review-terminal machinery lives in a package (`flowctl_review/` or better name) with a generated manifest + distribution integrity test, propagated to `.flow/bin/` by the existing mechanism; `flowctl.py` shrinks by at least the extracted region's size. Errors: stale install missing the package → soft-fail message naming flowctl_review; tampered/absent MANIFEST → installers fail closed (mirror ExecutableInstallerFailClosed).
- **R3:** the verdict→status mapping exists at exactly ONE Python site (the existing `_review_status_from_verdict` helper), consumed by all former inline-dict call sites; the ralph.sh template's inverse status→VERDICT bash mapping and ralph-guard.py's verdict-set enum are documented as deliberate independents with the why recorded at the single site. Errors: unknown-verdict fallback behavior verified identical across former sites before unification — any divergence is surfaced for decision, never silently unified.
- **R4:** full suite + ruff + smoke matrix green; `test_prompt_text_pinned` hashes unchanged; no CLI surface/schema/exit-code diffs. No error surface beyond the gate itself.
- **R5:** docs updated — `docs/flowctl.md` (:125 rewrite + `.flow/bin` tree at :38-42), `agent_docs/local-dev.md` (propagation + integrity recipe), root `CLAUDE.md` (final-gate propagation command extended), `docs/architecture.md` review-bookkeeping pointer (~:122-145), `docs/memory-schema.md:158-163` lockstep set widened, `agent_docs/optimizing-skills.md:25` stale LOC line, `docs/platforms.md` Codex-host copy lines checked — plus CHANGELOG Unreleased entry, outcome-first. No error surface beyond R4's gate.

## Boundaries
<!-- scope: business -->

- NOT a full decomposition of flowctl.py — one subsystem proves the pattern; further extractions are separate specs with their own evidence.
- NO behavior, schema, or CLI changes; no new dependencies; no async/daemon/server designs for startup (the import fix is sufficient and simple).
- `flowctl_bootstrap.py`'s in-memory exec design is untouched (its integrity rationale stands for the authenticated fast path).
- ralph-guard.py stays a single-copy hook, untouched except R3's documented non-change. ralph.sh's bash inverse mapping stays as-is (documented independent).
- The 49-line bash launcher contract (fn-77) is preserved — the launcher may gain lines but stays a bash launcher.

## Strategy Alignment

Active tracks served:
- **Tracker determinism** — explicitly extends its own stated template ("prose that grew into plumbing" extractions) from prose→plumbing to monolith→package; same manifest/integrity contract.
- **Ralph autonomous mode** — hundreds of flowctl calls per autonomous run make startup overhead a real factor in loop wall-clock; parity-surface reduction directly attacks the drift-class bugs the fn-159 review loop kept finding.

## Decision Context

Why now: fn-159 produced the concrete evidence (multi-site status map, cross-path parity misses across 11 bot rounds, measured 250-400ms/invocation at 48,283 lines) and flowctl_tracker (fn-139-141) proved the extraction pattern end-to-end including distribution integrity. Why importable-launcher over alternatives: pyc caching is the entire win, zero-risk vs lazy-argparse (invasive) or a resident daemon (violates zero-dep simplicity). Why the review-terminal region first: newest code, highest parity-bug density in the field record, cleanest seam (fn-159 built it with explicit function boundaries), and it carries the multi-site map R3 unifies. Deliberately NOT captured as "split everything": the bitter-lesson principle says prove the mechanism cheaply and let evidence drive the next extraction.

Plan-time resolutions (2026-08-04):
- **flowctl.md:125 conflict resolved by scoping, not overturning:** the bytecode-cache rejection protects the manifest-authenticated static-help path (bootstrap), which is untouched; the main CLI path makes no authentication claim and adopts standard import+pyc. The paragraph is rewritten to say exactly this.
- **R3 is a deletion, not an abstraction:** the canonical helper already exists; the work is deleting two duplicate inline dicts and routing through it, plus documenting the two non-Python independents. Scoped small deliberately.
- **Unification (R3) lands BEFORE extraction (R2):** a pure in-file refactor verified independently, so the extraction then moves a single already-unified site.
- **Distribution contract (manifest/integrity/installers) is a separate task from the code move:** after the move the repo is green with manual propagation; the contract task then makes it enforceable. No broken intermediate state (tasks land on one spec branch, one PR).
- **Serial task chain (review round 1):** every task mutates flowctl.py, its `.flow/bin` copy, or manifest/propagation state — concurrent execution risks conflicting commits and stale propagated copies. Dependencies enforce .1 → .2 → .3 → .4 → .5; no parallel wave is offered.

## Early proof point
Task fn-166-flowctl-module-split-importable.2 validates the core perf claim (thin importing entry gives pyc caching → warm `show --json` >=2x faster). If measurement lands under 2x, stop and re-evaluate the entry shape (or document a floor with evidence) before treating R1 as satisfiable; the extraction tasks (R2/R3) are independent and may proceed.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Importable launcher, >=2x warm startup, flowctl.md:125 scoped rewrite | fn-166-flowctl-module-split-importable.2 | — |
| R2 | flowctl_review/ package + manifest + integrity test + propagation | fn-166-flowctl-module-split-importable.3, fn-166-flowctl-module-split-importable.4 | — |
| R3 | One Python verdict→status site + documented independents | fn-166-flowctl-module-split-importable.1 | — |
| R4 | Full gate green, hashes unchanged, zero surface diffs | every task (focused suites); final gate in fn-166-flowctl-module-split-importable.5 | — |
| R5 | Docs + CHANGELOG Unreleased | fn-166-flowctl-module-split-importable.5 (flowctl.md:125 rewrite lands with .2) | — |

## References

- `plugins/flow-next/scripts/flowctl:1-49` — bash launcher (FLOWCTL_ENTRY at :44-49); identical twin at `.flow/bin/flowctl` (fn-77 contract)
- `plugins/flow-next/scripts/flowctl.cmd` — Windows launcher twin
- `plugins/flow-next/scripts/flowctl_bootstrap.py:98-176` — deliberate no-cache exec (fn-139.5); `main()` call at :176
- `plugins/flow-next/docs/flowctl.md:125` — recorded bytecode-cache rejection (rewrite target)
- `plugins/flow-next/scripts/flowctl.py:46820` — main(); `:49735` — module entry guard
- `plugins/flow-next/scripts/flowctl.py:9546-11797` — review-terminal region (extraction target); prompt loaders :9425-9489 stay
- `plugins/flow-next/scripts/flowctl.py:9966-9976 / :10741-10745 / :40053-40057` — verdict→status sites (helper + 2 duplicates)
- `skills/flow-next-ralph-init/templates/ralph.sh:1278-1285`, `scripts/hooks/ralph-guard.py:128` — documented independents
- `plugins/flow-next/scripts/flowctl.py:1706-1709, :38576-38582` — flowctl_tracker lazy-import + soft-fail pattern
- `scripts/gen_tracker_manifest.py:1-71` — manifest generator (generalize); `scripts/lib/verify_tracker_manifest.py` — shared verifier
- `plugins/flow-next/tests/test_tracker_distribution.py` — integrity-suite template (:115-125 installer prose assertions; :197-201 MANIFEST.json string ban)
- `plugins/flow-next/skills/flow-next-setup/workflow.md:140-151` — copy-mode propagation steps
- Open-spec coordination: fn-120 (concurrent-edit caution), fn-160 + fn-158 (line anchors that will churn)

## Open questions (delegated to work; not blockers)

- Entry shape: new thin entry .py file (recommended — one quoting-safe implementation shared by bash + .cmd) vs inline `python3 -c` in both launchers. Decided in task .2. Either shape must propagate through the FULL launcher artifact graph (embedded constants, bin/ copies, installers, ralph-init, smoke fixtures — see Architecture refinements) AND must normalize `sys.argv[0]` to the sibling `flowctl.py` path before calling `main()` — argparse derives `prog` from argv[0], so an unnormalized entry changes every usage/error string (`usage: flowctl_entry.py …` / `usage: -c …`), a frozen-surface diff. The bootstrap already demonstrates this normalization at `flowctl_bootstrap.py:174`.
- (RESOLVED review round 1) Shared-helper access: explicit injection + facade re-export, never `import flowctl` from the package (double-load hazard under `python3 flowctl.py`). See Architecture refinements.
- Integrity-suite shape: tracker's BridgeInactiveByteParity has no analog (review machinery has no inactive mode) — absent-package soft-fail test replaces it. Confirmed in task .4.
