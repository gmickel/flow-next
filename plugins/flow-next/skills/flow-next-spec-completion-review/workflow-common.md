# Spec Completion Review Workflow — Common

## Philosophy

Spec completion review verifies spec compliance, NOT code quality. impl-review handles code quality per-task. This review catches:
- Requirements that never became tasks (decomposition gaps)
- Requirements partially implemented across tasks (cross-task gaps)
- Scope drift (task marked done without fully addressing spec intent)
- Missing doc updates

---

## Phase 0: Backend Detection

**Run this first. Do not skip.**

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Prefer RepoPrompt CE; retain Classic only as the final compatibility rung.
if command -v rpce-cli >/dev/null 2>&1 \
  || [ -x "$HOME/RepoPrompt/repoprompt_ce_cli" ] \
  || [ -x "$HOME/Library/Application Support/RepoPrompt CE/repoprompt_ce_cli" ] \
  || command -v rp-cli >/dev/null 2>&1; then
  RP_ELIGIBLE=1
else
  RP_ELIGIBLE=0
fi

# Priority: --review flag > per-spec `default_review` override > env > config (flag parsed in SKILL.md).
# Resolve the spec id from $ARGUMENTS FIRST so a per-spec `default_review` override routes to the
# right backend before branching (empty → env/config, no regression).
# Text output is bare backend name for back-compat grep. --json returns full
# resolved spec (backend, spec, model, effort, source).
SPEC_ID="${1:-}"   # the spec-id positional arg (canonicalized by review-backend); empty falls back to env/config
BACKEND=$($FLOWCTL review-backend "$SPEC_ID")

if [[ "$BACKEND" == "ASK" ]]; then
  echo "Error: No review backend configured."
  if [ "$RP_ELIGIBLE" = 1 ]; then
    echo "Run /flow-next:setup to configure, or pass --review=rp|codex|copilot|cursor|host|none"
  else
    echo "Run /flow-next:setup to configure, or pass --review=codex|copilot|cursor|host|none"
  fi
  exit 1
fi

echo "Review backend: $BACKEND"
```

**Spec-form env var (optional):** `FLOW_REVIEW_BACKEND` accepts bare or full spec:

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
FLOW_REVIEW_BACKEND=codex:gpt-5.5:xhigh $FLOWCTL codex completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
FLOW_REVIEW_BACKEND=copilot:claude-opus-4.5 $FLOWCTL copilot completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
# Cursor folds effort into the model name (no :<effort>):
FLOW_REVIEW_BACKEND=cursor:gpt-5.5-high $FLOWCTL cursor completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
# Or pass spec directly:
$FLOWCTL codex completion-review "$SPEC_ID" --spec "codex:gpt-5.5:xhigh" --receipt "$RECEIPT_PATH"
```

Per-spec `default_review` (set via `flowctl spec set-backend`) overrides env.

**If backend is "none"**: Skip review, inform user, and exit cleanly (no error).

**Then branch to the backend-specific workflow file:**

| `$BACKEND` | Read |
|------------|------|
| `codex`    | [workflow-codex.md](workflow-codex.md) |
| `copilot`  | [workflow-copilot.md](workflow-copilot.md) |
| `cursor`   | [workflow-cursor.md](workflow-cursor.md) |
| `host`     | [workflow-host.md](workflow-host.md) |
| `rp`       | [workflow-rp.md](workflow-rp.md) |

Only the file for the active backend should enter context. Do not read the other backend files.

**Foreground rule — review CLI calls are blocking.** Run every `flowctl <backend> …` review command as a single **foreground** Bash call with a generous timeout (10 minutes; verdicts typically land in 1–7). **Never** launch one with `run_in_background` + a monitor/poll — a background completion does not reliably resume a subagent context, and the call is bounded, so blocking is safe and simpler.

---

## Anti-patterns (all backends)

- **Reviewing yourself** - You coordinate; the backend reviews
- **No receipt** - If REVIEW_RECEIPT_PATH is set, you MUST write receipt
- **Ignoring verdict** - Must extract and act on verdict tag
- **Mixing backends** - Stick to one backend for the entire review session
- **Checking code quality** - That's impl-review's job; focus on spec compliance
- **Backgrounding the review CLI** - Never `run_in_background` + monitor/poll a `flowctl <backend>` review call; one blocking foreground Bash call with a long timeout (Foreground rule, Phase 0)

Backend-specific anti-patterns live in each `workflow-<backend>.md` file.
