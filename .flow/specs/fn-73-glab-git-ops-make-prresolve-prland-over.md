# fn-73-glab-git-ops-make-prresolve-prland-over Forge adapters and make-pr over GitLab merge requests

> **Refined 2026-11-02** for GitHub issue #462 (reporter @TechupBusiness, who offered to test a branch on a GitLab repo). fn-69 and fn-139 have landed, so the GitLab transport groundwork exists. Plan next. The merge-request `glab` commands are unverified until the first task records them.
>
> **Split 2026-11-04** into three specs, shipped in order: this one (forge adapters, make-pr, and `flow --auto` up to an open MR), then resolve-pr over MR discussions, then land and merge evidence. Customers are blocked on make-pr first.

## Goal & Context
<!-- scope: business -->

flow-next's **code-review / ship pipeline** — `/flow-next:make-pr`, `/flow-next:resolve-pr`, `/flow-next:land` — assumes **GitHub**: it shells out to `gh` and operates on **Pull Requests** + PR review threads (GraphQL). Companies that host their **code** on **GitLab** (not just their tracker) are locked out of the pipeline even though their issues could sync via fn-69.

This is the **code-hosting** counterpart to fn-69 (which is the *tracker/issue* side). This spec lays the forge seam every later forge uses and makes make-pr open and update **GitLab Merge Requests** via **`glab`**, so `flow --auto` on a GitLab origin ends at an open MR. resolve-pr and land over MRs follow in their own specs. **Distinct from fn-69**: fn-69 mirrors specs to GitLab *issues*; this drives GitLab *merge requests*.

As of 9.5.1, a GitLab-hosted run gets past `flow --auto`'s PR probe (#583, fn-310) and make-pr stops cleanly with `NEEDS_HUMAN` before any close or push. This spec replaces that stop with a working merge-request path.

## Architecture & Data Models
<!-- scope: technical -->

- **Map before moving.** The first planning step maps exactly where `gh` and PR-shaped reads are wired in (see Resolved via Codebase) and which of them this spec moves behind the adapter.
- **Reuse fn-69's groundwork:** same `glab` + PAT auth, same self-managed host resolution (`GITLAB_HOST`/`CI_SERVER_URL`), same token-scope findings (`api`; fine-grained needs granular grants).
- **Self-managed first-class** — same as fn-69; never assume gitlab.com.
- **Shape decided 2026-11-02, amended 2026-11-04.**
  - **The forge is derived from the origin remote.** github.com, or a host `gh` is logged in to, means GitHub. A GitLab host (gitlab.com, a host `glab` is logged in to, or `CI_SERVER_HOST`) means GitLab. An unknown host stops with `NEEDS_HUMAN`, as make-pr's preflight does today. There is no config key and nothing is persisted, so the tracker axis and the forge axis stay independent: GitLab issues with GitHub code still works, and so does the reverse.
  - **flowctl answers questions; skills act.** flowctl owns deterministic reads only. Every action (create or update the MR, and later reply, resolve and merge) stays with the agent, using the forge's own CLI as that forge's skill reference describes.
  - **Each forge is an internal adapter behind one interface.** In this spec an adapter answers two questions: does this origin host belong to me, and which PRs or MRs exist for a branch (as the shared row). Later specs add reads to the same interface (merge evidence, merge readiness). A registry keyed by forge name holds the adapters; the forge rule and the shared lookup dispatch through it, and no caller names a forge or branches on one. Internal names are forge-neutral (no `pr_`/`mr_` in the shared code). The existing `gh` calls move behind the GitHub adapter unchanged. A later forge (Bitbucket Cloud, Bitbucket Data Center) adds one adapter and one reference per skill and changes no caller. The interface is internal: no public flowctl verb.
  - **flowctl has one internal "PRs or MRs for this branch" lookup.** Today four places run `gh pr list` themselves: spec-approval PR rows, the route judge, the pilot snapshot, and the tracker's merge evidence. They all call one function, dispatched through the registry, that returns number, url, state, head SHA and merged for any forge.
  - **Each skill dispatches on the forge by name.** make-pr checks the forge once; for any forge other than GitHub it reads that forge's reference (`forge-gitlab.md` beside make-pr). The dispatch names no forge, so a new forge is a new reference file, not a new conditional. GitHub skill paths are not edited.

## API Contracts
<!-- scope: technical -->

- Anchor points to record live: `glab mr create/view/update` or their `glab api` equivalents (see Resolved via Contributor Research), and the MR list by source branch.
- The internal lookup returns the same row for every forge: number (GitHub PR number or GitLab MR iid), url, state (open, closed, merged), head SHA, and merged. Every caller reads only that row.

## Edge Cases & Constraints
<!-- scope: technical -->

- Token scope: writing MRs needs `api` scope (fn-69 finding).
- A missing or unauthenticated `glab` on a GitLab origin stops make-pr before any close or push, naming the `glab auth login --hostname <host>` command.
- Until land's GitLab path ships, `flow --auto --until=merge` on a GitLab origin stops after make-pr with the MR URL and `NEEDS_HUMAN`; it never dispatches land on an MR. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- *(R1–R3 were stubs, superseded by R4–R12; R7–R9 moved to the resolve-pr and land specs in the 2026-11-04 split.)*
- **R4:** The forge comes from the origin remote's host, with no config key; an unknown host stops with `NEEDS_HUMAN`. [paraphrase]
- **R5:** flowctl's four PR lookups (spec-approval rows, route judge, pilot snapshot, tracker merge evidence) share one internal function that answers for GitHub and GitLab, and no public flowctl verb is added. [paraphrase]
- **R6:** On a GitLab origin, make-pr opens or updates a merge request with the same rendered body and close behaviour it uses on GitHub, replacing today's `NEEDS_HUMAN` stop. [inferred]
- **R10:** Behaviour on a GitHub origin is unchanged; the existing make-pr, land, resolve-pr, route, pilot and merge-evidence tests pass unmodified. [inferred]
- **R11:** Each `glab` command this spec relies on is first run against a live GitLab project and its real output saved as a test fixture. Tests with a stubbed `glab` built from those fixtures cover R4–R6 and R12 in CI. [inferred]
- **R12:** Forge-specific code sits behind one internal adapter interface with a registry keyed by forge name, and skills load a forge's reference by name. No caller branches on a forge, and a test adapter registered in the tests is detected and answers the shared lookup without any caller changing. [paraphrase]

## Boundaries
<!-- scope: business -->

- **Not fn-69** — fn-69 is tracker/issue projection; this is code hosting.
- **GitHub/Linear/Jira unaffected** — additive forge.
- **fn-69 and fn-139 have landed.** Reuse their `glab` transport, host resolution and recorded `glab` defects; don't build a second transport.
- No `forge.type` config key and no public forge verbs; the adapter interface stays internal to flowctl (see Architecture).
- No resolve-pr or land over MRs here; they are the next two specs.
- No Bitbucket, Gitea or other forges.
- The full live GitLab end-to-end run (idea → merged MR) happens after the land spec. The reporter of #462 offered to test a branch.

## Decision Context
<!-- scope: both -->

### Motivation
Companies hosting code on GitLab want flow-next's full pipeline, not just issue sync. make-pr is the first blocker customers hit, so it ships first, on the seam the later specs reuse. A disposable self-managed GitLab EE instance (with an Ultimate trial, later Free) is the live test project.

### Implementation Tradeoffs
- **Forge from origin, not a config key.** make-pr's preflight already reads the origin host, and a key could disagree with the remote. The cost is that a repo can't route to GitLab while origin points elsewhere.
- **Seams plus one shared lookup, not a forge layer (#462's proposal).** GitHub paths in the skills stay exactly as they are and are already proven, so the risk sits only in the new GitLab arms. The forge layer would mean about eight new flowctl verbs and rewriting land and resolve-pr's working GitHub paths, against "flowctl grows only under burden of proof" and "Agent first". A third forge later adds one branch to the shared lookup and one reference per skill. That is also the point to extract a layer, designed from three real implementations.
- **Amended 2026-11-04: internal adapters now, not branches.** The maintainer wants a forge added later without touching callers, not an if/else that is refactored at forge three. The adapter interface and registry stay internal (no public verbs, no config key), so the cost is moving the existing `gh` lookups behind the GitHub adapter, guarded by R10's unchanged tests. The interface is designed from two forges, so a third may still widen it; that is accepted.
- **Amended 2026-11-04: reads in flowctl, actions in skills.** Decisions that would otherwise be copied into every forge's prose (which forge, which PR, and later green, approved, merged) live once in tested Python. Actions stay agent-driven through each forge's reference. This keeps machinery minimal and the agent in charge.
- **Split 2026-11-04.** One spec covering make-pr, resolve-pr, land and merge evidence was one very large PR, and customers would wait for all of it. Three specs ship the make-pr unblock first; each is planned, reviewed and landed on its own.
- **Record before relying.** fn-69 verified `glab` for issues only. No merge-request command has been run, so fixtures come from a live project first.

## Strategy Alignment
- **Cross-platform parity** track — extends parity from *trackers* (fn-69/70) to *code hosting*, closing the GitLab-shop gap end-to-end.

## Conversation Evidence
> user: "might be worth creating a stub spec for using this gitlab for testing glab for git ops too for our companies that use gitlab instead of github for code hosting" (2026-06-28)

## Cross-spec dependency (added 2026-07-26)

**Depends on [[fn-139-tracker-sync-determinism-flowctl-owns]].**

fn-139 moves GitLab issue transport out of skill prose and into deterministic flowctl Python, which means it builds the `glab` subprocess plumbing this spec also needs: token/host resolution for self-managed instances, the tier probe (`GET /namespaces/:id -> plan`), and the structured error shape.

It also captures two measured `glab` defects that this spec would otherwise rediscover:

- **`glab` prints its "Multiple config files found" warning to STDOUT**, corrupting JSON parsing.
- **`glab api -F file=@` produces invalid multipart** and **`-f "assignee_ids[]="` is not array-encoded** - both require raw curl.

This spec targets Merge Requests rather than issues, so it is not blocked on fn-139's semantics - only on reusing its transport layer instead of deriving a second, divergent one.

## Resolved via Codebase
- **Where gh is wired in.** flowctl: `_gh_pr_rows` (`scripts/flowctl.py:23590`, used for spec-approval PRs at :23655, :23919 and :23932), `judge_route_state` (:24039), `pilot_snapshot` (:43689), and tracker `merge_evidence` (`scripts/flowctl_tracker/status/policy.py:123`, which also runs `gh pr view` for changed files at :186). Skills: `scripts/make-pr-create.sh`, `scripts/make-pr-preflight.sh` (the origin check at :7-17, and a stacked-PR fetch of `refs/pull/<n>/head` at :75), `skills/flow-next-land/workflow.md` (compare, rulesets, update-branch, run rerun, merge with `--match-head-commit`), `skills/flow-next-resolve-pr/workflow.md` and its four GraphQL scripts, plus the PR probes in `skills/flow-next-flow/auto.md:447` and `references/tail.md:22-49`.
- **The origin check already exists.** `make-pr-preflight.sh:7-17` reads the origin host and stops on a non-GitHub host. That makes it the natural place for the forge decision.
- **The GitLab credential ladder exists.** `scripts/flowctl_tracker/credentials.py:32-86` reads `GITLAB_TOKEN` or glab's per-host stored token.
- **No merge-request transport exists.** The only `glab mr` call in the repo is read-only `glab mr list` in `agents/why-scout.md:32`.

## Resolved via Project Docs
- **fn-69 and fn-139 are done** (`.flow/specs/fn-69-*.json`, `.flow/specs/fn-139-*.json`, status `done`). Their verified `glab` set covers issues only (`.flow/specs/fn-69-tracker-sync-gitlab-adapter-glab-cli.md:16`).
- **Strategy rules.** "flowctl grows only under burden of proof" and "Agent first" (`STRATEGY.md:27-28`) argue against new public verbs and a config key.

## Resolved via Contributor Research
Jan Hommels (@janhommels) ran the merge-request side of `glab` against a live self-managed GitLab in janhommels/flow-next#1. That PR adds public `flowctl forge` verbs and branches inside make-pr's shell scripts, so its shape is not adopted; its measurements are. They are the starting point for R11's fixtures, which are still recorded against a live project.
- **JSON writes need an explicit Content-Type.** `glab api --input` sends none, and GitLab rejects a JSON body without it. Sending the body on stdin also keeps large MR descriptions clear of Windows argv limits.
- **A just-pushed branch can be briefly invisible.** MR create answers `{"message":{"source_branch":["does not exist"]}}`; retry on that exact answer.
- **Open means `opened` plus `locked`.** An open-MR lookup that reads only `opened` misses locked MRs.
- **Drafts are a title prefix.** A draft MR is created with `Draft: ` in front of the title.
- **SSH host aliases resolve through `ssh -G`**, the same way git and gh resolve them, before the origin host is classified.
- **`GH_ENTERPRISE_TOKEN` makes gh claim every host.** When it is set, ask `glab auth status --hostname <host>` before gh.
- **A missing or failing `glab` is a probe failure, never "no MR".**
- **Merged MRs behind a commit:** `projects/:id/repository/commits/<sha>/merge_requests`, keeping `state == merged` (why-scout and the defect route).
