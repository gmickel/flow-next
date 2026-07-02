# fn-82 Skill prompt diet: progressive-disclosure gating, intra-skill dedupe, archaeology sweep

## Goal & Context

Hot-path skills carry always-loaded prompt weight that never influences the default run: default-OFF feature machinery inlined in always-read files, the same instruction blocks duplicated across two files that both load every run, dev-time scaffolding (spike harnesses, `fn-NN` task provenance, "lands in Task 2" prose) shipped as live runtime text. A 4-agent fleet survey (2026-07-02) measured per-invocation always-loaded cost per skill; the multiplied cost concentrates in the per-task/per-tick loops (work, pilot, impl-review) and the two heaviest skills (make-pr ~46k, tracker-sync ~24k baseline + adapters).

Goal: cut always-loaded tokens with zero quality loss, following `agent_docs/optimizing-skills.md` — archaeology-first (safe strips), structural gating second (move default-OFF machinery behind cheap gates, copying the proven `backlog-mode.md` / `codex-delegation.md` pattern), eval-guarded trims ONLY where a skill is accuracy-critical (capture regressed once before on exactly this — proximity is load-bearing, see optimization-log.md).

## Architecture & Data Models

Three mutation classes, in rising risk order:

**Class 1 — archaeology sweep (safe, no behavior):**
- tracker-sync: dev-time round-trip "spike" harnesses inside runtime adapter refs (`linear-ladder.md:194-260`, `github.md:554-648`, `gitlab.md:904-917`, jira analog) → move to a non-runtime dev doc; strip fn-NN task-id citations from always-loaded `SKILL.md`+`steps.md` (~93 refs; KEEP rule-keyed R-IDs like the status who-wins ids)
- qa: fn-53 build scaffolding — ownership table `workflow.md:7-17`, `<!-- OWNER: fn-53.x -->` comments, skeleton/proof-point prose (`workflow.md:126`, `:268`, `:332-339`, `:374`, `:441`, `:583`; `SKILL.md:126`); evaluate dropping the transient proof-receipt (`workflow.md:352-358`) now that the §6.3 qa_verdict receipt always runs
- map: "lands in fn-50.2-.5" forward refs for shipped features (`SKILL.md:12`, `:80`) → present tense
- memory-migrate: flowctl.py absolute line-number citations that rot (`phases.md:3`) → function/constant names only; "Task 2 ships this" prose (`SKILL.md:14`, `workflow.md:35`)
- audit: flowctl.py line-number refs (`workflow.md:561`, `phases.md:172`, `:246`)
- prospect: stale "Phase 2 scaffolding lands later" + stdout snapshot dump (`workflow.md:357-378`); interview/plan/audit fn-NN parentheticals (low value, bulk-safe)

**Class 2 — progressive-disclosure gating (structural move, behavior preserved):**
- work: tracker touchpoints are always-loaded but default-OFF (`SKILL.md:168-197`; `phases.md:205-222`, `:297-314`, `:420-442`, `:500-550`; ~1.6k tok × every task) → `references/tracker-touchpoints.md` loaded only when the bridge is active; dedupe the delegation value-check duplicated verbatim (`SKILL.md:224-242` ≡ `phases.md:36-55`)
- pilot: QA-freshness probe always-loaded but `pipeline.qa` default-off (`workflow.md:340-375`, ~0.7k × every tick) → `references/qa-stage.md` gated on QA_STAGE_ENABLED; backlog-mode duplication — workflow.md restates select/triage/ask that `backlog-mode.md` owns (`workflow.md:155-296`, `:565-602` ≡ `backlog-mode.md:260-266`, `:324-337`) → keep enforcing bash inline, delegate prose
- make-pr: `phases.md` (~6.1k) force-loaded yet duplicates the inline per-phase "### Done when" blocks (`phases.md:3` vs `workflow.md:272/352/607/1044/1589`) → load-on-demand or fold. NOTE: make-pr is accuracy-critical (optimization-log: mostly load-bearing) — this is the one Class-2 item that needs the eval guard (existing body-eval, 5/5 held standard).

**Class 3 — intra-skill dedupe of always-loaded pairs (needs care; adjacent-to-consumer copies stay):**
- impl-review: SKILL.md and workflow-common.md both fully spell out backend detection + RP_ELIGIBLE + trivial-diff triage (`SKILL.md:26-99`, `:275-309` ≡ `workflow-common.md:9-74`, `:93-165`), and both invoke `flowctl review-backend` (double round-trip) → SKILL.md keeps intent + arg parse, delegates executable Phase 0 to workflow-common
- spec-completion-review: same shape (`SKILL.md:44-97` ≡ `workflow-common.md:14-52`) → same fix
- interview: 39-line inline template-cascade bash walker (`SKILL.md:644-682`; cascade also described in plan `steps.md:268` and the template file itself) → 2-line cross-link to one shared reference; auxiliary-section block duplicated across the two write branches (`:690-708` ≡ `:741-759`) → define once
- audit: Replace/supersession/mark-stale flows spelled out in both always-loaded files (`workflow.md:551-576`, `:602-606` ≡ `phases.md:164-185`, `:264-271`, `:318-322`) → phases.md authoritative, workflow.md delegates
- prospect: python-picker block verbatim 3× (`workflow.md:66-71`, `:502-507`, `:761-766`) → define once
- setup (cold-path, lowest pri): overwrite-consent ceremony triplicated (`workflow.md:204-234`, `:236-248`, `:626-640`)
- capture: source-tag/biz-routing/forbidden tables duplicated across always-loaded pair (`phases.md:92-124`, `:190-203` ≡ `workflow.md:281-286`, `:341-358`; `SKILL.md:112-122`) — **EVAL-GUARDED ONLY**: a previous capture DRY trim regressed Decision Context routing and was reverted (proximity is load-bearing). Dedupe only copies far from their consuming step, run the capture eval suite before keeping.

**Docs update:** refresh `agent_docs/optimizing-skills.md` target map + `optimization-log.md` with the survey corrections: no uncapped free-form agents remain (github/practice/docs/spec-scout + quality-auditor already carry hard budgets); prime template scouts are fixed-size (budget headers optional, low yield); the remaining prizes are always-loaded skill weight, not agent output.

## API Contracts

Skill-markdown-only. No flowctl changes, no new flags. New `references/*.md` files follow existing progressive-disclosure conventions (cheap bash gate before Read, one-line pointer on the default path). Machine-readable markers, receipts, verdict grammar untouched. `sync-codex.sh` regenerates the mirror; tool-name rewrites unchanged.

## Edge Cases & Constraints

- **Proximity rule (hard):** never relocate a routing/taxonomy/guardrail table out of the phase that consumes it, even when a copy exists elsewhere — dedupe keeps the copy NEXT TO the consumer and removes the far one.
- Gating must fail open to correctness: if the gate probe errors, load the reference (never silently skip active-bridge/QA behavior).
- R-ID keyed rules in tracker-sync (status who-wins, merge-evidence) keep their R-IDs — only task-id (`fn-NN.M`) provenance is stripped.
- make-pr + capture mutations require their eval suites (body-eval / capture suite) per methodology; all other classes validated by smoke tests + mirror byte-parity + a grep-gate that gated content is reachable from its gate.
- Estimated wins (survey): work ~1.6-2k/task, make-pr ~6k/run, impl-review ~1.3k/review, pilot ~0.7k/tick, tracker-sync ~3-5k/run, interview ~0.8k/run, audit ~0.6k/run.

## Acceptance Criteria

- **R1:** work's tracker touchpoints live in a gated reference; default (bridge-inactive) task run never loads them; active-bridge behavior byte-equivalent.
- **R2:** pilot default tick (pipeline.qa off) no longer loads the QA-freshness probe; QA-on behavior unchanged; backlog-mode prose exists in exactly one file.
- **R3:** impl-review + spec-completion-review resolve the backend in exactly one place; `flowctl review-backend` invoked once per run.
- **R4:** make-pr no longer pays for duplicated Done-when checklists (phases.md gated or folded); body eval holds 5/5.
- **R5:** tracker-sync adapter refs contain no spike/acceptance harnesses; always-loaded files carry no fn-NN task-id citations (rule R-IDs retained).
- **R6:** qa/map/memory-migrate/prospect/audit archaeology stripped per the Class-1 list; no flowctl.py absolute line numbers remain in any skill markdown.
- **R7:** interview template cascade is a cross-link (single source); aux-section block defined once.
- **R8:** audit Replace/supersede/mark-stale flows have a single authoritative copy.
- **R9:** capture dedupe (if kept) passes the capture eval suite at baseline score; any regression reverts (ratchet).
- **R10:** optimizing-skills.md target map + optimization-log.md updated with survey findings/corrections.
- **R11:** sync-codex mirror regenerated + byte-parity; `bash smoke_test.sh` green; CHANGELOG under `## Unreleased`; no version bump.
- **R12:** measured before/after always-loaded token counts recorded per touched skill (chars/4) in the PR body.

## Boundaries

- Runtime emission/round-trip fixes are fn-81, not here.
- No prompt REWRITES — this spec moves/dedupes/deletes dead weight only; wording changes to live instructions are out of scope (those need dedicated eval loops).
- Agent files (`agents/*.md`) out of scope (already budgeted; survey confirmed no uncapped free-form output remains).
- land, drive, resolve-pr, strategy, sync, rp-explorer, worktree-kit, flow-next(core), ralph-init: surveyed clean or deliberately-verbose — out of scope.
- No version bump; docs-site changes only at batched release.

## Decision Context

Ranked by multiplied impact (per-run saving × invocation frequency): per-task/per-tick loops first (work, pilot, impl-review), heaviest skills second (make-pr, tracker-sync), interactive skills third. Three-class structure keeps risk legible: Class 1 is provably dead text; Class 2 copies the already-proven gated-reference pattern (backlog-mode.md, codex-delegation.md — both shipped and battle-tested); Class 3 is where the capture precedent bit us, so it carries the eval-guard requirement explicitly rather than trusting "looks safe". Survey source: 4 parallel Explore agents, 2026-07-02, all 28 skills; skeptical notes preserved (land's re-probe and prospect's 4-prompt snapshot reuse are load-bearing — flagged so nobody "optimizes" them into bugs).
