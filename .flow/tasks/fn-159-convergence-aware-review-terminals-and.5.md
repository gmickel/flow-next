---
satisfies: [R7, R8, R9]
---
# fn-159-convergence-aware-review-terminals-and.5 Bot-surface bounding (resolve-pr triage, land trigger text) + guard-block reset/--force

## Description
Bot-surface bounding and gate-integrity guarding: resolve-pr prose-triage rule, recommended land.reviewTrigger scope text in docs, and ralph-guard blocking of the reset verbs and --force.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md` (+ SKILL.md if triage summarized there), `plugins/flow-next/agents/pr-comment-resolver.md`, `plugins/flow-next/docs/flowctl.md` (land.reviewTrigger row ~L803 + review-cap section), `plugins/flow-next/skills/flow-next-land/workflow.md` (§2.6), `plugins/flow-next/scripts/hooks/ralph-guard.py`, pilot/land/work skill prose (one-line human-only statements), `plugins/flow-next/docs/ralph.md` (guard rule table), tests for the guard

### Approach
- resolve-pr: add one triage classification to the resolver contract ("Decide verdict" table in pr-comment-resolver.md ~L73): on a code PR, a spec/doc-prose finding = fix-or-record (spec-touchup commit or reasoned FYI reply + resolve), never merge-gating; a prose finding revealing the code does the wrong thing = code finding, blocks normally. Resolver reply states the assigned class.
- land docs: recommended reviewTrigger text (example value in flowctl.md config row + land workflow §2.6 callout): scope the bot pass to integration effects / diff-as-narrative / cross-task regressions; spec-prose findings welcome as FYI, not merge-gating. Default stays "". State bot comments are outside detector/guard blast radius.
- ralph-guard: new PreToolUse blocks for `spec reset-review-rounds`, `review-rounds reset`, and `--force` on review dispatch/increment. Follow the existing re.search/output_block pattern in handle_pre_tool_use (:673+) BUT tokenize argv (shlex) rather than substring-match — memory lesson shell-command-allowlist-gates-must-2026-06-05 (5 historical bypasses). SAFE ONLY because .1 made SHIP reset system-owned inside `record` and removed the explicit reset calls from the workflow-rp.md files (round-2 P0) — verify .1 landed before enabling these blocks; add a guard test that a SHIP flow under Ralph completes with the blocks active.
- One-line "counter reset / --force is human-only" statements where pilot/land/work/ralph prose discusses escalation; ralph.md guard table row.

### Investigation targets
**Required:**
- `plugins/flow-next/agents/pr-comment-resolver.md` — full read (verdict table, deliberate-decision rule)
- `plugins/flow-next/scripts/hooks/ralph-guard.py:600-800` — block patterns + output_block
- `plugins/flow-next/skills/flow-next-land/workflow.md:280-350` — §2.5-2.6 trigger/signal section
- `.flow/memory/bug/security/shell-command-allowlist-gates-must-2026-06-05.md` — tokenization lesson

**Optional:**
- `plugins/flow-next/docs/ralph.md:790-810` — guard rule table format
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md` — triage flow

### Key context
- Guard hooks do not fire on Cursor (different hook events) — prose statements are the only rail there; that asymmetry is pre-existing and acceptable.
- Do not touch the fn-149 stacked-PR land sections (open-spec overlap; different subsections).

### Acceptance
- [ ] Resolver contract carries the prose-vs-code triage rule with named-class replies
- [ ] flowctl.md + land workflow document the recommended trigger text; default unchanged
- [ ] ralph-guard blocks all three verbs/flags via tokenized matching; guard tests cover a bypass attempt (quoted/spaced variants)
- [ ] Human-only prose lines present in pilot/land/work/ralph escalation sections
## Acceptance
- [ ] R7, R8, R9 satisfied
## Done summary
Bot-surface bounding + gate-integrity guarding (fn-159 R7/R8/R9): the pr-comment-resolver contract now classifies spec/doc-prose findings on code PRs as fix-or-record (never merge-gating, class named in each reply) with the behavior-gap carve-out as a code finding; flowctl.md's land.reviewTrigger row and land workflow 2.6 document the recommended scoped trigger text (default "" unchanged, bot comments declared outside detector/guard blast radius); ralph-guard blocks `spec reset-review-rounds`, `review-rounds reset`, and `--force` on review dispatch/increment via tokenized argv matching (quoted/spaced/python-launcher bypasses covered, unparseable-prose fallback screen so heredoc writes are not blocked, SHIP-flow `review-rounds record` proven allowed with blocks active), and human-only recovery prose landed in pilot/land/work/ralph plus the ralph.md guard table.
## Evidence
- Commits: 24269a070a0c2ffdb9870cce22351e51f32dc0d1, 07495d52
- Tests: baseline: green (cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_host_review_backend test_prompt_text_pinned test_review_prompt_template_parity -q), cd plugins/flow-next/tests && python3 -m unittest test_ralph_guard test_ralph_guard_codex_delegation -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh (x2, idempotent), python3 scripts/run_tests_parallel.py (3995/0 post-fix) + ruff + live adversarial probes
- PRs: