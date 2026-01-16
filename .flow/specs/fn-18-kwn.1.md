# fn-18-kwn.1 Add --create flag to setup-review

## Description

Add `--create` flag to `flowctl rp setup-review` that auto-creates a RepoPrompt window via `workspace create --new-window --folder-path` when no existing window matches the repo root.

## Implementation

Updated `cmd_rp_setup_review()` in flowctl.py:

```python
if win_id is None:
    if getattr(args, "create", False):
        ws_name = os.path.basename(repo_root)
        create_cmd = f"workspace create {shlex.quote(ws_name)} --new-window --folder-path {shlex.quote(repo_root)}"
        create_res = run_rp_cli(["--raw-json", "-e", create_cmd])
        data = json.loads(create_res.stdout or "{}")
        win_id = data.get("window_id")
    else:
        error_exit("No RepoPrompt window matches repo root", ...)
```

## Acceptance

- [x] `--create` flag added to setup-review argparser
- [x] Auto-creates window when no match and --create is set
- [x] Reuses existing windows (backward compatible)
- [x] Docs updated (flowctl.md, README.md, ralph.md, CLAUDE.md)

## Done summary

Implemented `--create` flag for `flowctl rp setup-review`. When set and no window matches repo root, uses `rp-cli -e 'workspace create <name> --new-window --folder-path <path>'` to auto-create. Requires RP 1.5.68+.

## Evidence

```bash
# Test: auto-creates window
$ flowctl rp setup-review --repo-root /tmp/test --summary "Test" --create --json
{"window": 4, "tab": "...", "repo_root": "/tmp/test"}

# Test: reuses existing window
$ flowctl rp setup-review --repo-root /tmp/test --summary "Test2" --create --json
{"window": 4, "tab": "...", "repo_root": "/tmp/test"}  # same window ID
```
