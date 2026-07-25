---
satisfies: [R19, R20]
---
# fn-134-spec-id-collisions-widen-allocation.3 tracker-sync: create-first operation for the fresh-idea path

## Description

Build the tracker-sync **create-first** operation that the fresh-idea tracker-first path depends on. Today every tracker-sync operation takes a local spec id, and create-if-unlinked renders an existing spec before writing the issue. There is no way to create an issue and learn its key *before* a spec exists, so "create the issue first, then mint" is currently inexpressible. This task makes it expressible.

Plan-review found this gap: without it, task `.4` would be instructing five skills to call something that does not exist.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-tracker-sync/` (the operation: SKILL.md op list, steps.md, and the adapter references it touches)
- `plugins/flow-next/scripts/flowctl.py` only if a thin helper is genuinely needed (prefer not; this is skill-orchestrated)
- tests: a fake-adapter test for the create → attach → merge-base sequence

## Approach

- The operation takes a **title and body**, creates the issue, and returns `{id, identifier, url}` with **no local spec id as input**. That is the whole point: the caller has not minted yet.
- The caller sequence it enables: create issue → mint `KEY-N-slug` → attach via `sync set-tracker-id` (id, identifier, url) → seed the merge base so the first reconcile is not a spurious whole-body conflict.
- **Failure recovery is part of the contract.** If remote creation succeeds and local minting then fails, the run must not strand an orphan issue or create a second one on retry. Surface the created identifier and url on the failure path so the run can resume by linking. A retry after partial failure links, never re-creates.
- Works across all four adapters. GitHub and GitLab return `#N` / `<project>#<iid>` rather than a `KEY-N` string; the operation returns what the adapter gives and leaves synthetic-key minting to the caller (task `.2` owns that).
- **Receipts are a chicken-and-egg problem here and must be designed, not assumed.** Every other tracker-sync op writes a receipt via `sync receipt`, which requires and resolves a **local spec id** - and at create-first time no spec exists yet. Do not simply assert "writes its own receipt". Pick one and state it: (a) emit durable pre-spec recovery output (identifier + url + a stable retry lookup key) and write the normal receipt **after** minting, or (b) add a thin opaque pre-spec receipt helper keyed by something that exists before the spec does. Either way, define the **retry lookup key** so a resumed run finds the already-created issue instead of making a second one.
- Follow the existing best-effort discipline otherwise: a tracker failure never blocks the lifecycle.

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-tracker-sync/SKILL.md` - the operation list and where a new op is declared
- `plugins/flow-next/skills/flow-next-tracker-sync/steps.md` - the create-if-unlinked flow this diverges from, and the receipt convention
- `plugins/flow-next/skills/flow-next-tracker-sync/references/identity.md` - the hybrid id model and `set-tracker-id` attach semantics
- `plugins/flow-next/docs/tracker-sync.md:40-70` - flow-first vs tracker-first as documented today

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-tracker-sync/references/{gitlab,jira,github}.md` - per-adapter create semantics
- `plugins/flow-next/references/tracker-dispatch.md` - background runner dispatch, if the op is dispatched that way

## Key context

This is skill-orchestrated, not a new flowctl subcommand: creating an issue and deciding what to do with the result is judgment, and the repo's split rule keeps that in the skill. Only add flowctl plumbing if something genuinely atomic is missing.

Canonical prose changes require `./scripts/sync-codex.sh` twice with the mirror diff committed.


## Acceptance

- [ ] A create-first operation exists that takes a title and body, creates the issue with no local spec, and returns `{id, identifier, url}` (R19).
- [ ] The enabled sequence is documented end to end: create → mint → attach → seed merge base, with the merge base seeded so the first reconcile is not a spurious conflict (R19).
- [ ] Failure after remote creation surfaces the created issue's identifier and url so the run resumes by linking; a retry links rather than creating a second issue. Covered by a fake-adapter test (R19).
- [ ] Works for all four adapters; GitHub/GitLab return their native reference and synthetic minting is left to the caller.
- [ ] The receipt/recovery path is explicitly designed for the pre-spec case, since `sync receipt` resolves a local spec id that does not exist yet: either durable pre-spec recovery output plus a normal receipt after minting, or a thin pre-spec receipt helper. The chosen approach and the **retry lookup key** are stated, and a test proves a resumed run links the existing issue rather than creating a second one (R19).
- [ ] The operation is best-effort like its siblings: a tracker failure never blocks the lifecycle.
- [ ] `./scripts/sync-codex.sh` run twice: idempotent, guards green, mirror diff committed.
- [ ] Focused suite green plus the new fake-adapter test.

## Done summary
Added a `create-first` operation to the tracker-sync skill: takes a title and body with no local spec id, returns `{id, identifier, url}`, and enables the sequence create issue -> mint `KEY-N-slug` -> attach via `set-tracker-id` -> seed the merge base. This unblocks the fresh-idea tracker-first path that task `.4` depends on; before it, five skills would have been told to call something that did not exist.

Implemented by grok-4.5 via the grok CLI bridge; reviewed in-host (opus-5).

Grok resolved the pre-spec receipt chicken-and-egg with approach (a): durable recovery file at `.flow/create-first/<retryKey>.json` plus a normal `sync receipt` after mint/attach, rather than growing a flowctl pre-spec receipt helper. Retry key is `sha256(tracker.type + title + body)[:16]`, recomputable before create and on every retry, so a resumed run finds the existing issue and links instead of re-creating.

REVIEW FIX (mine, not grok's): `create-first/` was not gitignored, unlike every sibling transient dir (`receipts/`, `tmp/`, `sync-runs/`, `pilot-runs/`, `locks/`, `.cache/`) which all sit in flowctl's auto-managed `.flow/.gitignore` block. This is a correctness bug rather than repo hygiene: because the retry key is a content hash, a committed recovery file would let a teammate who computes the same key "resume" by linking to someone else's issue instead of creating their own. Added `create-first/` to `FLOW_GITIGNORE_AUTO_PATTERNS` in flowctl so new repos get it, re-ran init to materialize it here, verified with `git check-ignore`, and stated the requirement in the skill prose so it is not silently reintroduced.

Known limitation, accepted: the content-hash retry key means a retry that regenerates the body slightly differently computes a different key and would create a second issue. The prose frames this as "a rephrased new idea gets a new key", which is right for a genuinely new intent but optimistic for a same-intent regeneration. Acceptable for the failure-recovery case it targets; worth revisiting if it bites.
## Evidence
- Commits: d947e987
- Tests: python3 scripts/run_tests_parallel.py (files=131 ran=2375 failures=0 errors=0), cd plugins/flow-next/tests && python3 -m unittest test_flowctl_surface test_startup_bootstrap -q (29 tests OK), ./scripts/sync-codex.sh run twice - idempotent, all validation guards green, git check-ignore -v .flow/create-first/abc.json -> ignored via .flow/.gitignore:13 (was NOT ignored before the review fix), dual-copy byte-identical + SOURCE_SHA256 re-pinned after the gitignore-pattern edit
- PRs: