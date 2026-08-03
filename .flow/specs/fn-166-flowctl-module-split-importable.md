# fn-166-flowctl-module-split-importable flowctl module split: importable launcher, package extraction on the flowctl_tracker pattern

## Goal & Context
<!-- scope: business -->

`flowctl.py` is a 48,283-line single file. Measured 2026-08-04 (macOS, M-series): every invocation costs ~250-400ms of pure parse/exec before any work (`show --json` ≈ 290ms total; module import+exec alone ≈ 390ms cold; a trivial script ≈ 40ms) because Python does not bytecode-cache a file run as `python3 file.py` — only imported modules get `__pycache__`. A full spec run makes hundreds of flowctl calls, so aggregate startup overhead is roughly 1-3 minutes per run. [evidence: measured in-session]

The larger cost is parity and navigation, with fresh field evidence from fn-159 (PR #290): the verdict→status literal existed at FOUR sites and fixes repeatedly landed on one path while missing a sibling (RP vs in-process vs host; plan vs completion — multiple bot rounds were exactly such parity misses); plan-sync spent three passes re-anchoring line numbers as the file shifted by hundreds of lines per task; agents never read the file in full (~1.4M tokens) and navigate exclusively by Grep + offset Reads. A monolith makes drift-class bugs likelier and every review slower. [evidence: fn-159 review ledger, plan-sync breadcrumbs]

**The extraction pattern is already proven in this repo:** `flowctl_tracker/` (fn-139-141) moved the tracker bridge's repeatable machinery into a deterministic package with a generated MANIFEST integrity contract, deleting per-provider prose and cutting reached-path size ~70%. STRATEGY.md's Tracker-determinism track explicitly calls it "the template for future 'prose that grew into plumbing' extractions". This spec applies that template to flowctl itself.

## Architecture & Data Models
<!-- scope: technical -->

Two independent improvements, ordered by risk:

1. **Importable launcher (perf, near-zero risk):** the `.flow/bin/flowctl` bash launcher and the plugin entry invoke flowctl as a MODULE (`python3 -c 'import flowctl_main; flowctl_main.main()'` shape, or a 3-line entry script importing the real module) so `__pycache__` kicks in. Expected ~3-5x startup cut after first invocation per checkout. Must respect: the 49-line bash launcher contract (fn-77 — never overwrite `.flow/bin/flowctl` with Python), `.flow/bin/` dual-copy distribution, `--ignore-user-config`-style env isolation unaffected, `sys.path` containment (no repo-module shadowing), and stale-pyc safety across copy-mode upgrades (compare source mtime/hash or rely on Python's own invalidation).
2. **Package extraction (parity surface, staged):** split cohesive subsystems out of flowctl.py into a package next to `flowctl_tracker/` (working name `flowctl_review/` first), starting with the newest and most parity-sensitive region: the fn-159 review-terminal machinery (reservations, journal lifecycle, replay gate, supersession, epochs, digests, stall rules, ratchet rendering — the :9300-11500 region) plus its FOUR-site status map unified behind one function. Follow the flowctl_tracker contract exactly: deterministic package, generated MANIFEST via `scripts/gen_tracker_manifest.py` pattern (extend or sibling generator), `.flow/bin/` rsync propagation, `test_tracker_distribution`-style integrity test. Later stages (separate follow-up specs, NOT this one): rp/backend dispatch, receipts/findings, gates. This spec proves the pattern on one subsystem; it does not boil the file.

## Edge Cases & Constraints

- **Zero behavior change.** Byte-identical CLI surface, exit codes, markers, JSON shapes. The full suite is the contract; `test_flowctl_surface` must not change except import-path plumbing.
- **Zero-dep contract holds** (stdlib only; package lives in-repo, copied to `.flow/bin/`).
- **Prompt-text discipline:** extraction must not alter any embedded prompt constant — `test_prompt_text_pinned` + parity suites green with UNCHANGED hashes (a moved constant keeps its bytes).
- **Windows launcher + smoke matrix** (10 suites × 3 OS) must stay green; fn-120's concurrent-edit caution applies — coordinate if it activates.
- **Copy-mode upgrade path:** propagation gains package dirs — setup/installers already rsync `flowctl_tracker/`; extend the same mechanism, never a new one.
- **Line-anchor churn:** an extraction shifts every downstream doc/task anchor once — do it in one PR, run plan-sync after, and note it in the CHANGELOG entry.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** flowctl invocations import a bytecode-cacheable module; measured warm startup for `flowctl show <spec> --json` drops ≥2x vs the 2026-08-04 baseline (~290ms) on the same machine class, with the measurement method recorded in the spec/PR.
- **R2:** the fn-159 review-terminal machinery lives in a package (`flowctl_review/` or better name) with a generated manifest + distribution integrity test, propagated to `.flow/bin/` by the existing mechanism; `flowctl.py` shrinks by at least the extracted region's size.
- **R3:** the verdict→status mapping exists at exactly ONE site, consumed by all four former call sites (flowctl paths + ralph-guard keeps its own independent enum by design — document why).
- **R4:** full suite + ruff + smoke matrix green; `test_prompt_text_pinned` hashes unchanged; no CLI surface/schema/exit-code diffs.
- **R5:** docs updated (flowctl.md architecture note, agent_docs/local-dev.md propagation steps, CLAUDE.md final-gate propagation command extended if paths change) + CHANGELOG Unreleased entry, outcome-first.

## Boundaries
<!-- scope: business -->

- NOT a full decomposition of flowctl.py — one subsystem proves the pattern; further extractions are separate specs with their own evidence.
- NO behavior, schema, or CLI changes; no new dependencies; no async/daemon/server designs for startup (the import fix is sufficient and simple).
- ralph-guard.py stays a single-copy hook, untouched except R3's documented non-change.
- The 49-line bash launcher contract (fn-77) is preserved — the launcher may gain lines but stays a bash launcher.

## Strategy Alignment

Active tracks served:
- **Tracker determinism** — explicitly extends its own stated template ("prose that grew into plumbing" extractions) from prose→plumbing to monolith→package; same manifest/integrity contract.
- **Ralph autonomous mode** — hundreds of flowctl calls per autonomous run make startup overhead a real factor in loop wall-clock; parity-surface reduction directly attacks the drift-class bugs the fn-159 review loop kept finding.

## Decision Context

Why now: fn-159 produced the concrete evidence (four-site status map, cross-path parity misses across 11 bot rounds, measured 250-400ms/invocation at 48,283 lines) and flowctl_tracker (fn-139-141) proved the extraction pattern end-to-end including distribution integrity. Why importable-launcher over alternatives: pyc caching is the entire win, zero-risk vs lazy-argparse (invasive) or a resident daemon (violates zero-dep simplicity). Why the review-terminal region first: newest code, highest parity-bug density in the field record, cleanest seam (fn-159 built it with explicit function boundaries), and it carries the four-site map R3 unifies. Deliberately NOT captured as "split everything": the bitter-lesson principle says prove the mechanism cheaply and let evidence drive the next extraction.
