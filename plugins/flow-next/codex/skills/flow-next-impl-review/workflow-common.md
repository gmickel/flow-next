# Implementation Review Workflow — Common

## Philosophy

The reviewer model only sees selected files. RepoPrompt's Builder discovers context you'd miss (rp backend). Codex, Copilot, and Cursor use context hints from flowctl (codex/copilot/cursor backends).

---

## Phase 0: Backend Detection

**Run this first. Do not skip.**

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
set -e
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# RepoPrompt is macOS-only (rp-cli bridges the GUI). Only offer the rp path
# when it can actually run: on macOS, or when rp-cli is already on PATH.
if [ "$(uname 2>/dev/null)" = "Darwin" ] || command -v rp-cli >/dev/null 2>&1; then
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
# leave the bash positional `${1}`: a Bash-prompt turn does not populate `$1`, so it would be
# empty and the per-task `review:` override (fn-74) would silently fall back to the project
# default. Empty ONLY for a genuine standalone no-spec diff review.
REVIEW_ID="<fn-N.M task or fn-N spec id from \$ARGUMENTS, or empty for a standalone diff>"
# Text output is bare backend name for back-compat grep. The same command in --json mode returns
# {backend, spec, model, effort, source} — use that if you need the model / effort resolved.
BACKEND=$($FLOWCTL review-backend "$REVIEW_ID")

if [[ "$BACKEND" == "ASK" ]]; then
 echo "Error: No review backend configured."
 if [ "$RP_ELIGIBLE" = 1 ]; then
 echo "Run /flow-next:setup to configure, or pass --review=rp|codex|copilot|cursor|none"
 else
 echo "Run /flow-next:setup to configure, or pass --review=codex|copilot|cursor|none"
 fi
 exit 1
fi

if [ "$RP_ELIGIBLE" = 1 ]; then
 echo "Review backend: $BACKEND (override: --review=rp|codex|copilot|cursor|none)"
else
 echo "Review backend: $BACKEND (override: --review=codex|copilot|cursor|none)"
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

Per-task `review` (set via `flowctl task set-backend`) overrides env.

**If backend is "none"**: Skip review, inform user, and exit cleanly (no error).

**Then branch to the backend-specific workflow file:**

| `$BACKEND` | Read |
|------------|------|
| `codex` | [workflow-codex.md](workflow-codex.md) |
| `copilot` | [workflow-copilot.md](workflow-copilot.md) |
| `cursor` | [workflow-cursor.md](workflow-cursor.md) |
| `rp` | [workflow-rp.md](workflow-rp.md) |

Only the file for the active backend should enter context. Do not read the other backend files.

**Foreground rule — review CLI calls are blocking.** Run every `flowctl <backend> …` review command (`impl-review` / `plan-review` / `completion-review` / `validate` / `deep-pass`) as a single **foreground** Bash call with a generous timeout (10 minutes; verdicts typically land in 1–7). **Never** launch one with `run_in_background` + a monitor/poll — a background completion does not reliably resume a subagent context (observed in the fn-78 dogfood: a worker idled on an already-finished cursor review until manually poked), and the call is bounded, so blocking is safe and simpler. (The one sanctioned background launch stays codex-delegation's `codex exec` implementation offload — a different pattern that polls a result file in foreground calls; it is not a review command.)

---

## Phase 0.5: Trivial-diff triage (fn-29.6)

A cheap pre-check that short-circuits lockfile-only, docs-only, release-chore,
and generated-file diffs. Runs before the configured backend — when it returns
SKIP, the receipt is written with `mode: "triage_skip"` / `verdict: "SHIP"`
and no expensive backend review is invoked.

**Default behavior:** deterministic whitelist only (no LLM call). Ambiguous
diffs default to REVIEW. Opt-in to LLM judge with `FLOW_TRIAGE_LLM=1`.

**Opt-out:**
- `--no-triage` argument on the skill
- `FLOW_RALPH_NO_TRIAGE=1` env var (Ralph runs)

**Invocation (from SKILL.md):**

```bash
if [[ -z "${TRIAGE_DISABLED:-}" && -z "${FLOW_RALPH_NO_TRIAGE:-}" ]]; then
 RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt${TASK_ID:+-${TASK_ID}}.json}" # fn-90 R5: task-scoped default (concurrent tasks no longer collide); explicit REVIEW_RECEIPT_PATH still wins
 TRIAGE_ARGS=(triage-skip --receipt "$RECEIPT_PATH" --json)
 [[ -n "$BASE_COMMIT" ]] && TRIAGE_ARGS+=(--base "$BASE_COMMIT")
 [[ -n "$TASK_ID" ]] && TRIAGE_ARGS+=(--task "$TASK_ID")
 [[ -z "${FLOW_TRIAGE_LLM:-}" ]] && TRIAGE_ARGS+=(--no-llm)

 if TRIAGE_OUT=$($FLOWCTL "${TRIAGE_ARGS[@]}" 2>/dev/null); then
 SKIP_REASON=$(echo "$TRIAGE_OUT" | jq -r '.reason // "trivial diff"' 2>/dev/null)
 echo "Triage-skip: $SKIP_REASON"
 echo "VERDICT=SHIP"
 exit 0
 fi
fi
```

**Exit codes:**
- `0` → SKIP (verdict=SHIP, receipt written, skill exits early)
- `1` → proceed to full review (normal fallthrough to backend)
- `>=2` → error (falls through to full review — never fail closed)

**Receipt shape on SKIP:**

```json
{
 "type": "impl_review",
 "id": "fn-29.6",
 "mode": "triage_skip",
 "base": "main",
 "verdict": "SHIP",
 "reason": "lockfile-only (bun.lock)",
 "source": "deterministic",
 "changed_file_count": 1,
 "timestamp": "2026-04-24T10:00:00Z"
}
```

Ralph reads `verdict` — `SHIP` satisfies the gate regardless of `mode`. No
Ralph-script changes required.

**Triage rules (deterministic layer):**

| Shape | Action |
|-------|--------|
| Any code file (`.py`, `.ts`, `.go`, `.sh`, ...) present | REVIEW (AC9) |
| Any `.flow/specs/*.md` / `.flow/specs/*.json` / `.flow/tasks/*.md` / legacy `.flow/epics/*.json` | REVIEW |
| All files are lockfiles (`package-lock.json`, `bun.lock`, ...) | SKIP |
| All files are docs (`.md`, `.mdx`, `.txt`, `.rst`, `.adoc`) | SKIP |
| All files are under generated paths (`codex/`, `vendor/`, `node_modules/`, ...) | SKIP |
| Release-chore: `plugin.json` / `package.json` / `Cargo.toml` / `pyproject.toml` + optional `CHANGELOG.md` | SKIP |
| Lockfile + manifest combo | SKIP |
| Anything else | REVIEW (conservative fallthrough) |

When `FLOW_TRIAGE_LLM=1`, ambiguous diffs get a one-shot fast-model call
(`gpt-5.6-luna` @high for codex backend, `claude-haiku-4.5` @low for copilot backend).
Malformed LLM output falls through to REVIEW.

---

## Phase ordering & flag-combination matrix (fn-32.4)

The opt-in flags (`--validate`, `--deep`, `--interactive`) layer on top of the
primary review. When multiple are set, phases run in a fixed order:

```
1. Primary review (always)
2. If --deep: run deep passes in same session → merge findings into receipt
3. If --validate: validator re-checks merged findings → drops false positives
4. If --interactive: user walks surviving findings → Apply/Defer/Skip/Acknowledge
5. Verdict computed over surviving findings (deep may upgrade SHIP→NEEDS_WORK;
 validate may upgrade NEEDS_WORK→SHIP; walkthrough never flips)
6. Receipt each phase writes its own additive block without disturbing others
```

Mode split (fn-113): steps 2-3 mutate the receipt ONLY under autonomy markers
(FLOW_RALPH=1 / REVIEW_RECEIPT_PATH set / FLOW_AUTONOMOUS=1). In an interactive
session deep/validate return raw JSON with host_judges: true and leave the
receipt unchanged - the host judges merge/promotion/survivors from that JSON
instead of re-reading the receipt. optional-phases.md documents both paths.

**Why this order:**
- Deep runs before validate: deep expands the finding superset; validator
 filters the (larger) merged set in a single pass — cheaper than running
 validator twice (once for primary, once for deep).
- Validate runs before interactive: the user walks only validated findings,
 reducing decision burden and keeping per-finding quality high.
- Interactive is always last: it consumes the fully-merged, fully-validated
 set; it never flips the verdict, only sorts findings into Apply / Defer /
 Skip / Acknowledge buckets.

**Flag combination matrix:**

| Combo | Phases executed |
|------------------------------------|--------------------------|
| (default, no flags) | 1 → 5 → 6 |
| `--validate` | 1 → 3 → 5 → 6 |
| `--deep` | 1 → 2 → 5 → 6 |
| `--interactive` | 1 → 4 → 5 → 6 |
| `--validate --deep` | 1 → 2 → 3 → 5 → 6 |
| `--validate --interactive` | 1 → 3 → 4 → 5 → 6 |
| `--deep --interactive` | 1 → 2 → 4 → 5 → 6 |
| `--validate --deep --interactive` | 1 → 2 → 3 → 4 → 5 → 6 |

**Receipt composition:** each phase appends its own block to the receipt
without mutating any other block. The receipt schema is additive — old
Ralph scripts read `verdict` / `mode` / `session_id` and ignore unknown
keys.

| Phase | Receipt keys written | Verdict effect |
|-------|----------------------|----------------|
| 1. Primary | `type`, `id`, `mode`, `verdict`, `session_id`, `timestamp`, `model`, `effort`, `spec` | Sets `verdict` |
| 2. Deep | `deep_passes`, `deep_findings_count`, `cross_pass_promotions`, `deep_timestamp`, optional `verdict_before_deep` | SHIP → NEEDS_WORK (upgrade only; never downgrades) |
| 3. Validator | `validator: {dispatched, dropped, kept, reasons}`, `validator_timestamp`, optional `verdict_before_validate` | NEEDS_WORK → SHIP (upgrade only when all drop; never downgrades) |
| 4. Walkthrough | `walkthrough: {applied, deferred, skipped, acknowledged, lfg_rest}`, `walkthrough_timestamp` | None — walkthrough never flips verdict |

**Empty-block invariants:**
- When no `--validate`, the receipt has **no** `validator` key, **no**
 `validator_timestamp`, and **no** `verdict_before_validate`.
- When no `--deep`, the receipt has **no** `deep_passes`, **no**
 `deep_findings_count`, **no** `cross_pass_promotions`, **no**
 `deep_timestamp`, and **no** `verdict_before_deep`.
- When no `--interactive`, the receipt has **no** `walkthrough` and
 **no** `walkthrough_timestamp`.
- When `--validate` ran with zero dispatched findings, an empty validator
 block (`{dispatched: 0, dropped: 0, kept: 0, reasons: []}`) + its
 timestamp are still written — this keeps the receipt shape deterministic
 for consumers.
- `verdict_before_validate` / `verdict_before_deep` are only written when
 their phase actually upgraded the verdict; otherwise absent.

**Ralph compatibility:** the receipt-gate logic reads `verdict`, `mode`,
and `session_id`. All new fields are optional and ignored by older Ralph
scripts. `FLOW_VALIDATE_REVIEW=1` and `FLOW_REVIEW_DEEP=1` are the only
env opt-ins; `--interactive` hard-errors in Ralph mode (see SKILL.md
Step 0).

---

## Optional phases (--deep / --validate / --interactive) — loaded on demand

These three phases are default-OFF. Load their detail **only when the flag resolves true** (per the flag-combination matrix above) — do NOT read it on a default review:
- `DEEP=true` → read [`optional-phases.md`](optional-phases.md) **§ Deep-Pass Phase**.
- `VALIDATE=true` → read [`optional-phases.md`](optional-phases.md) **§ Validator Pass**.
- `INTERACTIVE=true` → read [`optional-phases.md`](optional-phases.md) **§ Interactive Walkthrough Phase** (and [`walkthrough.md`](walkthrough.md) for the per-finding loop).

The default per-task review (no flags) never loads any of this — ~5.4k tokens off every review, and reviews run per task.

## Anti-patterns (all backends)

- **Reviewing yourself** - You coordinate; the backend reviews
- **No receipt** - If REVIEW_RECEIPT_PATH is set, you MUST write receipt
- **Ignoring verdict** - Must extract and act on verdict tag
- **Mixing backends** - Stick to one backend for the entire review session
- **Backgrounding the review CLI** - Never `run_in_background` + monitor/poll a `flowctl <backend>` review call; run it as one blocking foreground Bash call with a long timeout (Foreground rule, Phase 0)

Backend-specific anti-patterns live in each `workflow-<backend>.md` file.
