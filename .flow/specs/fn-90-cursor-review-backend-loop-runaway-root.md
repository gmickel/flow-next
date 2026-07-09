# fn-90 Cursor review backend loop runaway: root-cause analysis + convergence fix

> **STUB** (created from external-team field feedback, 2026-07-09). Investigation-first spec: find *why* the Cursor review backend loops, then fix the cause — not just cap it. Refine via `/flow-next:interview` before planning.

## Goal & Context
<!-- scope: business -->

Field signal from the first external team running flow-next live (2026-07-09 feedback session; detailed notes in the maintainer's vault): one ticket looped **~11x** in the cross-model review before the two models converged; the dev read it as "the models couldn't agree." On Gordon's own setup (default `rp` backend + Codex) he has **never seen >3 re-loops in 4 months**, and there is meant to be a hard cap of ~5. The reporting team runs the **Cursor review backend** (`cursor-agent` CLI, shipped in fn-74). So the runaway correlates with the Cursor backend, which is new.

This is a **root-cause spec, not a guard spec.** A loop cap alone hides the symptom (expensive, slow, erodes trust in the review gate) without fixing why the reviewer and implementer never agree. Gordon's read: the cause may be mundane — the **default `cursor-agent` system prompt interfering** with the injected flow-next reviewer instruction (competing built-in guidance diluting the scope anchor — not the prompt being dropped), and/or the **plan-review skill prompt being too loose** so the reviewer keeps expanding scope (matches his meeting observation that on big tickets "plan-review pulls in too much instead of concentrating on what was actually implemented"). His 2025 token-efficiency/speed trims are also a suspect (a trimmed reviewer may lose the in-scope anchor).

## Architecture & Data Models
<!-- scope: technical -->

TBD (interview). Areas the investigation touches:
- The Cursor review backend from **fn-74** (`cursor-agent` CLI; models gpt-5.5 / codex / opus) and how the reviewer prompt + spec/plan context are passed to it vs the `rp` and Codex backends.
- The **review loop controller** in `/flow-next:plan-review` (and impl-review): where the max-loop cap lives, whether it is enforced per-backend, and the convergence/"agreement" signal between implementer and reviewer.
- How the **default `cursor-agent` system prompt composes with** the flow-next reviewer instruction (the scope anchor that limits the review to what the spec/plan covers): whether the CLI's built-in guidance competes with/dilutes the injected review scoping, and how the final prompt is assembled on that transport vs `rp` and Codex.

## API Contracts
<!-- scope: technical -->

TBD (interview). No new public surface expected — this is a behavior/prompt/plumbing fix on an existing backend. Any config knob (e.g. explicit per-backend loop cap, reviewer-system-prompt injection mode) to be defined during planning.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Large tickets (20+ acceptance criteria / >3.0 backend)** are the trigger surface — the reviewer over-expands scope; the fix must hold the reviewer to the implemented plan, not the whole codebase.
- **Backend parity:** whatever the cause, verify behavior across `rp`, Codex, and Cursor — the fix must not regress the two backends that already converge fast.
- **Model diligence differences:** gpt-5.5 vs codex vs opus as the Cursor reviewer model may differ in verbosity/strictness; isolate model effect from backend effect.
- **Cap as backstop, not cure:** a divergence circuit-breaker (cap + escalate-to-human) is acceptable *in addition to* the root-cause fix, never instead of it.

## Acceptance Criteria
<!-- scope: both -->

- [ ] **R1:** The runaway is **reproduced** on a representative large ticket (concrete example to be provided by the reporting team) with loop-count + per-iteration reviewer output captured.
- [ ] **R2:** **Root cause identified and documented** (e.g. default-system-prompt interference on `cursor-agent`, loose plan-review scoping, unenforced per-backend cap, reviewer-context trim, or model effect) — with evidence, not a guess.
- [ ] **R3:** After the fix, typical loop count on the Cursor backend is back in line with the other backends (≤3 typical; cap enforced and observable), verified on the repro.
- [ ] **R4:** The reviewer stays **in-scope** — it evaluates what the spec/plan covered and does not expand into unrelated codebase concerns (the "concentrate on what was implemented" bar).
- [ ] **R5:** **A/B evidence** captured for the same plan through Codex vs Cursor (and rp) to confirm the fix and isolate backend vs model effect.
- [ ] **R6:** A regression is added to the **eval harness (fn-54)** so review-loop convergence on the Cursor backend is guarded going forward.

## Boundaries
<!-- scope: business -->

- In: diagnosing + fixing review-loop convergence on the Cursor (`cursor-agent`) backend; reviewer prompt/scope; per-backend cap enforcement.
- Out: rebuilding the Cursor backend (that's fn-74, shipped); a general per-stage model-routing policy (separate roadmap item); changing the default backend.

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
- **Open questions for interview:** is the max-loop cap backend-agnostic today? How does `cursor-agent` compose its default system prompt with injected instructions — does the built-in prompt interfere with the reviewer scope anchor? Did the 2025 token/speed trims remove the reviewer's scope anchor? Is the "agreement" signal a diff-based or judgement-based convergence check?
