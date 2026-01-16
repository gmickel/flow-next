# fn-18-kwn RP CLI: Auto-open RepoPrompt window for reviews

## Overview

RepoPrompt 1.5.68+ supports `workspace create <name> --new-window --folder-path <path>` to programmatically open a window. Added `--create` flag to `flowctl rp setup-review` to auto-create RP windows instead of requiring user to have one open beforehand.

## Scope

- ✅ Add `--create` flag to `flowctl rp setup-review`
- ✅ Auto-creates window via `workspace create --new-window` when no match found
- ✅ Reuses existing windows (no duplicates)
- ✅ Docs updated with RP 1.5.68+ requirement

## Implementation

Added `--create` flag to `setup-review` command in flowctl.py. When no window matches repo root and `--create` is set, calls `rp-cli -e 'workspace create <basename> --new-window --folder-path <repo_root>'` and extracts `window_id` from JSON response.

## Quick commands

```bash
# Test auto-create (no RP window needed)
flowctl rp setup-review --repo-root . --summary "Test" --create --json

# Without --create, still requires pre-existing window (backward compatible)
flowctl rp setup-review --repo-root . --summary "Test"
```

## Acceptance

- [x] `flowctl rp setup-review --create` opens RP if not already open
- [x] Existing open windows are reused (no duplicate windows)
- [x] Without `--create`, behavior unchanged (errors if no window)
- [x] Docs mention RP 1.5.68+ requirement

## References

- `rp-cli -e 'workspace create --help'`
- `plugins/flow-next/scripts/flowctl.py` - `cmd_rp_setup_review()`
