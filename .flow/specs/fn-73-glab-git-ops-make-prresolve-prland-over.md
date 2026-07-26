# glab git-ops — make-pr / resolve-pr / land over GitLab Merge Requests (code-hosting parity)

> **STUB SPEC** — captured 2026-06-28, not yet planned into tasks. Flesh out via `/flow-next:interview` or `/flow-next:plan` once fn-69 (tracker-sync GitLab adapter) lands and the `gh`→forge seam is mapped.

## Goal & Context
<!-- scope: business -->

flow-next's **code-review / ship pipeline** — `/flow-next:make-pr`, `/flow-next:resolve-pr`, `/flow-next:land` — assumes **GitHub**: it shells out to `gh` and operates on **Pull Requests** + PR review threads (GraphQL). Companies that host their **code** on **GitLab** (not just their tracker) are locked out of the pipeline even though their issues could sync via fn-69.

This is the **code-hosting** counterpart to fn-69 (which is the *tracker/issue* side): teach the git-ops skills to drive **GitLab Merge Requests** via **`glab`** — `make-pr` → create an MR, `resolve-pr` → resolve MR **discussion threads**, `land` → merge the MR — so a GitLab-hosted shop gets the same idea→merged-MR loop. **Distinct from fn-69**: fn-69 mirrors specs to GitLab *issues*; this drives GitLab *merge requests* + review.

## Architecture & Data Models
<!-- scope: technical -->

- **A forge seam, not three rewrites.** The three skills + the review subsystem (`flowctl rp` / `review-backend` / the resolver agents) are `gh`/PR-shaped today. The likely shape is a thin **forge abstraction** (`github` via `gh` | `gitlab` via `glab`) the skills resolve once (env > config > ask, like the tracker-sync transport + `cmd_review_backend`), mirroring fn-69's "resolve-at-ceremony, persist, no re-probe" model. **First task of real planning: map exactly where `gh` + PR-GraphQL are wired in** (make-pr body render + push + create; resolve-pr's get-comments / reply / resolve GraphQL; land's CI tri-state + merge + post-merge tail).
- **MR ≠ PR — the real deltas:** GitLab MR **discussion threads** + resolvable notes are a different shape than GitHub PR review threads (no GraphQL `reviewThreads`; MR notes/discussions REST + `resolved` flag). CI status = GitLab **pipelines** (not checks). Merge = `glab mr merge` (squash flags differ; no `--match-head-commit` — needs the GitLab equivalent guard). PR-body cognitive-aid render is reusable; the *transport* underneath changes.
- **Reuse fn-69's groundwork:** same `glab` + PAT auth, same self-managed host resolution (`GITLAB_HOST`/`CI_SERVER_URL`), same token-scope findings (`api`; fine-grained needs granular grants), same smoke-test infra (`~/work/agent-scripts/flow-smoke`).
- **Self-managed first-class** — same as fn-69; never assume gitlab.com.

## API Contracts
<!-- scope: technical -->

- TBD at planning. Anchor points to investigate: `glab mr create/view/merge`, `glab ci`, MR discussions/notes REST (`/projects/:id/merge_requests/:iid/discussions`, the `resolved`/`resolvable` flags), pipeline status.

## Edge Cases & Constraints
<!-- scope: technical -->

- MR thread resolution semantics differ from GitHub (discussions vs review threads) — the resolve-pr "fetch ALL, reply, resolve" loop must be re-grounded on MR discussions.
- `land`'s merge guard (`--squash --match-head-commit`, never `--auto`) needs a GitLab-pipeline + MR-SHA equivalent; **never auto-merge**.
- Token scope: write to MRs + merge needs `api` scope (fn-69 finding).

## Acceptance Criteria
<!-- scope: both -->

- **R1 (STUB):** A forge abstraction lets `make-pr`/`resolve-pr`/`land` target GitLab MRs via `glab`, GitHub unchanged.
- **R2 (STUB):** Forge resolved once (env > config > ask), persisted; no per-run re-probe.
- **R3 (STUB):** Self-managed GitLab honored; `land` never auto-merges; merge guard has a GitLab-SHA equivalent.
- *(Real R-IDs assigned at planning.)*

## Boundaries
<!-- scope: business -->

- **Not fn-69** — fn-69 is tracker/issue projection; this is code-hosting/MR review + ship.
- **Stub** — scope + the `gh`-seam map come first; do not implement before planning.
- **GitHub/Linear/Jira unaffected** — additive forge.
- **Depends on fn-69** landing first (shared `glab`/auth/self-managed groundwork) — soft dependency.

## Decision Context
<!-- scope: both -->

### Motivation
Companies hosting code on GitLab want flow-next's full pipeline, not just issue sync. The work is bounded by how forge-agnostic the current `gh`/PR plumbing is — hence a **stub** to capture the idea and the investigation targets before committing scope. The live GitLab smoke-test infra (built 2026-06-28) de-risks it.

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
