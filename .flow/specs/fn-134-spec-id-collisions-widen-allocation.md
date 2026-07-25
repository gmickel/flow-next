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

- The request already names an issue → mint from that key.
- No issue yet → create the tracker issue first via tracker-sync, then `spec create --tracker-first --tracker-identifier <key>`.

**This adds no net network cost.** Flow-first already pushes to the tracker at the capture/plan touchpoint (`tracker.perEvent.capture` / `.plan`). Tracker-first reorders that same call earlier in the same run rather than adding one.

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

The synthetic key is used **only** when `tracker.type` matches, so it cannot collide with a real tracker key: a Linear team literally keyed `GH` still mints `gh-…` from its own native key, because type is `linear` and no synthesis happens. One repo, one type, no overlap. Bare `gh-123` / `gl-456` resolve as aliases exactly like `wor-17` does, and ids never change.

### Sites to sweep

Spec creation happens in: `flow-next-capture`, `flow-next-plan` (steps.md Route B), `flow-next-work` (phases.md spec-less and markdown-file starts), `flow-next-qa` (references/bug-filing.md), `flow-next-interview` (references/write-back.md). Each needs the gate or an explicit note that it inherits it.

`tracker-first` currently appears in skill prose only in `flow-next-capture/workflow.md` and the tracker-sync skill's own files. `plan`, `work`, and setup never mention it. That is the discoverability defect.

## API Contracts
<!-- scope: technical -->

```bash
flowctl config set tracker.specIds tracker    # or "flow" (default)
flowctl config get tracker.specIds --json
```

- Strict string enum. Only the literal `tracker` activates; any other value, including a coerced bool or a typo, resolves to `flow`. Matches the existing strict-enum convention used by `pipeline.qa` and `pilot.autonomy`.
- No change to `spec create`'s existing flags. `--tracker-first --tracker-identifier` keep working exactly as today; the config only changes what the skills *choose* by default.
- No new flowctl subcommand. Selecting a scheme is configuration; deciding when it applies is skill judgment.

### Setup question, and reaching people who never re-run setup

`/flow-next:setup` gains one question, asked when **a tracker is configured AND `tracker.specIds` is unset**. Both conditions matter:

- Gating on *tracker configured* keeps it meaningless-question-free for solo repos.
- Gating on *unset* is what makes this reach **existing** repos. They already have a tracker and no `specIds` key, so their next setup run asks. Once the key is set either way, setup never asks again: "asks once" means once per repo, not once globally, and an explicit `flow` answer is a real answer that must be respected rather than re-prompted.

The question states the collision rationale rather than offering a bare preference, and defaults to `tracker` for tracker-configured repos.

That still leaves people who never re-run setup. For them, the spec-creating skills emit **one advisory line** when a tracker is active, `tracker.specIds` is unset, and they are about to mint a flow-first id: name the collision risk and the one-line fix. Constraints, so this does not become nagging: advisory only (never a prompt, never blocking), **interactive mode only** (suppressed under `mode:autonomous` / Ralph, where nobody can act on it), and it disappears permanently the moment the key is set either way. No new state is tracked to achieve this; the unset key *is* the state.

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
- **R3:** Allocation completes under 150ms on a fixture comparable to this repo (300+ refs, 15+ worktrees), with the worktree scan performed in-process rather than one subprocess per worktree.
- **R4:** A test pins that the hot-path commands (`list`, `status`, `show`, `ready`, `next`) issue no worktree or ref scan, so the fn-109 latency work cannot regress.
- **R5:** A regression test reproduces the two-worktree collision: create a spec in worktree A without committing, then create one in worktree B, and assert the second gets `max+2` rather than a duplicate.
- **R6:** `tracker.specIds` exists as a strict string enum defaulting to `flow`; only the literal `tracker` activates it.
- **R7:** Every spec-creating skill (capture, plan, work, qa, interview) routes on `tracker.specIds` using the existing config snapshot, adding no new config read, and each degrades to flow-first when the bridge is inactive or no transport is reachable.
- **R8:** With `tracker.specIds=tracker` and an active bridge, a spec created from a fresh idea produces a `KEY-N-slug` id, having created the tracker issue first. Net tracker network calls for the run are unchanged versus flow-first, because the existing push touchpoint is reordered rather than duplicated.
- **R9:** `/flow-next:setup` asks the id-scheme question when a tracker is configured **AND `tracker.specIds` is unset**, states the collision rationale, and defaults to `tracker`. Once the key is set to either value it never asks again. A test covers the existing-repo path: tracker configured, key absent, question asked.
- **R10:** Spec-creating skills emit a single advisory line when a tracker is active, `tracker.specIds` is unset, and a flow-first id is about to be minted. It is advisory only (never a prompt, never blocking), suppressed under `mode:autonomous` and Ralph, and disappears once the key is set either way. No new persisted state.
- **R11:** Tracker-first is discoverable from where specs are actually created: `plan`, `work`, and `capture` prose name it as the recommended team default, not only the tracker-sync skill's own files.
- **R12:** Bare `fn-N` resolution disambiguates rather than guessing when the ordinal is duplicated, listing candidates and requiring the full id.
- **R13:** `validate` reports a duplicate ordinal whose full ids are distinct as a **warning**, not a root error. A test covers the current live `fn-122` pair.
- **R14:** Synthetic-key minting works for `github` (`gh-<issue>`) and `gitlab` (`gl-<iid>`), uses the project-scoped `iid` for GitLab, and is applied only when `tracker.type` matches. A test covers a Linear/Jira repo whose native key is `GH`, asserting no synthesis and no collision.
- **R15:** Repo docs updated in the same workstream: `docs/tracker-sync.md` (hybrid id model, synthetic keys, the new default), `docs/teams.md` (team recommendation and why), `docs/flowctl.md` (`tracker.specIds`), `docs/architecture.md` (spec-id scheme), plus the sync-codex mirror and a CHANGELOG entry under `## Unreleased`.
- **R16:** flow-next.dev updated in the same workstream: `teams/tracker-sync.mdx` and `teams/collaboration.mdx` (the option exists and is the team default), `flowctl/configuration.mdx` (`tracker.specIds` alongside the other `tracker.*` keys), `specs/schema.mdx` (id scheme), `reference/troubleshooting.mdx` (what to do about a duplicate ordinal), and a new `proof/faq.mdx` entry in the existing question voice covering "two of us created specs and both got the same number". Site build gate passes.

## Boundaries
<!-- scope: business -->

Out of scope:

- **Dropping the `fn-N` ordinal or any identity rename.** Explicitly rejected; see Decision Context.
- **Renumbering existing specs**, including the live `fn-122` pair. Ids never change.
- **Any server, daemon, or lock service.** The zero-external-dependency contract holds; the tracker is used only where a team already has one.
- **Per-contributor number ranges** (`FLOW_SPEC_RANGE`-style). Considered and rejected: it degrades the moment ephemeral agents create specs, and it is a workaround wearing a design's clothes.
- **Closing the separate-clone case.** Move A cannot see an unfetched clone. That is what move B is for, and the limitation is documented rather than papered over.
- **Retro-minting tracker ids for existing `fn-N` specs.** Ids never change. A repo that switches to `tracker` gets tracker-keyed ids for *new* specs only, and the mixed store is permanent and expected.

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
