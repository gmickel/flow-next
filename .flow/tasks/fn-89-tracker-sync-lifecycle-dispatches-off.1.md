---
satisfies: [R5, R7, R8, R11, R12, R13, R3, R10]
---

# Foundations: config leaf + tracker-runner agent + Phase 0 mode-threading + Codex mirror + interleave proof point

## Description

Size: M
Files:
- `plugins/flow-next/scripts/flowctl.py` (config default + enum constant)
- `plugins/flow-next/docs/flowctl.md` (config-table row)
- `plugins/flow-next/tests/test_tracker_config.py` (+ optional new `test_tracker_dispatch.py`)
- `plugins/flow-next/agents/tracker-runner.md` (NEW)
- `plugins/flow-next/skills/flow-next-tracker-sync/SKILL.md` (:45 claim narrow)
- `plugins/flow-next/skills/flow-next-tracker-sync/steps.md` (Phase 0 mode-threading)
- `scripts/sync-codex.sh` (Task→role rewrite rule)
- Regenerate `plugins/flow-next/codex/` (runner role .toml auto-generates)

Lay the reusable foundations every touchpoint task consumes: the `tracker.dispatch` config leaf, the `tracker-runner` subagent contract, the Phase 0 `DISPATCH: forked` fold-in, the `host_is_claude_code` capability gate, the SKILL.md:45 narrowing, and the sync-codex mirror rule. **STARTS with a Step 0 LIVE proof point** (Early proof point in the spec) run BEFORE any code is edited — the interleave + fork-context reconcile writeback — so the state-shaped serialization model and the Write/Edit-keeping runner contract are both validated before any touchpoint (or any foundation code) is wired. Size stays M: the Step 0 spike is cheap (no fn-89 code) but gates everything after it.

## Approach

0. **Interleave + fork-reconcile-writeback proof point (STEP 0 — run FIRST, before ANY code edit; Early proof point).** **HOST-EXECUTED:** this step runs in the `/flow-next:work` CONDUCTOR's context, BEFORE the .1 worker is dispatched — workers carry `disallowedTools: Task` and per R13 runners never dispatch from worker subagents, so the worker cannot own this proof; the conductor records hold/no-hold and the worker consumes the recorded result in its done-summary. **DISPOSABLE TARGET:** run the reconcile against a throwaway spec + issue (create a scratch spec, link, mutate the issue, reconcile, then unlink + delete — or snapshot/restore) so a failed writeback never corrupts a real spec or tracker issue. This needs NO fn-89 code — it uses a generic background `Task` dispatch of the EXISTING `flow-next-tracker-sync` skill body plus an intervening foreground `Task`. (a) Dispatch a background runner op that is a **reconcile** (tracker-side-changed → spec writeback) so the fork-context Write/Edit writeback of the merged flow body to `.flow/specs/<id>.md` (`references/body-merge.md` Step 5) is exercised — feasibility T1/T2 proved only push + comment in fork, never the reconcile writeback the `disallowedTools: Task`-only runner depends on. (b) While it is in flight, spawn an intervening foreground `Task` (e.g. a scout). (c) Join the runner; confirm the outcome line + receipt + the spec-writeback all settle. Record hold/no-hold in the done-summary. **On no-hold (interleave breaks OR fork writeback fails): STOP — land NO code and escalate to the user.** The .2 serialization model and this task's runner contract both depend on this holding, so it runs before the config leaf, not after the foundations.
1. **Config leaf (R5).** In `flowctl.py`, add `TRACKER_DISPATCH_MODES = {"async", "inline"}` beside `TRACKER_TIEBREAKS` (flowctl.py:1033). In `get_default_tracker_config()`, add `"dispatch": "async"` as a top-level scalar sibling of `readyState` (flowctl.py:1131-1140, after the `readyState` key). No enum enforcement in `set_config` is required (it is a plain nested setter — flowctl.py:1503-1550); the gate does the exact-match read. Add a `TRACKER_DISPATCH_MODES` reference in a code comment for discoverability.
2. **Docs row (R5).** In `docs/flowctl.md`, add a `| tracker.dispatch | string | async | ... |` row immediately after the `tracker.readyState` row (L661). Describe `async` (default) vs `inline` (support/debug hatch, restores byte-identical inline behavior), and the exact-match activation (`inline` only; bool never activates).
3. **Test (R5).** Extend `test_tracker_config.py` to assert the default `tracker.dispatch == "async"` and the dotted-path get/set round-trips (`config set tracker.dispatch inline` → `config get` returns `inline`; `config set tracker.dispatch async` restores). Follow the existing default-shape assertion pattern in that file.
4. **Runner agent (R7, R12).** Create `agents/tracker-runner.md`, frontmatter `name: tracker-runner`, `model: sonnet`, `disallowedTools: Task` **only**, `user-invocable: false`. **Model the frontmatter on `agents/pr-comment-resolver.md`** — a WRITING subagent that blacklists `Task` only — NOT on `agents/plan-sync.md` (a read-only sync agent that blacklists `Task, Write, Bash`). The runner KEEPS `Write`/`Edit` (and `Bash`): the reconcile writeback in `references/body-merge.md` Step 5 writes the merged flow body to `.flow/specs/<id>.md` via Write/Edit, so a Write/Edit-blacklisted runner cannot execute a state-shaped reconcile — the very thing Step 0 proves in-fork. Document this WHY in the agent contract body (one line: "keeps Write/Edit because reconcile writeback edits `.flow/specs/<id>.md`"). Body: inputs `OPERATION`, `SPEC_ID`, `EVENT`, `FLOWCTL`, `DISPATCH: forked`, autonomy markers (`FLOW_RALPH`/`FLOW_AUTONOMOUS`/`REVIEW_RECEIPT_PATH`); instruct it to run the existing `flow-next-tracker-sync` skill body for the ONE op (no reimplementation), load MCP via `ToolSearch` when needed (feasibility T2), and return EXACTLY one outcome line `<status> <spec-id> <note>` with `status` = the FULL tracker receipt enum `pushed|pulled|merged|updated|diverged|queued|errored|noop` (leaves can be `pull`; reconcile can receipt `diverged` — a narrower enum forces lossy reporting). State the 10-min self-bound expectation (R12) and that it is dispatched from HOST contexts only, never nested (R13). The contract body ALSO defines the canonical dispatch+join block — how the host launches background vs awaited, what it records in the ledger, how it joins, and timeout handling — in ONE place that .2/.3 reference instead of re-deriving per touchpoint.
5. **Phase 0 mode-threading (R11).** In tracker-sync `steps.md` Phase 0 (:21-30), fold an explicit `DISPATCH: forked` input into the single `RALPH` queue gate: when `DISPATCH: forked`, force queue-not-ask (`AskUserQuestion` unreachable) regardless of the other markers, parity with the existing R14 invariant at :32. Parse `DISPATCH` alongside `EVENT` (:29).
6. **SKILL.md:45 narrow (R11).** Rewrite the "Inline skill (no `context: fork`)" paragraph to: ceremonies + manual/interactive conflict resolution stay inline; lifecycle dispatches MAY run forked (the runner). Keep the `AskUserQuestion` reachability note scoped to the inline paths.
7. **Capability gate (R8).** Add a `host_is_claude_code` check (mirror the codex-delegation gate — see `skills/flow-next-work/references/codex-delegation.md`) that resolves async ONLY on Claude Code; document that Codex/Copilot/Droid resolve inline in v1. This is prose doctrine consumed by the touchpoint gates in .2/.3; define it here (where + how the host detects Claude Code) so those tasks reference one place.
8. **Codex mirror (R8) — GLOBAL sweep, not a per-file rule.** The `Task flow-next:tracker-runner` token lands in ~8 mirror skill markdown files across .1/.2/.3, so add a **single GLOBAL rewrite** to `sync-codex.sh`: a `find "$CODEX_DIR/skills" -name '*.md' -exec sed -i.bak 's/Task flow-next:tracker-runner/… tracker_runner agent …/g' {} +` sweep (then clean the `.bak` files), placed after the per-skill rewrite section and before the structural guard. **Do NOT model this on the file-scoped `:312-323` per-file `sed -i.bak … "$file"` rules** — a per-file rule would only rewrite the files THIS task touches and leave the token in the files owned by .2/.3, failing the structural guard at `:1627-1633` ("No 'Task flow-next:' refs") on those tasks with the fix unowned. Naming convention: the prose role is `tracker_runner` (underscore, the sed target); the generated agent toml is `tracker-runner.toml` (hyphen — the `.md → .toml` loop at `:1367-1372` auto-generates it from `agents/tracker-runner.md`). ALSO add `tracker-runner` to `sandbox_for()` (sync-codex.sh:84-90) → `workspace-write`: today only `worker|plan-sync` are write-sandboxed, so the generated `tracker-runner.toml` would be read-only and contradict the Write/Edit-keeping contract (dormant on Codex v1 per R8, but the generated contract must not lie). Regenerate the mirror and confirm the guard + `test_tracker_sync_mirror_parity.py` are green.
9. Regenerate the Codex mirror (`./scripts/sync-codex.sh`) and confirm the structural guard + `test_tracker_sync_mirror_parity.py` are green. (The Step-0 proof point ran FIRST — see Approach Step 0.)

## Investigation targets

Required:
- `plugins/flow-next/scripts/flowctl.py:1031-1141` — enum constants + `get_default_tracker_config` (where the leaf lands)
- `plugins/flow-next/agents/pr-comment-resolver.md` — **the precedent to model** (writing subagent, `disallowedTools: Task` only); `agents/plan-sync.md` is the CONTRAST (read-only, `disallowedTools: Task, Write, Bash`) — do NOT copy its Write/Bash blacklist; the runner keeps Write/Edit/Bash
- `plugins/flow-next/skills/flow-next-tracker-sync/references/body-merge.md:259-274` — Step 5 reconcile writeback (writes merged flow body to `.flow/specs/<id>.md` via Write/Edit — WHY the runner keeps Write/Edit)
- `plugins/flow-next/skills/flow-next-tracker-sync/steps.md:7-32` — Phase 0 RALPH gate + event-tag parse
- `scripts/sync-codex.sh:310-323` (the per-file `Task→role` rewrites — the shape NOT to model on; the tracker-runner sweep must be GLOBAL), `:1367-1372` (agent .md→.toml loop), `:1627-1633` (structural guard the global sweep must satisfy)
- `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md` — the `host_is_claude_code` gate pattern to mirror

Optional:
- `plugins/flow-next/docs/flowctl.md:659-661` — config-table insertion point
- `plugins/flow-next/tests/test_tracker_config.py` — default-shape assertion pattern
- `plugins/flow-next/tests/test_tracker_sync_mirror_parity.py` — mirror-parity harness

## Key context

- `set_config` does NOT enforce enums (plain nested setter, flowctl.py:1503) — activation discipline lives in the consumer gate (exact-match `dispatch == "inline"`), NOT in flowctl. Do not add enum validation to `set_config` unless a test demands it.
- Fleet convention: every dispatched subagent needs an `agents/*.md`; the sync-codex `.md→.toml` loop turns it into a Codex role automatically. `map_model` (sync-codex.sh:46) maps `model: sonnet` (not in INTELLIGENT_SCOUTS) → CODEX_MODEL_FAST — fine, since v1 Codex resolves inline anyway (the role is cosmetic in v1).
- The dispatch string MUST introduce a `Task flow-next:tracker-runner` token or the touchpoint tasks can't reference a runner; that token is exactly what the structural guard forbids in the mirror — so the sync-codex rule and the token must land together in this task. Because the token then recurs in ~8 files owned by .2/.3, the rewrite MUST be a GLOBAL sweep landed here (see Approach Step 8), not a per-file rule — otherwise .2/.3 inherit an unowned guard failure.
- Do NOT run `scripts/bump.sh` / touch version manifests (batched-release rule). Regenerating the Codex mirror (`./scripts/sync-codex.sh`) is required and expected.

## Acceptance

- [ ] `flowctl config get tracker.dispatch --json` returns `async` on a fresh repo; `config set tracker.dispatch inline` then `get` returns `inline`; `set ... async` restores.
- [ ] `TRACKER_DISPATCH_MODES = {"async","inline"}` exists; default lands as a top-level sibling of `readyState`.
- [ ] `docs/flowctl.md` carries a `tracker.dispatch` row after `tracker.readyState`.
- [ ] `test_tracker_config.py` (or new dispatch test) asserts the default + round-trip; `uvx pytest plugins/flow-next/tests -q` green.
- [ ] `agents/tracker-runner.md` exists: `model: sonnet`, `disallowedTools: Task` only (Write/Edit/Bash retained — reconcile writeback needs Write/Edit; precedent `pr-comment-resolver.md`), the keep-Write/Edit WHY noted in the body, one-line outcome contract documented, host-only + 10-min-bound noted.
- [ ] tracker-sync `steps.md` Phase 0 threads `DISPATCH: forked` → forces queue-not-ask; SKILL.md:45 claim narrowed to "lifecycle dispatches may run forked".
- [ ] `host_is_claude_code` capability doctrine documented in one place (referenced by later tasks); v1 Codex/Copilot/Droid = inline.
- [ ] `sync-codex.sh` has a GLOBAL `Task flow-next:tracker-runner` → `tracker_runner`-role sweep across all mirror skill markdown (`find "$CODEX_DIR/skills" -name '*.md' -exec sed …`, NOT a per-file rule); `./scripts/sync-codex.sh` regenerates `codex/agents/tracker-runner.toml`; structural guard + `test_tracker_sync_mirror_parity.py` green.
- [ ] **Step 0 gate:** the interleave validation HOLDS (background dispatch survives an intervening foreground `Task` and joins cleanly) AND the fork-context reconcile writeback lands — outcome recorded in the done-summary. On no-hold: STOP, no code landed, escalate to the user.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
