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
- [ ] Allocation completes **under 150ms** on a fixture comparable to this repo (300+ refs, 15+ worktrees), with the worktree scan performed in-process rather than one subprocess per worktree (R3).
- [ ] A test pins that `list`, `status`, `show`, `ready`, and `next` perform no worktree or ref scan, so the fn-109 latency work cannot regress (R4).
- [ ] A regression test reproduces the two-worktree collision: create a spec in worktree A without committing, create one in worktree B, assert the second gets `max+2` and not a duplicate (R5).
- [ ] Both git invocations pass `--no-color` or equivalent, and neither can hang (explicit timeout).
- [ ] `SOURCE_SHA256` re-pinned in both bootstrap copies; all `.flow/bin/` copies byte-identical to their `plugins/flow-next/scripts/` originals.
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_spec_id_allocation test_flowctl_surface test_startup_bootstrap -q`
- [ ] **Proof-point check reported explicitly:** the measured allocation time on the fixture. If it exceeds 150ms, STOP and report before task `.2` rather than shipping a slow allocator; the documented fallback is to drop the ref source and keep worktree scanning.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
