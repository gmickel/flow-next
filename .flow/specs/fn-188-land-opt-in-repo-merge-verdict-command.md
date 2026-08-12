# land: opt-in repo merge-verdict command gate (#330)

## Goal & Context

Issue #330 (@TechupBusiness): on a free-plan private repo, branch protection and rulesets 403, so no required status check exists and land's Phase 2 gate tree - CI tri-state (2.4), review threads (2.5), QA receipt (2.5b), merge state (2.8) - has no hook for a repo-local gate of record. land's own SKILL.md already concedes the premise (`--auto` is refused because "on a repo with no branch protection --auto merges instantly, so server-side gating adds nothing"). `flowctl gate receipt` cannot fill the hole: it is an honest assertion warrant (never executes the command, always green on a clean tree) - the reporter's reading verified correct.

Decision: ACCEPT, as a block-only, fail-closed, opt-in gate. Modified from the ask:

- **Name**: `land.mergeVerdictCommand` (NOT gateVerdictCommand - avoids colliding with the `flowctl gate` subsystem vocabulary).
- **Placement**: a new §2.9, reached only when every other gate is satisfied and the planned action is `merge` - one execution per merge attempt, not one per patience tick; freshest verdict at the decision point.
- **Contract**: exit code only. `bash -c` with cwd = REPO_ROOT on ORIG_BRANCH; context arrives as environment only (`FLOW_HEAD_SHA` = the PR `.headRefOid` land already reads, `FLOW_BASE_REF`, `FLOW_PR_NUMBER`, `FLOW_SPEC_ID`) - the configured string is never built from PR-derived text. Exit 0 = green. Non-zero = verdict `NEEDS_HUMAN`, action `none` (BLOCKED stays reserved for server-side merge refusals), reason carries the exit code + last stderr line (truncated ~200 chars).
- **Fail-closed set**: configured-but-missing/unexecutable (127), timeout (600s bound, stated), signal death - all block, never skip.
- **Never under `--dry-run`**: report `would-run: <command>` in the classification report (mirrors the reviewTrigger dry-run treatment); the zero-mutation promise is a hard invariant.
- **Wrong-tree trap**: documented in the section body the way 2.5b does (:278 pattern) - the command runs on the base checkout; it must key on `$FLOW_HEAD_SHA` and refuse (non-zero) when it cannot see that head. land does not check out the PR branch for it.
- **Off states**: unset, null, AND "" all mean OFF (today's behavior byte-for-byte) - stated explicitly because `cleanReviewCommentPattern` has a null-vs-"" asymmetry that must not be miscopied.
- **No label on refusal** (matches 2.5b's NEEDS_WORK posture); the Phase 4 evidence block gains `mergeVerdict=<green|refused|skipped|would-run>`.

Doctrine: this is a #313-adjacent config ask accepted where #313 was declined, and the reply/docs must name the asymmetry - #313 wanted to alter a classification floor an agent can already override upward; this key is block-only (can only tighten) and lands in an autonomous flow where conductor prose is not fail-closed. Trust domain unchanged: `.flow/config.json` is a committed repo file, the same authorship channel as the release-doc commands land already executes and spec Quick commands work already runs. STRATEGY "Built-in CI runners" is adjacent, not conflicting: land consumes the repo's verdict; it never runs a pipeline.

Plumbing constraints (verified): defaults block `flowctl.py` ~:1363 (`"land": {` - seven skill-read leaves today); schema generator `scripts/gen_flow_config_schema.py` needs a DESCRIPTIONS entry (~:341-376 land block) + TABLE row (~:728-735) + seeded default, then regenerate the committed schema artifact; the fn-138 drift test passes automatically for a skill-read key once defaults + TABLE exist. HARD: `test_skill_prose_diet.py:77-95` asserts land's workflow makes exactly ONE `config get` call - the new key must be read off the existing `lcfg` subtree capture, no new probe.

## Acceptance Criteria

- R1: config leaf `land.mergeVerdictCommand` exists (default ""), in `get_default_config()`, the schema generator TABLE + DESCRIPTIONS, and the regenerated committed schema artifact; `test_flow_config_schema_drift` green; docs/flowctl.md config table row added.
- R2: land/workflow.md gains §2.9 "Repo merge-verdict gate (opt-in, fail-closed)" after 2.8 and before the dry-run stop, modeled on 2.5b's prose shape (why-paragraph, wrong-tree warning, verdict table, a "has broken this" invariant), with the full contract above (env-only context, exit-code verdict, fail-closed set, 600s timeout, off-states, no label). Phase 0's existing `lcfg` capture gains the one-line read; Phase 4's evidence block gains the mergeVerdict field. SKILL.md gets one sub-bullet (mirroring the cleanReviewCommentPattern bullet).
- R3: `--dry-run` never executes the command - §2.9 and the §4.0-equivalent classification report state `would-run`; the zero-mutation invariant sentence names it.
- R4: tests in test_land_config.py: default-value assertion, config set round-trip, sibling-no-clobber, plus static workflow assertions (gate section present; fail-closed branch present; dry-run would-run branch present; env-var names present) in the file's existing static-assertion style; `test_skill_prose_diet` stays green (no second config get).
- R5: agent_docs/conduct/land.md gains one checklist item (no merge without exit-0 when set; missing/unexecutable/timeout blocks, never skips; dry-run reports would-run and executes nothing).
- R6: docs + CHANGELOG: docs/flowctl.md row; the land section of docs where gates are enumerated updated; CHANGELOG under `## Unreleased` credits @TechupBusiness and names the #313 asymmetry (block-only, autonomous-context) in one sentence.

## Boundaries

- No new flowctl subcommand or Python logic beyond the config default; execution is skill-side Bash per the split rule.
- No JSON verdict contract in v1 (exit code only; room to add structured mode later).
- No label application on refusal; no change to 2.4-2.8 semantics; the merge-license boundary (land merges explicitly, --squash --match-head-commit, never --auto) is untouched.
- sync-codex.sh twice at close-out (skill prose changed); watch for new Claude-only phrases (none expected).
- No version bump in implementation commits.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_land_config test_skill_prose_diet test_flow_config_schema_drift -q
```
