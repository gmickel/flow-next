## Description

Wire Copilot into flowctl's argparse + backend-selection cascade. Adds the `flowctl copilot` command group skeleton (with `check` subcommand only — review subcommands land in task 3), and extends `cmd_review_backend` to recognize `copilot` as a valid value.

**Size:** S (close to M when the argparse boilerplate is counted)
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

- **Backend cascade extension** — Edit `cmd_review_backend` at `flowctl.py:2679-2702`. Add `"copilot"` to both tuples:
  - Line 2683: `if env_val and env_val in ("rp", "codex", "copilot", "none"):`
  - Line 2688: `if cfg_val and cfg_val in ("rp", "codex", "copilot", "none"):`
  - No further changes — the function returns the plain backend string; skills will branch on it in task 4.

- **`cmd_copilot_check`** — mirror `cmd_codex_check` at `flowctl.py:5891-5903`. Unlike codex check (binary presence only), copilot check MUST also probe auth live — per spec acceptance #1 and risks #1. Use a trivial invocation: `run_copilot_exec("ok", str(uuid.uuid4()), repo_root, "claude-haiku-4.5", "low")` with a 60s timeout (override 600s default for the probe). Report JSON: `{installed: bool, version: str, authed: bool, model_used: str, error: str|null}`.
  - Auth failure signature: exit 1 + stderr containing `"not authenticated"` or similar (probe to confirm actual message). Treat any exit-1 with `Error:` prefix as auth/config problem.
  - Allow `--skip-probe` flag to skip the live probe (fast CI path where auth already verified).

- **Argparse `p_copilot` subparser** — mirror `p_codex` at `flowctl.py:7710-7777`, insert immediately after the codex block. Include only the `check` subcommand now (`p_copilot_check`). Leave `impl-review`, `plan-review`, `completion-review` to task 3 — wire them in the same subparser when task 3 adds the commands.

- **`get_embedded_file_contents` budget env var** — the helper at `flowctl.py:1007-` currently reads `FLOW_CODEX_EMBED_MAX_BYTES`. Per spec env-var table, copilot uses `FLOW_COPILOT_EMBED_MAX_BYTES` (same 512KB default). Add an optional `budget_env_var: str = "FLOW_CODEX_EMBED_MAX_BYTES"` kwarg (non-breaking default). Copilot call sites in task 3 pass `"FLOW_COPILOT_EMBED_MAX_BYTES"`.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:2679-2702` — `cmd_review_backend`
- `plugins/flow-next/scripts/flowctl.py:5891-5903` — `cmd_codex_check` (mirror)
- `plugins/flow-next/scripts/flowctl.py:7710-7777` — `p_codex` argparse group (insertion point + shape)
- `plugins/flow-next/scripts/flowctl.py:1007-` — `get_embedded_file_contents` (add optional kwarg)

**Optional:**
- `.flow/specs/fn-27-copilot-review-backend.md` §Env Vars (expected `FLOW_COPILOT_*` names)

## Acceptance

- [ ] `FLOW_REVIEW_BACKEND=copilot flowctl review-backend` prints `copilot` (both env and config source paths)
- [ ] `flowctl copilot check --json` returns installed + version + authed fields
- [ ] `flowctl copilot check --skip-probe` skips the live probe (fast path)
- [ ] Probe failure (e.g., `COPILOT_GITHUB_TOKEN=bogus flowctl copilot check`) reports `authed: false` with stderr context
- [ ] `flowctl copilot --help` shows check subcommand (other subcommands added in task 3)
- [ ] `get_embedded_file_contents` accepts `budget_env_var` kwarg; existing codex call sites unchanged
- [ ] No regression in `flowctl codex check` or existing `cmd_review_backend` behavior

## Done summary

(filled in when task completes)

## Evidence

(filled in when task completes)
