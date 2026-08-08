---
satisfies: [R1, R2, R3]
---
# fn-174-yagni-scope-discipline-in-plan-review.1 Transplant scope-minimality prose to all four sites + guard-exemption amendment + hash pin + mirrors

## Description
Apply the tested prose from worktree commit `5a54d5f0` (view with `git show 5a54d5f0`) to the four canonical files, add the same rubric text to the fifth site (workflow-rp.md), extend each site's rigor-exemption clause per R2 with the exact sentences below, sync the pinned-prompt parity chain, regenerate mirrors.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-plan/steps.md`, `plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md`, `plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md`, `plugins/flow-next/templates/spec.md`, `plugins/flow-next/agents/worker.md`, `plugins/flow-next/scripts/flowctl.py` (PLAN_REVIEW_PROMPT_FALLBACK string only), `.flow/bin/flowctl.py` (copy), `plugins/flow-next/tests/test_prompt_text_pinned.py` (two hash entries), `plugins/flow-next/tests/fixtures/review_prompts/plan.txt` + `plan_no_tasks.txt` (regenerated), `.flow/templates/spec.md` (copy), `plugins/flow-next/codex/**` (regenerated)

### Approach
Transplant (`git show 5a54d5f0` is the payload; anchors verified on main):
- steps.md: insert the **Scope minimality (YAGNI)** block between the stakeholder paragraph (ends "...user-facing feature.") and `## Step 3: Flow gap check`.
- plan-review-prompt.md: replace line `6. **Scope** - Right-sized? Over/under-engineering?` with the expanded criterion 6 from the commit.
- workflow-rp.md (~L189): replace `7. **Scope** - Right-sized? Over/under-engineering?` with the SAME expanded text as criterion 6, renumbered `7.`.
- templates/spec.md: insert the `SCOPE DISCIPLINE (YAGNI ...)` comment block between the customization-cascade comment's closing `-->` and `# <spec-id> <Title>`.
- worker.md: insert the `**Build to the AC, not past it (YAGNI):**` bullet between `- Follow existing code style` and `- Add tests if spec requires them` (exact position, not list end).

R2 amendment - EXACT sentences (append; never delete or weaken tested wording):
- steps.md, extend the final bullet's last sentence: after "...as do Boundaries and R-ID coverage." append " Equally exempt are filesystem-identity, permission, and concurrency guards (realpath/symlink containment, lock-guarded writes, forced excludes of runtime state) - an eliminated guard is not an eliminated feature."
- plan-review-prompt.md criterion 6 AND workflow-rp.md criterion 7, extend the closing sentence: "...flag the plan if minimality was achieved by dropping error handling" becomes "...flag the plan if minimality was achieved by dropping error handling or by dropping filesystem-identity, permission, or concurrency guards (realpath/symlink containment, lock-guarded writes, forced excludes of runtime state)."
- templates/spec.md comment, after "...are EXEMPT and stay complete." append " So are filesystem-identity, permission, and concurrency guards (realpath/symlink containment, lock-guarded writes, forced excludes of runtime state) - an eliminated guard is not an eliminated feature."
- worker.md, append a new sentence to the YAGNI bullet after "...it is the spec.": " Neither are filesystem-identity, permission, or concurrency guards (realpath/symlink containment, lock-guarded writes, forced excludes of runtime state) - never trim a guard as scope."

Pinned-prompt parity chain (site 2 blast radius; precedent commit `16dcd7a0`):
1. Mirror the edited `plan-review-prompt.md` byte-for-byte into the `PLAN_REVIEW_PROMPT_FALLBACK` triple-quoted string in `plugins/flow-next/scripts/flowctl.py` (~L9323).
2. `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py` (the .py target; NEVER touch the bash launcher `.flow/bin/flowctl`).
3. Update BOTH hash tables in `plugins/flow-next/tests/test_prompt_text_pinned.py`:
   - template hash: `python3 -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md').read_text().replace(chr(13)+chr(10),chr(10)).encode()).hexdigest())"`
   - fallback hash: `python3 -c "import sys;sys.path.insert(0,'plugins/flow-next/scripts');import hashlib,flowctl;print(hashlib.sha256(flowctl.PLAN_REVIEW_PROMPT_FALLBACK.replace(chr(13)+chr(10),chr(10)).encode()).hexdigest())"`
4. Rebaseline rendered fixtures: `python3 optimization/reached-path/generate_review_prompt_parity_evidence.py` (regenerates tests/fixtures/review_prompts/plan.txt + plan_no_tasks.txt; check its --help/docstring if flags needed).
5. Commit message MUST state what prompt text changed and why (fn-174 scope-minimality criterion + guard exemption).

Copies + mirrors:
- Copy updated `plugins/flow-next/templates/spec.md` over `.flow/templates/spec.md` (test_dogfood_template_parity enforces).
- `./scripts/sync-codex.sh` TWICE (second run must produce no diff); verify the worker bullet survived in `plugins/flow-next/codex/agents/worker.toml` and the four md mirror files carry the new prose.
- No Claude-native tool names in any new prose (Cursor/Droid consume canonical as-is).

### Investigation targets
**Required** (read before editing):
- `git show 5a54d5f0` - the exact tested prose
- `plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md` criteria list
- `plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md` ~L185-195 criteria copy
- `plugins/flow-next/scripts/flowctl.py` ~L9320-9420 PLAN_REVIEW_PROMPT_FALLBACK
- `plugins/flow-next/tests/test_prompt_text_pinned.py` PROMPT_HASHES + TEMPLATE_HASHES
- `plugins/flow-next/agents/worker.md` Rules list

### Acceptance
- [ ] All five sites carry prose functionally equivalent to 5a54d5f0 (R1); tested wording never weakened
- [ ] Every site's exemption clause carries its exact R2 sentence (both categories named)
- [ ] Criterion 6 (and rp criterion 7) list the three overengineering patterns (R3)
- [ ] PLAN_REVIEW_PROMPT_FALLBACK byte-identical to template; .flow/bin/flowctl.py identical to scripts/flowctl.py; both hashes updated; fixtures regenerated
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_review_prompt_template_parity test_review_prompt_constraints test_dogfood_template_parity test_template_canonical -q`
- [ ] sync-codex.sh run twice, idempotent; codex mirror diff committed with the canonical change; worker.toml carries the bullet
- [ ] .flow/templates/spec.md refreshed to match the bundled template
- [ ] Commit message states the prompt change + rationale
## Acceptance
- [ ] All five sites carry prose functionally equivalent to 5a54d5f0; tested wording never weakened (R1)
- [ ] Every site's exemption clause carries its exact R2 sentence naming both error-case enumeration and filesystem-identity/permission/concurrency guards (R2)
- [ ] Both rubric copies list the three overengineering patterns (R3)
- [ ] Parity chain green: fallback constant, dual copy, both hashes, fixtures; focused suite passes
- [ ] sync-codex.sh idempotent; .flow/templates/spec.md refreshed; commit message carries prompt rationale
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
