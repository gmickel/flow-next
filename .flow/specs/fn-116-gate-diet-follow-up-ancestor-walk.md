# Gate diet follow-up: ancestor-walk receipt honor + suite-output capture fix

## Goal & Context

The fn-103 run was trace-measured against the fn-89 baseline (post-mortem 2026-07-19, memory `delegation-brief-eval-2026-07-19` addendum). The 2.17.0 tracker dispatch fully delivered (~190k tokens off-host, 0s serial cost, 3 context items per dispatch). The 2.18.0 gate diet delivered NOTHING: 7 full suite runs for 2 tasks, zero receipts honored, zero docs-only tiers - gate share unchanged at ~50.6% of wall vs the pre-registered target of <=25%. Three verified causes, two of them fixable mechanically:

1. **Receipts are structurally orphaned (the big one).** `gate check` honors only an EXACT HEAD match, but the work loop's own done-flow always commits `.flow` state 27-45s after writing the receipt - so every receipt dies before any consumer can check it. Live proof: receipt `e76025d5` (written 14:22:42) missed by worker .2's baseline check at 14:27:49 (HEAD had moved to `1c157256`; the diff between them was 3 files, ALL `.flow/memory|specs|tasks/**` - exactly the paths the check's own ignore-set deems non-executable). Cost this run: ~245s serial + ~520s compute + a worker turn-split.
2. **Suite-output capture defect (~1,119s = 15% of the whole pipeline).** Both workers piped the suite through `tail -N`, got trailing test noise instead of the `Ran/OK` summary line, and RE-RAN THE ENTIRE SUITE just to observe greenness (runs 2 and 7 of 7 were pure duplicates). No gate policy addresses this - it is a worker.md prose defect.
3. **Force-full floor (accepted, documented, NOT changed here).** Run 6 classified FULL because the diff touched skill prose + its codex mirror - which is correct conservatism (prose-contract tests pin skill wording). Even with fixes 1-2, the floor is ~4 legitimate runs/2 tasks (~35% share); the bigger lever below that is making runs cheaper (parallelization), which is out of scope here and noted as a candidate investigation.

## Acceptance criteria

- **R1: Ancestor-walk receipt honor.** `gate check` honors a receipt when ALL current conditions hold EXCEPT exact HEAD match, provided: receipt `head_sha` is an ancestor of HEAD (`git merge-base --is-ancestor`), AND `git diff --name-only <receipt_sha>..HEAD` (NUL-safe, --no-renames) contains ONLY ignore-set paths (`.flow/**` minus `.flow/bin/**` minus `.flow/config.json` - the SAME predicate as the worktree cleanliness check, one shared helper, no second list), AND the worktree cleanliness / command fingerprint / 0<=age<=24h / schema conditions are unchanged. Any non-ignore-set path in the walk, non-ancestor receipt, or git failure -> exit 1 (fail closed); tooling errors 2+. Bounded: if the walk spans > 50 commits, exit 1 (fail closed - receipts are same-session artifacts, a long walk means something else is going on).
- **R2: Capture fix.** worker.md's suite-run prose (Baseline check + Verify site) captures greenness from the COMMAND EXIT CODE (`; echo "suite_rc=$?"`) with output to a file (`> log 2>&1`), reading the summary from the file - NEVER re-running a suite to observe its result. One sentence stating the rule: a green observation is the exit code, not a scraped line; re-running a suite for observation is forbidden.
- **R3: Receipt-after-state-commit ordering.** The done-flow writes the gate receipt AFTER the `.flow` state commit where feasible (worker.md ordering swap), so the receipt's head_sha is the branch tip a successor actually sees - making R1's walk the fallback, not the primary path. Where the ordering cannot be swapped (host Phase 4), R1 covers it.
- **R4: Tests.** Hermetic gate tests: ancestor-walk honor (receipt at sha A, .flow-only commit to B -> exit 0); non-.flow commit in the walk -> exit 1; non-ancestor receipt -> exit 1; walk-bound exceeded -> exit 1; renamed/moved path in walk fails closed. Existing exact-match tests unchanged.
- **R5: Measured claim discipline.** CHANGELOG + docs state the honest status: the diet's receipt path was structurally dead in 2.18.0, fixed here; the ~35% floor and the parallelization lever are recorded in the post-mortem decision context, not promised.
- **R6: Cross-platform.** Dual-copy flowctl, mirror x2 idempotent, no version bump (batched).

## Key files / interfaces

- `plugins/flow-next/scripts/flowctl.py` + `.flow/bin/flowctl.py` (`cmd_gate_check` ~L27667, `_gate_ignored_worktree_path` ~L27482 - extract the shared path predicate)
- `plugins/flow-next/agents/worker.md` (suite-run capture prose, receipt/state-commit ordering)
- `plugins/flow-next/tests/test_gate_receipt.py` (ancestor-walk cases)
- `CHANGELOG.md`, `plugins/flow-next/docs/flowctl.md` (gate section: ancestor-walk clause)

## Decision Context

- Post-mortem evidence (fn-103 run): 7 suite runs / 2 tasks; 3 receipts written, 0 honored, all orphaned by .flow state commits 27-45s later; duplicate runs 2+7 = ~1,119s pure waste from tail-scraping; tracker dispatch delivered exactly as designed (~190k tokens off-host, 0s serial).
- The ancestor-walk predicate is hash + path membership - mechanical, doctrine-clean (STRATEGY.md design principles: flowctl burden of proof met; no judgment).
- Force-full conservatism for skill prose is KEPT (prose-contract tests pin wording; loosening it trends toward semantic judgment).
- Suite parallelization is the next lever below the ~35% floor - separate investigation, not this spec.
- Delegation A/B from the same run: path-handoff composition 244s net vs 519s composed-brief (2.1x faster), prompt 13x smaller - fn-103 confirmed in production.
