# fn-97-multi-model-orchestration-defaults.1 Direct edits + docs: delegate steering keys, setup scaffold question, worker pin, recipe hardening, orchestration defaults

## Description
Implement all of fn-97 as one pass (R1-R7). Work items:
1. (Amended fn-97.1, matching the amended spec R1.) The steering keys already exist from fn-55 as work.delegateModel / work.delegateEffort and are already wired into the codex-delegation bridge, ALWAYS passed explicitly as -m / -c model_reasoning_effort= (no omit-when-unset path; --ignore-user-config isolation). Actual delta: flip the work.delegateModel default gpt-5.6-sol -> gpt-5.6-terra (eval-motivated; effort stays medium) + document the keys in codex-delegation.md, flowctl.md, orchestration.md, usage.md template.
2. flow-next-setup: bridge-CLI-detected optional question scaffolding the multi-model routing block + review.backend codex offer; skipped when non-interactive.
3. sync-codex.sh / agents/worker.toml: pin Codex-mirror worker to gpt-5.6-terra medium; Claude-side worker stays inherit.
4. usage.md template recipe hardening (--skip-git-repo-check on codex exec lines, cursor-agent git-repo warning) - edits already exist uncommitted on main; include them.
5. orchestration.md: host-relative default-pipeline table, wrapper-pattern subsection (foreground-bridge rule, self-heal scope), severity-tier review-verdict note.
6. Regenerate codex mirror; CHANGELOG Unreleased entry; stage docs-site updates (orchestration page + changelog) per releasing.md; no version bump.
Evidence base: memory note multimodel-pipeline-eval-2026-07-14; spec Decision Context.
## Acceptance
- All fn-97 acceptance criteria R1-R7 pass.
- smoke_test.sh + unit tests green; sync-codex.sh run and mirror committed.
- No behavior change when setup question declined and config untouched, except the strictly-safer recipe flags and the R1 delegate-default flip (gpt-5.6-sol -> gpt-5.6-terra, visible only when delegation is actively enabled) - per amended spec R1/Boundaries.
## Done summary
Implemented fn-97 in one pass: flipped the work.delegateModel default to gpt-5.6-terra (spec R1 amended to the as-shipped fn-55 camelCase always-explicit contract), gated setup's Model Routing question on bridge-CLI detection with a writer-family-aware review.backend codex offer (Recommended label + step-8 non-destructive switch, both skipped on Codex hosts), pinned the Codex-mirror worker to terra-medium in sync-codex.sh, hardened the usage.md bridge recipes (--skip-git-repo-check + write-mode workspace guard, cursor-agent git-repo warning), and added orchestration.md's "A proven default pipeline" (model-per-role table with per-host reach, wrapper pattern, raw-bridge severity-tier note). Codex mirror regenerated, CHANGELOG Unreleased entry added, docs-site orchestration page + changelog staged (flow-next.dev commit d613d22); codex impl-review SHIP after 2 fix rounds.
## Evidence
- Commits: 4401919d6d3a9d5273f06496695a0505c5ea95db, dee3d7f733c135ba4e8600d01846a3fa18829b7c, 74dec9c0ddb78de54717e30d77e8d92462df469d, fc2aa555175afe10917681d85339b6478ad4b47d
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (1770 tests, OK; baseline red only on dogfood-parity caused by this task's own pre-staged R4 template edit, fixed in-task), bash plugins/flow-next/scripts/smoke_test.sh (144/144, baseline green and post-edit green), python3 -m unittest test_model_routing_scaffold test_dogfood_template_parity test_work_delegate_config (affected modules re-run each fix round), cd ~/work/flow-next.dev && pnpm build (65 pages, green)
- PRs: