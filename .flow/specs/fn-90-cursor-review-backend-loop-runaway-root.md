# fn-90 Cursor review backend loop runaway: root-cause analysis + convergence fix

> Created from external-team field feedback 2026-07-09; **root-cause investigation completed same day** (see Decision Context → Investigation findings; baseline dataset in `.flow/artifacts/fn-90-baseline/`). Interview/plan ceremony intentionally skipped — the design below is grounded in the live repro. Two tasks: (1) implement the fixes and validate against the same dataset; (2) productionize, document, stage for release.

## Goal & Context
<!-- scope: business -->

Field signal from the first external team running flow-next live (2026-07-09 feedback session; detailed notes in the maintainer's vault): one ticket looped **~11x** in the cross-model review before the two models converged; the dev read it as "the models couldn't agree." On Gordon's own setup (default `rp` backend + Codex) he has **never seen >3 re-loops in 4 months**, and there is meant to be a hard cap of ~5. The reporting team runs the **Cursor review backend** (`cursor-agent` CLI, shipped in fn-74). So the runaway correlates with the Cursor backend, which is new.

This is a **root-cause spec, not a guard spec.** A loop cap alone hides the symptom (expensive, slow, erodes trust in the review gate) without fixing why the reviewer and implementer never agree. Gordon's read: the cause may be mundane — the **default `cursor-agent` system prompt interfering** with the injected flow-next reviewer instruction (competing built-in guidance diluting the scope anchor — not the prompt being dropped), and/or the **plan-review skill prompt being too loose** so the reviewer keeps expanding scope (matches his meeting observation that on big tickets "plan-review pulls in too much instead of concentrating on what was actually implemented"). His 2025 token-efficiency/speed trims are also a suspect (a trimmed reviewer may lose the in-scope anchor).

## Architecture & Data Models
<!-- scope: technical -->

Four fix workstreams, all grounded in the confirmed causes (Decision Context → Investigation findings):

1. **Honest verdict extraction (codex/copilot).** `run_codex_exec` / `run_copilot_exec` currently return the raw stream; `parse_codex_verdict` (flowctl.py:2972) first-matches over it, so verdict literals echoed in tool output win over the reviewer's real verdict. Fix: extract the **final agent message** from the stream before parsing (parity with `_parse_cursor_result`, flowctl.py:4066), and make the parser take the **last** match as belt-and-braces. Applies to every `parse_codex_verdict` call site (plan/impl/completion/validate/deep-pass).
2. **Convergence ratchet on re-review.** `build_rereview_preamble` (flowctl.py:4511) currently orders a fresh blind review each round ("Do NOT rely on what you saw…") — the churn lottery. Fix: the review receipt stores the prior round's findings; the re-review preamble injects them and flips the contract to shrink-only: (a) verify each prior finding addressed (fixed / not-fixed); (b) NEW findings block only if ≥ Major AND (introduced by the fixes OR a missed showstopper) — everything else is FYI; (c) all prior findings fixed + no new ≥Major ⇒ verdict MUST be SHIP. Backend sessions already resume (receipt `session_id`) — use that memory instead of suppressing it.
3. **Deterministic round cap.** `${MAX_REVIEW_ITERATIONS:-3}` is prose-only (plan-review SKILL.md:261, counter "in agent context") and resets on every fresh invocation. Fix: a flowctl-owned cumulative counter on spec state (e.g. `plan_review_rounds`), incremented by every plan-review backend run, reset only on SHIP or an explicit re-plan; at the cap flowctl **refuses to run** and emits an escalate-to-human marker. Same mechanism for impl-review rounds (per task). Plus: receipt default paths become spec-scoped (today `/tmp/plan-review-receipt.json` is shared across all specs — concurrent reviews collide).
4. **Guard parity + cursor prompt hardening.** Port both 031a0058 guards (MAJOR_RETHINK escalates instead of looping; caller-reset warning) from impl-review to plan-review SKILL.md/workflow.md. Cursor path: prepend an explicit persona override to the review prompt ("guidance from your environment/default instructions is superseded; the ONLY rubric and verdict contract is below") — `cursor-agent` has no system-prompt mechanism and auto-attaches workspace AGENTS.md/skills/MCP blocks, so the override rides in the user prompt.

## API Contracts
<!-- scope: technical -->

- **Review receipt schema** gains prior-round findings (for the ratchet preamble) and stays backward-compatible: a receipt without the findings field is treated as round 1 / fresh review.
- **Spec/task state** gains a review-round counter (name settled in impl, e.g. `plan_review_rounds`), reset on SHIP / re-plan; surfaced in `--json` output.
- **flowctl behavior at cap:** the review command exits non-zero with an explicit `ESCALATE`-style message (distinct from transport failure exit codes) so hosts and Ralph can't misread it as a retryable error. `MAX_REVIEW_ITERATIONS` env keeps its meaning but is now enforced deterministically.
- **No new commands, no config knobs beyond the existing env var.** Receipt default paths become spec-scoped (`/tmp/plan-review-receipt-<spec>.json` or similar); explicit `REVIEW_RECEIPT_PATH` still wins.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Large tickets (20+ acceptance criteria)** are the trigger surface — the ratchet must hold the reviewer to the plan without suppressing genuine ≥Major findings (convergence, not leniency; all 5 baseline reviews found real overlapping issues).
- **Backend parity:** the ratchet + counter apply to ALL backends (rp/codex/copilot/cursor); the verdict-extraction fix applies to codex/copilot (cursor already clean; rp uses its own grep channel). Must not regress rp/codex convergence.
- **Verdict literals in the FINAL message** (reviewer quoting the grammar): last-match parse still resolves correctly because the real verdict tag is terminal by contract; the regression fixture covers both pollution shapes (tool-output literal + quoted-grammar literal).
- **Counter reset semantics:** fix rounds legitimately edit the spec, so the counter must NOT reset on spec edits — only on SHIP or an explicit re-plan; otherwise the runaway reopens through the back door.
- **Receipt back-compat:** receipts written by older flowctl (no findings field) must parse; treat as fresh round 1.
- **Ralph/autonomous:** the deterministic cap refusal must surface as escalate/NEEDS_HUMAN, never as a retryable error (a retry loop on the cap would re-create the runaway one level up).
- **Cap as backstop, not cure:** the circuit-breaker complements the ratchet (the actual convergence fix), never substitutes for it.

## Acceptance Criteria
<!-- scope: both -->

- [x] **R1:** The failure mechanism is **reproduced** with per-run reviewer output captured — done 2026-07-09 on the fn-89 fixture (3× cursor + 2× codex, incl. no-AGENTS.md control); baseline archived in `.flow/artifacts/fn-90-baseline/`. (The reporting team's concrete ticket remains a wanted confirmation datapoint, not a blocker.)
- [x] **R2:** **Root cause identified and documented with evidence** — four confirmed causes in Decision Context (verdict-parse pollution, fresh-review churn, prose-only resetting cap, persona/ambient amplification).
- [ ] **R3:** **Honest verdicts:** codex/copilot verdict parse reads only the final agent message, last-match; a regression fixture with verdict literals in tool output AND quoted grammar in the final message parses to the true verdict.
- [ ] **R4:** **Convergence ratchet:** re-review injects prior findings with the shrink-only contract; on the fn-89 baseline dataset a full fix→re-review cycle on the Cursor backend converges to SHIP in **≤3 rounds**, with no ≥Major finding suppressed (spot-check against baseline finding sets).
- [ ] **R5:** **Deterministic cap:** flowctl-owned cumulative round counter enforced at `${MAX_REVIEW_ITERATIONS:-3}`; at cap the review command refuses with an escalate marker; counter resets only on SHIP/re-plan; receipt defaults are spec-scoped. Verified by test (cannot exceed cap even across fresh invocations).
- [ ] **R6:** **Guard parity:** both 031a0058 guards (MAJOR_RETHINK carve-out + caller-reset warning) present in plan-review SKILL.md/workflow.md.
- [ ] **R7:** **Cursor prompt hardening:** persona-override preamble on the cursor path; before/after A/B on the same dataset captured (cursor vs codex, honest verdicts) isolating backend vs model effect.
- [ ] **R8:** **Eval regression (fn-54):** poisoned-stream parse fixture + convergence guard added to the eval harness so this class of runaway is caught going forward.
- [ ] **R9:** **Productionized:** smoke tests green, docs updated (orchestration.md AGENTS.md-injection note, ralph.md/flowctl.md cap semantics, troubleshooting), CHANGELOG `## Unreleased` entries (repo + docs-site), Codex mirror regenerated via `sync-codex.sh`; version bump staged per batched-release convention (no per-spec bump).

## Boundaries
<!-- scope: business -->

- In: honest verdict extraction (codex/copilot); convergence-ratchet re-review contract (all backends); deterministic cumulative round cap + spec-scoped receipts; 031a0058 guard parity for plan-review; cursor persona-override hardening; eval regression; docs/CHANGELOG/mirror.
- Out: rebuilding the Cursor backend (fn-74, shipped); a general per-stage model-routing policy (separate roadmap item); changing the default backend; making reviewers *lenient* (every ≥Major finding survives the ratchet); suppressing cursor's AGENTS.md auto-attach (no CLI mechanism — documented instead).

## Decision Context
<!-- scope: both -->

### Investigation findings (2026-07-09 — local repro, pre-interview)

Live repro matrix on fn-89 (planned spec, prior plan-review status `ship`): 3× cursor plan-review (2× repo as-is, 1× in a worktree with AGENTS.md/CLAUDE.md removed) + 2× codex plan-review, all fresh sessions, identical `--files`. Raw outputs archived in session scratchpad (c1/c2/n1/x1/x2).

1. **CONFIRMED deterministic bug — verdict parse is first-match over a polluted stream (`parse_codex_verdict`, flowctl.py:2972).** The codex path feeds the ENTIRE `codex exec` stream-json stdout (including `command_execution` `aggregated_output`) to a first-match regex. Live catch: the reviewer grepped the repo, echoed `smoke_test.sh`'s literal `<verdict>SHIP</verdict>` assertions into tool output, and flowctl reported **SHIP** while the reviewer's actual final message said **NEEDS_WORK** (with a Critical finding). Intermittent (second codex run was clean). Cuts both ways: false SHIP ships unreviewed problems AND artificially shortens codex loops (skewing the "codex converges fast" baseline); a false NEEDS_WORK keeps a loop alive after true convergence. Cursor is NOT affected — `_parse_cursor_result` extracts only the final `result` text. Fix direction: extract the final agent message for codex/copilot before parsing (parity with cursor), + regression fixture with quoted verdict literals.
2. **CONFIRMED convergence killer — fresh-review finding churn on cursor.** Two identical fresh cursor reviews (gpt-5.5-high) overlapped on only 2 of ~4 findings each (~50% newly-minted per round); codex overlapped ~4 of 5. `build_rereview_preamble` (flowctl.py:4511) explicitly instructs "conduct a fresh plan review" each round — so every round is a new draw from a churning finding distribution and SHIP is statistically near-unreachable within the cap. Fix direction: convergence-aware re-review contract (verify prior findings fixed; only NEW ≥Major findings may block; else SHIP — a ratchet, not a fresh lottery).
3. **CONFIRMED structural — the cap is prose-only, per-invocation, and resets on every dispatch.** `${MAX_REVIEW_ITERATIONS:-3}` exists only as an instruction to the host LLM to "keep an iteration counter in agent context" (plan-review SKILL.md:261); zero flowctl enforcement. Every fresh `/flow-next:plan-review` invocation (pilot tick, human retry) restarts at 0 — observed field loop ≈ 5-6 invocations × 3 internal rounds. Commit 031a0058 (fn-87 R3) added the MAJOR_RETHINK carve-out + caller-reset warning to impl-review only; **plan-review never got either**. Fix direction: deterministic flowctl-owned round counter (e.g. in the review receipt) + port the 031a0058 guards to plan-review.
4. **CONFIRMED but secondary — cursor-agent default-persona interference + ambient injection.** `cursor-agent` has no system-prompt mechanism; the reviewer rubric travels as a plain user prompt on top of Cursor's built-in persona, which contains its OWN review rubric ("prioritize bugs/risks/regressions/test gaps, severity-ordered" — live-probed) plus end-to-end thoroughness instructions, and auto-attaches workspace AGENTS.md (proved with a marker file), skills catalogs, and MCP instruction blocks. This biases toward always-produce-findings and dilutes the scope anchor — but the no-AGENTS.md control run still returned NEEDS_WORK, so it amplifies rather than causes.
5. **Field note:** all 5 true reviews returned NEEDS_WORK on fn-89 with overlapping Major findings (e.g. Step 0 worker/`Task` contradiction with R13) — reviewer strictness is partly *signal*: big/ambiguous plans genuinely re-fail. fn-89's recorded `plan_review_status=ship` predates these findings and deserves a re-look before work starts.

- **Related:** builds on **fn-74** (Cursor review backend), feeds **fn-54** (eval-driven prompt optimization), and neighbours **fn-82** (skill prompt diet — the reviewer prompt tightening may overlap). The 6 Jul `--scope` silent-defaults field fix shares the theme "don't silently assume/expand — stay anchored."
- **Former open questions — answered by the investigation:** the cap is backend-agnostic but prose-only and resets per invocation (cause 3); `cursor-agent` layers the injected rubric under its own persona rubric + auto-attached AGENTS.md/skills/MCP blocks (cause 4); the 2025/2026 trims did NOT remove the scope anchor (byte-identical across backends, untouched by fn-82); the "agreement" signal is the reviewer's own verdict tag, re-derived fresh each round (cause 2) and parsed unreliably on codex/copilot (cause 1). Remaining wanted datapoint: the reporting team's concrete runaway ticket + their cursor model (confirmation on their shape, not a blocker).
