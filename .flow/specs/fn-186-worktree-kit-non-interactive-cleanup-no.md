# Worktree kit: non-interactive cleanup, --no-track create, invocation docs (#333)

## Goal & Context

Issue #333 (@sn-furali) raised four asks against the worktree kit. Verified against main at 3.28.0:

- **(b) CONFIRMED.** `cleanup` reads two answers from stdin unconditionally (`worktree.sh:193` `read -r to_remove`, `:198` `read -r confirm`, under `set -euo pipefail` at `:2`). With no terminal the first `read` hits EOF and the script dies exit-1 *before* its own cancel branch, with no diagnostic. `cleanup` is the only sanctioned removal path, so automated flows have no route and the failure never names its cause. Reproduced live.
- **(c) CONFIRMED.** `create` resolves the start point to `origin/<base>` when that ref exists (`:149-152`) and runs `git worktree add -b` (`:158`) without `--no-track`, so the new branch tracks the base's remote branch. Corrected risk model (the issue's is backwards): `push.default=simple` refuses on name mismatch and `current` safely pushes `name -> name`; **`upstream` is the dangerous mode** — a bare `git push` aims at the base branch. An isolated per-worktree branch is exactly the case where tracking the base is wrong.
- **(d) Behavior confirmed, doc claim refuted.** `switch` prints the path (`:175`) and `SKILL.md:17` already says "(prints path)"; only the consequence ("cannot change your shell's directory") is unstated.
- **(a) REFUTED as framed.** The missing `commands/` wrapper is a deliberate design: worktree-kit is one of five phrase-triggered skills (`docs/skills.md`, CHANGELOG "user-invocable: false" dedupe). Since the host-side skills/commands merge, the skill is **already slash-invocable as `/flow-next:flow-next-worktree-kit`** (verified live in the Claude Code menu, 2026-08-12). The real defect is ours: `README.md` §Commands opens "Every skill is invocable as `/flow-next:<name>`", which is false for the five phrase-triggered skills two lines before it names them. Decision: document the real invocation; do NOT promote worktree-kit to a `commands/` wrapper (no count churn, no catalog spend; posture stays).

Tests: `plugins/flow-next/tests/test_worktree_kit.py` never exercises `cleanup`, stdin behavior, or branch tracking — all three fixes need regression pins.

Out of scope: renaming `switch`; any `commands/` wrapper; `push.autoSetupRemote` or other git-config writes; changes to `deps`/`drive`/`export-context` posture.

## Acceptance Criteria

- R1: `cleanup` accepts names as arguments plus `--yes`: `cleanup <name>... [--yes]`. Names given as args skip the first prompt. Confirmation prompt runs only on a TTY (`[[ -t 0 ]]`); non-TTY with names but without `--yes` fails loudly naming the remedy; non-TTY with no names fails loudly with "no terminal and no names given" (never dies inside a bare `read` — both reads are EOF-guarded). Interactive no-arg behavior unchanged. A leading-dash token is never a valid name (`validate_name` already rejects it), so parsing is unambiguous.
- R2: `create`'s new-branch path passes `--no-track`; the created branch has no upstream. Existing-branch path (`git worktree add -- target name`) unchanged.
- R3: `SKILL.md` documents: the non-interactive cleanup form; that `switch` prints the path and cannot change the caller's shell directory (`cd "$(...switch <name>)"` idiom); that `create` sets no upstream (first push needs `-u`/`--set-upstream`).
- R4: `README.md` §Commands no longer overclaims: the opening line distinguishes the 24 slash-command skills (`/flow-next:<name>`) from the 5 phrase-triggered skills, and the phrase-triggered paragraph notes they are also invocable by full skill name (`/flow-next:flow-next-<name>`) on hosts that surface skills as commands. `docs/skills.md` phrase-triggered intro gets the same one-line note.
- R5: regression tests in `test_worktree_kit.py`: cleanup with `</dev/null` and no names exits non-zero with the diagnostic on stderr (not a bare read death); `cleanup <name> --yes` non-interactively removes a registered worktree; `cleanup <name>` non-TTY without `--yes` refuses with remedy text; created branch has no upstream (`git rev-parse --abbrev-ref @{upstream}` fails). Pin contract tokens, not sentences.

## Boundaries

- worktree.sh stays a single self-contained bash script; no new files.
- No `commands/` wrapper, no plugin.json count changes, no codex catalog changes (the codex mirror regen picks up SKILL.md prose via sync-codex.sh — orchestrator runs it at close-out).
- CHANGELOG under `## Unreleased`, credit @sn-furali; no version bump in implementation commits.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_worktree_kit -q
```
