# Spec-id collisions: widen allocation visibility, make tracker-keyed ids the team default

## Goal & Context
<!-- scope: business -->

`fn-N` spec ids collide in collaborative and agent-parallel settings, and the complaints are correct. The collision is **structural, not unlucky**: `cmd_spec_create` calls `scan_max_native_fn_spec_id(flow_dir)` and adds 1, scanning only the current working tree's `.flow/specs/`. Two branches or worktrees cut from the same base both observe the same max and both allocate `max+1`. It is guaranteed whenever two specs are created in parallel, which in an agent-heavy workflow is the normal case rather than the exception.

This repo carries a live instance: `fn-122-flowctl-hardening-and-performance-completion-sweep` (created 2026-07-21T12:49Z) and `fn-122-harden-verdict-graduate-recurring` (created 2026-07-21T22:45Z). `flowctl validate --all` reports it as a root error today.

**This spec explicitly does NOT drop the number.** The number is not the defect; unqualified local allocation is. The full `fn-N-slug` is already the filesystem, branch, and task identity, so a true identity collision needs the same number AND the same slug. What actually breaks is narrow: a `validate` root error, and ambiguity when the bare `fn-N` shorthand appears in prose. That shorthand is load-bearing across CHANGELOG entries, commit messages, tags, tracker comments, memory entries, and vault notes, and `fn` is a deliberately reserved namespace (`reject_reserved_tracker_key`). Dropping it would be a vocabulary migration on the scale of fn-43's epic-to-spec rename, spent on a symptom that has a much cheaper fix.

Two moves instead:

**A. Widen what the allocator can see** so the common in-repo cases stop colliding.
**B. Make tracker-keyed spec ids the easy default for teams**, because a tracker is a real distributed allocator and collaborative settings are precisely the ones that have one. flow-next already supports this end-to-end and essentially nobody uses it, which is a discoverability and defaults problem rather than an engineering one.

**Honest bound stated up front:** sequential allocation without coordination is unsolvable in general. Move A shrinks the collision window; it does not close it. Two separate clones that have not fetched each other can still collide, and that is what move B is for.

## Architecture & Data Models
<!-- scope: technical -->

### Part A: union-source allocation (flowctl, deterministic)

`scan_max_native_fn_spec_id` becomes a union of three sources, taking the maximum across all of them:

1. **Current working tree** `.flow/specs/` (today's behavior, always available).
2. **Every registered worktree** via `git worktree list --porcelain`, scanning each one's `.flow/specs/`. This closes the *created-but-not-yet-committed* window, which measurement shows is the dominant real-world case: the colliding spec above sat on disk for roughly 6.5 hours before it appeared in any commit. This repo has 16 registered worktrees, each carrying its own `.flow/specs/`.
3. **Every ref**, via a single `git log --all --diff-filter=A --format= --name-only -- <specs-dir>` extracting `fn-<N>`. This closes the *committed on another branch* window and covers fetched remote branches.

**Monotonic, max-ever-allocated.** Source 3 sees specs that were added and later deleted or renamed, so a retired number is never reused. That is deliberate: reusing a retired `fn-N` would resurrect an ambiguous reference in prose and commit history.

**Fail-open, always.** Not a git repo, `git` absent, a worktree path that no longer exists, an unreadable or missing `.flow/` in a sibling worktree, or a `git log` failure each degrade to the sources that did work, worst case source 1 alone. Allocation must never block spec creation on a git problem.

### Part B: tracker-keyed ids as a first-class default (skill + thin config)

flowctl already mints `KEY-N-slug` ids via `spec create --tracker-first --tracker-identifier WOR-17`, resolves bare `wor-17`, and guarantees ids never change. The gap is that reaching it requires knowing the flag and passing the key on every invocation, and the capability is only documented where people are not looking.

New config leaf **`tracker.specIds`**: `"flow"` (default, today's behavior) | `"tracker"`.

The routing is **agentic, in skill prose**, consistent with the repo's split rule: flowctl stays atomic plumbing, the skill composes the multi-step decision. Skills that create specs already hold a root config snapshot (fn-110), so the gate costs **zero new config reads**.

When `tracker.specIds == "tracker"` AND the bridge is active:

- The request already names an issue → mint from that key. **This path works today** ("grab issue X and spec it").
- No issue yet → **this path does not exist yet and must be built.** See below.

### The fresh-idea path needs a new tracker-sync operation

Every current tracker-sync operation takes a **local spec id**: create-if-unlinked renders an existing spec and then writes the issue. There is no operation that creates an issue and returns its key *before* a spec exists. So "create the tracker issue first, then mint" cannot be expressed with today's surface, and a plan that simply instructs five skills to do it would not be executable.

This spec therefore requires a **create-first operation** on tracker-sync that, given a title and body, creates the issue and returns `{id, identifier, url}` with no local spec. The full sequence becomes: create issue → mint `KEY-N-slug` → attach (`sync set-tracker-id` with id, identifier, url) → seed the merge base so the first reconcile is not a spurious conflict.

**Failure recovery is part of the contract, not an afterthought.** Remote creation succeeding while local minting fails would strand an orphan issue and risk creating a second one on retry. The operation must surface the created issue's identifier and url on failure so the run can be resumed by linking rather than re-creating, and a retry must never create a duplicate.

### Network cost: the honest version

An earlier draft claimed tracker-first "adds no net network cost" because flow-first already pushes at the capture/plan touchpoint. **That claim is false in the general case and is withdrawn.** Bridge-active does not imply the relevant `tracker.perEvent.*` leaf is enabled; those leaves default to `off`, and a repo can legitimately run with the bridge active and every lifecycle event off. In that configuration flow-first performs no remote write at all, and tracker-first adds one.

The accurate statement: **when the matching lifecycle touchpoint is already active, tracker-first reorders an existing call rather than adding one; when it is off, tracker-first introduces an earlier remote write that flow-first would not have made.** The setup question must disclose this, because choosing `tracker` means spec creation starts talking to the tracker immediately.

Degradation, in order, each silent-and-continue rather than blocking:
- Bridge inactive or no transport reachable → flow-first `fn-N`.
- Explicit user override in the invocation always wins.

### Part B2: synthetic keys close the GitHub and GitLab gap

Linear and Jira ship a native `KEY-N` identifier (`WOR-17`, `PROJ-123`) that mints directly. GitHub `#123` and GitLab `<project>#<iid>` do not, which is why `--tracker-first` rejects them today. That is a grammar limitation, not a real ambiguity problem, and it is fixable here rather than deferred.

**`.flow/` lives inside exactly one repo, and `tracker.type` pins exactly one tracker.** A GitHub issue number is unique within its repo; a GitLab `iid` is unique within its project. So the scope that makes them ambiguous in the abstract is already pinned by configuration. Mint a **synthetic key derived from `tracker.type`**:

| `tracker.type` | Native identifier | Minted spec id |
|---|---|---|
| `linear` | `WOR-17` | `wor-17-slug` (native key, unchanged) |
| `jira` | `PROJ-123` | `proj-123-slug` (native key, unchanged) |
| `github` | `#123` | `gh-123-slug` (synthetic `gh`) |
| `gitlab` | `<project>#456` | `gl-456-slug` (synthetic `gl`) |

**Type-gating alone does NOT make this safe, and an earlier draft was wrong to claim it did.** "One repo, one type, no overlap" ignores that ids are permanent while configuration is not. Two concrete collisions survive type-gating:

1. A repo runs Linear with team key `GH` and accumulates `gh-123-slug` specs. It is later re-pointed to GitHub. Synthetic minting now produces `gh-123-slug` for issue 123, colliding with a historical native id.
2. A GitHub-configured repo is handed an explicit native `GH-123` identifier at link time, which is still a legal tracker key.

Bare `gh-123` can therefore become ambiguous even when the slugs differ, which is the same failure this spec is trying to remove.

So synthesis needs **contextual reservation plus a preflight**, not just a type check:

- While `tracker.type` is `github` / `gitlab`, the matching prefix (`gh` / `gl`) is reserved for synthesis in that repo: an explicit native identifier using that key is rejected at link and create time with a message naming the conflict.
- Before minting, **preflight the existing store** for a canonical id or resolvable alias that would collide, and refuse with an actionable message rather than creating the duplicate.
- Native `GH` behavior is preserved unchanged while the type remains `linear` / `jira`.
- **Re-pointing `tracker.type`** is a documented hazard on the same footing as re-pointing a GitLab project: previously minted ids keep their meaning, and the preflight is what stops a new mint from colliding with them.

Bare `gh-123` / `gl-456` otherwise resolve as aliases exactly like `wor-17` does, and ids never change.

### Sites to sweep

Spec creation happens in: `flow-next-capture`, `flow-next-plan` (steps.md Route B), `flow-next-work` (phases.md spec-less and markdown-file starts), `flow-next-qa` (references/bug-filing.md), `flow-next-interview` (references/write-back.md). Each needs the gate or an explicit note that it inherits it.

`tracker-first` currently appears in skill prose only in `flow-next-capture/workflow.md` and the tracker-sync skill's own files. `plan`, `work`, and setup never mention it. That is the discoverability defect.

## API Contracts
<!-- scope: technical -->

```bash
flowctl config set tracker.specIds tracker    # or "flow" (default)
flowctl config get tracker.specIds --json
```

- Strict string enum with **two distinct contracts**, because "reject invalid" and "fail closed" are different guarantees and conflating them was ambiguous in an earlier draft:
  - **Write side:** `flowctl config set tracker.specIds <anything-but-flow-or-tracker>` is **rejected** with a usage error, following the ad hoc `cmd_config_set` validation pattern used by `review.backend`.
  - **Read side:** a malformed value that reached the file by hand-editing, a merge, or an older version **fails closed to `flow`**. Only the literal `tracker` activates; a coerced bool or a typo never does.
  - Both contracts are tested.
- No change to `spec create`'s existing flags. `--tracker-first --tracker-identifier` keep working exactly as today; the config only changes what the skills *choose* by default.
- No new flowctl subcommand. Selecting a scheme is configuration; deciding when it applies is skill judgment.

### Setup question, and reaching people who never re-run setup

`/flow-next:setup` gains one question, asked when **a tracker is configured AND `tracker.specIds` is unset**. Both conditions matter:

- Gating on *tracker configured* keeps it meaningless-question-free for solo repos.
- Gating on *unset* is what makes this reach **existing** repos. They already have a tracker and no `specIds` key, so their next setup run asks. Once the key is set either way, setup never asks again: "asks once" means once per repo, not once globally, and an explicit `flow` answer is a real answer that must be respected rather than re-prompted.

The question states the collision rationale rather than offering a bare preference, and defaults to `tracker` for tracker-configured repos.

That still leaves people who never re-run setup, and the tempting fix is a runtime advisory at spec-creation time. **Rejected.** A conditional living in five skill files whose only purpose is to nag is scaffolding built around a discoverability gap, and it rots: it has to be suppressed under autonomy, kept from repeating, and swept every time a new spec-creating site appears. It also fails the repo's own bitter-lesson principle.

The durable answer is a **notable-updates surface** that serves every release rather than this one feature: a short "Notable updates" section on the docs home (repo `plugins/flow-next/docs/README.md`, which is the GitHub docs entry point) and on the flow-next.dev landing page, carrying behavior-affecting changes and new opt-in defaults with a one-line "how to turn it on". This spec seeds it with the `tracker.specIds` entry and establishes the format; later releases append. Discoverability becomes a documented, linkable place people can check, not a message they have to be interrupted by.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Performance is a hard constraint, and the win is that this is a cold path.** The union scan runs in `spec create` only. It must never be added to `list`, `status`, `show`, `ready`, `next`, or any per-tick loop read. Those were taken from about 30 seconds to under half a second by fn-109 and nothing here may regress them. Measured on this repo (325 refs, 16 worktrees): working-tree listdir 27ms; `git log --all` over the spec path adds about 42ms; naive shell iteration over all worktrees costs about 270ms. **Budget: total allocation under 150ms** on a repo of this shape, which requires doing the worktree scan in-process (`os.scandir`) rather than a subprocess per worktree. A test must pin the hot-path commands as untouched.
- **Synthetic-key minting must not widen the reserved-key guard incorrectly.** `fn` stays reserved. `gh` / `gl` are *not* globally reserved: they are synthesized only when `tracker.type` is `github` / `gitlab`, so a Linear or Jira team whose native key happens to be `GH` is unaffected. A test must cover that exact case.
- **GitLab `iid` versus global id.** The minted key uses the project-scoped `iid` (the number in `<project>#<iid>`), never the opaque global id, matching the existing `list-relations` handle rule. A repo that re-points `tracker` at a different GitLab project would produce ids that collide with previously minted ones; ids never change, so this is called out in docs as a re-point hazard rather than auto-handled.
- **Mixed stores are expected and permanent.** An existing repo will hold `fn-N-slug` and `KEY-N-slug` specs side by side. Both resolve, ids never change, and there is no migration or rename. The hybrid id model already specifies this.
- **The existing `fn-122` duplicate must not be renumbered.** Its references live in commit messages, a pushed tag, PR bodies, and tracker comments that cannot be rewritten. Instead: the resolver disambiguates bare `fn-N` the way git disambiguates short hashes (list the candidates, ask for the full id), and `validate` downgrades the duplicate-ordinal root error to a **warning** when the full ids are distinct. A duplicate ordinal with unique identities is untidy, not broken.
- Worktree scanning must tolerate a registered worktree whose path was deleted, lives on another filesystem, is not readable, or has no `.flow/` at all.
- Bare `fn-N` resolution stays supported. This spec does not deprecate it.
- Cross-platform: canonical skill prose changes require `./scripts/sync-codex.sh` twice with the mirror diff committed.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `scan_max_native_fn_spec_id` returns the maximum across the current working tree, every registered worktree's `.flow/specs/`, and every ref, and is monotonic over numbers that were allocated and later removed.
- **R2:** Each source degrades independently and silently. With `git` absent, outside a repo, with a stale or unreadable worktree registration, or on a `git log` failure, allocation still succeeds using whatever sources worked. A unit test covers each failure in isolation.
- **R3:** Allocation completes **under 250ms** on a fixture comparable to this repo (300+ refs, 15+ worktrees), with the worktree scan performed in-process rather than one subprocess per worktree. *(Budget raised from 150ms during task `.1` review, 2026-07-25, on measured evidence: working tree 0.2ms, worktrees ~47ms, refs ~85ms, total ~155ms on a near-worst-case checkout of 327 refs / 16 worktrees / 1723 commits. 150ms sat exactly on the total and was a latent flake. This is a cold `spec create` path that already performs several atomic writes, so the headroom costs nothing observable and preserves all three sources plus monotonicity. The documented fallback - dropping the ref source - was declined because it would trade the committed-on-another-branch window and monotonicity for time nobody perceives.)*
- **R4:** A test pins that the hot-path commands (`list`, `status`, `show`, `ready`, `next`) issue no worktree or ref scan, so the fn-109 latency work cannot regress.
- **R5:** A regression test reproduces the two-worktree collision: create a spec in worktree A without committing, then create one in worktree B, and assert the second gets `max+2` rather than a duplicate.
- **R6:** `tracker.specIds` exists as a strict string enum defaulting to `flow`, with both contracts tested: an invalid value is **rejected** by `config set`, and an invalid value already on disk **fails closed** to `flow` on read. Only the literal `tracker` activates it.
- **R7:** Every spec-creating skill (capture, plan, work, qa, interview) routes on `tracker.specIds` from a **root config snapshot (fn-110), never a per-leaf read, and never more than one snapshot per run**. Where the skill already holds one (plan Step 0, capture preamble) the mint site `jq`s that file and adds no read at all. Where it does not, the skill takes exactly one root snapshot and reuses it: work promotes its Phase 0 `config get work.delegate` leaf read into a root snapshot serving both delegation and minting, so the run performs **one** config read where it previously performed two; interview has no earlier snapshot, so its write-back is where the run's single snapshot is taken. *(Wording corrected at completion review: the original 'adding no new config read' was unsatisfiable for a skill that held no snapshot to begin with, and would have forbidden tracker-first minting there outright.)* Each degrades to flow-first when the bridge is inactive or no transport is reachable.
- **R8:** With `tracker.specIds=tracker` and an active bridge, a spec created from a fresh idea produces a `KEY-N-slug` id via the full sequence: create issue → mint → attach → seed merge base. Network cost is stated accurately, not as a blanket zero-cost claim: **no net new call when the matching `tracker.perEvent.*` touchpoint is already active; one earlier remote write when it is off.** The setup question discloses that choosing `tracker` makes spec creation contact the tracker immediately.
- **R19:** A tracker-sync **create-first** operation exists that creates an issue from a title and body with no local spec and returns `{id, identifier, url}`. On a failure after remote creation it surfaces the created issue's identifier and url so the run resumes by linking, and a retry never creates a duplicate issue. Covered by a fake-adapter test.
- **R21:** `flowctl task set-title <task-id> --title "..."` exists, updates the JSON `title` and the markdown H1 together so they cannot disagree, and is covered by a test. `task set-spec --file` no longer leaves the two out of sync.
- **R22:** A verdict-bearing review finalizes cleanly and **exits zero**. The reset-on-convergence path and the finalize path no longer race over the same reservation. The resolution must be one of: **finalize consumes the reservation before reset clears it**, or **reset stops clearing pending reservations**. Simply tolerating a zero-pending verdict is NOT acceptable on its own: finalize cannot distinguish "cleared by this attempt's own reset" from an unreserved, duplicated, or stale verdict, so that option would let a duplicate verdict finalize and would hole the reservation invariant the deterministic round cap rests on. If a zero-pending verdict is to be allowed at all, it requires **attempt identity** so the finalize can prove it is the same attempt that reserved. Tests: a SHIP drives end to end and asserts exit code 0; the no-verdict transport-failure refund path is unchanged; and **negative paths still fail** - an unreserved verdict and a duplicate finalize are both rejected without recording a second attempt.
- **R20:** Contract tests cover the routing behavior rather than asserting it in prose, split by what is actually executable:
  - **Behavioral, with a counted fake at the transport boundary** - the create -> mint -> attach -> later-touchpoint sequence runs through the real flowctl state transitions and asserts exactly one remote creation across a create, an interrupted mint, and a retry; a genuinely different intent still creates a second issue.
  - **Prose-contract, asserted against the skill files** - the five mint sites, explicit-override precedence, and graceful degradation when no transport is reachable. These are host-agent behaviors with no executable entry point. A Python model of them would re-implement the prose and assert the model against itself, which can pass while the prose it mirrors is wrong; the repo has been bitten by that before, so these stay pinned by file-level contract tests rather than a simulated agent.
- **R9:** `/flow-next:setup` asks the id-scheme question when a tracker is configured **AND `tracker.specIds` is unset**, states the collision rationale, and defaults to `tracker`. Once the key is set to either value it never asks again. A test covers the existing-repo path: tracker configured, key absent, question asked.
- **R10:** *(withdrawn during planning - a runtime advisory in the spec-creating skills was rejected as scaffolding around a docs gap; superseded by R17.)*
- **R11:** Tracker-first is discoverable from where specs are actually created: `plan`, `work`, and `capture` prose name it as the recommended team default, not only the tracker-sync skill's own files.
- **R12:** Bare `fn-N` resolution disambiguates rather than guessing when the ordinal is duplicated, listing candidates and requiring the full id.
- **R13:** `validate` reports a duplicate ordinal whose full ids are distinct as a **warning**, not a root error, and the warning is machine-readable. `validate --all --json` currently exposes `root_errors`, per-spec `warnings`, and `total_warnings` but **no top-level root-warning collection**, so moving the message into the existing warning count would print and count it while dropping its text from JSON. This requires a new top-level field (`root_warnings`), `total_warnings` updated to include it, and text output, docs, and the spec's Quick commands kept consistent. A test covers the live `fn-122` pair in both renderers.
- **R14:** Synthetic-key minting works for `github` (`gh-<issue>`) and `gitlab` (`gl-<iid>`), uses the project-scoped `iid` for GitLab, and is guarded by **contextual reservation plus a preflight**, not type-gating alone: while the type is `github`/`gitlab` the matching prefix is reserved and an explicit native identifier using it is rejected; before minting, the existing store is preflighted for a colliding canonical id or resolvable alias and refuses with an actionable message. Tests cover a Linear/Jira repo natively keyed `GH` (no synthesis, unchanged behavior) and a **mixed historical store** where a `gh-123` spec predates a re-point to GitHub.
- **R15:** Repo docs updated in the same workstream: `docs/tracker-sync.md` (hybrid id model, synthetic keys, the new default), `docs/teams.md` (team recommendation and why), `docs/flowctl.md` (`tracker.specIds`), `docs/architecture.md` (spec-id scheme), plus the sync-codex mirror and a CHANGELOG entry under `## Unreleased`.
- **R16:** flow-next.dev updated in the same workstream: `teams/tracker-sync.mdx` and `teams/collaboration.mdx` (the option exists and is the team default), `flowctl/configuration.mdx` (`tracker.specIds` alongside the other `tracker.*` keys), `specs/schema.mdx` (id scheme), `reference/troubleshooting.mdx` (what to do about a duplicate ordinal), and a new `proof/faq.mdx` entry in the existing question voice covering "two of us created specs and both got the same number". Site build gate passes.
- **R17:** A **Notable updates** surface exists and is seeded, on both the repo docs home (`plugins/flow-next/docs/README.md`) and the flow-next.dev landing page: a short, append-only list of behavior-affecting changes and new opt-in defaults, each one line plus how to enable it. Its first entry is `tracker.specIds`. The section documents its own format so later releases append consistently, and `agent_docs/releasing.md` names updating it as a release step so it does not decay.
- **R18:** Every statement that GitHub or GitLab cannot use tracker-first is corrected, since synthetic keys make it false. Known sites: `docs/tracker-sync.md:47`, `skills/flow-next-tracker-sync/SKILL.md:142`, `skills/flow-next-tracker-sync/steps.md:277-290`, `skills/flow-next-tracker-sync/references/gitlab.md:365-378`, and the equivalent in `references/github.md` if present. A grep sweep proves none remain.

## Boundaries
<!-- scope: business -->

Out of scope:

- **Dropping the `fn-N` ordinal or any identity rename.** Explicitly rejected; see Decision Context.
- **Renumbering existing specs**, including the live `fn-122` pair. Ids never change.
- **Any server, daemon, or lock service.** The zero-external-dependency contract holds; the tracker is used only where a team already has one.
- **Per-contributor number ranges** (`FLOW_SPEC_RANGE`-style). Considered and rejected: it degrades the moment ephemeral agents create specs, and it is a workaround wearing a design's clothes.
- **Closing the separate-clone case.** Move A cannot see an unfetched clone. That is what move B is for, and the limitation is documented rather than papered over.
- **Retro-minting tracker ids for existing `fn-N` specs.** Ids never change. A repo that switches to `tracker` gets tracker-keyed ids for *new* specs only, and the mixed store is permanent and expected.

## Plan-time findings (repo-scout, 2026-07-25) - these shrink the work

Verified against the tree; they change what needs building versus what needs proving:

- **`scan_max_native_fn_spec_id` (flowctl.py:7362-7404) has exactly ONE call site**, `cmd_spec_create:14783`. R4's "hot paths must not scan" is therefore already true today. The task is a pinning test that keeps it true, not a change to `list`/`status`/`show`/`ready`/`next`. Keep the `scan_max_spec_id` / `scan_max_epic_id` aliases at :7407-7408 working.
- **The tracker key grammar already accepts `gh` and `gl`.** `parse_any_id` (:2584-2617) matches `^[a-z][a-z0-9]{0,9}-…`, and only `fn` is globally reserved (`RESERVED_TRACKER_KEY`, :2573). `id_sort_key`, `is_spec_id`, `is_task_id`, `spec_id_from_task` all route through `parse_any_id`, so **no grammar layer changes are needed**. B2 is confined to the minting path.
- **But minting needs a new parse helper.** `validate_tracker_identifier`'s `allow_reference` mode (:2724-2801) is link-time only and returns `("", n, display)` with an EMPTY key, which is the wrong shape for minting a resolvable id. Do not reuse it; add a mint-side parse for `#123` / `<project>#456`.
- **Ambiguity disambiguation may already exist.** `expand_bare_spec_id` (:7498-7581) already errors with "Spec id … is ambiguous. Matches: … Use the full slug to disambiguate." for the native-`fn` branch, tested in `test_expand_bare_spec_id.py:69,84`. **Verify against the live `fn-122` pair before writing any resolver code** - R12 may reduce to a regression test.
- **The validate downgrade is a retarget, not new logic.** `cmd_validate:26363-26386` appends to `root_errors`; the "full ids are distinct" condition is structurally guaranteed because ids come from unique file stems. Existing assertions in `test_validate_all_diagnostics.py:93-146` expect `root_errors` and must move to warnings.
- **Reuse the existing git subprocess shape.** `_prime_git` (:26681-26706) uses `git -C`, `capture_output`, `text`, `check=False`, an explicit `timeout`, and catches `TimeoutExpired` / `OSError` / `SubprocessError` without raising. Match it. There is no existing `git worktree list --porcelain` parser or `git log --all` caller; both are new. `_prime_sibling_git_dirs` (:26975) has reusable logic for tolerating gitdir-pointer worktrees.
- **Config leaf placement.** `tracker.*` defaults live in `get_default_tracker_config()` (:1069-1080); strict-enum precedent is `pipeline.qa` (:1322) and `pilot.autonomy` (:1339). There is no central enum registry, so write-time validation follows the ad hoc `cmd_config_set` pattern (:9032+, e.g. `review.backend` at :9043). **Open item for the implementer:** R9 needs `tracker.specIds` to be *unset-detectable*, so decide deliberately whether it materializes at `init` (like `pipeline`) or stays unmaterialized (`_INIT_UNMATERIALIZED_BLOCKS`, :1358) - a materialized default of `flow` would make "unset" indistinguishable and silently break the setup question.
- **Git colour hazard.** Forced ANSI colour breaks regex post-filters on git output (memory `forced-color-git-grep-output-defeats-2026-07-19`). Pass `--no-color` or neutralize config in the scan.

## Incidental flowctl fixes (found while planning this spec)

Two papercuts surfaced during fn-134's own planning. Neither belongs to the collision thesis; both are small, atomic, zero-judgment flowctl gaps, and they are folded in here rather than spawning a spec each.

**1. No `task set-title`.** `flowctl task` offers `create`, `set-description`, `set-acceptance`, `set-spec`, `reset`, `set-backend` - but no way to change a title after creation. Restructuring a plan mid-review is normal (this spec's own review split one task into two and shifted four others), and the only route today is hand-editing `.flow/tasks/<id>.json`, which violates the "never edit `.flow/*` directly" rule the file header states. Note that `task set-spec --file` rewrites the markdown H1 but leaves the JSON `title` untouched, so the two silently disagree - the markdown says one thing and `flowctl tasks` lists another.

**2. A converged review exits non-zero after succeeding.** On a SHIP verdict the reset-on-convergence helper pops the pending reservation (`flowctl.py:7070-7073`), and the finalize path then finds `pending_count == 0` and calls `error_exit(..., code=2)` with "No reserved <kind>-review round exists ... refusing to finalize or refund" (`:6888-6898`). Observed live on this spec's round 3: the verdict was written, `plan_review_status` became `ship`, the counter reset correctly, **and the command still exited non-zero**. This is not cosmetic. An autonomous pilot or land tick that treats a non-zero review exit as a transport failure would retry or escalate a review that had already converged, which is exactly the runaway class the deterministic round cap exists to prevent.

## Decision Context
<!-- scope: both -->

### Why not drop the number

The strongest case for dropping it is real: sequential allocation without coordination is unsolvable in general, ids would get *shorter*, slug collisions are semantically informative because two people writing the same slug are probably duplicating work, and git set the precedent that nobody misses sequence numbers.

It loses on cost-benefit. The number is not the identity, so what actually breaks is a validate error plus prose ambiguity. Against that, dropping it forfeits at-a-glance backlog chronology, breaks bare-`fn-N` shorthand that is everywhere in prose and muscle memory, requires coordination with flow-swarm which reads `.flow/specs/` natively, and partly discards a deliberately reserved namespace. That is fn-43-scale disruption for a symptom that move A mostly removes.

### Why the allocator moved backwards once already

The original design incremented `meta.json` `next_spec`. Scan-based allocation replaced it explicitly "for merge safety" and to "reduce merge conflicts" (flowctl.py:14846). It succeeded at that, by converting a **loud** merge conflict into a **silent** duplicate that surfaces weeks later in a validate run. That is a worse failure mode. Union-source allocation restores failure-at-creation without reintroducing the conflicting write, because it reads rather than writes shared state.

### Why ref-scanning alone is not enough

The first version of this analysis proposed scanning refs only. Measurement falsified it as a complete fix: the live collision's first spec existed on disk for about 6.5 hours before appearing in any commit, and a ref scan is blind to that window. Worktree scanning is what closes the dominant case, and this repo's 16 worktrees show why it matters in agent-heavy use. Both sources are kept because they cover different windows.

### Why tracker-first is the team answer

A tracker is a real distributed allocator that a team already coordinates on, and collaborative settings are exactly the ones that have one. The machinery is shipped and first-class today. The reason it is unused is that it costs two flags per invocation and is documented only where people are not looking. That makes this a defaults and discoverability problem, and the fix belongs in skill prose and setup rather than in new engineering.

## Quick commands

Focused suites for this feature. The FULL suite runs ONCE at the final gate, not per task.

```bash
# Allocation, resolution, validate, config leaves
cd plugins/flow-next/tests && python3 -m unittest \
  test_expand_bare_spec_id test_validate_all_diagnostics test_tracker_config \
  test_flowctl_surface test_startup_bootstrap -q

# Spec-id allocation smoke against the real store
.flow/bin/flowctl validate --all --json | jq '{total_errors, total_warnings, root_errors, root_warnings}'
.flow/bin/flowctl show fn-122 --json 2>&1 | head -3   # ambiguity path

# Skill prose changed -> mirror must regenerate idempotently
./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --porcelain plugins/flow-next/codex/

# Site gate (task .5 only)
cd ~/work/flow-next.dev && pnpm build
```

## Early proof point

Task `.1` validates the core bet of move A: that a union scan over the working tree, all registered worktrees, and all refs stays inside the 150ms budget on a repo of this shape (325 refs, 16 worktrees) while actually catching the two-worktree collision.

If it cannot hit the budget, stop and re-scope before `.2` (this fired on 2026-07-25 and resolved by raising the budget to 250ms on measured evidence rather than dropping a source): the fallback is to drop the ref scan (the cheaper, lower-value source) and keep worktree scanning, which measurement shows covers the dominant created-but-uncommitted window. Do not silently ship a slow allocator.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Union allocation across worktree + worktrees + refs, monotonic | .1 | - |
| R2 | Every source degrades independently and silently | .1 | - |
| R3 | Under 150ms on a 300-ref / 15-worktree fixture, in-process | .1 | - |
| R4 | Hot-path commands pinned as scan-free | .1 | - |
| R5 | Two-worktree collision regression test | .1 | - |
| R6 | `tracker.specIds` strict enum, default `flow` | .2 | - |
| R7 | Spec-creating skills route on the config, no new config read | .4 | - |
| R8 | Full create->mint->attach->seed sequence; honest conditional network-cost statement | .4 | - |
| R9 | Setup asks when tracker configured AND key unset; never re-asks; discloses the remote write | .4 | - |
| R10 | *(withdrawn during planning)* | - | Superseded by R17 |
| R11 | Tracker-first named in plan / work / capture prose | .4 | - |
| R12 | Bare `fn-N` disambiguates on duplicate ordinal | .2 | May already hold; task verifies before building |
| R13 | Duplicate ordinal is a machine-readable warning via a new `root_warnings` field | .2 | - |
| R14 | Synthetic keys with contextual reservation + preflight; mixed-history test | .2 | - |
| R15 | Repo docs + CHANGELOG + mirror | .5 | - |
| R16 | flow-next.dev pages + FAQ + build gate | .6 | - |
| R17 | Notable-updates surface, seeded, format documented, release step | .5, .6 | repo home in .5, landing page in .6 |
| R18 | Every GitHub/GitLab "flow-first only" statement corrected | .5 | - |
| R19 | tracker-sync create-first operation + failure recovery, no duplicate on retry | .3 | - |
| R20 | Behavioral sequence test (counted fake) + prose-contract tests for mint sites, degradation, override | .3, .4 | sequence in .3, routing/prose in .4 |
| R21 | `task set-title` keeps JSON title and markdown H1 in sync | .7 | incidental fix |
| R22 | Converged review exits zero; reservation race removed | .7 | incidental fix |
