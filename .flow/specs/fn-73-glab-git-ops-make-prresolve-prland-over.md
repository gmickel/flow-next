# glab git-ops — make-pr / resolve-pr / land over GitLab Merge Requests (code-hosting parity)

> **Refined 2026-11-02** for GitHub issue #462 (reporter @TechupBusiness, who offered to test a branch on a GitLab repo). fn-69 and fn-139 have landed, so the GitLab transport groundwork exists. Plan next. The merge-request `glab` commands are unverified until the first task records them.

## Goal & Context
<!-- scope: business -->

flow-next's **code-review / ship pipeline** — `/flow-next:make-pr`, `/flow-next:resolve-pr`, `/flow-next:land` — assumes **GitHub**: it shells out to `gh` and operates on **Pull Requests** + PR review threads (GraphQL). Companies that host their **code** on **GitLab** (not just their tracker) are locked out of the pipeline even though their issues could sync via fn-69.

This is the **code-hosting** counterpart to fn-69 (which is the *tracker/issue* side): teach the git-ops skills to drive **GitLab Merge Requests** via **`glab`** — `make-pr` → create an MR, `resolve-pr` → resolve MR **discussion threads**, `land` → merge the MR — so a GitLab-hosted shop gets the same idea→merged-MR loop. **Distinct from fn-69**: fn-69 mirrors specs to GitLab *issues*; this drives GitLab *merge requests* + review.

As of 9.5.1, a GitLab-hosted run gets past `flow --auto`'s PR probe (#583, fn-310) and make-pr stops cleanly with `NEEDS_HUMAN` before any close or push. This spec replaces that stop with a working merge-request path.

## Architecture & Data Models
<!-- scope: technical -->

- **A forge seam, not three rewrites.** The three skills + the review subsystem (`flowctl rp` / `review-backend` / the resolver agents) are `gh`/PR-shaped today. The likely shape is a thin **forge abstraction** (`github` via `gh` | `gitlab` via `glab`) the skills resolve once (env > config > ask, like the tracker-sync transport + `cmd_review_backend`), mirroring fn-69's "resolve-at-ceremony, persist, no re-probe" model. **First task of real planning: map exactly where `gh` + PR-GraphQL are wired in** (make-pr body render + push + create; resolve-pr's get-comments / reply / resolve GraphQL; land's CI tri-state + merge + post-merge tail).
- **MR ≠ PR — the real deltas:** GitLab MR **discussion threads** + resolvable notes are a different shape than GitHub PR review threads (no GraphQL `reviewThreads`; MR notes/discussions REST + `resolved` flag). CI status = GitLab **pipelines** (not checks). Merge = `glab mr merge` (squash flags differ; no `--match-head-commit` — needs the GitLab equivalent guard). PR-body cognitive-aid render is reusable; the *transport* underneath changes.
- **Reuse fn-69's groundwork:** same `glab` + PAT auth, same self-managed host resolution (`GITLAB_HOST`/`CI_SERVER_URL`), same token-scope findings (`api`; fine-grained needs granular grants), same smoke-test infra (`~/work/agent-scripts/flow-smoke`).
- **Self-managed first-class** — same as fn-69; never assume gitlab.com.
- **Shape decided 2026-11-02 (supersedes the "resolve once, env > config > ask, persisted" sketch above).**
  - **The forge is derived from the origin remote.** github.com, or a host `gh` is logged in to, means GitHub. A GitLab host (gitlab.com, a host `glab` is logged in to, or `CI_SERVER_HOST`) means GitLab. An unknown host stops with `NEEDS_HUMAN`, as make-pr's preflight does today. There is no config key and nothing is persisted, so the tracker axis and the forge axis stay independent: GitLab issues with GitHub code still works, and so does the reverse.
  - **flowctl has one internal "PRs or MRs for this branch" lookup.** Today four places run `gh pr list` themselves: spec-approval PR rows, the route judge, the pilot snapshot, and the tracker's merge evidence. They all call one function that returns number, url, state, head SHA and merged for either forge. No new public flowctl verb is added.
  - **Each skill branches once on the forge.** The GitLab side lives in a GitLab reference per skill (make-pr, resolve-pr, land), with resolve-pr's MR discussion scripts beside the existing GitHub ones. GitHub skill paths are not edited.
  - **A general forge layer waits for a third forge.** A normalized merge-request interface with adapters is built only when a third forge (for example Bitbucket) arrives, so it can be designed from three real implementations.

## API Contracts
<!-- scope: technical -->

- TBD at planning. Anchor points to investigate: `glab mr create/view/merge`, `glab ci`, MR discussions/notes REST (`/projects/:id/merge_requests/:iid/discussions`, the `resolved`/`resolvable` flags), pipeline status.
- The internal lookup returns the same row for both forges: number (GitHub PR number or GitLab MR iid), url, state (open, closed, merged), head SHA, and merged. Every caller reads only that row. The tracker merge evidence's changed-files probe gets the same treatment.
- The land merge on GitLab sends the expected head SHA, so the merge fails if the head has moved (the GitLab merge API's `sha` parameter). It never sets auto-merge. Recent `glab mr merge` versions may enable auto-merge by default; this is unverified, so the first task checks it and uses the API call if that is true.

## Edge Cases & Constraints
<!-- scope: technical -->

- MR thread resolution semantics differ from GitHub (discussions vs review threads) — the resolve-pr "fetch ALL, reply, resolve" loop must be re-grounded on MR discussions.
- `land`'s merge guard (`--squash --match-head-commit`, never `--auto`) needs a GitLab-pipeline + MR-SHA equivalent; **never auto-merge**.
- Token scope: write to MRs + merge needs `api` scope (fn-69 finding).
- GitLab pipeline states are wider than GitHub checks (manual, skipped, canceled, none). land treats anything it cannot read as not green.
- Approvals can be optional, required or unreadable (the tier or permissions hide them). land treats an unknown approval state as not approved.
- A project that forbids squash merges makes land stop with `NEEDS_HUMAN`. It never picks another merge method.
- GitHub-only land steps (merge queue, rulesets, `update-branch`, rerunning failed checks) have no GitLab arm in this spec. Where land needs one of them on GitLab, it stops with `NEEDS_HUMAN`.

## Acceptance Criteria
<!-- scope: both -->

- **R1 (STUB):** A forge abstraction lets `make-pr`/`resolve-pr`/`land` target GitLab MRs via `glab`, GitHub unchanged.
- **R3 (STUB):** Self-managed GitLab honored; `land` never auto-merges; merge guard has a GitLab-SHA equivalent.
- *(Real R-IDs assigned at planning.)*
- **R4:** The forge comes from the origin remote's host, with no config key; an unknown host stops with `NEEDS_HUMAN`. [paraphrase]
- **R5:** flowctl's four PR lookups (spec-approval rows, route judge, pilot snapshot, tracker merge evidence) share one internal function that answers for GitHub and GitLab, and no public flowctl verb is added. [paraphrase]
- **R6:** On a GitLab origin, make-pr opens or updates a merge request with the same rendered body and close behaviour it uses on GitHub, replacing today's `NEEDS_HUMAN` stop. [inferred]
- **R7:** On a GitLab origin, resolve-pr fetches every unresolved MR discussion, replies, and resolves each one it fixed. [inferred]
- **R8:** On a GitLab origin, land reads pipeline and approval state, merges only when green and approved, sends the expected head SHA, never enables auto-merge, and reports `MERGED` with the merge commit. [inferred]
- **R9:** A merged MR is merge evidence for tracker Done, under the same "never terminal without merge evidence" rule as a merged PR. [inferred]
- **R10:** Behaviour on a GitHub origin is unchanged; the existing make-pr, land, resolve-pr, route, pilot and merge-evidence tests pass unmodified. [inferred]
- **R11:** Each `glab` command the skills and flowctl rely on is first run against a live GitLab project and its real output saved as a test fixture. Tests with a stubbed `glab` built from those fixtures cover R4-R9 in CI. [inferred]

## Boundaries
<!-- scope: business -->

- **Not fn-69** — fn-69 is tracker/issue projection; this is code-hosting/MR review + ship.
- **GitHub/Linear/Jira unaffected** — additive forge.
- **fn-69 and fn-139 have landed.** Reuse their `glab` transport, host resolution and recorded `glab` defects; don't build a second transport.
- No `forge.type` config key and no general forge layer (see Architecture).
- No Bitbucket, Gitea or other forges.
- No GitLab merge trains, and no merge-when-pipeline-succeeds.
- The full live GitLab end-to-end run (idea → merged MR) happens later, outside this spec's CI tests. The reporter of #462 offered to test a branch.

## Decision Context
<!-- scope: both -->

### Motivation
Companies hosting code on GitLab want flow-next's full pipeline, not just issue sync. The work is bounded by how forge-agnostic the current `gh`/PR plumbing is — hence a **stub** to capture the idea and the investigation targets before committing scope. The live GitLab smoke-test infra (built 2026-06-28) de-risks it.

### Implementation Tradeoffs
- **Forge from origin, not a config key.** make-pr's preflight already reads the origin host, and a key could disagree with the remote. The cost is that a repo can't route to GitLab while origin points elsewhere.
- **Seams plus one shared lookup, not a forge layer (#462's proposal).** GitHub paths in the skills stay exactly as they are and are already proven, so the risk sits only in the new GitLab arms. The forge layer would mean about eight new flowctl verbs and rewriting land and resolve-pr's working GitHub paths, against "flowctl grows only under burden of proof" and "Agent first". A third forge later adds one branch to the shared lookup and one reference per skill. That is also the point to extract a layer, designed from three real implementations.
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
