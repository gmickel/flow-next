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
# in flow-next-work phases — the ONLY inline addition (cheap value-check):
delegation_active = (arg `delegate:codex` | flow config work.delegate == "codex") && not `delegate:local`
if delegation_active AND input is a plan/spec with tasks (not a bare prompt):
    read references/codex-delegation.md and follow it (serial, batched)
else:
    standard in-session execution  # unchanged, zero new steps
```

**Resolution chain (precedence):** arg token (`delegate:codex` / `delegate:local`, + fuzzy "use codex" / "no codex") > flow config (`.flow/config.json` `work.delegate` block) > hard default **off**.

**Config keys** (flow-next-namespaced; defaults are the spec's law):
- `work.delegate` — `codex` | `false` (default `false`)
- `work.delegateModel` — default **`gpt-5.5`** (passthrough; unset → `gpt-5.5`)
- `work.delegateEffort` — `minimal|low|medium|high|xhigh`, default **`medium`** (the floor)
- `work.delegateSandbox` — `yolo` (default) | `full-auto`
- `work.delegateConsent` — `true` | `false` (default `false`)
- `work.delegateDecision` — `auto` (default) | `ask`

**Orchestration split:** Claude owns plan-reading, review, **all git ops**, and decisions; `codex exec` only writes code. Codex is **forbidden from git** and repo-scoped. The reference owns: pre-flight gates, batching, per-batch effort, the prompt template, the result schema, the invocation, the background+poll loop, result classification, rollback, circuit breaker, mixed-model attribution.

**Pre-flight gates (run once, before the first batch; any failure → standard mode for the rest):**
1. **Platform gate** — only when the orchestrator is Claude Code (Codex/Gemini/OpenCode → off).
2. **Environment guard** — skip if already inside a Codex sandbox (avoids recursion):
   ```bash
   if [ -n "$CODEX_SANDBOX" ] || [ -n "$CODEX_SESSION_ID" ]; then echo inside_sandbox=true; else echo inside_sandbox=false; fi
   ```
3. **Availability** — `command -v codex` resolves to an absolute path (else: "install via `npm i -g @openai/codex`" → standard mode).
4. **Consent** — one-time blocking-question consent (`AskUserQuestion`) for the **sandbox mode**: **yolo** (`--dangerously-bypass-approvals-and-sandbox`, full access incl. network — needed to run tests/install; recommended) vs **full-auto** (`-s workspace-write`, no network by default). Persist `work.delegateConsent`/`work.delegateSandbox` to flow config. Headless: proceed only if consent already `true`, else off silently.
5. **Input** — requires a plan/spec with tasks; a bare prompt → standard mode.

**Per-batch effort (proven model, gpt-5.5/medium floor):** each batch picks an effort proportional to risk — `default`/`medium` for well-scoped changes, `high` for high-risk areas (auth/session, payments, migrations, external API contracts, retry/fallback error handling), `xhigh` for architectural/cross-cutting; floor against config: `effective_effort = max(picked, work.delegateEffort)`. Emit `-c 'model_reasoning_effort="<value>"'`; never pass literal `"default"`. **Batching:** ≤5 units/batch, split at phase boundaries, never split units sharing files; skip delegation if all units trivial.

## API Contracts
<!-- scope: technical -->

**The `codex exec` invocation (lifted; gpt-5.5/medium defaults):**
```bash
SANDBOX_MODE="<work.delegateSandbox>"   # yolo | full-auto
if [ "$SANDBOX_MODE" = "full-auto" ]; then SANDBOX_FLAG="-s workspace-write"; else SANDBOX_FLAG="--dangerously-bypass-approvals-and-sandbox"; fi

codex exec \
  -m "gpt-5.5" \
  -c 'model_reasoning_effort="medium"' \
  $SANDBOX_FLAG \
  --output-schema "<scratch-dir>/result-schema.json" \
  -o "<scratch-dir>/result-batch-<n>.json" \
  - < "<scratch-dir>/prompt-batch-<n>.md"
```
`-m` and `-c` lines are conditional: omit only when the user explicitly overrides to unset (defer to `~/.codex/config.toml`); the **spec default substitutes `gpt-5.5` / `medium`**. `effective_effort` (per-batch) replaces `medium` when escalated.

**Background-launch + poll (lifted — timeout-free, tree-integrity):** launch as a **separate Bash call with the `run_in_background` tool parameter** (NOT shell `&` — the param is what removes the 2-min ceiling), then poll the result file in **separate foreground** Bash calls (keeps the turn active so the working tree can't be touched mid-run):
```bash
RESULT_FILE="<scratch-dir>/result-batch-<n>.json"
for i in $(seq 1 6); do test -s "$RESULT_FILE" && echo DONE && exit 0; sleep 10; done
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

**Prompt template (lifted — XML-tagged sections):** `<task> <files> <patterns> <approach> <constraints> <testing> <verify> <output_contract>`. `<constraints>` MUST forbid Codex from `git commit`/`push`/PRs (orchestrator owns git), restrict modifications to the repo root, keep scope tight. `<verify>` runs all test files in one process and forbids `status:"completed"` unless verification passes — Codex verifies + fixes itself; the orchestrator does **not** re-verify.

**Result classification (lifted):**
| Signal | Class | Action |
|---|---|---|
| exit ≠ 0 | CLI failure | rollback to HEAD; fall back to standard for ALL remaining work |
| exit 0, result JSON missing/malformed | task failure | rollback; `consecutive_failures++` |
| exit 0, `status:"failed"` | task failure | rollback; `consecutive_failures++` |
| exit 0, `status:"partial"` | partial | keep diff; finish locally + verify + commit; `consecutive_failures++` |
| exit 0, `status:"completed"` | success | commit; reset `consecutive_failures=0` |

**Safety (lifted):** clean-baseline preflight `git diff --quiet HEAD` (never auto-stash — present commit/stash/standard-mode options on dirty tree); rollback `git checkout -- . && git clean -fd -- <scoped paths>` (never bare `git clean`); **circuit breaker** — 3 consecutive failures → `delegation_active=false`, finish remaining in standard mode. Each batch surfaces a brief result block to the user (summary / files / verification / issues).

## Edge Cases & Constraints
<!-- scope: technical -->

- **Default path is untouched.** With delegation off (the default), `phases.md` adds exactly one value-check; no behavioral change, no new prerequisites, `codex` not assumed.
- **Recursion guard** is load-bearing — delegating from inside a Codex sandbox would recurse/fail.
- **Bare prompt / no codex / no consent / dirty tree** all degrade to standard mode — delegation never blocks the worker.
- **Codex CLI flag drift** — pin/verify flags at build; do not improvise the invocation beyond the documented conditional `-m`/`-c` insertions.
- **Trust boundary:** the orchestrator trusts Codex's `verification_summary` (does not re-run tests); an absent/malformed result after exit 0 is a task failure (rollback).
- **Quoting:** `-c 'model_reasoning_effort="high"'` — single quotes around the pair, double quotes around the TOML string.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** **Opt-in activation, default OFF.** `delegate:codex` arg token (+ fuzzy "use codex"; `delegate:local` / "no codex" forces off) or flow config `work.delegate=codex`; resolution arg > config > default. With delegation off, `/flow-next:work` is **byte-identical** to today — a single cheap value-check on the default path, zero new steps. [user]
- **R2:** **Model & effort default to `gpt-5.5` / `medium`** unless the user or config states otherwise. `work.delegateModel` default `gpt-5.5`; `work.delegateEffort` default `medium` (the floor). The proven per-batch risk escalation is retained (medium→high→xhigh), floored at the config value; the user may pin or override. [user]
- **R3:** **Progressive disclosure.** All delegation mechanics live in `references/codex-delegation.md`, loaded **only when delegation is active**. `phases.md`/`SKILL.md` gain only the value-checked gate + a one-line pointer — no bloat to the default work path. [user]
- **R4:** **Pre-flight gates (once):** orchestrator-is-Claude-Code; not-inside-a-Codex-sandbox (`$CODEX_SANDBOX`/`$CODEX_SESSION_ID`); `codex` available; one-time consent + sandbox-mode (yolo|full-auto) persisted to flow config; plan/task input required; headless consent only if already granted. Any failure → standard mode. [paraphrase]
- **R5:** **Orchestration split** — Claude owns plan-reading, review, **all git**, and decisions; `codex exec` only writes code, **forbidden from git**, repo-scoped. Batching (≤5/batch, never split shared-file units, skip-if-trivial) + per-batch risk-based effort floored against config. [paraphrase]
- **R6:** **Structured-output contract** — `codex exec --output-schema <schema> -o <result>`; result JSON `{status, files_modified, issues, summary, verification_summary}`; Codex verifies + fixes itself; orchestrator trusts it (no re-verify). Absent/malformed result after exit 0 = task failure → rollback. (Lift the schema verbatim.) [paraphrase]
- **R7:** **Timeout-free run + tree integrity** — launch `codex exec` via the Bash **`run_in_background` parameter** (not shell `&`), then poll the result file in **separate foreground** calls so the turn stays active and the tree isn't touched mid-run. (Lift the bg+poll snippet.) [paraphrase]
- **R8:** **Safety** — clean-baseline preflight (`git diff --quiet HEAD`, no auto-stash); 5-row result classification → scoped rollback (`git checkout -- . && git clean -fd -- <paths>`, never bare), keep-partial-finish-locally, commit-on-success; **circuit breaker** disables delegation after 3 consecutive failures. (Lift verbatim.) [paraphrase]
- **R9:** **Receipts + Ralph-safe** — each delegated batch emits a flow-next proof-of-work receipt consistent with the existing receipt model; in Ralph/autonomous mode delegation proceeds only when consent is already granted and any failure falls back to standard mode (never blocks the loop). Mixed-model runs credit both models in the PR/commit attribution. [inferred]
- **R10:** **Cross-platform + docs + version** — canonical Claude-native (`AskUserQuestion`, Bash `run_in_background`); `sync-codex.sh` mirrors the new reference + rewrites tool names; version bump (skill change); docs: `flowctl.md` config keys, `teams.md`/work docs, `.flow/usage.md`, flow-next.dev. [inferred]

## Boundaries
<!-- scope: business -->

- **Strictly opt-in** — default `/flow-next:work` is unchanged; this is a **mode**, not a new skill/command. Delegation OFF by default; nothing new unless the user activates it.
- **Claude owns git, review, and judgment; Codex only implements** (forbidden from git/PRs).
- Delegation requires a plan/task + `codex` CLI + consent; **bare prompt / no codex / no consent / dirty tree → standard mode** (never blocks).
- **NOT** the CLAUDE.md anti-pattern of "flowctl spawns codex/copilot to make a judgment" — this is **host-orchestrated implementation-offload for token economics**; the host keeps all review/judgment. The carve-out is narrow (heavy implementation only) and recorded as a decision.
- Default model/effort is **`gpt-5.5` / `medium`**, defined once in config; not hardcoded across files.
- **NOT** tied to the fn-54 prompt-optimization initiative — a separate efficiency lever (offload work vs trim prompts).
- **NOT** delegating to Copilot / other backends in this spec (Codex only); the shape stays extensible.

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
Implementation is the most token-heavy phase of `/flow-next:work`; doing it in the Claude host burns the expensive budget. Delegating implementation to `codex exec` (gpt-5.5) while Claude keeps orchestration + review offloads that cost to a separate budget without giving up the quality layer. It complements the prompt-optimization track (fn-54) as a second, orthogonal efficiency lever.

### Implementation Tradeoffs
**Lift, don't reinvent.** The invocation template, `--output-schema` contract, background-launch+poll loop, per-batch effort model, rollback/circuit-breaker, and pre-flight gates come from a proven, well-tested delegation implementation — reimplementing risks subtle bugs (timeout ceilings via shell `&`, unscoped `git clean`, sandbox recursion, malformed-result handling, flag quoting). Preserve them.
**The CLAUDE.md carve-out.** "Don't spawn a second LLM from a skill" targets *judgment* (the host is the intelligence). Delegating heavy *implementation* to a cheaper budget — host-orchestrated, host-reviewed — is a deliberate economics trade-off, not a judgment hand-off. Record as a decision.
**gpt-5.5 / medium default** balances cost and quality; the proven per-batch escalation bumps risky batches up (overridable), so routine work stays cheap and risky work gets resourced.
**Progressive disclosure** keeps the zero-bloat default-path contract: a value-check gates a reference that's read only when active — the same pattern as the tracker-sync touchpoints.
**Interactive AND Ralph — no extra Ralph gating (decided).** Delegation runs in both modes with the **same** consent/sandbox config (incl. `yolo` if pre-consented); there is no Ralph-specific restriction. Ralph only requires consent **pre-granted in config** (no live prompt is possible headless) and leans on Ralph's existing impl-review gate to catch a bad Codex implementation. Chosen to capture the biggest win — overnight unattended runs are where implementation tokens pile up — accepting the unsupervised blast radius because the safety rails (fall-back-to-standard on any failure, scoped rollback, 3-strike circuit breaker, never-blocks-the-loop) contain it.

## Strategy Alignment

Serves token efficiency of the core build loop (a work-delegation lever, orthogonal to fn-54's prompt-trimming) while preserving the architecture (host orchestrates + reviews; Codex is a swappable executor — the same detect-best-available shape as the review backends and fn-51's driver ladder). Opt-in + zero-dep-base-preserving: no `codex` requirement on the default path.

## Requirement coverage

| R-ID | Task |
|------|------|
| R1 | fn-55.M (TBD — populate via /flow-next:plan) |
| R2 | fn-55.M (TBD) |
| R3 | fn-55.M (TBD) |
| R4 | fn-55.M (TBD) |
| R5 | fn-55.M (TBD) |
| R6 | fn-55.M (TBD) |
| R7 | fn-55.M (TBD) |
| R8 | fn-55.M (TBD) |
| R9 | fn-55.M (TBD) |
| R10 | fn-55.M (TBD) |
