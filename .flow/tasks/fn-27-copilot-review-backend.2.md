## Description

Wire Copilot into flowctl's argparse + backend-selection cascade. Adds the `flowctl copilot` command group skeleton (with `check` subcommand only — review subcommands land in task 3), and extends `cmd_review_backend` to recognize `copilot` as a valid value.

**Size:** S (close to M when the argparse boilerplate is counted)
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

- **Backend cascade extension** — Edit `cmd_review_backend` at `flowctl.py:2679-2702`. Add `"copilot"` to both tuples:
  - Line 2683: `if env_val and env_val in ("rp", "codex", "copilot", "none"):`
  - Line 2688: `if cfg_val and cfg_val in ("rp", "codex", "copilot", "none"):`
  - No further changes — the function returns the plain backend string; skills will branch on it in task 4.

- **`cmd_copilot_check`** — mirror `cmd_codex_check` at `flowctl.py:5891-5903`. Unlike codex check (binary presence only), copilot check MUST also probe auth live — per spec acceptance #1 and risks #1. Use a trivial invocation against a GPT probe model that accepts `--effort`: `run_copilot_exec("ok", str(uuid.uuid4()), repo_root, "gpt-5-mini", "low")` with a 60s timeout (override 600s default for the probe). Report JSON: `{installed: bool, version: str, authed: bool, model_used: str, error: str|null}`.
  - **Model caveat from task 1**: Claude Haiku models (and likely all Claude-family models accessible via Copilot) REJECT the `--effort` flag with `Error: Model ... does not support reasoning effort configuration`. `run_copilot_exec` always passes `--effort`, so the probe MUST use a GPT model (`gpt-5-mini` is cheap + fast + accepts effort). If you need Claude for the probe, you must plumb a skip-effort path through `run_copilot_exec` — out of scope for this task.
  - Auth failure signature: exit 1 + stderr containing `"not authenticated"` or similar (probe to confirm actual message). Treat any exit-1 with `Error:` prefix as auth/config problem.
  - Allow `--skip-probe` flag to skip the live probe (fast CI path where auth already verified).
<!-- Updated by plan-sync: task 1 discovered claude-haiku-4.5 rejects --effort; probe must use gpt-5-mini -->


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
Wired Copilot into flowctl's argparse + backend-selection cascade: `cmd_review_backend` accepts `copilot` (env + config), new `flowctl copilot check` command verifies binary + live auth (via `gpt-5-mini` since Claude-family models reject `--effort`) with `--skip-probe` fast path, and `get_embedded_file_contents` takes an optional `budget_env_var` kwarg so copilot callers in task 3 can route through `FLOW_COPILOT_EMBED_MAX_BYTES` without disturbing the 3 existing codex call sites.
## Evidence
- Commits: 6ee42d6b37a1e8f4b0a6a4da40f66a2da64285fc
- Tests: bash plugins/flow-next/scripts/smoke_test.sh (52/52 passed from /tmp), flowctl copilot check --json live probe: available=true version=1.0.34 authed=true model_used=gpt-5-mini error=null, flowctl copilot check --skip-probe --json: authed=null (probe skipped), FLOW_REVIEW_BACKEND=copilot flowctl review-backend --json -> backend=copilot source=env, flowctl config set review.backend copilot + review-backend --json -> backend=copilot source=config, regression: FLOW_REVIEW_BACKEND=rp -> rp/env, review.backend=codex -> codex/config, FLOW_REVIEW_BACKEND=invalid falls through to config, flowctl codex check --json still returns version 0.94.0, get_embedded_file_contents signature has budget_env_var default 'FLOW_CODEX_EMBED_MAX_BYTES'; accepts 'FLOW_COPILOT_EMBED_MAX_BYTES' kwarg; 3 existing codex callers at 6350/6566/6929 unchanged, python3 -m py_compile flowctl.py
- PRs: