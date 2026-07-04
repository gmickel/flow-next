---
satisfies: [R1, R2, R3, R4, R5, R6, R8]
---

## Description
Run the eval-gated loop on the `audit` skill (memory garbage-collector: Keep/Update/Consolidate/Replace/Delete per entry). FINALIZE `optimization/audit/` (evals incl. lever scoring eval + answer-key fixture) → baseline (extended schema) → trim + ≥1 quality lever → ratchet → log → regen mirror → CHANGELOG line. Audit is FINDER-SHAPED → over-flag guard mandatory.

**Size:** M
**Files:** `optimization/audit/{README.md,evals.md,fixtures/*,results.tsv,changelog.md,baseline/*}`; `plugins/flow-next/skills/flow-next-audit/{SKILL.md,phases.md,workflow.md}` (mutations); `agent_docs/optimization-log.md`; `CHANGELOG.md`; `plugins/flow-next/codex/**`

## Approach
- Clone suite shape from `optimization/make-pr/` (fixture-shaped input suits audit). Extended `results.tsv` schema. **Finalize evals (incl. the Consolidate-vs-Delete scoring eval) BEFORE baseline (Major-B).**
- **Run permission + isolation (Major-1/C):** audit mutates memory (`memory mark-stale` etc.) — write-capable child confined to a throwaway `git worktree` (read-only w.r.t. the real repo) with a frozen COPY of a `.flow/memory/` snapshot + codebase state staged in; emit per-entry Keep/Update/Consolidate/Replace/Delete verdicts; score vs a hand-labeled answer key; discard worktree.
- **Interactive protocol (Major-D):** audit defaults interactive — run with `mode:autofix` (non-interactive, documented), recorded in the suite README; any residual prompt gets a canned fixture answer.
- **Frozen inputs:** real memory stores (SCRUB private data — memory holds real names/keys; freeze copies).
- **Accuracy evals (≥2-3):** classification correctness vs the answer key; **over-flag guard on a CLEAN corpus** (current/valid memory → zero false "stale/delete"); no silent deletion of a valid entry.
- **Quality lever (blind spot):** Consolidate-vs-Delete discrimination — scoring eval finalized above; try a LEAN discriminator; keep only if classification-accuracy rises.

## Investigation targets
Required:
- `agent_docs/optimizing-skills.md` — loop + accuracy guard + over-flag guard for finders
- `optimization/make-pr/` — fixture-shaped suite template
- `plugins/flow-next/skills/flow-next-audit/workflow.md` — prose being optimized (bulk, 863L)
Optional:
- `plugins/flow-next/docs/memory-schema.md` — the classification taxonomy audit applies

## Key context
- Finder-shaped: false-missing = 0 AND finding-rate ≈ baseline on the clean corpus — the over-flag guard is the ratchet's teeth here.
- Frozen grammars: audit's classification labels + any receipt — assert unchanged.
- Memory snapshots are the HIGHEST private-data risk in this spec — scrub hard, grep before commit.

## Acceptance
- [ ] `optimization/audit/` committed with the FINAL eval set (≥2-3 `[ACCURACY]` incl. answer-key classification + lever scoring eval) + frozen inputs (R1, Major-B)
- [ ] Fixtures scrubbed — scoped privacy grep clean over `optimization/audit/` (highest-risk: real memory names/keys) (R1)
- [ ] Baseline row 0 (extended schema) under the FINAL eval set before any mutation; write-capable child in a worktree against a COPIED memory snapshot; `mode:autofix` (no hang) (R2, Major-B/C/D)
- [ ] ≥1 trim + ≥1 quality-lever experiment; kept rows accuracy held/raised AND tokens↓/quality↑, discards logged (R3, R4)
- [ ] Over-flag guard on a CLEAN corpus: false-missing = 0, finding-rate ≈ baseline (R4)
- [ ] Frozen classification labels unchanged; no relocated consuming-phase tables (R5)
- [ ] `optimization-log.md` row per experiment (R6)
- [ ] `sync-codex.sh` regenerated + committed; `pytest` + `audit_smoke_test.sh` + `smoke_test.sh` green; `CHANGELOG` `## Unreleased`; no bump (R8)

## Done summary
New eval suite for `/flow-next:audit` (the memory garbage-collector). This one earned its keep the hard way — the fable review caught a real methodology flaw.

**What happened:** built 3 synthetic memory stores (M1 mixed / M2 clean over-flag guard / M3 stress) with frozen codebase context + hidden answer keys; run-trick = `mode:autofix` EMISSION at sonnet. First baseline scored a clean 4/4 — but the fable review flagged it **NEEDS_WORK: SPOON-FED**. My "frozen contexts" stated the classification CONCLUSION in the taxonomy's own vocabulary ("problem domain no longer exists" = Delete's definition), so classification had degenerated to "don't contradict your own input."

**Fix (fixtures rewritten):** every frozen context restated as RAW investigation FACTS (grep hits, git-log, symbol presence, code snippets) with zero verdict adjectives — the run must DERIVE each verdict. Also: added M3-b to E1's scoring (was scope-header-only), tightened E1 to 6/6, fixed accept-sets for genuine taxonomy tensions.

**Corrected baseline = 4/4, EARNED:** E1 6/6 (audit inferred the `_parse_frontmatter`→`_read_yaml_header` rename from grep facts alone; correctly mark-staled the ambiguous cases), E2 over-flag 0 false positives incl. the HARD M3-a (looks-stale-but-valid: 8mo old + 'old ORM' aside, but audit read the raw fact — N+1 code present+unfixed — over the surface age), E3 delete-discipline, E4 consolidate BOTH directions (M1 dup→Consolidate, M3 distinct→Keep-both).

**Answer-key correction (mine to fix):** I keyed M1-c as Delete; the git-log fact says "superseded by flow-next-tui" → a successor exists → problem domain may persist → Delete unsupported → **mark-stale** is correct. audit classified it mark-stale in both runs — correctly. Chased a Delete-vs-mark-stale lever to "fix" it, confirmed audit was already right, **reverted** (prose byte-identical to baseline).

**Two durable outputs:** (1) a classification + over-flag + consolidate-restraint harness with facts-not-conclusions fixtures; (2) a **standing process lesson** — fable-review the eval DESIGN before the expensive baseline runs (Gordon's call), now saved to memory and applied from fn-84.6 on. **Fixture gap noted:** no clean-Delete case remains — add a no-successor Delete fixture next iteration. No prose change; no version bump.
## Evidence
- Commits:
- Tests: no prose change (Delete-vs-mark-stale lever reverted; phases.md byte-identical to baseline) — audit test surface unaffected, fable review of eval DESIGN: NEEDS_WORK (spoon-fed fixtures) -> fixtures rewritten as raw facts; corrected baseline 4/4 earned, 6 audit runs total (spoon-fed baseline x3, facts-only baseline x3, lever x2) at sonnet mode:autofix emission
- PRs: