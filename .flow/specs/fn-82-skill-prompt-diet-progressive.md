# fn-82 Skill prompt diet: progressive-disclosure gating, intra-skill dedupe, archaeology sweep

## Overview

Hot-path skills carry always-loaded prompt weight that never influences the default run: default-OFF machinery inlined in always-read files, duplicated instruction blocks across always-loaded file pairs, and dev-time scaffolding shipped as runtime text. Fleet survey (2026-07-02) + post-fn-81 anchor verification measured the always-loaded cost per skill (chars/4): make-pr ~46.6k (workflow 36.6k + phases 6.1k + SKILL 3.8k), capture ~26.4k, tracker-sync ~24k, audit ~19.8k, pilot ~17.4k, impl-review ~16.1k, qa ~15.9k, interview ~15.9k, work ~11.3k.

Cut that weight with zero quality loss per `agent_docs/optimizing-skills.md`: archaeology first (safe), structural gating second (proven gate patterns), eval-guarded dedupe last (ratchet). Anthropic's skill docs confirm the model: referenced files cost zero until Read; "mutually exclusive contexts → separate paths". Builds on fn-81 (dep recorded; branch stacks on fn-81).

## Quick commands

```bash
bash scripts/sync-codex.sh                    # regen mirror + parity guards (new references/*.md under skill dirs auto-mirror — wholesale dir copy, sync-codex.sh:133-136)
(cd "$(mktemp -d)" && bash /Users/gordon/work/flow-next/plugins/flow-next/scripts/smoke_test.sh)
python3 -m pytest plugins/flow-next/tests/ -q
```

## Approach — three mutation classes + binding design rules

**Design rules (from verified research + gap analysis — binding on every task):**
- **One level deep:** every gated reference links directly from the always-loaded file that gates it (nested refs trigger partial reads).
- **TOC rule:** any new/moved reference file >100 lines starts with a short table of contents.
- **Forcing sentinel — exact gate skeleton (binding for every new gate):**
  ```bash
  ACTIVE=0
  # NO pipelines in the probe — a failed producer masked by a healthy consumer
  # (flowctl … | jq …) fails CLOSED. Capture first, rc-checked; parse separately.
  RAW="$(<probe-cmd> 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
  if [ "$ACTIVE" = "0" ]; then
    VAL="$(printf '%s' "$RAW" | jq -r '<path>' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
    [ "<active-condition on $VAL>" ] && ACTIVE=1
  fi
  if [ "$ACTIVE" = "1" ]; then
    echo "GATE ACTIVE — STOP. Read <skill>/references/<file>.md#<section> before continuing."
  fi   # default branch: bare no-op — NO link, NO read path
  ```
  The always-loaded prose immediately after the gate repeats the imperative ("When the sentinel prints, STOP and Read the named reference before any further step"). The fn-82.5 grep-gate verifies, per gate: sentinel text present, fail-open `|| ACTIVE=1` present on BOTH the probe and the parse, NO unguarded `| jq` pipeline inside any gate block, reference linked directly (one level), and the default branch contains no Read of the reference.
- **Dedupe rule:** merge duplicated *explanatory/context* blocks to one site; KEEP short imperative rules repeated at action sites (verbatim repetition is load-bearing — externally corroborated); when keeping one copy, keep it VERBATIM, never paraphrase.
- **Strip/keep allowlist (Class 1):** STRIP `fn-N`/`fn-N.M` provenance parentheticals only where surrounding prose carries the rule; when an fn-tag is the sole carrier of a rule reference, rewrite the rule into prose first, then strip. KEEP: `R\d+` requirement ids (status who-wins R1/R2/R6/R7, work R16, etc.), `S-[A-Z]` fixture oracles in status-sync.md (live host-exercisable tests, NOT scaffolding), and version numbers.
- **Proximity rule (hard, unchanged):** never relocate a routing/taxonomy/guardrail table out of the phase that consumes it.

**Class 1 — archaeology strips (safe; no behavior):**
- tracker-sync: ~93 fn-NN occurrences in always-loaded `SKILL.md`+`steps.md` (allowlist above); adapter spike harnesses `linear-ladder.md:191-269`, `github.md:546-642`, `gitlab.md:862-931` → move to `agent_docs/tracker-sync-spikes.md` (dev archive OUTSIDE the plugin/skill tree — never shipped or mirrored); runtime breadcrumb reads "Round-trip spike: dev archive at agent_docs/tracker-sync-spikes.md — not runtime material" (NOTE: on-demand refs — dead-text cleanup, not always-loaded savings; jira.md has NO spike — no action). Do NOT touch status-sync.md S-A…S-G oracles.
- qa: fn-53 scaffolding — ownership table `workflow.md:9-15`, OWNER comments `:268,332,374,441,583`, skeleton/proof prose `:335-348`, `SKILL.md:126`; drop the transient proof-receipt (`workflow.md:352`) now that §6.3 qa_verdict always runs.
- map `SKILL.md:12,:80` ("lands in fn-50.x" — shipped → present tense); memory-migrate `phases.md:3` flowctl.py line numbers → constant/function names, "Task 2" prose `SKILL.md:14,:82`, `workflow.md:35`; audit flowctl.py line refs `phases.md:172`, `workflow.md:561`.

**Class 2 — progressive-disclosure gating (copy the proven patterns: pilot `workflow.md:58-105` backlog gate; work `phases.md:29-61` delegation gate):**
- work: tracker-touchpoint PROSE (SKILL.md:170-197 overview + the three touchpoint blocks phases.md:207-222, :299-314, and 3g's block) → `references/tracker-touchpoints.md` behind the existing bridge predicate + forcing sentinel. **KEEP INLINE:** Phase 5's end-of-run `sync check` + retro-fire mechanics + the MANDATORY 4-state `Tracker sync:` summary template (phases.md:500-550) — it is the safety net for a skipped gated Read and a shared contract (docs/tracker-sync.md:119); also keep SKILL.md's R16 handle-recognition + unlink prose (general input grammar, not bridge-gated). Dedupe the delegation value-check duplicated across SKILL.md:199-212 ≡ phases.md:29-61 (define once, reference).
- pilot: move ONLY the QA-freshness probe (`workflow.md:340-375`) → `references/qa-stage.md` behind the existing `QA_STAGE_ENABLED` gate (:317-321) + forcing sentinel; the probe's output contract (QA_FRESH determination) is consumed by inline classification rows (:334, :392) — the reference states what to compute and the inline flow keeps the consumption. Do NOT move the interleaved branch-matrix/dispatch tables (:415-439) or Phase 5/6 qa routing (:500-541, :621) — qa logic is threaded through core phases. Backlog-mode prose dedupe: `workflow.md:155-296`, `:565-602` restate select/triage/ask that `backlog-mode.md:260-266`, `:324-337` owns — keep enforcing bash + invariants inline, delegate prose; verify no stranded bash reads a var the moved prose defined.

**Class 3 — intra-skill dedupe:**
- impl-review: SKILL.md still fully inlines Phase 0 (RP_ELIGIBLE `SKILL.md:29-40`, `review-backend` call `:71` + branches) ≡ `workflow-common.md:9-91` — SKILL.md keeps intent + arg parse + the backend-at-a-glance summary, delegates the executable Phase 0; kills the double `review-backend` round-trip. spec-completion-review: same shape (`workflow-common.md:13-51`), same fix.
- interview: inline template-cascade bash walker (`SKILL.md:633-680`) → move the FULL walker mechanics VERBATIM (case-insensitive-FS probe, SPEC.md/spec.md both-exist warning, plugin-root fallback) to one dedicated shared location (new reference or expanded template-header comment) BEFORE deleting the inline copy; repoint BOTH cross-refs (plan `steps.md:268`, interview). APFS/Windows case handling and the 4-tier fallback must survive byte-for-byte. Aux-section block duplicated across write branches (`SKILL.md:377` ≡ `:394`, restated `:403`, `:428`) → define once.
- audit: Replace/supersede/mark-stale flows duplicated (workflow.md ~:303-349 region ≡ phases.md `:135` + tables) → phases.md authoritative, workflow.md delegates.
- prospect: python-picker verbatim 3× (`workflow.md:67,:503,:762` — fn-77 blocks) → define once, reference per phase; stale "printed to stdout / lands later" scaffolding (`workflow.md:357` + `:180,:203`) → drop dump or gate behind debug, present-tense prose.

**Class 4 — EVAL-GUARDED pair (ratchet; baseline BEFORE mutating, recorded in results.tsv):**
- make-pr: **FOLD, do not gate** — phases.md content is needed every run, so gating is net-loss + skip-risk. Verify authority direction first (workflow.md inline `### Done when` at :272,:352,:607,:1044,:1228,:1599,:1864 vs phases.md map — fold toward the richer copy, expected workflow.md), reduce phases.md to a thin stub/index (deletion FORBIDDEN — links may point at it) + remove it from SKILL.md:16's force-load list; sweep skill/doc/test references to phases.md and update. Procedure: run the make-pr body eval (`optimization/make-pr/`, agent-driven per optimizing-skills.md §"How to run") on the pre-change branch, record baseline row; fold; re-run; keep only at 5/5-held; revert on any drop.
- capture: table dedupe across always-loaded pair — biz-routing `phases.md:101-122` vs consuming step `workflow.md:298,:305` (§2.6 Decision-Context routing = the exact proximity that regressed before). Dedupe ONLY copies far from their consuming step; run `optimization/capture/` suite baseline-first; revert on regression.

**Docs (R10):** optimizing-skills.md target map corrected (no uncapped free-form agents remain — github/practice/docs/spec-scout + quality-auditor already budgeted; prime scouts fixed-size; remaining prizes = always-loaded skill weight); optimization-log.md rows for kept/discarded/eval-guarded results; optional adding-skills.md "gated references/*.md" heuristic (third landed instance).

## Boundaries / non-goals

- Runtime emission/round-trip fixes were fn-81 (merged separately, PR #191) — not here.
- No prompt REWRITES — move/dedupe/delete only; wording changes to live instructions are out of scope.
- Agent files (`agents/*.md`) out of scope (already budgeted).
- land, drive, resolve-pr, strategy, sync, rp-explorer, worktree-kit, flow-next(core), ralph-init, deps, plan, make-pr-beyond-phases-fold: out of scope. setup's triplicated overwrite-consent ceremony: explicitly OUT of scope this pass (cold-path, ~300 tok; revisit only if a later pass targets setup).
- status-sync.md S-fixtures, work Phase-5 sync-check + summary template, pilot Phase 5/6 qa routing, R16 handle-recognition: explicitly NOT moved.
- No version bump (CHANGELOG under existing `## Unreleased`); docs-site changes only at batched release.

## Strategy Alignment

Active tracks served by this plan:
- **Ralph autonomous mode** — work (-~1.6-2k/task), pilot (-~0.5k/tick), impl-review (-~1.3k/review) always-loaded cuts multiply across every autonomous tick.
- **Cross-platform parity** — new gated references auto-mirror (sync-codex wholesale skill-dir copy verified); Agent Skills 3-level loading is now a cross-platform standard, so savings replicate on Codex/Droid.
- **Self-improving through normal work** — target-map corrections + eval rows land in agent_docs per the append-a-row convention.

## Decision context

- make-pr folds instead of gates: its checklists are consumed every run — gating adds probe cost + skip risk for zero default-path benefit (gap analysis P4).
- pilot moves only the freshness probe: qa logic is interleaved with core Phase 3/4 tables and threaded through Phases 5/6 — a wholesale 340-438 move would fragment shared tables and strand references (gap analysis P2).
- work keeps Phase 5 inline: the end-of-run sync-check is the independent safety net that catches a skipped gated Read, and the 4-state summary template is a shared contract required on EVERY run including bridge-inactive (gap analysis P1).
- Forcing sentinel chosen over prose pointers: research shows conditional loading fails via ignorable "read X if Y" prose; a gate whose stdout is an imperative the agent must act on closes the loop.
- Strip/keep allowlist formalized after the gap analysis flagged rule-carrying fn-tags (fn-66 merge-evidence, fn-52.10 resolver) and live S-fixtures as over-strip casualties.
- Eval-guarded items get explicit baseline-first procedure because a ratchet without a recorded baseline can't prove no-regression.

## Acceptance Criteria

- **R1:** work's three tracker-touchpoint blocks + SKILL.md bridge overview live in `references/tracker-touchpoints.md` (TOC if >100 lines) behind the existing bridge predicate with a forcing sentinel; default (bridge-inactive) run never loads it; Phase 5 sync-check + retro-fire + the 4-state `Tracker sync:` summary template remain inline and byte-equivalent in behavior; R16/unlink prose stays in SKILL.md; delegation value-check defined once.
- **R2:** pilot's QA-freshness probe lives in `references/qa-stage.md` behind `QA_STAGE_ENABLED` with a forcing sentinel; default tick never loads it; QA_FRESH producer/consumer contract intact (inline rows :334/:392 unchanged); Phase 5/6 qa routing untouched; backlog select/triage/ask prose exists in exactly one file with enforcing bash still inline and no stranded var reads.
- **R3:** impl-review and spec-completion-review resolve the backend in exactly one place (workflow-common Phase 0); `flowctl review-backend` invoked once per run; SKILL.md keeps intent/arg-parse/at-a-glance only.
- **R4:** make-pr phases.md folded (not gated) toward the verified richer copy; SKILL.md no longer force-loads it; make-pr body eval baseline recorded BEFORE the fold and held after (results.tsv rows); any regression reverts.
- **R5:** tracker-sync always-loaded files carry no strip-eligible fn-NN citations (allowlist applied: R-IDs, S-fixtures, rule-carrying refs rewritten to prose first); adapter spike harnesses moved out of runtime refs (linear/github/gitlab; jira n/a); status-sync oracles untouched.
- **R6:** qa fn-53 scaffolding + proof-receipt removed; map/memory-migrate/audit archaeology per Class 1 list; no flowctl.py absolute line numbers remain in any canonical skill markdown.
- **R7:** interview cascade is a single cross-linked description with BOTH prior cross-refs repointed; aux-section block defined once; audit Replace/supersede/mark-stale single authoritative copy; prospect python-picker defined once + stale scaffolding dropped.
- **R8:** capture dedupe (if kept) passes the capture eval suite at recorded baseline; the SURVIVING copy of any deduped table sits in `workflow.md` §2.6 beside the drafting step that consumes it — if it would not, revert/skip and log considered-and-skipped; regression reverts (log the discard row).
- **R9:** every new gate fails OPEN on probe error; every gated reference is linked one level deep from its always-loaded file; grep-gate proves each gated file is reachable from its gate AND each gate emits the forcing sentinel.
- **R10:** optimizing-skills.md target map + optimization-log.md updated with the survey corrections and this spec's kept/discarded rows.
- **R11:** tasks 1-4 canonical-only; final task regenerates the mirror ONCE (×2 idempotent + parity guards), runs smoke (non-repo cwd) + pytest green.
- **R12:** measured before/after always-loaded chars/4 per touched skill recorded in the PR body (method: `wc -c` over the always-loaded file set, pre/post, reproducible).
- **R13:** CHANGELOG sibling entry under existing `## Unreleased`; no version bump.

## Early proof point

Task fn-82.1 (work + pilot gating) validates the gated-reference pattern end-to-end — forcing sentinel, fail-open, mirror auto-copy, default-path zero-load. If the gate can't reliably force the Read (or mirror parity breaks on new reference files), re-evaluate Class 2 before the dedupe classes proceed.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | work gating + Phase-5 stays inline | fn-82.1 | — |
| R2  | pilot qa-stage probe + backlog dedupe | fn-82.1 | — |
| R3  | review skills single Phase 0 | fn-82.3 | — |
| R4  | make-pr fold, eval-guarded | fn-82.4 | — |
| R5  | tracker-sync strips (allowlist) | fn-82.2 | — |
| R6  | qa/map/memory-migrate/audit archaeology | fn-82.2 (qa/map/mm), fn-82.3 (audit line refs ride with audit dedupe) | — |
| R7  | interview/audit/prospect dedupe | fn-82.3 | — |
| R8  | capture dedupe, eval-guarded | fn-82.4 | — |
| R9  | gate contract (sentinel, fail-open, one-level) | fn-82.1, gate-check in fn-82.5 | — |
| R10 | agent_docs updates | fn-82.5 | — |
| R11 | mirror once + full gate | fn-82.5 | — |
| R12 | token-count table in PR body | fn-82.5 | — |
| R13 | CHANGELOG Unreleased | fn-82.5 | — |
