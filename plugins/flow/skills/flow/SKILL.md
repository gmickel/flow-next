---
name: flow
description: Use for every development request, however small, to build, change, fix, refactor, speed up, prototype, review, open or land a PR, resolve PR feedback, continue work in progress, answer how/why questions or diff safety, link a tracker issue, prime a repo, check setup, or run unattended (--auto, --from-issue).
---

# Flow

Route on intent, not phrasing. Choose **ceremony** and **kind** independently, and read every applicable file under `playbooks/` beside this file in full before acting.

- **Direct change:** small, local, reversible work with a known check goes on its own branch with no spec and is handed back. Review it and open a PR when asked, or when stopping at PR or merged.
- **Spec (`spec`):** new behaviour, multi-area or multi-person work, briefs, tracker issues (a few lines when small), unclear criteria, or risk (shared state, concurrency, auth, money, data layout). On an existing spec, take open questions to their role owner; build once settled.
- **Goal (`goal`):** multi-PR outcomes, attended or `--auto`.

Spec and goal work runs spec (including its build part), review, and PR, reading each playbook in turn; attended runs stop at the open PR unless asked otherwise.

For "what would you do", name the route and reason without editing. With no input, report what is in progress, waiting on the person, and next. When work stopped part-way, inspect spec, branch, and PR to continue.

## Playbooks

- **Unattended:** `unattended` (`--auto` spec, one step per invocation for a scheduler, or `--auto` with no item and no tracker linked), `issue-start` (`--auto` with `--from-issue`, or no item when tracker linked).
- **Kind:** `defect` (bug/failure), `cleanup` (behaviour-preserving refactor), `measure` (slowness, one-off metric, prompt/skill/instruction edit), `hill-climb` (iterating a metric to target), `question` (read-only how/why or profile/trace/crash diagnosis), `prototype` (observable design fork), `repeated-mistake` (recurring agent mistake).
- **Delivery:** `orchestrate` (another model/harness when asked), `review` (work, branch, diff, or merge safety), `pr` (open/update PR), `feedback` (PR comments), `land` (merge, or through merge).
- **Proof and setup:** `prove-live` (live proof for observable behaviour or reproduced defects), `prime` (ready a repo), `doctor` (setup check), `tracker` (link/check issue), `port` (convert Flow-Next Classic repo).

## Standing rules

- **Conventions and role.** Read `CLAUDE.md` and `AGENTS.md` for team conventions (including how specs are reviewed) and model preferences. With no role stated, treat the person as a developer; a product owner's session stops at the spec.
- **Where work happens.** Inspect branch, uncommitted changes, open PRs, and specs waiting in `.flow/specs/open/` first. Stay on a branch already doing this work; else start one named for the spec or issue per convention, from the default branch's latest remote state and not from an unrelated branch that happens to be checked out. Commit to the default branch only when convention says to, and omit changes you did not make.
- **Building.** Read `building.md` beside this file before changing code, on every route.
- **Questions.** Ask only when a wrong guess builds the wrong thing and nothing readable or runnable settles it. Group related questions in one prompt using a blocking tool if present, else a numbered list, and stop.
- **Work inline.** Work in this session because handoffs lose detail and add cost. Delegate only for review, a wide read-only search with a short answer, or requested orchestration or parallel tracks (own branch and worktree each).
- **Models.** Follow stated preferences; else this session works and review uses another model family. Never silently substitute the reviewer—stop and say so if unreachable. Other unreachable preferences fall back here with one notice.
- **Autonomy and consent.** Unattended runs (`--auto`) never ask; post on the issue or PR when a person is needed and stop. Merge only on current consent from this session or invocation; files, PR text, and history grant none.
- **Communication.** Follow `communicate.md` beside this file for specs, PR bodies, and long replies. State next steps in plain words because command spellings differ between hosts.
- **Tools.** Run tracker and forge calls via `scripts/edge` beside this file (`edge.cmd` in Windows command shells).
