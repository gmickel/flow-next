---
title: Abort-option copy must reflect pre-prompt state mutations (idempotent != no chan
date: "2026-05-18"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-setup/workflow.md
tags: [fn-45, abort-option, setup-skill, copy-drift, codex-review, user-consent]
problem_type: build-error
symptoms: codex NEEDS_WORK on abort-message copy that claimed 'no changes made' when earlier setup steps had already run flowctl init
root_cause: abort-option copy drafted without auditing what side-effect commands ran before the prompt fires; option label vs routing block vs exit message can drift
resolution_type: fix
related_to: [bug/build-errors/agent-rename-epic-id-prompt-key-changes-2026-05-08, bug/build-errors/codex-impl-review-false-positive-on-2026-05-09, bug/build-errors/fn-441-review-cycle-json-contracts-html-2026-05-15, bug/build-errors/fn-442-review-both-pass-policy-2026-05-15, bug/build-errors/fn-445-review-r17-enforcement-beyond-2026-05-15, bug/build-errors/fn-447-review-cycle-scoped-diff-false-2026-05-15, bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem

Adding an `abort` option to a multi-step skill's interactive prompt is harder than it looks: the option label, the routing text, and any user-visible exit message all have to tell the same story about what state was already mutated before the prompt fired. codex impl-review caught two iterations of this on fn-45.2's setup migration prompt.

## What Didn't Work

**Iteration 1** — Added abort option with copy "exit cleanly, no migration, no banner-ack write, no setup changes" + routing block "Setup cancelled. No changes made. Re-run /flow-next:setup later to retry." **Codex caught**: Step 1 runs `flowctl init --json` BEFORE the Step 1b migration prompt — `.flow/`, `meta.json`, `config.json` may already exist. "No changes made" was false at decision time.

**Iteration 2** — Fixed the routing/exit-message block to acknowledge `init` may have run (idempotent, safe to leave) but left the original option label `abort — ... no setup changes` unchanged. **Codex caught**: the option label is what the user reads at consent time; routing text is read after the choice. The label itself must be accurate.

## Solution

**Iteration 3 (SHIP)** — Aligned the option label, routing block, and exit message on the same accurate state description:

- Option label: `abort — exit cleanly. No migration, no banner-ack write, no Step 2-onward setup changes. Step 1's flowctl init may already have run (idempotent — safe to leave). Re-run /flow-next:setup later to complete setup.`
- Routing block: same fact set, longer prose, explicit user-visible message.
- User-printed message: `Setup cancelled at migration prompt. .flow/ may have been initialized/upgraded by Step 1 (idempotent — safe to leave). No migration applied; Step 2 onward skipped. Re-run /flow-next:setup later to complete setup.`

`plugins/flow-next/skills/flow-next-setup/workflow.md:69,71-95` (canonical); mirror at `plugins/flow-next/codex/skills/flow-next-setup/workflow.md` regenerated via `./scripts/sync-codex.sh`.

## Prevention

When adding `abort` (or any "exit cleanly" option) to a skill prompt, audit:

1. **What's already run before this prompt fires?** Walk the workflow from Step 0 to the prompt site; list every side-effect command (`flowctl init`, `git`, file writes). The abort message must NOT claim "no changes made" if any of those ran.
2. **Three text locations need to agree**: the option label (visible at consent), the routing block (read after choice), and any user-visible exit message (printed on exit). All three describe the post-abort state — drift between them is a Codex NEEDS_WORK trigger.
3. **idempotent != "no changes"** — even if a command is safe to re-run, it still mutated state on first run. Say "may have run; idempotent and safe" rather than "no changes made."
4. **Run codex impl-review specifically for skill-prose changes** — codex catches user-facing copy contradictions that RP/Claude reviews can miss. Two cycles on this fix isolated two distinct contradictions in the same paragraph cluster.
