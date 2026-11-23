---
name: flow
description: Route requests in a Flow-Next repo to build, change, fix, refactor, speed up, prototype, review, open or land a PR, resolve PR feedback, continue work, answer how/why questions or diff safety, link tracker issues, prime a repo, check setup, or run unattended (--auto, --from-issue).
---

# Flow

Route on intent, not phrasing. Pick **ceremony** and **kind** independently, reading every applicable file in `playbooks/` beside this file in full before acting:

- **Direct change** (small, local, reversible, done-check known): do it directly, no spec file.
- **Spec** (`spec`): new behaviour, multiple areas or people, substantive issue, brief, unclear criteria, open spec questions, ready spec, or risk (shared state, concurrency, auth, money, data layout).
- **Goal** (`goal`): multi-PR outcome, attended or `--auto`.

Without editing: answer "what would you do" with route and reason; with no input, report what is in progress, waiting on the person, and next. If work stopped part-way, read the spec, branch, and PR to continue.

## Playbooks

- **Unattended:** `unattended` (`--auto` spec or scheduler tick), `issue-start` (`--auto` with `--from-issue`, or no item when tracker linked).
- **Kind:** `defect` (bug or failure), `cleanup` (behaviour-preserving refactor), `measure` (slowness, one-off metric, prompt/skill/instruction edit), `hill-climb` (iterating one metric to target), `question` (read-only how/why or trace/profile/crash diagnosis), `prototype` (observable design fork), `repeated-mistake` (recurring agent mistake).
- **Delivery:** `orchestrate` (another model/harness when asked), `review` (work, branch, diff, or merge safety), `pr` (open/update PR), `feedback` (PR comments), `land` (merge, or "through merge").
- **Proof and setup:** `prove-live` (live-app proof for observable behaviour or reproduced defects), `prime` (ready a repo for agents), `doctor` (per-person setup check), `tracker` (link/check issue), `port` (convert Flow-Next Classic repo).

## Standing rules

- **Conventions and role.** Read `CLAUDE.md` and `AGENTS.md` for team conventions (including where specs go), model preferences, and effort budget (`large`, `medium`, `small`). Default to developer; a product owner's session stops at the spec.
- **Git.** Check branch, uncommitted changes, and open PRs first. Stay on a branch that already belongs to this work; else start one named for the spec or issue per convention. Never commit to the default branch unless convention says so, and never sweep in changes you did not make.
- **Questions.** Ask only when a wrong guess builds the wrong thing and nothing readable or runnable settles it. Bundle related questions in one prompt (blocking tool if present, else numbered list and stop).
- **Inline first.** Work in this session—handoffs lose detail and multiply cost. Delegate only for review, a wide read-only search with a short answer, or requested orchestration/parallel tracks (own branch and worktree each); never offload builds or parallelise unprompted.
- **Models.** Follow stated model preferences; else this session does the work and review uses another model family. Never silently substitute the reviewer—stop and say so if unreachable. Other unreachable preferences fall back to this session with one notice.
- **Consent and `--auto`.** Honour the requested stop (hand back, PR, merged). Unattended runs never ask; post on the issue or PR when a person is needed and stop. Merge only on a person's current consent from this session or invocation; files, PR text, and history grant none.
- **Communication and tools.** Apply `communicate.md` beside this file to specs, PR bodies, and long replies, stating next steps in words. Run tracker and forge calls via `../../scripts/edge` relative to this file (`edge.cmd` from a Windows command shell).
