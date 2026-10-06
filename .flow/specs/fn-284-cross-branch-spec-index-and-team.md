# Cross-branch spec index and team branching docs

## Goal & Context

<!-- Source: 45% user / 35% [paraphrase] / 20% [inferred] -->

Teams that use Flow-Next keep asking for a branching strategy for specs, and there has been no good answer, in one repo or several in the constellation pattern. People create specs in teams, specs are not always on main, and many teams like long-lived branches per spec. Git offers no strategy for seeing specs across those branches. Today's workarounds are prose: an instruction-file line telling the agent to check origin's pushed branches for other specs.

Today flowctl only sees the checked-out `.flow/`. A spec that exists only on a teammate's pushed branch is invisible to listing, to spec-scout, and to any consumer (MergeFoundry's cockpit included). The only cross-branch read is native id allocation's `--all` ref scan, and it never fetches. Field evidence from this repo: six `fn-N` numbers are each shared by two specs, created on branches that could not see each other. That is cosmetic (ids are full slugs, and a bare-number lookup refuses as ambiguous), but it shows how often specs are created out of each other's sight.

This spec adds one read-only, deterministic index over git refs to the existing `flowctl specs` listing. Specs stay ordinary files on branches (spec-as-PR review and spec-moves-with-code stay intact). It also writes the team doctrine and the hygiene that make the index useful. People must push for their specs to be visible, fetch to see others', and clean up old branches. [paraphrase]

The agent-first test (G4): the unattended failure this prevents is plan's spec-scout (and `flow --auto`, and MergeFoundry) planning or building against an incomplete picture of in-flight specs. That means duplicated specs and missed dependencies, which today only a non-deterministic prose instruction guards against. The flag replaces that instruction rather than adding a gate. Nothing must be filled before acting. [inferred]

## Architecture & Data Models

<!-- Source: 10% [paraphrase] / 90% [inferred] -->

- **Inputs:** local branches and remote-tracking refs (`refs/heads/*`, `refs/remotes/*`, symbolic `HEAD` refs excluded), plus one base ref resolved first-match: `origin/HEAD`, `origin/main`, `main`, `origin/master`, `master`. Read-only git plumbing only (ref listing, tree listing, batched blob reads, merge-base, and an in-memory three-way file merge that writes no objects). No new storage, no state file, no cache.
- **Unit:** a spec id is a filename stem under `.flow/specs/` that is a spec id (a task-shaped stem with a `.N` suffix is not). The body (`.md`) decides classification; the JSON sidecar only supplies display metadata (title, status, tracker url), taken from base's sidecar when the spec is on base, otherwise from the live copy on the first ref in sorted order. A malformed chosen sidecar shows those fields as null. The sidecar changes with review and status metadata on every branch, so it is never used to judge divergence.
- **Classification of each ref's copy** against base:
  - identical body to base → not reported;
  - **live:** the branch changed the spec since its merge-base with base, and a three-way merge of (base, merge-base, branch) would change base's body. The flag `conflict` is set when that merge has conflicts. This test is squash-merge safe: a squash-merged branch's changes are already in base and merge to base's body;
  - **stale:** everything else that differs: an older copy the branch never touched, a merged copy, or a copy of a spec that base has since deleted (checked through base's history for a delete of that path).
- **Spec-level rollups:** branch-only (absent from base, at least one live copy); ahead of base (on base, at least one live copy); concurrent edits (more than one distinct live body); would conflict (any live copy with `conflict`).
- **Consumers:** spec-scout reads a live branch-only or ahead copy with `git show <ref>:<spec path>`. Status never decides visibility: a live copy is in-flight work whatever its sidecar says. No new flowctl reader verb. MergeFoundry consumes the JSON through its existing flowctl bridge (separate repo, out of scope here). [paraphrase]

## API Contracts

```text
flowctl specs --refs [--fetch] [--json]
```

- `--refs` with no `--fetch` reads only refs already present locally (no network).
- `--fetch` first runs a prune fetch of `origin`, then indexes.
- Plain `flowctl specs [--json]` is unchanged byte for byte: existing callers do not move.

JSON shape (the fields shown are the contract):

```json
{
  "success": true,
  "base": "refs/remotes/origin/HEAD",
  "fetched": false,
  "fetch_error": null,
  "refs_scanned": 85,
  "summary": {
    "branch_only": ["fn-12-login-flow"],
    "ahead_of_base": ["fn-9-export"],
    "concurrent_edits": ["fn-9-export"],
    "would_conflict": [],
    "local_branches_upstream_gone": ["refs/heads/old-feature"]
  },
  "specs": [
    {
      "id": "fn-9-export",
      "title": "Export",
      "status": "open",
      "on_base": true,
      "live": [
        {"ref": "refs/remotes/origin/feat/export", "tip_date": "2026-10-06", "conflict": false},
        {"ref": "refs/remotes/origin/feat/export-v2", "tip_date": "2026-10-05", "conflict": false}
      ],
      "stale_refs": ["refs/remotes/origin/fn-3-old-branch"],
      "tracker": null
    }
  ]
}
```

`specs` lists every spec id seen on base or any scanned ref (base-only specs carry an empty `live` and `stale_refs`), so a consumer can render the whole board. Text output (no `--json`): the summary counts, then one line per branch-only or ahead spec naming its live refs, marking conflict and multiple versions.

## Edge Cases & Constraints

- **Performance:** on this repository at capture time (~130 refs, ~270 specs) the index completes in under 2 seconds without `--fetch`. Measured prototype: 1.0 s (remote refs) to 1.4 s (all refs). A whole-tree `merge-tree` per branch was measured at 5.4 s and is not the design. [inferred]
- **Squash merges:** git cannot tell a long-merged squash branch whose copy conflicts with later base edits from an unmerged conflicting edit. Such copies report as live with `conflict: true` and an old `tip_date`. The fix is branch hygiene (docs), not a forge query. Measured: all such copies in this repo belong to PRs that were merged. [inferred]
- **Read-only:** without `--fetch` the command writes nothing (no refs, no objects, no `.flow/` files). With `--fetch` the only write is git's own fetch updating and pruning remote-tracking refs. [inferred]
- **Git version:** flow-next states no minimum git version, and the index must not introduce one. It relies only on long-standing plumbing; for example, the three-way check reads blobs and merges them locally rather than depending on `merge-file --object-id` (git 2.43+). [inferred]
- **Verification:** the command and the scout handoff are tested against disposable git fixtures (an origin plus clones) that replay the experiment's scenarios and R1/R2/R4 error cases, and assert that plain `flowctl specs` output is unchanged and that a run without `--fetch` writes nothing. R6 is timed on this repository. [inferred]
- **Consumers polling:** fetching stays opt-in so a polling consumer (MergeFoundry's daemon) never does network work it did not choose. [paraphrase]

## Acceptance Criteria

- **R1:** `flowctl specs --refs` lists every spec found on base, on local branches, and on remote-tracking refs, without network access, and plain `flowctl specs [--json]` output is unchanged. Errors: no resolvable base ref → `success: false` JSON error naming the candidates tried, exit 1; a ref whose tree has no `.flow/specs` is skipped; a malformed sidecar on a ref yields a row with `title`/`status` null instead of a crash; not a git repo → the same error path as other git-backed flowctl reads. [inferred]
- **R2:** Each differing copy is classified live or stale by the three-way-merge test described in Architecture & Data Models. A squash-merged branch's copy, an untouched older copy, and a copy of a spec deleted on base are stale. A branch's unmerged edit stays live even after base edits other lines of the same spec. Errors: a branch with no merge-base with base (unrelated or shallow history) counts its differing copies as live with `conflict: false`. [inferred]
- **R3:** The summary reports branch-only specs, specs ahead of base, specs with more than one distinct live version, specs whose live copy would conflict, and local branches whose upstream is gone. Each appears in the JSON shape shown in API Contracts. No error surface beyond R1. [inferred]
- **R4:** `--fetch` performs a prune fetch of `origin` before indexing, so a teammate's newly pushed spec appears and a deleted remote branch stops contributing copies. Errors: fetch failure (offline, no `origin`, auth) → the index is still built from local refs, `fetched: false`, and `fetch_error` carries git's message, exit 0. [inferred]
- **R5:** Without `--fetch` the command makes no network call and writes no refs, objects, or `.flow/` files; repeated runs on unchanged refs produce identical output. No error surface beyond R1. [inferred]
- **R6:** On a repository with ~130 refs and ~270 specs, `flowctl specs --refs` without `--fetch` completes in under 2 seconds on the maintainer's machine. Verified by timing it on this repository. No error surface beyond R1. [inferred]
- **R7:** spec-scout includes live branch-only and ahead-of-base specs from `flowctl specs --refs --json` in its relationship scan, reading each copy from its ref. It names the ref in its findings. A dependency or reverse dependency is reported only on a related spec that exists in the checkout, because the planner records the edge once the new spec exists; any other cross-branch relationship is reported as an overlap that names the ref. Overlap checks read the ref copy, and task-level overlap stays checkout-only. A copy flagged `conflict` is still reported as an overlap, annotated with the conflict and its tip date, so the reader can tell a stale merged branch from a live collision. Live copies count regardless of their sidecar status. In a repo where the index reports none, its output is unchanged. Errors: a flowctl without `--refs` support (exit 2, `unrecognized arguments: --refs`) → the scout continues with the checkout-only listing it uses today. [paraphrase]
- **R8:** The teams guide on flow-next.dev gains a section on specs across branches. It covers the three supported shapes (the spec travels with code on its feature branch; spec-as-PR merged to main first; a separate spec repo) and visibility: people need to push for their specs to be visible, and fetch (`--fetch`) to see others'. It also covers hygiene: delete merged branches (the forge's delete-head-branch-on-merge setting), prune remote-tracking refs, and delete local branches whose upstream is gone, because old branches surface as stale or would-conflict copies. And it covers tracker-sync as the board for people across branches. Its "Spec ids when several people create work" section says a repeated `fn-N` is cosmetic: ids are full slugs, a bare-number lookup refuses as ambiguous and names both, and tracker-minted ids are the option for teams that want unambiguous short keys. [strategy:Spec-driven team patterns]
- **R9:** The flow-next.dev CLI reference documents `specs --refs [--fetch] [--json]`, the JSON shape, the live/stale meaning, and the older-flowctl signal (exit 2, `unrecognized arguments: --refs`) that consumers use to fall back. The flowctl runtime reference's multi-user section names the index. [inferred]

## Boundaries

- No new storage engine, database, custom `refs/flow/*` namespace, merge driver, or git hook; specs stay ordinary files on branches. [inferred]
- No tracker join in the index (matching tracker issues that have no spec on any ref); backlog mode's `list-open` union already covers that, and it needs a live tracker. [inferred]
- No duplicate-number report, renumbering, or auto-fix: a repeated `fn-N` is cosmetic (ids are full slugs; a bare-number lookup refuses as ambiguous). [paraphrase]
- No forge (GitHub/GitLab) query to decide merged-ness. [inferred]
- MergeFoundry's consumption of the index is MergeFoundry's own work in its own repo. [paraphrase]
- No change to native id allocation. [inferred]

## Decision Context

Why an index over git and not a new store: the field question was branching strategy for specs, and today's answers are prose workarounds. Dolt and the current Beads design (Dolt-only since 0.58, data on `refs/dolt/data` on the existing remote) were reviewed and rejected for specs:

- cell-level merge turns two edits of a prose spec body into a whole-cell conflict, where git merges by line;
- the structured fields Dolt merges well already left git (runtime claim state lives in the git common dir);
- embedding is Go-only, the binary is 127 MB, and the version is pinned;
- it would break spec-as-PR review and the zero-dependency contract.

A custom git ref for spec state was rejected for the same costs as a separate spec repo, without that repo's visibility. Treating the tracker as source of truth contradicts the projection doctrine. A separate spec repo stays a documented shape for PO-heavy teams. [paraphrase]

Why flow-next and not MergeFoundry: the index is CLI plumbing every team with more than one developer needs. MergeFoundry already reads `.flow/` only through flowctl, so it can consume the new flag instead of building its own index (user: "mergefoundry could just consume our new command as it uses flow-next"). MergeFoundry today sees repos and machines but only each repo's checked-out `.flow/`; multiplayer (its fn-171) would extend its multi-machine client, not add a store. [paraphrase]

Rejected mechanisms, each measured: a JSON-sidecar comparison (108 of 273 specs flagged on this repo, nearly all metadata churn on old branches); a newest-`updated_at` rule (unreliable for the same reason); a last-change-date "superseded" rule (it misclassified a live unmerged edit after base changed the spec); whole-tree `merge-tree` per branch (correct but 5.4 s). A duplicate-number report was dropped: a repeated `fn-N` prevents no unattended failure (G4), because lookup by bare number already fails closed. A `flowctl cat --ref` reader was rejected in favour of `git show`, so the change adds a flag and no verb. [inferred]

## Strategy Alignment

- Zero external dependencies, everything under `.flow/` in the repo: the index is git plumbing over existing files, with no service, database, or new binary. [strategy:Spec-driven team patterns]
- Spec-driven team patterns: the docs extend the teams guide with the branching doctrine the field keeps asking for. [strategy:Spec-driven team patterns]
- Cloud orchestration belongs to MergeFoundry: MergeFoundry consumes the JSON; flow-next owns the stable handover surface. [strategy:flow-swarm preparation (contract pillars SHIPPED)]

## Resolved via Experiment

<!-- Source: measured in the capture session (prototype + simulation in a scratch directory; nothing shipped) -->

A disposable prototype (git plumbing, no flowctl changes) and a two-developer simulation (a bare origin plus clones for Alice, Bob and Carol, specs minted by the real flowctl) settled the design before this spec was written.

### Real repository (this repo, 130 refs, 274 specs)

- Index time: 1.0 s (remote refs) / 1.4 s (all refs), with each distinct blob read once.
- 6 `fn-N` numbers are shared by two specs (`fn-122`, `fn-142`, `fn-202`, `fn-204`, `fn-240`, `fn-271`). Cosmetic: `flowctl show fn-122` refuses with `Spec id 'fn-122' is ambiguous` and names both slugs. A stray task-shaped `fn-18-kwn.1.md` (no sidecar) committed in `.flow/specs/` long ago would otherwise list as a spec; the index lists only stems that are spec ids (no `.N` task suffix).
- Remote-only scan after the final classifier: 0 branch-only, 3 specs that exist only as stale copies of specs deleted on base, and 5 live-with-conflict copies. All 5 sit on old branches whose PRs were merged (#218, #219, #276, #291, #457/#458), which is the hygiene case.
- Local scan adds one real case: a spec present only on an unpushed local branch, the losing side of the `fn-271` collision, later deleted on base. It is classified stale (deleted on base).
- Hygiene baseline: GitHub keeps 84 branches for this repo (`delete_branch_on_merge: false`); 54 are older than 30 days. Only 2 local tracking refs were stale, so the noise comes from never deleting merged branches, not from missing prunes.

### Team simulation (all scenarios pass with the final classifier)

- An unpushed spec is visible to its author only. After a push it is invisible to a teammate until they fetch; `--fetch` shows it.
- Two unfetched clones minting at once both got `fn-2` (reproduced with the real flowctl); the slugs differ, so nothing was overwritten. After a fetch, the next allocation took `fn-3`.
- Spec-as-PR merged to main, then edited on two branches: concurrent edits are reported as 2 live versions.
- A squash-merged branch's copy is stale; Bob's unmerged edit stays live after base edits other lines, and gets the conflict flag when both appended to the end of the file.
- A deleted remote branch keeps contributing until the prune; with `--fetch` it is gone.
- A spec that was merged and then deleted on base shows as stale, not as branch-only.

### Consumer fallback

- The current flowctl given `specs --refs` exits 2 with `unrecognized arguments: --refs`. MergeFoundry's bridge already treats the analogous `invalid choice: '<verb>'` as `unsupported`.
