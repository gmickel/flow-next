---
satisfies: [R10, R11, R12, R13]
---
# fn-159-convergence-aware-review-terminals-and.6 Docs + CHANGELOG + STRATEGY sentence + propagation/sync + downstream chain

## Description
Docs, CHANGELOG, STRATEGY.md sentence, propagation, codex sync, full gate, and the maintainer downstream chain.

**Size:** M
**Files:** `CHANGELOG.md`, `STRATEGY.md`, `plugins/flow-next/docs/{flowctl.md,ralph.md,troubleshooting.md,orchestration.md,review-findings.md}`, `GLOSSARY.md`, `.flow/bin/flowctl.py` + `flowctl_tracker/` (propagation), `plugins/flow-next/codex/**` (regen only), `plugins/flow-next/skills/flow-next-ralph-init/templates/{prompt_plan.md,prompt_completion.md}` (PINNED), `plugins/flow-next/tests/test_review_prompt_template_parity.py`, `plugins/flow-next/scripts/flowctl.py` (review-lock hardening), downstream repos per maintainer instructions

### Approach
- CHANGELOG `## Unreleased`: expand the existing 4→8 draft entry to cover the full fn-159 story, user-outcome-first per agent_docs/releasing.md (converging loops stop wasting rounds; stuck loops escalate early; reviewers can hand a judgment call to a human; plan reviews stop blocking on outcome-free prose). No version bump (batched-release rule).
- flowctl.md: hash-guard + NOT_RETRYABLE stanza + --force in the review-rounds section; the `review-artifact` CLI verb (domain-separated blob builders) and the side-effect-free `rp mode-probe` command landed by .7 — document both in the review-rounds/CLI reference section; stall rules + both new ESCALATE variants + NEEDS_HUMAN in the deterministic-cap section; verdict grammar mentions; land.reviewTrigger row already updated in .5 — verify. <!-- Updated by plan-sync: fn-159-convergence-aware-review-terminals-and.7 landed the review-artifact CLI + rp mode-probe, not yet documented anywhere -->
- ralph.md: cap section notes stall/NEEDS_HUMAN escalation routes; guard table row from .5 — verify; verdict enum note matches ralph-guard.
- troubleshooting.md: NOT_RETRYABLE entry (distinct from cap ESCALATE); ratchet description now structured-findings; reset runbook gains human-only caveat.
- review-findings.md: consumer note — flowctl's detector/ratchet now read findings.items (fn-159).
- orchestration.md ratchet mention. <!-- Updated by plan-sync: fn-159-convergence-aware-review-terminals-and.3 already extended GLOSSARY.md's Receipt entry with the NEEDS_HUMAN verdict enum + escalation-persistence sentence — verify only, do not re-edit or double-list it here. -->
- STRATEGY.md: extend the Ralph-track quality-discipline sentence to name convergence-aware review terminals (trajectory-based early escalation + reviewer-emitted NEEDS_HUMAN). Nothing else.
- Final gate: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py` (the .py target, NEVER the bash launcher) + rsync flowctl_tracker + `python3 scripts/gen_tracker_manifest.py` + `./scripts/sync-codex.sh` twice (commit mirror diff) + `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`.
- Downstream chain (maintainer-local, same workstream): flow-next.dev repo at `~/work/flow-next.dev` (Starlight pages for review caps / land / orchestration; BOTH nav sources if any page added: `src/lib/site.ts` navGroups + `astro.config.mjs` sidebar; gate `pnpm build`), docs-site changelog entry staged, AI×SDLC guide at `~/work/AI-x-SDLC-Starter-Kit` swept (explicit per-page checked-no-op recorded in the task summary), Obsidian vault notes at `~/work/GordonsVault/Spaces/Projects/flow-next` (Autonomy + Release Timeline; direct file edits, not git). Follow `~/work/agent-instructions/downstream-properties.md` incl. narrative discipline. **Unavailable-repo outcome:** if a downstream repo is missing on the machine running this task, record `downstream: <repo> unavailable — needs maintainer walk` in the task summary; that line is the durable evidence CI/another implementer checks, and the task still completes.
- Conductor-queued review residuals (fold into this task, not a new spec):
  - `plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_plan.md:49` and `prompt_completion.md:45` both open step 4 with "The skill returns one terminal verdict", immediately followed by "Repeats until SHIP" / loop-until-SHIP bullets in the same numbered step — self-contradictory phrasing (a single "returns one terminal verdict" claim next to a repeat-until-terminal loop). Rephrase to separate the reviewer-tag-set (what a single review call can return: SHIP/NEEDS_WORK/MAJOR_RETHINK/NEEDS_HUMAN or SHIP/NEEDS_WORK/NEEDS_HUMAN) from the step's actual return-set (only SHIP/MAJOR_RETHINK/NEEDS_HUMAN return control to Ralph; NEEDS_WORK loops in-step). Both files are PINNED (`test_prompt_text_pinned.py`) — update the SHA-256 pins in the same commit with rationale.
  - `plugins/flow-next/tests/test_review_prompt_template_parity.py:213` — `TestReviewPromptPreChangeBinding.rendered_prompts(self, module: Any = flowctl)` takes a `module` parameter that every call site (`self.rendered_prompts()`, both test methods) invokes with zero arguments; the default is the only value ever used. Drop the dead parameter (and the now-unneeded `Any` import if it becomes unused).
  - One-line hardening at the review-lock site (component 1's sidecar-scoped cross-process lock, flock under `.flow/locks/`): the `_ensure_flow_gitignore` call there is unguarded against `OSError`/`UnicodeDecodeError`. Either wrap the call in `except (OSError, UnicodeDecodeError): pass` (best-effort, matching its own stated contract) or narrow its docstring/comment to state precisely what "best-effort" tolerates. Residual from review r3 of .7 — verify against the landed .7 diff before editing, the exact call site may have shifted.
  <!-- Updated by plan-sync: fn-159-convergence-aware-review-terminals-and.5 landed the land.reviewTrigger docs + ralph-guard blocks + human-only prose (R7/R8/R9); folded in three conductor-queued review residuals (ralph-init verdict phrasing, dead test param, gitignore-call hardening) not previously tracked anywhere in this task -->

### Investigation targets
**Required:**
- `agent_docs/releasing.md` — changelog ordering rules + rejection test
- `plugins/flow-next/docs/flowctl.md` — review-cap + review-rounds + land config sections
- `~/work/agent-instructions/downstream-properties.md` — the downstream walk contract

- `plugins/flow-next/tests/test_prompt_text_pinned.py` — pin-update procedure for the ralph-init templates

**Optional:**
- `plugins/flow-next/docs/README.md` — index bullets mentioning the cap

### Key context
- Docs-only files do NOT bump plugin version; the whole spec stages under Unreleased.
- test_tracker_distribution fails on missed propagation — run the full copy/rsync/manifest sequence, not a subset.

### Acceptance
- [ ] CHANGELOG Unreleased entry covers raise + detector + NEEDS_HUMAN + calibration, outcome-first
- [ ] All listed repo docs updated; no doc states default 4
- [ ] STRATEGY.md single-sentence extension only
- [ ] Propagation + manifest + double sync-codex committed; full suite + ruff green
- [ ] Downstream chain walked with per-property outcome noted (updated / checked-no-op)
- [ ] ralph-init `prompt_plan.md`/`prompt_completion.md` verdict-return phrasing de-contradicted; prompt-hash pins updated with rationale
- [ ] `test_review_prompt_template_parity.py` dead `module` param removed
- [ ] `_ensure_flow_gitignore` review-lock call site hardened (except clause or narrowed best-effort comment)
## Acceptance
- [ ] R10, R11, R12, R13 satisfied
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
