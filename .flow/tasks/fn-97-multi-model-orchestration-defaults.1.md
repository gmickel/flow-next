# fn-97-multi-model-orchestration-defaults.1 Direct edits + docs: delegate steering keys, setup scaffold question, worker pin, recipe hardening, orchestration defaults

## Description
Implement all of fn-97 as one pass (R1-R7). Work items:
1. flowctl config keys work.delegate_model / work.delegate_effort + wire into flow-next-work codex-delegation bridge (-m / -c model_reasoning_effort=, omit when unset). Update codex-delegation.md reference + flowctl.md.
2. flow-next-setup: bridge-CLI-detected optional question scaffolding the multi-model routing block + review.backend codex offer; skipped when non-interactive.
3. sync-codex.sh / agents/worker.toml: pin Codex-mirror worker to gpt-5.6-terra medium; Claude-side worker stays inherit.
4. usage.md template recipe hardening (--skip-git-repo-check on codex exec lines, cursor-agent git-repo warning) - edits already exist uncommitted on main; include them.
5. orchestration.md: host-relative default-pipeline table, wrapper-pattern subsection (foreground-bridge rule, self-heal scope), severity-tier review-verdict note.
6. Regenerate codex mirror; CHANGELOG Unreleased entry; stage docs-site updates (orchestration page + changelog) per releasing.md; no version bump.
Evidence base: memory note multimodel-pipeline-eval-2026-07-14; spec Decision Context.
## Acceptance
- All fn-97 acceptance criteria R1-R7 pass.
- smoke_test.sh + unit tests green; sync-codex.sh run and mirror committed.
- No behavior change when new config keys unset and setup question declined (except strictly-safer recipe flags).
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
