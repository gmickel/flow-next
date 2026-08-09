# Implementation Review Workflow — Common

## Unchanged-artifact terminal

`NOT_RETRYABLE: artifact unchanged since last verdict` plus exit `1` is a
human-action terminal, not a transport error. Stop the autonomous flow; never
refund, reset, use `--force`, or redispatch. The human path is edit the exact
artifact, explicitly reset, or deliberately use `--force`.

## Philosophy

The reviewer model only sees selected files. RepoPrompt's Builder discovers context you'd miss (rp backend). Codex, Copilot, and Cursor use context hints from flowctl (codex/copilot/cursor backends).

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

# Priority: --review flag > per-task/spec `review` override > env > config (flag parsed in SKILL.md).
# FIRST resolve the review-target id from $ARGUMENTS — the `fn-N.M` task / `fn-N` spec being
# reviewed. This is BEFORE the later `TASK_ID` parse (Workflow Step 0), so extract it HERE (do
# NOT rely on `$TASK_ID`, which is still unset at Phase 0); leave empty for a standalone no-spec
# diff review. Passing it lets a per-task `review: <backend>:...` override route to the RIGHT
# backend before dispatch, even when it differs from the project default. Empty → env/config
# unchanged (no regression).
# Substitute the ACTUAL review-target id from $ARGUMENTS here (the `fn-N.M` task / `fn-N`
# spec being reviewed) — a literal value you fill in, e.g. REVIEW_ID="fn-12-auth.3". Do NOT
# leave the bash positional `${1}`: a Bash-tool call does not populate `$1`, so it would be
# empty and the per-task `review:` override (fn-74) would silently fall back to the project
# default. Empty ONLY for a genuine standalone no-spec diff review.
REVIEW_ID="<fn-N.M task or fn-N spec id from \$ARGUMENTS, or empty for a standalone diff>"
# Text output is bare backend name for back-compat grep. The same command in --json mode returns
# {backend, spec, model, effort, source} — use that if you need the model / effort resolved.
BACKEND=$($FLOWCTL review-backend "$REVIEW_ID")

if [[ "$BACKEND" == "ASK" ]]; then
  echo "Error: No review backend configured."
  if [ "$RP_ELIGIBLE" = 1 ]; then
    echo "Run /flow-next:setup to configure, or pass --review=rp|codex|copilot|cursor|host|none"
  else
    echo "Run /flow-next:setup to configure, or pass --review=codex|copilot|cursor|host|none"
  fi
  exit 1
fi

if [ "$RP_ELIGIBLE" = 1 ]; then
  echo "Review backend: $BACKEND (override: --review=rp|codex|copilot|cursor|host|none)"
else
  echo "Review backend: $BACKEND (override: --review=codex|copilot|cursor|host|none)"
fi
```

**Spec-form env var (optional):** `FLOW_REVIEW_BACKEND` accepts bare or full spec:

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
# Bare backend (back-compat)
FLOW_REVIEW_BACKEND=codex $FLOWCTL codex impl-review "$TASK_ID" --receipt "$RECEIPT_PATH"

# Full spec — model + effort resolved automatically
FLOW_REVIEW_BACKEND=codex:gpt-5.5:xhigh $FLOWCTL codex impl-review "$TASK_ID" --receipt "$RECEIPT_PATH"
FLOW_REVIEW_BACKEND=copilot:claude-opus-4.5 $FLOWCTL copilot impl-review "$TASK_ID" --receipt "$RECEIPT_PATH"
# Cursor folds effort into the model name (no :<effort>):
FLOW_REVIEW_BACKEND=cursor:gpt-5.5-high $FLOWCTL cursor impl-review "$TASK_ID" --base "$DIFF_BASE" --receipt "$RECEIPT_PATH"

# Or pass spec directly (preferred for one-offs, avoids env pollution):
$FLOWCTL codex impl-review "$TASK_ID" --spec "codex:gpt-5.5:xhigh" --receipt "$RECEIPT_PATH"
```

Per-task `review` (set via `flowctl task set-backend`) overrides env. Per-backend model/effort detail (at-a-glance descriptions + `backend[:model[:effort]]` grammar) lives in [references/backend-specs.md](references/backend-specs.md) — read only when you must surface backend guidance.

**If backend is "none"**: Skip review, inform user, and exit cleanly (no error).

**Then branch to the backend-specific workflow file** named in SKILL.md's routing table for `$BACKEND`. Only the file for the active backend should enter context. Do not read the other backend files.

**Foreground rule — review CLI calls are blocking.** Run every `flowctl <backend> …` review command (`impl-review` / `plan-review` / `completion-review` / `validate` / `deep-pass`) as a single **foreground** Bash call with a generous timeout (10 minutes; verdicts typically land in 1–7). **Never** launch one with `run_in_background` + a monitor/poll — a background completion does not reliably resume a subagent context (observed in the fn-78 dogfood: a worker idled on an already-finished cursor review until manually poked), and the call is bounded, so blocking is safe and simpler. (The one sanctioned background launch stays codex-delegation's `codex exec` implementation offload — a different pattern that polls a result file in foreground calls; it is not a review command.)

---

## Phase 0.5: Trivial-diff triage (fn-29.6)

A cheap pre-check that short-circuits lockfile-only, docs-only, release-chore,
and generated-file diffs. Runs before the configured backend — when it returns
SKIP, the receipt is written with `mode: "triage_skip"` / `verdict: "SHIP"`
and no expensive backend review is invoked.

The executable block is [SKILL.md](SKILL.md) Step 0.5 (run it there, once).

**Exit codes:**
- `0` → SKIP (verdict=SHIP, receipt written, skill exits early)
- `1` → proceed to full review (normal fallthrough to backend)
- `>=2` → error (falls through to full review — never fail closed)

Rule table, SKIP receipt shape, and the `FLOW_TRIAGE_LLM=1` judge:
[references/triage-rules.md](references/triage-rules.md) (read only when a
triage result needs justifying or auditing).

---

## Optional phases (--deep / --validate / --interactive) — loaded on demand

These three phases are default-OFF. Load their detail **only when the flag resolves true** (SKILL.md Step 0 sets and announces them) — do NOT read it on a default review:
- `DEEP=true` → read [`optional-phases.md`](optional-phases.md) **§ Deep-Pass Phase**.
- `VALIDATE=true` → read [`optional-phases.md`](optional-phases.md) **§ Validator Pass**.
- `INTERACTIVE=true` → read [`optional-phases.md`](optional-phases.md) **§ Interactive Walkthrough Phase** (and [`walkthrough.md`](walkthrough.md) for the per-finding loop).

`optional-phases.md` also owns the phase-ordering & flag-combination matrix (which phase runs when several flags are set) and the per-phase receipt-key contract.

The default per-task review (no flags) never loads any of this — ~5.4k tokens off every review, and reviews run per task. Its receipt therefore carries **no** `validator`, `deep_passes`, or `walkthrough` keys.

## Anti-patterns (all backends)

- **Reviewing yourself** - You coordinate; the backend reviews
- **No receipt** - when `REVIEW_RECEIPT_PATH` is set, every verdict writes a receipt; a verdict reported with no receipt at that path has broken this
- **Ignoring verdict** - the verdict tag is extracted from the backend response and acted on; a run that continues without reading it has broken this
- **Mixing backends** - Stick to one backend for the entire review session
- **Backgrounding the review CLI** - Never `run_in_background` + monitor/poll a `flowctl <backend>` review call; run it as one blocking foreground Bash call with a long timeout (Foreground rule, Phase 0)

Backend-specific anti-patterns live in each `workflow-<backend>.md` file.
