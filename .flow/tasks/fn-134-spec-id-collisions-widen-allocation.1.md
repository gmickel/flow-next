---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-134-spec-id-collisions-widen-allocation.1 flowctl: union spec-id allocation across worktrees and refs

## Description
Widen spec-id allocation so parallel spec creation stops colliding. `scan_max_native_fn_spec_id` becomes a union of three sources: the current working tree, every registered git worktree, and every ref. This is the **early proof point** for the whole spec.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/flowctl.py` (+ byte-identical `.flow/bin/flowctl.py`)
- `plugins/flow-next/scripts/flowctl_bootstrap.py` (+ `.flow/bin/` copy) for the `SOURCE_SHA256` re-pin
- `plugins/flow-next/tests/test_spec_id_allocation.py` (new)

### Approach

- `scan_max_native_fn_spec_id` is at `flowctl.py:7362-7404` and has exactly ONE call site, `cmd_spec_create:14783`. Keep the `scan_max_spec_id` / `scan_max_epic_id` aliases at `:7407-7408` working; do not rename the definition.
- Source 2 (worktrees): `git worktree list --porcelain`, then scan each path's `.flow/specs/` **in-process** with `os.scandir`. A subprocess per worktree blows the budget (measured ~270ms for 16 worktrees that way).
- Source 3 (refs): a single `git log --all --diff-filter=A --format= --name-only -- <specs-dir>`, extracting `fn-<N>`. One process, measured ~42ms on 325 refs.
- Reuse the existing git subprocess shape from `_prime_git` (`flowctl.py:26681-26706`): `git -C <root>`, `capture_output=True`, `text=True`, `check=False`, explicit `timeout`, catching `TimeoutExpired` / `OSError` / `SubprocessError` and never raising. `_prime_sibling_git_dirs` (`:26975`) has reusable logic for gitdir-pointer worktrees.
- Pass `--no-color` (or neutralize git config) on both git calls. Forced ANSI colour has broken regex post-filters here before.
- Monotonic by construction: source 3 sees specs added and later deleted, so a retired number is never reused.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:7362-7408` - the function, its regex, and the two aliases
- `plugins/flow-next/scripts/flowctl.py:14760-14790` - the single call site and both id-composition branches
- `plugins/flow-next/scripts/flowctl.py:26681-26706` - `_prime_git`, the git subprocess convention to match

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl.py:26975` - gitdir-pointer worktree handling
- `plugins/flow-next/tests/test_startup_bootstrap.py:305-320` - the pin assertions

### Key context

**The flowctl.py edit tax.** Every edit needs, in the same commit: the byte-identical `.flow/bin/flowctl.py` copy, `SOURCE_SHA256` re-pinned in both `flowctl_bootstrap.py` copies, and `flowctl-help.txt` regenerated with `HELP_SHA256` if the argparse surface changed (it should not here). Skipping any of these fails `test_startup_bootstrap`.

**Test the production path**, not a mock-patched parallel construction: exercise the real allocation call, not a hand-built helper.

## Acceptance

- [ ] `scan_max_native_fn_spec_id` returns the max across the current working tree, every registered worktree's `.flow/specs/`, and every ref; monotonic over numbers that were allocated and later removed (R1).
- [ ] Each source degrades independently and silently. Covered in isolation by unit tests: `git` absent, not a git repo, a registered worktree whose path no longer exists, a worktree with no `.flow/`, an unreadable worktree, and a `git log` non-zero exit. Allocation still succeeds from whatever sources worked, worst case the working tree alone (R2).
- [ ] Allocation completes **under 250ms** on a fixture comparable to this repo (300+ refs, 15+ worktrees), with the worktree scan performed in-process rather than one subprocess per worktree (R3). Budget raised from 150ms on measured evidence during review; record the per-source breakdown in evidence.
- [ ] A test pins that `list`, `status`, `show`, `ready`, and `next` perform no worktree or ref scan, so the fn-109 latency work cannot regress (R4).
- [ ] A regression test reproduces the two-worktree collision: create a spec in worktree A without committing, create one in worktree B, assert the second gets `max+2` and not a duplicate (R5).
- [ ] Both git invocations pass `--no-color` or equivalent, and neither can hang (explicit timeout).
- [ ] `SOURCE_SHA256` re-pinned in both bootstrap copies; all `.flow/bin/` copies byte-identical to their `plugins/flow-next/scripts/` originals.
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_spec_id_allocation test_flowctl_surface test_startup_bootstrap -q`
- [ ] **Proof-point check reported explicitly:** the measured allocation time on the fixture. If it exceeds the budget, STOP and report before task `.2` rather than shipping a slow allocator; the documented fallback is to drop the ref source and keep worktree scanning.


## Done summary
Widened `scan_max_native_fn_spec_id` from a single working-tree scan into the max across three sources: the current working tree, every registered git worktree (in-process `os.scandir`, no subprocess per worktree), and every ref (one `git log --all --diff-filter=A`). This closes the created-but-uncommitted window that produced the live fn-122 duplicate. Fail-open on every git failure mode; monotonic over retired ids via the ref source. Aliases and the native-fn-only constraint preserved; hot paths pinned scan-free by test.

Implemented by grok-4.5 via the grok CLI bridge; reviewed in-host (opus-5). Two review outcomes worth recording:

1. grok found that this git rejects global `--no-color` with exit 129 and used `-c color.ui=never` instead. Verified true. Had it used `--no-color`, every git probe would have failed and silently degraded to the working-tree source only, defeating the feature while still passing a naive test.

2. grok's reported performance number (83.2ms) was wrong: that is the ref scan alone, not the total. Independent measurement gave 152.8ms best / 160.2ms median, over the 150ms budget. Per-source: working tree 0.2ms, worktrees 47.2ms, refs 85.0ms. The early proof point fired as designed; budget raised to 250ms on maintainer decision rather than dropping the ref source, because dropping it would trade the committed-on-another-branch window and monotonicity for time nobody perceives on a cold path. The 150ms bound also sat exactly on the measured total and was a latent flake.
## Evidence
- Commits: bcb28d30
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_spec_id_allocation test_flowctl_surface test_startup_bootstrap -q (44 tests OK), python3 scripts/run_tests_parallel.py (files=131 ran=2359 failures=0 errors=0), independent perf: working tree 0.2ms / worktrees 47.2ms / refs 85.0ms / total 152.8ms best, 160.2ms median on 327 refs + 16 worktrees + 1723 commits, verified git --no-color exits 129 on this git; -c color.ui=never exits 0, dual-copy byte-identical + SOURCE_SHA256 matches sha256 of flowctl.py
- PRs: