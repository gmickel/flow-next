# Codex implementation-delegation — host pre-flight gates + one-time consent

> **Loaded only when delegation MAY be active.** `phases.md` / `SKILL.md` read
> this file ONLY after the cheap value-check resolves `delegation_active=true`
> (arg `delegate:codex` / `delegate:local` > config `work.delegate` > default
> OFF). With delegation off — the default — neither this file nor any gate below
> ever runs; the work flow is byte-identical to today. This is the
> progressive-disclosure contract (R3): mechanics live here, the default path
> stays a single `flowctl config get work.delegate` value-check.

This reference is the **host-side** substrate. The pre-flight gates + one-time
consent run **once, in the host work skill** (the orchestrator), BEFORE the
per-task loop — NOT in the spawned `worker` subagent. The worker is a subagent
and cannot prompt the user for consent (Claude Code #12890/#34592 — a spawned
subagent has no interactive consent path), so consent must live here. The host resolves the gates once, then passes the resolved flags
(`delegate on/off`, sandbox, effort floor, decision) into each spawned worker's
prompt where `phases.md` Phase 3c injects worker context.

The invocation / result-schema / background-launch+poll / per-batch effort
sections (filled by fn-55.3), the orchestration-split / batching / classification
/ safety sections (fn-55.4), and the circuit-breaker / Ralph-safe / attribution
sections (fn-55.5) are stubbed at the end of this file and authored by those
tasks. This task (fn-55.2) authors ONLY the pre-flight + consent section.

---

## Activation — disambiguated from the review backend (R1)

`/flow-next:work` already maps a generic fuzzy **"use codex"** to the **review
backend** (`SKILL.md` Review-mode option parsing — "use codex" → Codex CLI
review). Delegation must NOT reuse that phrase. Delegation activates ONLY via:

- the explicit arg token **`delegate:codex`** (off-switch **`delegate:local`**),
- the flow config **`work.delegate=codex`**,
- or an unambiguous natural phrase — "use codex **for implementation**" /
  "delegate implementation to codex".

Bare **"use codex"** / **"no codex"** keep their existing review-backend meaning.

**Resolution chain (precedence):** arg token (`delegate:codex` / `delegate:local`)
> flow config `work.delegate` > hard default **OFF**. This is the same predicate
the host evaluates with the cheap value-check before reading this file
(`resolve_delegation_active(arg_token, config_value)`, locked in
`tests/test_work_delegate_config.py`):

```text
delegation_active =
    arg == "delegate:codex"                  → true
    arg == "delegate:local"                  → false
    arg absent  AND  config == "codex"       → true
    arg absent  AND  config in (false, null) → false
# the generic "use codex" string is NOT the token → never activates delegation
```

---

## Host pre-flight gates — run ONCE, pre-loop (R4)

When `delegation_active` is true, the host runs the gates below **once**, before
the Phase 3 per-task loop. **Any failure → standard in-session mode** for the
rest of the run (delegation never blocks the worker; it silently degrades). The
gates are ordered cheapest-first.

### Gate 0 — Original-input-kind capture (BEFORE Phase 1 promotion)

`phases.md` Phase 1 promotes a bare idea into a spec+task. The input-kind gate
(Gate 5) must read the **ORIGINAL** input *before* Phase 1 runs — otherwise a
promoted bare prompt would look like a spec and wrongly qualify. So the host
captures `INPUT_WAS_BARE_PROMPT` here, at the top of delegation pre-flight.

**This capture runs ONLY when `delegation_active` is already true** (it sits
after the cheap value-check). The default (delegation-off) path never reaches
this step — it stays a single `flowctl config get work.delegate` value-check.

```bash
# Set BEFORE Phase 1 resolves/promotes the input. A bare idea-text input (input
# kind 5 in phases.md Phase 1 — not a Flow id, not a resolvable handle, not an
# existing .md spec path) is NOT eligible for delegation, even after Phase 1
# promotes it to a spec+task.
if <original input is idea text — none of: Flow id, resolvable handle, existing .md spec path>; then
  INPUT_WAS_BARE_PROMPT=1
else
  INPUT_WAS_BARE_PROMPT=0
fi
```

### Gate 1 — Platform gate (orchestrator is Claude Code)

Enable delegation ONLY when the orchestrator is **Claude Code**. Pinned probe
(verified against the Claude Code / Droid / OpenCode env markers at build):

- the Claude-Code marker **`CLAUDECODE`** is present, AND
- **`DROID_PLUGIN_ROOT`** is unset (Droid → off; Droid exposes
  `CLAUDE_PLUGIN_ROOT` as a *compat alias*, so do NOT key on that), AND
- **no OpenCode marker** (`OPENCODE` / `OPENCODE_*`).

**Do NOT exclude on `CODEX_*` env.** `CODEX_SANDBOX=auto` is flow-next's own
**review-backend** knob (Ralph exports it — see `flowctl.py`
`CODEX_SANDBOX_MODES = {read-only, workspace-write, danger-full-access, auto}`),
NOT a sign the orchestrator is Codex. The "inside a Codex sandbox" case is the
SEPARATE recursion guard (Gate 2), which is value-aware. Keying the platform
gate on `CODEX_*` would disable delegation in every Ralph run.

```bash
# Gate 1: platform = Claude Code only. Eligible iff CLAUDECODE present AND
# DROID_PLUGIN_ROOT unset AND no OpenCode marker. NOT keyed on CODEX_* — so
# CODEX_SANDBOX=auto (Ralph's review-backend knob) leaves delegation ELIGIBLE.
platform_gate_ok() {
  [ -n "${CLAUDECODE:-}" ] || return 1            # not Claude Code → off
  [ -z "${DROID_PLUGIN_ROOT:-}" ] || return 1     # Droid → off (compat alias not keyed)
  # OpenCode → off. Match the bare `OPENCODE` var AND any `OPENCODE_*` marker
  # (OPENCODE_BIN, OPENCODE_SESSION, OPENCODE_ROOT, …) — a fixed two-var check
  # would miss future/unknown markers, contradicting "AND no OpenCode marker".
  [ -z "${OPENCODE:-}" ] || return 1
  env | grep -q '^OPENCODE_' && return 1
  return 0
}
```

### Gate 2 — Recursion guard (not already inside a Codex sandbox)

Skip delegation if already running **inside a Codex runtime sandbox** (avoids
recursion). The guard is **value-aware**, not a bare-presence check:

- `CODEX_SESSION_ID` is **NOT** a real Codex env var (plan research:
  openai/codex#8923 — unmerged); do not key on it.
- `CODEX_SANDBOX` is ALSO a flow-next config knob — **Ralph exports
  `CODEX_SANDBOX=auto`** for the review backend. A bare `-n "$CODEX_SANDBOX"`
  check would FALSE-trip in every Ralph run and disable delegation (breaks R9).
  Trip ONLY on a Codex **runtime** value — one **outside** the flow-next config
  set `{read-only, workspace-write, danger-full-access, auto}`, e.g. `seatbelt`
  — or on the runtime-only `CODEX_SANDBOX_NETWORK_DISABLED`.

```bash
# Gate 2: recursion guard. inside_sandbox=true ONLY when CODEX_SANDBOX holds a
# Codex RUNTIME value (outside the flow-next config set) or
# CODEX_SANDBOX_NETWORK_DISABLED is set. CODEX_SANDBOX=auto (Ralph's
# review-backend knob) is NOT a sandbox signal → delegation stays eligible.
not_inside_codex_sandbox() {
  case "${CODEX_SANDBOX:-}" in
    ""|read-only|workspace-write|danger-full-access|auto)
      RUNTIME_SANDBOX=0 ;;   # unset OR a flow-next config knob → NOT a runtime sandbox
    *)
      RUNTIME_SANDBOX=1 ;;   # value outside the config set → Codex runtime sandbox
  esac
  if [ -n "${CODEX_SANDBOX_NETWORK_DISABLED:-}" ] || [ "${RUNTIME_SANDBOX:-0}" = "1" ]; then
    return 1                 # inside a Codex sandbox → recursion guard trips → off
  fi
  return 0
}
```

### Gate 3 — Availability (`codex` on PATH)

```bash
# Gate 3: codex CLI must resolve to an absolute path. Verified against
# codex-cli 0.136.0 at build. Else → standard mode with a one-line hint.
codex_available() {
  command -v codex >/dev/null 2>&1 || return 1
  return 0
}
# On failure, surface: "codex not found — install via `npm i -g @openai/codex`;
# running in standard in-session mode." Then proceed standard (never block).
```

### Gate 4 — One-time consent + sandbox mode (HOST skill only)

The host asks the user via `AskUserQuestion` (NOT the worker subagent — a spawned
subagent has no interactive consent path; #12890/#34592).
Issue it **once**; persist the result so a second run does not re-prompt.
Pattern: lead-with-recommendation + persist-on-confirmation (mirrors the
tracker-sync discovery ceremony).

The consent decides the **sandbox mode**:

| Mode | Flag | Network | Use |
|---|---|---|---|
| **yolo** (recommended, default) | `--dangerously-bypass-approvals-and-sandbox` | full access incl. network | needed to run tests / install deps |
| **full-auto** | `-s workspace-write` | no network by default | tighter blast radius |

Resolution is **config > ASK** — if `work.delegateConsent` is already `true`,
do NOT re-ask; use the persisted `work.delegateSandbox`.

```bash
# Gate 4 (interactive): only ask if consent not already granted.
CONSENT="$($FLOWCTL config get work.delegateConsent --json | jq -r '.value')"
if [ "$CONSENT" != "true" ]; then
  # Host asks the user for consent. Lead with the recommendation (yolo), explain
  # the network tradeoff, then on confirmation persist BOTH keys:
  $FLOWCTL config set work.delegateConsent true
  $FLOWCTL config set work.delegateSandbox <yolo|full-auto>   # the chosen mode
  # If the user declines consent → delegation OFF for this run (standard mode).
fi
```

**Headless (Ralph):** there is no prompt path. Proceed only if
`work.delegateConsent` is already `true` (pre-granted in config); else delegation
stays **silently off** — no consent prompt is issued, never blocks the loop.
Headless is detected by `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` being set.

### Gate 5 — Input is a plan/spec/task, not a bare prompt

```bash
# Gate 5: a bare-prompt-promoted spec is NOT eligible (decided on the ORIGINAL
# input via Gate 0's INPUT_WAS_BARE_PROMPT). A real plan/spec/task IS.
input_kind_ok() {
  [ "${INPUT_WAS_BARE_PROMPT:-0}" = "1" ] && return 1   # promoted bare prompt → off
  return 0
}
```

### Per-task decision — `work.delegateDecision`

After the gates pass, `work.delegateDecision` controls per-task prompting:

- **`auto`** (default) → delegate every eligible task without a per-task prompt.
- **`ask`** → in **interactive** mode the host asks the user via `AskUserQuestion`
  before delegating each task. **Headless** has no prompt path, so `ask` is treated
  as **`auto` only when** `work.delegateConsent` is already `true`; otherwise
  delegation stays off.

```bash
DECISION="$($FLOWCTL config get work.delegateDecision --json | jq -r '.value')"
# interactive + ask → host asks the user before each delegated task
# auto (or headless with consent) → delegate eligible tasks without a prompt
```

### Gate outcome — the resolved flags passed to each worker

When **all** gates pass, the host marks delegation active for the loop and
passes the resolved flags into each spawned worker's prompt (the
`phases.md` Phase 3c injection point):

```text
DELEGATE: codex                # on; absent/`local` ⇒ standard in-session worker
DELEGATE_MODEL: <work.delegateModel>      # default gpt-5.5
DELEGATE_SANDBOX: <yolo|full-auto>        # from consent
DELEGATE_EFFORT_FLOOR: <work.delegateEffort>  # default medium (per-batch escalation floors here)
DELEGATE_DECISION: <auto|ask>
```

When **any** gate fails, the host passes no delegation flags (or `DELEGATE:
local`) — the worker runs standard in-session implementation, unchanged.

---

## Invocation / result schema / background-launch+poll / per-batch effort

> **Verified against `codex-cli 0.136.0`** (early-proof gate fn-55.3, 2026-06-05).
> A live delegation drove a real implementation end-to-end and returned a
> schema-valid `result-batch-*.json` via the bg-launch+poll loop, with MCP
> isolated by `--ignore-user-config`. Re-verify the flag shape on any CLI bump
> (`codex exec --help`; CLI moves fast).

### The `codex exec` invocation (lifted; gpt-5.5/medium defaults)

The worker derives `$SANDBOX_FLAG` from the host-passed `DELEGATE_SANDBOX`
(`work.delegateSandbox`): **yolo** → `--dangerously-bypass-approvals-and-sandbox`
(full access incl. network, needed to run tests / install deps); **full-auto** →
`-s workspace-write` (tighter blast radius, no network). **Never emit the
deprecated `--full-auto` label** — it is not a valid `codex exec` flag in 0.136.0
and warns since 0.130.0; emit `-s workspace-write` for the full-auto mode.

```bash
SANDBOX_MODE="<DELEGATE_SANDBOX>"   # yolo | full-auto (from host consent)
if [ "$SANDBOX_MODE" = "full-auto" ]; then
  SANDBOX_FLAG="-s workspace-write"
else
  SANDBOX_FLAG="--dangerously-bypass-approvals-and-sandbox"   # yolo (default)
fi

FLOW_DELEGATE_CODEX=1 codex exec \
  --ignore-user-config \
  -m "<DELEGATE_MODEL>" \
  -c 'model_reasoning_effort="<effective_effort>"' \
  $SANDBOX_FLAG \
  --output-schema "<scratch-dir>/result-schema.json" \
  -o "<scratch-dir>/result-batch-<n>.json" \
  - < "<scratch-dir>/prompt-batch-<n>.md"
```

- **`FLOW_DELEGATE_CODEX=1` is an inline env prefix ON the command string** (NOT a
  pre-exported var). The `ralph-guard.py` PreToolUse hook (fn-55.5) sees only the
  command text and parses this full shape to allow the invocation; a separately
  `export`ed var would neither reach the hook nor persist across Bash tool calls.
  Keep it in the command string verbatim.
- **`-m` / `-c` are ALWAYS passed explicitly** from `DELEGATE_MODEL`
  (`work.delegateModel`, default `gpt-5.5`) and the per-batch `effective_effort`
  (default `medium`, escalated below). **There is NO "defer to `~/.codex/config.toml`"
  path** — `--ignore-user-config` deliberately skips the user Codex config (MCP
  isolation wins), so model + effort MUST come from flow config, never the user's
  codex config.
- **Cross-check vs. the proven review-path invocation** at
  `flowctl.py:2841-2853` (same `-m`, same `-c 'model_reasoning_effort="..."'`
  quoting, same stdin `-`, same `gpt-5.5` default-model fallback). This delegation
  path ADDS `--output-schema` + `-o` + `--ignore-user-config`, which the review
  path lacks; everything else matches the battle-tested shape.
- **stdin `-`** carries the prompt (avoids CLI length limits + escaping; GH-35).

### MCP isolation (load-bearing) — `--ignore-user-config`, #15451

`codex exec` **silently drops `--output-schema`** when MCP tools are active in the
request's tool list (openai/codex#15451) — you'd get unstructured prose and the
poll/classify contract would break with no error. The isolation mechanism is
**`--ignore-user-config`**: it skips `$CODEX_HOME/config.toml` (incl. its
`[mcp_servers]` block) — auth still uses `CODEX_HOME`. We pass `-m`/`-c`
explicitly, so losing the user's model defaults is fine.

`--output-schema` is **MANDATORY**. **There is NO runtime `--json` JSONL
fallback** — a JSONL degrade has no `ralph-guard` allowance, no defined poll
target, and no classifier input, so it would silently bypass the safety contract.
If isolation can't be made reliable, the blocker is fixed at build or the feature
does not ship.

> **Empirically proven at build (fn-55.3, codex-cli 0.136.0).** With 5
> `[mcp_servers]` configured in `~/.codex/config.toml`, a `codex exec
> --ignore-user-config` behavioral probe answered `NO_MCP_TOOLS` (no MCP plumbing,
> no hooks loaded), and the live delegation returned a schema-valid result.
> **A project-level `.codex/config.toml` is NOT skipped by `--ignore-user-config`
> in all cases** (the flag's docs cover `$CODEX_HOME/config.toml`) — so the build
> proof also confirmed no project `.codex/config.toml` exists in this repo. If a
> repo introduces one with `[mcp_servers]`, re-prove isolation (and prefer
> `-c 'mcp_servers={}'` as a belt-and-braces override) before relying on
> `--output-schema`.

### Background-launch + poll (lifted — timeout-free, tree-integrity)

**Launch as a separate Bash call with the `run_in_background` tool parameter**
(NOT shell `&`). The `run_in_background` PARAMETER is what removes the 2-minute
foreground ceiling — `codex exec` on a real task routinely exceeds it. Redirect
both streams to scratch logs so the background call is self-contained.

Then **poll the result file in separate FOREGROUND Bash calls** (keeps the turn
active, so the working tree can't be touched mid-run). DONE only when the file is
**non-empty AND JSON-parseable** — the `-o` file can be touched before the final
message lands, so `test -s` alone would accept a partial:

```bash
RESULT_FILE="<scratch-dir>/result-batch-<n>.json"
for i in $(seq 1 6); do
  test -s "$RESULT_FILE" && jq -e . "$RESULT_FILE" >/dev/null 2>&1 && echo DONE && exit 0
  sleep 10
done
echo "Waiting for Codex..."
```

Re-run the poll snippet (a fresh foreground Bash call each time) until it prints
`DONE`; on a long run, the `run_in_background` completion notification also fires.

### Structured result schema (lifted — the proof-of-work contract)

Write this verbatim to `<scratch-dir>/result-schema.json` and pass it to
`--output-schema`. `additionalProperties:false` + the `required` list are
load-bearing — they make `flowctl codex classify-result` (fn-55.4) deterministic.

```json
{ "type": "object",
  "properties": {
    "status": { "enum": ["completed", "partial", "failed"] },
    "files_modified": { "type": "array", "items": { "type": "string" } },
    "issues": { "type": "array", "items": { "type": "string" } },
    "summary": { "type": "string" },
    "verification_summary": { "type": "string" } },
  "required": ["status", "files_modified", "issues", "summary", "verification_summary"],
  "additionalProperties": false }
```

### Per-batch effort (lifted — proportional to risk, floored at config)

Pick the reasoning effort **proportional to the batch's risk**, then floor it at
the host-passed `DELEGATE_EFFORT_FLOOR` (`work.delegateEffort`, default `medium`):

| Risk of the batch | Picked effort |
|---|---|
| ordinary CRUD / small refactor / docs | `medium` (default) |
| auth / session / payments / DB migrations / external-API / retry-fallback | `high` |
| architectural / cross-cutting changes | `xhigh` |

```text
effective_effort = max(picked, DELEGATE_EFFORT_FLOOR)   # by enum ordinality
# enum order:  none < low < medium < high < xhigh
```

- Emit the chosen value as `-c 'model_reasoning_effort="<effective_effort>"'`.
- **Never emit the literal `"default"`** — it is not a valid effort value; the
  enum is exactly `none | low | medium | high | xhigh`.
- The floor means a per-batch pick BELOW the configured floor is raised to the
  floor; a pick at/above it is kept.

### Scratch dir

Per-task scratch lives at **`.flow/tmp/codex-<task-id>/`** (already gitignored via
`.flow/.gitignore`'s `tmp/` rule). Hold `result-schema.json`,
`prompt-batch-<n>.md`, `result-batch-<n>.json`, and the bg-launch logs there. The
scratch dir is cleaned post-commit (fn-55.4), so never persist a pointer to it in
`flowctl done` evidence — inline the result fields instead (fn-55.4 contract).

## Orchestration split / batching / result classification / safety

> **The classification + scoped-rollback logic is deterministic flowctl, NOT
> markdown the host re-interprets** (CLAUDE.md agentic-vs-deterministic split).
> The worker calls `flowctl codex classify-result` / `flowctl codex rollback-plan`
> and acts on their JSON; the host AGENT keeps the judgment (delegate-or-not,
> risk→effort, batching). The helpers are pure (no git, no model) so CI tests
> target executable code, not prose.

### Orchestration split (R5) — who owns what

Claude (the worker, which *is* Claude) owns **plan-reading, review, ALL git ops,
and decisions**. `codex exec` **only writes code** — it is **forbidden from git**
(`commit`/`push`/PRs) and repo-scoped. This split is **enforced, not prompt-only**:

- **Git ownership** — Codex is *told* not to commit, but a yolo sandbox CAN run
  git. The worker captures `BASE_COMMIT` (it already does, `worker.md:109-113`)
  and **asserts `git rev-parse HEAD == BASE_COMMIT` AFTER `codex exec`**. A
  committed Codex change is invisible to the `git status` cross-check, so this
  HEAD assertion is the real guard for "Claude owns all git."
- **`.flow/` integrity** — because the scoped rollback intentionally never
  touches `.flow/**` (to preserve plan-sync state), an unauthorized Codex write
  to a *non-scratch* `.flow/` path would otherwise survive a failed delegation.
  So the worker snapshots non-scratch `.flow/` BEFORE delegating and re-checks
  after.

The worker keeps Phase 3 commit, Phase 4 impl-review, Phase 5 done — only the
spawned `codex exec` is git-forbidden. The worker's existing `BASE_COMMIT` is
**reused** for rollback scope + the impl-review base (no base reset — preserves
the spec-wide-base rule for the final integration task).

### Batching (R5) — scoped to ONE flow task

A delegated task's implementation is split into **≤5 units**, where each unit is
a logical change-set:

- Split at **phase / file boundaries**; **never split a shared-file unit** across
  batches (concurrent edits to one file would conflict).
- **Skip delegation entirely if all units are trivial** (a one-line edit is not
  worth the round-trip — implement in-session).
- **No cross-task batching in v1** — batching is scoped to the single flow task
  the worker owns. (Cross-task batching is explicitly out of scope: each flow
  task is a fresh worker subagent; there is no shared orchestrator to batch
  across tasks.)

Each batch surfaces a brief **result block** (summary / files / verification /
issues). In Ralph it routes to the Ralph log / receipt (no human in the loop).

### The prompt template (lifted — 8 XML-tagged sections)

The per-batch prompt (`prompt-batch-<n>.md`) carries exactly these sections:

```
<task>            one-sentence statement of THIS batch's change-set
<files>           the files this batch may touch (repo-relative)
<patterns>        existing patterns to follow (signatures, naming, structure)
<approach>        the technical approach (from the spec / investigation)
<constraints>     the hard rules — see below
<testing>         which test files / commands prove this batch
<verify>          run all test files in ONE process; gate `completed` on green
<output_contract> emit the result JSON per result-schema.json (verbatim)
```

`<constraints>` **MUST**:
- **forbid Codex from `git commit` / `git push` / opening PRs** (the orchestrator
  owns all git);
- **restrict modifications to the repo root** and keep scope tight to `<files>`;
- **explicitly forbid writing anywhere under `.flow/` EXCEPT its own
  `.flow/tmp/codex-<task-id>/` scratch dir** — `.flow/specs`, `.flow/tasks`,
  `.flow/config.json`, `.flow/memory`, … are host-owned.

`<verify>` runs **all** test files in one process and **forbids
`status:"completed"` unless verification passes** — Codex verifies + fixes itself
before reporting `completed`.

### Result classification (lifted — computed by `classify-result`)

After the bg-launch+poll loop yields a non-empty, JSON-parseable result file,
classify with:

```bash
$FLOWCTL codex classify-result \
  --result "<scratch-dir>/result-batch-<n>.json" \
  --exit <codex-exit-code> --json
# → { class, status, action, scoped_paths, valid_schema }
```

| Signal | `class` | `action` |
|---|---|---|
| exit ≠ 0 | `cli_failure` | `rollback_and_disable` — rollback to HEAD; fall back to standard for ALL remaining work |
| exit 0, result JSON missing / malformed | `task_failure` | `rollback`; `consecutive_failures++` |
| exit 0, `status:"failed"` | `task_failure` | `rollback`; `consecutive_failures++` |
| exit 0, `status:"partial"` | `partial` | `finish_locally` — keep diff; finish locally + verify + commit; `consecutive_failures++` |
| exit 0, `status:"completed"` | `success` | `commit` — cross-check (below) → commit; reset `consecutive_failures=0` |

**A non-zero exit ALWAYS wins** — a CLI failure can leave a stale or
partially-written result behind, so the helper ignores the result body and
returns `cli_failure` regardless. The `valid_schema:false` branch (missing /
empty / unparseable / schema-mismatch on exit 0) is the **backstop**: even if
`--output-schema` silently degraded (the #15451 MCP-drop the invocation guards
against), we never commit blind — we roll back.

### Trust cross-check (cheap) — before committing `completed`

Before committing a `completed` result, intersect `git status --porcelain` with
the result's `files_modified`:

- **claimed-but-untouched** (in `files_modified`, not in `git status`) **or
  touched-but-unclaimed** (dirty in `git status`, not in `files_modified`) → a
  mismatch **downgrades** the result to `partial`/`failed` — don't commit blind.
- This cross-check + an impl-review SHIP gate (`REVIEW_MODE != none`) together
  are the independent check, so the orchestrator **skips a duplicate test run**.
  **When `REVIEW_MODE=none`** (worker Phase 4 skipped), there is no independent
  gate → the worker runs its own **Phase 5 verification** on the delegated diff
  before `flowctl done` (fix + follow-up commit on failure — never trust
  `verification_summary` as the sole gate). fn-55.5 owns the `REVIEW_MODE=none`
  verification wiring.

### Safety — clean-baseline preflight (scoped, EXCLUDES `.flow/`)

The clean-baseline preflight uses **`git status --porcelain`** (catches untracked
files that `git diff --quiet HEAD` misses), **never auto-stashes**, and is
**scoped to the code tree — it EXCLUDES host-owned `.flow/`**:

```bash
# Dirty = any non-.flow working-tree change. /flow-next:work runs plan-sync after
# each task (phases.md 3e), legitimately leaving uncommitted .flow/tasks/ edits;
# a whole-tree clean-baseline would false-disable delegation after task 1.
DIRTY="$(git status --porcelain | grep -v '^.. \.flow/' || true)"
if [ -n "$DIRTY" ]; then
  : # non-.flow dirtiness → offer commit / standard-mode; do NOT delegate dirty
fi
```

Only **non-`.flow/`** dirtiness counts as "dirty". A multi-task run with
`planSync.enabled=true` therefore does NOT disable delegation after task 1.

### Safety — git-ownership enforcement (HEAD assertion)

```bash
# AFTER codex exec (and after poll DONE): assert Claude still owns git.
if [ "$(git rev-parse HEAD)" != "$BASE_COMMIT" ]; then
  # Codex committed (yolo sandbox can run git). Un-commit, keep the diff:
  git reset --soft "$BASE_COMMIT"
  # → then scoped rollback (below) → classify as failure → DISABLE delegation.
fi
```

A committed Codex change is invisible to the `git status` cross-check, so this
assertion is the real "Claude owns all git" guard.

### Safety — non-scratch `.flow/` integrity (snapshot + restore)

```bash
# BEFORE delegating: snapshot non-scratch .flow/ (everything under .flow/ EXCEPT
# .flow/tmp/codex-*). After codex exec: re-check. Any new/changed non-scratch
# .flow/ path → restore THOSE paths from the snapshot (the one case rollback
# deliberately touches .flow/, to UNDO Codex's unauthorized edit) → disable.
```

Because the scoped rollback never touches `.flow/**`, this snapshot/restore is
the *only* mechanism that reinstates host state after an unauthorized `.flow/`
write. `<constraints>` already forbid the write; this is the enforcement backstop.

### Safety — scoped rollback (`rollback-plan`, never bare `git clean`)

Snapshot the untracked set **before** delegating and **again after** the run, both
with `git ls-files --others --exclude-standard -z` (NUL-delimited — odd paths +
files inside new dirs are listed individually, not collapsed to `?? dir/`):

```bash
# Pre (BEFORE codex exec):
git ls-files --others --exclude-standard -z > "$SCRATCH/pre-untracked.txt"
# … run codex exec, poll, classify …
# Post (AFTER the run):
git ls-files --others --exclude-standard -z > "$SCRATCH/post-untracked.txt"

# Compute the SAFE cleanup set (post − pre, sanitized):
$FLOWCTL codex rollback-plan --repo-root . \
  --preexisting-untracked-file "$SCRATCH/pre-untracked.txt" \
  --post-untracked-file "$SCRATCH/post-untracked.txt" --json > "$SCRATCH/plan.json"
# → { rollback_paths: [...sanitized repo-relative FILE paths...], rejected: [...] }

# Roll back (only when class is a failure / partial-discard):
git checkout -- <tracked paths>            # tracked-only revert (never untracked)

# MANDATORY non-empty guard — NEVER let `git clean` run with an empty path list.
# If EVERY new path was rejected (all .flow/**, backslash, absolute, traversal,
# bare-dir), `rollback_paths` is empty and `git clean -fd --` would degrade into
# a BARE clean (github/copilot-cli#1675). The guard makes that impossible. Read
# array via `--print0` (whitespace/newline-safe argv) — never shell-split it.
N="$(jq '.rollback_paths | length' "$SCRATCH/plan.json")"
if [ "$N" -gt 0 ]; then
  # `--print0` emits the sanitized paths NUL-delimited (whitespace/newline-safe
  # argv) — never shell-split the JSON text. Clean ONLY codex-created FILES:
  $FLOWCTL codex rollback-plan --repo-root . \
    --preexisting-untracked-file "$SCRATCH/pre-untracked.txt" \
    --post-untracked-file "$SCRATCH/post-untracked.txt" --print0 \
    | xargs -0 git clean -fd --
fi
# N == 0 → there is nothing codex-created to clean → DO NOT call `git clean`.
# (Belt-and-braces: --print0 emits nothing on an empty set, so even without
#  the count guard, xargs -0 --no-run-if-empty never invokes a bare clean.)
```

Key guarantees (all enforced by `rollback-plan` + the non-empty guard, all
covered by tests):
- The cleanup set is **`post − pre`** — derived from the snapshots, **NOT** from
  the result's `files_modified` (absent on CLI-failure / missing / malformed, yet
  Codex may have created untracked files). So cleanup works even with no result.
- **Never bare `git clean`** — a bare clean has destroyed gigabytes of untracked
  output in the wild (github/copilot-cli#1675). `git clean` is fed ONLY the
  sanitized path list, **and only when that list is non-empty** (the `N -gt 0`
  guard — an all-rejected set must NEVER reach `git clean`).
- **Never a pre-existing untracked file** (it's in `pre`, so excluded by the diff).
- **Never a `.flow/**` path** — host-owned (plan-sync, specs, tasks); `.flow/`
  paths are rejected by `rollback-plan`.
- Rejected: absolute paths, `..` traversal, empty, `.`, backslash paths, bare
  directories, `.flow/**`. `git clean -fd <files>` removes the now-empty parent
  dirs.

### Circuit breaker (host-owned)

The 3-consecutive-failure circuit breaker and the `DELEGATION_RESULT=` /
`DELEGATION_ACTION=` host signals are authored by **fn-55.5** in the next section.
This task supplies the per-task `action` (`commit` / `finish_locally` /
`rollback` / `rollback_and_disable`) that the host loop bridges into the counter.

## Circuit breaker / Ralph-safe / ralph-guard amendment / receipts / attribution

_(stub — authored by fn-55.5)_
