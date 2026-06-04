# Optional Codex implementation-delegation mode for /flow-next:work (gpt-5.5)

## Conversation Evidence

> user: "i heard they now had a --codex option for [an external plugin's work command] (the pendant to flow-next:work) -- check it out please"  *(source plugin name redacted per request)*
> user: "yes i want a spec, [keep the source plugin unnamed], the model to use should always be gpt-5.5 medium unless otherwise stated by the user, this is a new spec and not tied to the optimization work."
> user: "make sure build in a way that it's an optional path that doesn't bloat our work skill, progressive discovery as always, make heavy use of their code snippets as they are surely thoroughly tested"
> [context: a proven, battle-tested external delegation implementation drives code implementation through `codex exec` while the orchestrating Claude agent keeps planning / review / git / decisions. Its invocation template, `--output-schema` result contract, background-launch+poll loop, per-batch effort model, rollback / circuit-breaker, and pre-flight gates are the reusable substrate this spec lifts.]

## Goal & Context
<!-- scope: business -->
<!-- Source-tag breakdown: 55% [user] / 30% [paraphrase] / 15% [inferred] -->

`/flow-next:work` implements tasks **in the Claude host session** — the expensive budget does the heavy code writing. This spec adds an **optional, opt-in delegation mode**: when activated, the Claude host stays the **orchestrator** (reads the plan, reviews, owns git, makes decisions) and delegates the actual **code implementation** to `codex exec` — offloading implementation tokens to a separate Codex budget. **A different efficiency lever than prompt-trimming: it offloads *work*, not prompt size.** Default model **gpt-5.5**, default effort **medium**, unless the user/config overrides. The mode is **strictly opt-in and progressive-disclosure**: with delegation off, the work flow is byte-identical to today (one cheap value-check on the default path); all delegation mechanics live in a reference loaded **only when active**, so the work skill is not bloated. The invocation, structured-output contract, background+poll loop, effort model, and safety mechanics are **lifted verbatim from a proven, well-tested delegation implementation** rather than reinvented. [user]/[paraphrase]

## Architecture & Data Models
<!-- scope: technical -->

**Progressive-disclosure gate (no default-path bloat).** `phases.md` gains only a value-checked gate + a one-line pointer — same shape as the tracker-sync touchpoints (`flowctl sync active` cheap check, then load the reference). All mechanics live in a new `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md`, read **only when delegation is active**.

```
# default path adds ONLY this cheap value-check — nothing else:
delegation_active = (arg delegate:codex | config work.delegate == "codex") && not delegate:local
if delegation_active:
    # everything below runs ONLY when delegation MAY be active — never on the default path:
    capture INPUT_WAS_BARE_PROMPT          # before Phase 1 promotes a bare idea to a spec
    run host pre-flight gates + one-time consent (once, pre-loop)
    if gates pass AND not INPUT_WAS_BARE_PROMPT:
        per task → worker reads references/codex-delegation.md and delegates its Phase 2
# else: standard in-session execution — unchanged, zero new steps
```

**Activation tokens — disambiguated from the review backend.** `/flow-next:work` already maps a generic fuzzy `"use codex"` to the **review backend** (review with Codex). Delegation must NOT reuse that phrase. Activate ONLY via: the explicit arg token `delegate:codex` (off-switch `delegate:local`), the flow config `work.delegate=codex`, or an unambiguous natural phrase like "use codex **for implementation**" / "delegate implementation to codex". Bare "use codex" / "no codex" keep their existing review-backend meaning.

**Resolution chain (precedence):** arg token (`delegate:codex` / `delegate:local`) > flow config (`.flow/config.json` `work.delegate` block) > hard default **off**.

**Config keys** (flow-next-namespaced; defaults are the spec's law — added to `get_default_config()` so `config get` returns them, NOT null):
- `work.delegate` — `codex` | `false` (default `false`)
- `work.delegateModel` — default **`gpt-5.5`** (passthrough; unset → `gpt-5.5`)
- `work.delegateEffort` — `none|low|medium|high|xhigh`, default **`medium`** (the floor) — *(corrected from `minimal|…`: gpt-5.5 supports `none`, not `minimal` — plan research, OpenAI gpt-5.5 model docs)*
- `work.delegateSandbox` — `yolo` (default) | `full-auto`
- `work.delegateConsent` — `true` | `false` (default `false`)
- `work.delegateDecision` — `auto` (default) | `ask`. **Semantics:** `auto` = delegate every eligible task without a per-task prompt; `ask` = in **interactive** mode the host asks (via `AskUserQuestion`) before delegating each task. Headless/Ralph has no prompt path → `ask` is treated as `auto` **only if** `work.delegateConsent` is already `true`, else delegation stays off.

**Orchestration split:** Claude owns plan-reading, review, **all git ops**, and decisions; `codex exec` only writes code. Codex is **forbidden from git** and repo-scoped. The reference owns: pre-flight gates, batching, per-batch effort, the prompt template, the result schema, the invocation, the background+poll loop, result classification, rollback, circuit breaker, mixed-model attribution.

**Pre-flight gates (run once by the HOST, before the per-task loop; any failure → standard mode for the rest):**
1. **Platform gate** — only when the orchestrator is Claude Code. Concrete probe (pinned at build by fn-55.2): enable ONLY when the Claude-Code marker `CLAUDECODE` is present AND `DROID_PLUGIN_ROOT` is unset (Droid → off; it exposes `CLAUDE_PLUGIN_ROOT` as a compat alias, so don't key on that) AND no OpenCode marker. **Do NOT exclude on `CODEX_*` env** — `CODEX_SANDBOX=auto` is flow-next's own review-backend knob (Ralph exports it), NOT a sign the orchestrator is Codex. The "inside a Codex sandbox" case is the SEPARATE recursion guard (#2), which is value-aware.
2. **Environment guard** — skip if already inside a Codex sandbox (avoids recursion):
   ```bash
   # CODEX_SESSION_ID is NOT a real Codex env var (plan research: openai/codex#8923 — unmerged).
   # CAUTION: CODEX_SANDBOX is ALSO a flow-next config knob — Ralph EXPORTS
   # CODEX_SANDBOX=auto for the review backend (flowctl CODEX_SANDBOX_MODES =
   # {read-only,workspace-write,danger-full-access,auto}). A bare `-n "$CODEX_SANDBOX"`
   # would FALSE-trip in every Ralph run and disable delegation (breaks R9). Trip only
   # on a Codex RUNTIME value (outside the flow-next config set, e.g. `seatbelt`) or the
   # runtime-only CODEX_SANDBOX_NETWORK_DISABLED. fn-55.2 pins the exact runtime values.
   case "${CODEX_SANDBOX:-}" in
     ""|read-only|workspace-write|danger-full-access|auto) : ;;   # unset or flow-next config knob → NOT a sandbox
     *) RUNTIME_SANDBOX=1 ;;                                       # value outside the config set → Codex runtime
   esac
   if [ -n "${CODEX_SANDBOX_NETWORK_DISABLED:-}" ] || [ -n "${RUNTIME_SANDBOX:-}" ]; then echo inside_sandbox=true; else echo inside_sandbox=false; fi
   ```
3. **Availability** — `command -v codex` resolves to an absolute path (else: "install via `npm i -g @openai/codex`" → standard mode).
4. **Consent** — one-time blocking-question consent (`AskUserQuestion`) for the **sandbox mode**: **yolo** (`--dangerously-bypass-approvals-and-sandbox`, full access incl. network — needed to run tests/install; recommended) vs **full-auto** (`-s workspace-write`, no network by default). Persist `work.delegateConsent`/`work.delegateSandbox` to flow config. Headless: proceed only if consent already `true`, else off silently. **Consent runs in the host work skill (SKILL.md/phases.md) — the worker is a subagent and cannot call `AskUserQuestion` (Claude Code #12890/#34592).**
5. **Input** — requires the **original** input to be a plan/spec/task, NOT a bare prompt. `phases.md` Phase 1 promotes a bare idea into a spec+task, so the input-kind must be **captured BEFORE Phase 1** (a `INPUT_WAS_BARE_PROMPT` flag) — but ONLY when `delegation_active` is already true (it runs after the cheap value-check, so the default path stays a single step); a promoted bare prompt is NOT eligible and falls to standard mode.

**Per-batch effort (proven model, gpt-5.5/medium floor):** each batch picks an effort proportional to risk — `medium` for well-scoped changes, `high` for high-risk areas (auth/session, payments, migrations, external API contracts, retry/fallback error handling), `xhigh` for architectural/cross-cutting; floor against config: `effective_effort = max(picked, work.delegateEffort)`. Emit `-c 'model_reasoning_effort="<value>"'`; never pass literal `"default"`. **Batching** is scoped to ONE flow task (see "Topology reconciliation"): ≤5 units = the task's logical change-sets, split at phase boundaries, never split units sharing files; skip delegation if all units trivial.

## API Contracts
<!-- scope: technical -->

**The `codex exec` invocation (lifted; gpt-5.5/medium defaults):**
```bash
SANDBOX_MODE="<work.delegateSandbox>"   # yolo | full-auto
if [ "$SANDBOX_MODE" = "full-auto" ]; then SANDBOX_FLAG="-s workspace-write"; else SANDBOX_FLAG="--dangerously-bypass-approvals-and-sandbox"; fi

# MCP-isolation (load-bearing): codex silently DROPS --output-schema when MCP tools
# are active (openai/codex#15451). Mechanism = --ignore-user-config (skips
# ~/.codex/config.toml incl. its [mcp_servers]); we pass -m/-c explicitly so losing
# user model defaults is fine. --output-schema is MANDATORY: fn-55.3 proves
# isolation empirically at build (a project-level .codex/config.toml may still
# inject servers) — NO runtime JSONL fallback (it would bypass the ralph-guard
# canonical shape + the poll/classify contract).
FLOW_DELEGATE_CODEX=1 codex exec \
  --ignore-user-config \
  -m "gpt-5.5" \
  -c 'model_reasoning_effort="medium"' \
  $SANDBOX_FLAG \
  --output-schema "<scratch-dir>/result-schema.json" \
  -o "<scratch-dir>/result-batch-<n>.json" \
  - < "<scratch-dir>/prompt-batch-<n>.md"
```
- `FLOW_DELEGATE_CODEX=1` is an **inline env prefix on the command string** (NOT a pre-exported var) — the `ralph-guard.py` PreToolUse hook sees only the command text and parses the full delegation shape to allow the invocation; a separately-exported env var would not reach the hook nor persist across Bash tool calls (R9).
- **`-m`/`-c` are ALWAYS passed explicitly** from `work.delegateModel` (default `gpt-5.5`) + the effective effort (default `medium`, escalated per-batch). There is **no "defer to `~/.codex/config.toml`" path** for delegation — `--ignore-user-config` deliberately ignores user Codex config (MCP isolation wins), so the model/effort must come from flow config, never the user's codex config. Never emit the deprecated `--full-auto` label (warns since CLI 0.130.0) — emit `-s workspace-write`; keep `--dangerously-bypass-approvals-and-sandbox` long form for yolo. Pin/verify flags against `codex --version` at build.
- **No runtime fallback.** `--output-schema` is mandatory; the MCP-isolation must be proven at build (fn-55.3). A `--json` JSONL degrade is explicitly rejected — it has no guard allowance, no defined poll target, and no classifier input, so it would silently bypass the safety contract. If isolation can't be made to work, the blocker is fixed at build or the feature does not ship. fn-55.3 BLOCKS fn-55.4+.

**Background-launch + poll (lifted — timeout-free, tree-integrity):** launch as a **separate Bash call with the `run_in_background` tool parameter** (NOT shell `&` — the param is what removes the 2-min ceiling), then poll the result file in **separate foreground** Bash calls (keeps the turn active so the working tree can't be touched mid-run). Poll for **non-empty AND JSON-parseable** (the `-o` file can be touched before the final message lands):
```bash
RESULT_FILE="<scratch-dir>/result-batch-<n>.json"
# DONE only when the file is non-empty AND parses as JSON (the -o file can be
# touched before the final message lands — `test -s` alone accepts a partial).
for i in $(seq 1 6); do
  test -s "$RESULT_FILE" && jq -e . "$RESULT_FILE" >/dev/null 2>&1 && echo DONE && exit 0
  sleep 10
done
echo "Waiting for Codex..."
```

**Structured result schema (lifted — the proof-of-work contract):**
```json
{ "type": "object",
  "properties": {
    "status": { "enum": ["completed","partial","failed"] },
    "files_modified": { "type": "array", "items": { "type": "string" } },
    "issues": { "type": "array", "items": { "type": "string" } },
    "summary": { "type": "string" },
    "verification_summary": { "type": "string" } },
  "required": ["status","files_modified","issues","summary","verification_summary"],
  "additionalProperties": false }
```

**Deterministic classification helper (flowctl plumbing).** Per the repo's agentic-vs-deterministic split, result-schema validation + classification + scoped-rollback path computation are **mechanical** and live in a thin flowctl helper — NOT in markdown the host re-interprets (which would be untestable). The worker calls it; the host parses its output:
```
flowctl codex classify-result --result <result-batch-n.json> --exit <code> --json
  → { "class": "success|partial|task_failure|cli_failure",
      "status": "completed|partial|failed|null",
      "action": "commit|finish_locally|rollback|rollback_and_disable",
      "scoped_paths": [ "<files_modified>" ],   # for the scoped rollback
      "valid_schema": true|false }
```
This is the deterministic surface fn-55.4's tests target (all 5 rows + malformed/missing JSON). The host AGENT still owns the judgment (whether to delegate, risk→effort, batching).

A sibling helper computes the **safe rollback path set** from a pre/post untracked-snapshot DIFF — NOT from the result's `files_modified` (which is absent on a CLI failure / missing / malformed result, yet Codex may still have created untracked files):
```
flowctl codex rollback-plan --repo-root <root> \
  --preexisting-untracked-file <pre-snapshot.txt>    # captured BEFORE delegation
  --post-untracked-file <post-snapshot.txt> --json    # captured AFTER the run
  → { "rollback_paths": [ "<sanitized repo-relative FILE paths>" ],
      "rejected": [ "<path>: <reason>" ] }   # absolute / .. / empty / "." / dir / .flow/** → rejected
```
Both snapshots are taken with **`git ls-files --others --exclude-standard -z`** (NUL-delimited — avoids porcelain-v1 quoting of paths with spaces/backslashes/newlines, and enumerates files INSIDE newly-created directories individually rather than collapsing to `?? dir/`). fn-55.4 tests whitespace/odd-char paths. The untracked-cleanup set = `post − pre` (newly-created untracked FILES), independent of the result JSON — so CLI-failure / missing / malformed results still clean up after Codex. `git clean -fd <files>` removes the now-empty parent dirs. Tracked changes revert via a tracked-only checkout (never touches untracked). Every emitted path is sanitized repo-relative (absolute, `..`, empty, `.`, bare directories, and **any `.flow/**` path** rejected — `.flow/` is host-owned plan-sync/spec/task state, never reverted, never cleaned). fn-55.4 tests the rejection set + CLI-failure/malformed-result cleanup + nested-directory cleanup + `.flow/` exclusion.

**Structured host signal for the circuit breaker.** The worker **inlines the result fields** into `evidence.delegation = { result: {status, files_modified, issues, summary, verification_summary}, model, effort, class }` in `flowctl done --evidence-json` (NOT a `result_file` pointer — the scratch dir is cleaned post-commit, so a path would dangle), AND returns terminal `DELEGATION_RESULT=<class>` + `DELEGATION_ACTION=<action>` lines (the `action` from `classify-result`). The host loop bridges them: `DELEGATION_ACTION=rollback_and_disable` (a `cli_failure`) → disable delegation IMMEDIATELY for all remaining tasks; `task_failure`/`partial` → `consecutive_failures++` (disable at 3); `success` → reset to 0. Workers are fresh-context and cannot hold the counter, so the host owns it.

**Prompt template (lifted — XML-tagged sections):** `<task> <files> <patterns> <approach> <constraints> <testing> <verify> <output_contract>`. `<constraints>` MUST forbid Codex from `git commit`/`push`/PRs (orchestrator owns git), restrict modifications to the repo root, keep scope tight, and **explicitly forbid writing anywhere under `.flow/` EXCEPT its own `.flow/tmp/codex-<task-id>/` scratch dir** (`.flow/specs`, `.flow/tasks`, `.flow/config.json`, `.flow/memory`, … are host-owned). `<verify>` runs all test files in one process and forbids `status:"completed"` unless verification passes — Codex verifies + fixes itself.

**Result classification (lifted; computed by the helper above):**
| Signal | Class | Action |
|---|---|---|
| exit ≠ 0 | CLI failure | rollback to HEAD; fall back to standard for ALL remaining work |
| exit 0, result JSON missing/malformed | task failure | rollback; `consecutive_failures++` |
| exit 0, `status:"failed"` | task failure | rollback; `consecutive_failures++` |
| exit 0, `status:"partial"` | partial | keep diff; finish locally + verify + commit; `consecutive_failures++` |
| exit 0, `status:"completed"` | success | cross-check (below) → commit; reset `consecutive_failures=0` |

**Trust boundary (reconciled with the worker's gates).** The orchestrator does not run a *duplicate* test pass when (a) an impl-review SHIP gate runs (`REVIEW_MODE != none`) AND (b) a cheap `git status --porcelain` ∩ `files_modified` cross-check passes — together these are the independent check, so the token win holds. **When `REVIEW_MODE=none`** (worker Phase 4 skipped), there is no independent gate → the worker MUST run its own Phase 5 verification on the delegated diff before `flowctl done` (its existing verify-before-done gate; fix + follow-up commit on failure — do not trust `verification_summary` as the sole gate). A cross-check mismatch (claimed-but-untouched / touched-but-unclaimed) downgrades the result to `partial`/`failed` — don't commit blind.

**Safety (lifted, hardened):** clean-baseline preflight uses **`git status --porcelain`** (catches untracked files that `git diff --quiet HEAD` misses), never auto-stash — but **scoped to the code tree, EXCLUDING host-owned `.flow/`**. `/flow-next:work` runs plan-sync after each task (`phases.md` 3e), which legitimately leaves uncommitted `.flow/tasks/` edits before the next worker; a naive whole-tree clean-baseline would false-trip and disable delegation after task 1. So the preflight ignores `.flow/` dirtiness; only non-`.flow/` working-tree changes count as "dirty" (→ commit/standard-mode options).
**Git-ownership enforcement (not prompt-only):** Codex is told not to commit, but a yolo sandbox CAN run git. The worker captures `BASE_COMMIT` before delegating and **asserts `git rev-parse HEAD == BASE_COMMIT` after `codex exec`**. If HEAD moved (Codex committed), that's an enforcement failure → `git reset --soft BASE_COMMIT` (un-commit, keep the diff in the worktree) → scoped rollback → classify as failure → **disable delegation**. (A committed Codex change is invisible to the `git status` cross-check, so the HEAD assertion is the real guard for "Claude owns all git.")
**`.flow/` integrity enforcement (not prompt-only):** because the rollback intentionally never touches `.flow/**` (to preserve plan-sync), an unauthorized Codex write to a NON-scratch `.flow/` path (`.flow/specs`, `.flow/tasks`, `.flow/config.json`, …) would otherwise survive a failed delegation. So the worker records a content snapshot of non-scratch `.flow/` (everything under `.flow/` except `.flow/tmp/codex-*`) BEFORE delegating; after `codex exec` it re-checks. Any new/changed non-scratch `.flow/` path → enforcement failure → **restore those paths from the snapshot** (the one case rollback deliberately touches `.flow/`, to UNDO Codex's unauthorized edit and reinstate host state) → disable delegation → surface/escalate.
**Scoped rollback:** before delegating, snapshot the untracked set (`git ls-files --others --exclude-standard -z`, NUL-delimited so odd paths + files in new dirs are listed); after the run, snapshot again. Tracked-only checkout + `git clean -fd -- <paths>` feeds `git clean` ONLY the sanitized `post − pre` file paths from `flowctl codex rollback-plan` — which **always excludes `.flow/**`** (host-owned: plan-sync edits, specs, tasks must never be reverted) — so it works even when the result JSON is missing/malformed and emptied Codex-created dirs are removed. Never bare `git clean` (a bare clean has destroyed gigabytes of untracked output in the wild, github/copilot-cli#1675), never a pre-existing untracked file, never a `.flow/` path. **Circuit breaker** — 3 consecutive failures → `delegation_active=false`, finish remaining in standard mode (counter host-owned). Each batch surfaces a brief result block (summary / files / verification / issues); in Ralph it routes to the Ralph log/receipt (no human).

## Edge Cases & Constraints
<!-- scope: technical -->

- **Default path is untouched.** With delegation off (the default), `phases.md` adds exactly one value-check; no behavioral change, no new prerequisites, `codex` not assumed.
- **Recursion guard** is load-bearing — delegating from inside a Codex sandbox would recurse/fail. Trip on a Codex RUNTIME `CODEX_SANDBOX` value (outside the flow-next config set `{read-only,workspace-write,danger-full-access,auto}`, e.g. `seatbelt`) or `$CODEX_SANDBOX_NETWORK_DISABLED` — NOT on the bare presence of `$CODEX_SANDBOX` (Ralph exports `CODEX_SANDBOX=auto` as a review-backend knob; a naive check disables delegation in every Ralph run). Not the nonexistent `$CODEX_SESSION_ID`.
- **Bare prompt / no codex / no consent / dirty tree** all degrade to standard mode — delegation never blocks the worker. Bare-prompt eligibility is decided on the ORIGINAL input, before Phase 1 promotes it to a spec.
- **`ralph-guard.py` blocks bare `codex exec`** (PreToolUse Bash matcher allows only `flowctl codex` wrappers). The delegation allowance must match the **full canonical delegation shape**, not merely the presence of the sentinel (else any Ralph Bash call could bypass the guard by prepending `FLOW_DELEGATE_CODEX=1`). The guard requires ALL of: inline `FLOW_DELEGATE_CODEX=1` prefix; `codex exec` (not `resume`/`review`); `--ignore-user-config` (load-bearing — without it MCP servers can re-enable and silently drop `--output-schema`); `--output-schema` present; `-o` target under `.flow/tmp/codex-*`; the prompt/schema paths under the same scratch dir; a sandbox flag from the allowlist (`--dangerously-bypass-approvals-and-sandbox` | `-s workspace-write`); and NO `--last`. The copilot block stays intact; `RALPH_GUARD_VERSION` (currently `0.14.0`) is bumped with the change. Without this, delegation dies in Ralph mode (R9).
- **`--output-schema` is silently dropped when MCP servers are active** (openai/codex#15451) — invoke with `--ignore-user-config`; `--output-schema` is mandatory (no JSONL fallback). fn-55.3 proves a project-level `.codex/config.toml` doesn't still inject servers; the malformed-result→rollback branch is the backstop if one slips through.
- **`REVIEW_MODE=none` + delegation** — no impl-review gate, so the worker runs its own **Phase 5** verification before `flowctl done` (its existing verify-before-done gate; fix + follow-up commit on failure). The "no re-run" optimization applies only when a review gate exists; `verification_summary` is never the sole gate.
- **Codex CLI flag drift** — pin/verify flags at build (`codex --version`); do not improvise the invocation beyond the documented conditional `-m`/`-c` insertions.
- **Quoting:** `-c 'model_reasoning_effort="high"'` — single quotes around the pair, double quotes around the TOML string.
- **Scratch dir** lives under `.flow/tmp/codex-<task-id>/` (already gitignored via `.flow/.gitignore`); cleaned post-commit after the result JSON is folded into evidence.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** **Opt-in activation, default OFF.** `delegate:codex` arg token (off-switch `delegate:local`; disambiguated "use codex **for implementation**" — NOT the generic "use codex", which stays mapped to the review backend) or flow config `work.delegate=codex`; resolution arg > config > default. With delegation off, `/flow-next:work` is **byte-identical** to today — a single cheap value-check on the default path, zero new steps. [user]
- **R2:** **Model & effort default to `gpt-5.5` / `medium`** unless the user or config states otherwise. `work.delegateModel` default `gpt-5.5`; `work.delegateEffort` default `medium` (the floor, enum `none|low|medium|high|xhigh`). The proven per-batch risk escalation is retained (medium→high→xhigh), floored at the config value; the user may pin or override. [user]
- **R3:** **Progressive disclosure.** All delegation mechanics live in `references/codex-delegation.md`, loaded **only when delegation is active**. `phases.md`/`SKILL.md` gain only the value-checked gate + a one-line pointer — no bloat to the default work path. [user]
- **R4:** **Pre-flight gates (once, host-side):** orchestrator-is-Claude-Code (concrete probe); not-inside-a-Codex-sandbox (Codex-runtime `$CODEX_SANDBOX` value or `$CODEX_SANDBOX_NETWORK_DISABLED` — NOT the flow-next `CODEX_SANDBOX=auto` config knob Ralph exports); `codex` available; one-time consent + sandbox-mode (yolo|full-auto) persisted to flow config; **original** input is a plan/spec/task (captured before Phase 1 promotion), not a bare prompt; headless consent only if already granted. Any failure → standard mode. [paraphrase]
- **R5:** **Orchestration split** — Claude owns plan-reading, review, **all git**, and decisions; `codex exec` only writes code, **forbidden from git**, repo-scoped. "Forbidden from git" + "no non-scratch `.flow/` writes" are **enforced, not prompt-only**: the worker asserts `git rev-parse HEAD == BASE_COMMIT` after `codex exec` (moved HEAD → `git reset --soft` + rollback + disable), AND snapshots non-scratch `.flow/` before/after (any unauthorized `.flow/` mutation → restore from snapshot + disable). Batching (≤5/batch scoped to one flow task, never split shared-file units, skip-if-trivial) + per-batch risk-based effort floored against config. [paraphrase]
- **R6:** **Structured-output contract** — `codex exec --output-schema <schema> -o <result>` (`--output-schema` MANDATORY, no runtime fallback; `--ignore-user-config` for MCP isolation; model+effort ALWAYS passed explicitly from flow config — no defer-to-user-codex-config path); result JSON `{status, files_modified, issues, summary, verification_summary}`. Codex verifies + fixes itself; the orchestrator skips a *duplicate* test run ONLY when an impl-review gate runs AND the `files_modified ∩ git status` cross-check passes; with `REVIEW_MODE=none` the worker runs its own verification. Absent/malformed result after exit 0 = task failure → rollback. (Lift the schema verbatim.) [paraphrase]
- **R7:** **Timeout-free run + tree integrity** — launch `codex exec` via the Bash **`run_in_background` parameter** (not shell `&`), then poll the result file (non-empty + JSON-parseable) in **separate foreground** calls so the turn stays active and the tree isn't touched mid-run. (Lift the bg+poll snippet.) [paraphrase]
- **R8:** **Safety** — clean-baseline preflight via `git status --porcelain` (no auto-stash, **scoped to the code tree — excludes host-owned `.flow/`** so plan-sync edits between tasks don't false-trip); post-`codex exec` HEAD-unchanged assertion (un-commit + rollback + disable if Codex committed) AND non-scratch `.flow/` integrity assertion (restore from pre-snapshot + disable if Codex wrote outside its scratch dir); deterministic `flowctl codex classify-result` + `rollback-plan` helpers drive the 5-row classification → scoped rollback (`git clean -fd -- <paths>`, never bare, never a pre-existing untracked file, **never a `.flow/**` path**), keep-partial-finish-locally, commit-on-success; **circuit breaker** disables delegation after 3 consecutive failures, immediately on a `cli_failure` (counter host-owned via the `DELEGATION_RESULT=`/`DELEGATION_ACTION=` signals — workers are fresh-context). [paraphrase]
- **R9:** **Receipts + Ralph-safe** — each delegated batch's result JSON is **inlined** into the task's `flowctl done --evidence-json` as `evidence.delegation.result` ({status, files_modified, issues, summary, verification_summary} + model/effort/class) — the existing proof-of-work surface, no new receipt subsystem, no dangling scratch-file pointer; `ralph-guard.py` is amended to allow the invocation ONLY when it matches the **full canonical delegation shape** (inline `FLOW_DELEGATE_CODEX=1` + `codex exec` + `--ignore-user-config` + `--output-schema` + `-o` under `.flow/tmp/codex-*` + sandbox-flag allowlist, no `--last`/`resume`/`review`) — not merely the sentinel's presence (keeping `--last`/copilot blocked, bumping `RALPH_GUARD_VERSION` + tests); in Ralph/autonomous mode delegation proceeds only when consent is already granted and any failure falls back to standard mode (never blocks the loop), leaning on the worker's impl-review gate (or, when `REVIEW_MODE=none`, the worker's own verification). **Mixed-model attribution** is concrete: the worker appends commit-message trailers on a delegated commit (worker Phase 3) — `AI-Orchestrator: Claude` and `AI-Implementer: codex <model> (<effort>)` (e.g. `codex gpt-5.5 (medium)`); when `/flow-next:make-pr` runs, the PR body's model line reflects both. [inferred]
- **R10:** **Cross-platform + docs + version** — canonical Claude-native (`AskUserQuestion`, Bash `run_in_background`); `scripts/sync-codex.sh` mirrors the new reference + rewrites tool names (without mangling the literal `codex exec` it teaches); version bump (skill change) that ALSO updates the Codex marketplace `.agents/plugins/marketplace.json` (currently stale at 1.5.0 — `bump.sh` must be extended); docs: `flowctl.md` config keys, `ralph.md` autonomous-delegation section, `CLAUDE.md` carve-out note, `README.md`, `.flow/usage.md` (+ setup template parity); **`flow-next.dev` updated in the SAME workstream** (it lives in the separate `~/work/flow-next.dev` repo and is committed there separately per CLAUDE.md — a required deliverable, not deferred-to-maintainer; that deferral applies only to the marketing site mickel.tech). [inferred]

## Boundaries
<!-- scope: business -->

- **Strictly opt-in** — default `/flow-next:work` is unchanged; this is a **mode**, not a new skill/command. Delegation OFF by default; nothing new unless the user activates it.
- **Claude owns git, review, and judgment; Codex only implements** (forbidden from git/PRs).
- Delegation requires a plan/task + `codex` CLI + consent; **bare prompt / no codex / no consent / dirty tree → standard mode** (never blocks).
- **NOT** the CLAUDE.md anti-pattern of "flowctl spawns codex/copilot to make a judgment" — this is **host-orchestrated implementation-offload for token economics**; the host keeps all review/judgment. The carve-out is narrow (heavy implementation only) and recorded as a decision.
- Default model/effort is **`gpt-5.5` / `medium`**, defined once in config; not hardcoded across files.
- **NOT** tied to the fn-54 prompt-optimization initiative — a separate efficiency lever (offload work vs trim prompts).
- **NOT** delegating to Copilot / other backends in this spec (Codex only); the shape stays extensible.
- **NOT** cross-task batching in v1 — a "batch" is scoped to a single flow task (see Topology reconciliation); cross-task batching is a deferred extension.

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
Implementation is the most token-heavy phase of `/flow-next:work`; doing it in the Claude host burns the expensive budget. Delegating implementation to `codex exec` (gpt-5.5) while Claude keeps orchestration + review offloads that cost to a separate budget without giving up the quality layer. It complements the prompt-optimization track (fn-54) as a second, orthogonal efficiency lever.

### Implementation Tradeoffs
**Lift, don't reinvent.** The invocation template, `--output-schema` contract, background-launch+poll loop, per-batch effort model, rollback/circuit-breaker, and pre-flight gates come from a proven, well-tested delegation implementation — reimplementing risks subtle bugs (timeout ceilings via shell `&`, unscoped `git clean`, sandbox recursion, malformed-result handling, flag quoting). Preserve them.
**The CLAUDE.md carve-out.** "Don't spawn a second LLM from a skill" targets *judgment* (the host is the intelligence). Delegating heavy *implementation* to a cheaper budget — host-orchestrated, host-reviewed — is a deliberate economics trade-off, not a judgment hand-off. Record as a decision.
**gpt-5.5 / medium default** balances cost and quality; the proven per-batch escalation bumps risky batches up (overridable), so routine work stays cheap and risky work gets resourced.
**Progressive disclosure** keeps the zero-bloat default-path contract: a value-check gates a reference that's read only when active — the same pattern as the tracker-sync touchpoints.
**Classification is deterministic flowctl, not markdown.** Result-schema validation + the 5-row classification + scoped-rollback path computation are mechanical, so they live in a thin `flowctl codex classify-result` helper (testable, CLAUDE.md split-rule compliant); the host agent keeps the judgment (delegate-or-not, risk→effort, batching).
**Trust boundary reconciled with the worker.** The "no duplicate test run" token win is conditional: it holds only when an independent gate exists (impl-review SHIP, or — for `REVIEW_MODE=none` — the worker's own Phase 5 verification) plus the cheap files_modified cross-check. Blind trust of `verification_summary` is explicitly NOT the design.
**Interactive AND Ralph — no extra Ralph gating (decided).** Delegation runs in both modes with the **same** consent/sandbox config (incl. `yolo` if pre-consented); there is no Ralph-specific restriction. Ralph only requires consent **pre-granted in config** (no live prompt is possible headless) and leans on Ralph's existing impl-review gate to catch a bad Codex implementation. Chosen to capture the biggest win — overnight unattended runs are where implementation tokens pile up — accepting the unsupervised blast radius because the safety rails (fall-back-to-standard on any failure, scoped rollback, 3-strike circuit breaker, never-blocks-the-loop) contain it.

### Topology reconciliation (plan decision — resolves the lift vs flow-next's loop)
The lifted source is a **single orchestrator** that batches "units ≤5" and owns commit/rollback around each batch. flow-next's loop is different: `phases.md` Phase 3c spawns **one fresh `worker` subagent per flow task**, and the worker (`agents/worker.md`) owns implement (Phase 2) → commit (Phase 3) → impl-review SHIP gate (Phase 4) → verify+done (Phase 5). Reconciliation (chosen — hybrid):
- **Host runs the one-time pre-flight gates + consent before the per-task loop** (consent needs `AskUserQuestion`, unreachable from the worker subagent), resolves `delegation_active` once, captures `INPUT_WAS_BARE_PROMPT` before Phase 1, and passes the resolved flags (delegate on/off, sandbox, effort floor) into each spawned worker's prompt.
- **Each worker delegates ITS task's implementation** to `codex exec` inside Phase 2 when the flag is set; a "batch" collapses to the worker's own task (≤5 units = the task's logical change-sets; cross-task batching dropped in v1).
- **The worker keeps Phase 3 commit, Phase 4 impl-review, Phase 5 done** — the worker *is* Claude, so "Claude owns all git" holds; only the spawned `codex exec` is git-forbidden (enforced by the HEAD-unchanged assertion, not just the prompt). The worker's existing `BASE_COMMIT` capture is reused for rollback scope + impl-review base (preserving the spec-wide-base rule for the final integration task).
- **Plan-sync coexistence:** `/flow-next:work` runs plan-sync after each completed task (`phases.md` 3e), which leaves host-owned `.flow/tasks/` edits uncommitted before the next worker. The delegation clean-baseline preflight is therefore **scoped to the code tree (excludes `.flow/`)**, and the scoped rollback **never touches `.flow/**`** — so delegation neither false-disables after task 1 nor wipes plan-sync's host-owned state. A multi-task run with `planSync.enabled=true` is a required test.
- **Impl-review still fires unconditionally** for delegated diffs when `REVIEW_MODE != none` — R6's "no re-verify" means "don't re-run tests," NOT "skip the SHIP review." When `REVIEW_MODE=none`, the worker runs its own Phase 5 verification (no independent gate otherwise).
- **The circuit-breaker counter is owned by the host loop**, not the worker — workers are fresh-context and would reset the counter every task. The host reads each worker's `DELEGATION_RESULT=` line + `evidence.delegation` and disables delegation for the remaining tasks at 3 consecutive failures.

## Strategy Alignment

Serves token efficiency of the core build loop (a work-delegation lever, orthogonal to fn-54's prompt-trimming) while preserving the architecture (host orchestrates + reviews; Codex is a swappable executor — the same detect-best-available shape as the review backends and fn-51's driver ladder). Opt-in + zero-dep-base-preserving: no `codex` requirement on the default path.

Active tracks served:
- **Ralph autonomous mode** — delegation runs in Ralph with consent pre-granted; the impl-review gate + circuit breaker + fall-back-to-standard keep the receipt-gated loop honest. The `ralph-guard.py` amendment keeps the autonomous safety surface intact.
- **Cross-platform parity** — canonical Claude-native; `scripts/sync-codex.sh` mirrors the new reference; the platform gate disables delegation on non-Claude-Code orchestrators (ship-and-disable on the Codex mirror).

## Quick commands

```bash
# Activate via config (or pass `delegate:codex` as a /flow-next:work arg)
.flow/bin/flowctl config set work.delegate codex
.flow/bin/flowctl config get work.delegate --json          # expect "codex"
.flow/bin/flowctl config get work.delegateModel --json     # expect "gpt-5.5" (default)
.flow/bin/flowctl config get work.delegateEffort --json    # expect "medium" (floor)

# Recursion guard: inside-codex iff CODEX_SANDBOX has a RUNTIME value (outside the
# flow-next config set) or CODEX_SANDBOX_NETWORK_DISABLED is set. CODEX_SANDBOX=auto
# (Ralph's review-backend knob) is NOT a sandbox signal.
echo "CODEX_SANDBOX=${CODEX_SANDBOX:-<unset>}  NET_DISABLED=${CODEX_SANDBOX_NETWORK_DISABLED:-<unset>}"

# Availability gate
command -v codex && codex --version

# Mirror parity after editing the skill + new reference (repo-root path)
bash scripts/sync-codex.sh && git status --short plugins/flow-next/codex/

# Default-path bloat check: with delegation OFF, the work flow adds one value-check only
.flow/bin/flowctl validate --spec fn-55-optional-codex-implementation --json
```

## Early proof point

Task **fn-55.3** validates the core lift end-to-end AND **blocks fn-55.4–.6**: that `codex exec` (with `--ignore-user-config` so MCP servers don't drop `--output-schema`, #15451) actually drives a single task's implementation and returns a **parseable** result JSON via the `run_in_background`-launch + poll loop. `--output-schema` is MANDATORY (no runtime JSONL fallback — it would bypass the ralph-guard shape + poll/classify contract). If the structured-output contract can't be made reliable (MCP-drop, flag drift, bg+poll never yields a well-formed file), the blocker is fixed at build (e.g. tighten the MCP isolation) or the feature does not ship — fn-55.4–.6 do not start until fn-55.3 passes.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | Opt-in activation (disambiguated tokens), default OFF, byte-identical default path | fn-55.1 (resolution), fn-55.2 (gate) | — |
| R2  | gpt-5.5 / medium defaults + per-batch escalation floored at config | fn-55.1 (defaults in config), fn-55.3 (effort emission/escalation) | — |
| R3  | Progressive disclosure — mechanics in reference, loaded only when active | fn-55.2 | — |
| R4  | Host-side pre-flight gates + one-time consent + original-input-kind capture | fn-55.2 | — |
| R5  | Orchestration split + per-task batching + risk-based effort | fn-55.3 (effort), fn-55.4 (split/batching/constraints) | — |
| R6  | Structured-output contract (+ MCP isolation/fallback) + cross-check + conditional verification | fn-55.3 (schema/invocation), fn-55.4 (classify helper/cross-check), fn-55.5 (review-none verification) | — |
| R7  | Timeout-free bg-launch + poll, tree integrity | fn-55.3 | — |
| R8  | Porcelain clean-baseline, deterministic classify helper, scoped rollback, host-owned breaker | fn-55.4 (helper/classification/rollback), fn-55.5 (host counter via DELEGATION_RESULT) | — |
| R9  | Receipts (evidence.delegation), inline-sentinel ralph-guard + version bump, Ralph-safe, attribution | fn-55.5 | — |
| R10 | Cross-platform mirror + docs + version bump (incl. Codex marketplace) | fn-55.6 | — |
