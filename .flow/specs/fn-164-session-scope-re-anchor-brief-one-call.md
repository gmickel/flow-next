# Session-scope re-anchor brief: one call, token-bounded

## Goal & Context
<!-- scope: business -->

Benchmark evidence (SlopCodeBench lite-opus5, 2026-08-03, gmickel/scb-flow-next; vault: "flow-next - SlopCodeBench Experiment"): a fresh agent session re-anchoring on `.flow/` state costs ~5+ tool calls (`flowctl list`, then reading spec bodies, receipts, memory files) and drags full spec markdown into context every session. Measured: 3.81x cache-read tokens vs a no-flow control across 16 checkpoints — the carried `.flow/` context is the biggest cost multiplier after ceremony call count, and it recurs every session in every flow-next repo.

`flowctl anchor` (task scope, `cmd_anchor` at `flowctl.py:34413`) already solves this for TASK scope. The gap is SESSION scope: an agent arriving cold (benchmark checkpoint, fresh pilot tick, new chat session) has no task id yet and today reconstructs the workspace picture by hand.

Goal: one flowctl call that gives a cold session everything it needs to orient — token-bounded, deterministic, teachable as THE re-anchor step in the always-loaded block.

## Overview
<!-- scope: technical -->

New verb: **`flowctl brief`** (decision: a separate verb, NOT `anchor --session` — task-scope `anchor` is deliberately no-truncation "floor not ceiling" (`flowctl.py:34462-34465`); putting a budgeted view under the same verb would mean two contradictory truncation philosophies under one name). Pure read, no LLM, no writes.

Verified current state (HEAD): reusable task-agnostic building blocks exist — `cmd_specs` (:28563), `cmd_tasks`/`cmd_list` (:28640/:28700, runtime claim state merged via `TaskInventory.load`), `cmd_memory_list` (:22262, returns entry_id/title/track/category/status), `cmd_glossary_list`, `cmd_config_get`; the `_anchor_capture` fail-open capture pattern (:34260-34277) is the composition template. Done summaries live in task `.md` `## Done summary` sections (read via `get_task_section`) — there is no separate receipts store. No CLI reader exists for `.flow/locks/` or sync-runs/pilot-runs.

## Architecture & Data Models
<!-- scope: technical -->

**Contents** (fixed section order, pinned by test):
1. **Header**: repo/flow root, counts (open specs, ready/in-progress/done tasks), memory enabled flag.
2. **Open specs**: id, title, status, ready flag, one-line goal. Closed/done/superseded specs excluded by default.
3. **Actionable tasks**: ready + in-progress tasks with claim state. **Readiness algorithm = the canonical `cmd_ready` semantics** (task-dependency gates AND parent-spec dependency gates), reused/extracted over ONE global `TaskInventory` load — NOT `cmd_list`'s status field alone (which computes no readiness). Claim state renders the runtime fields (`assignee`, `claimed_at`, `claim_note`) from the runtime-state merge. Orphan rule preserved: tasks whose parent spec is closed still appear.
4. **Recent completions**: last N=5 done tasks — id + first line of `## Done summary` + evidence flag. **Evidence predicate (authoritative):** `true` iff the task json's done evidence dict has ANY non-empty list among `commits`/`tests`/`prs`; the default `{commits: [], tests: [], prs: []}` and legacy tasks with no evidence dict are `false` (dict presence alone is NOT evidence — `cmd_done` always writes one).
5. **Memory index**: entry_id + title one-liners from `cmd_memory_list` frontmatter (no bodies), active entries only.
6. **Pointers**: how to go deeper (`flowctl cat <id>`, `flowctl anchor <task-id> --md`, `flowctl memory search <q>`).

**Deterministic extraction rules**:
- One-line goal = first non-empty, non-heading, non-comment prose line after `## Goal & Context` (fallback: first such line in the body), hard-truncated at 120 chars.
- Memory one-liner = frontmatter title (already surfaced by `cmd_memory_list`) — never body content.
- "Oldest receipts first" ordering = ascending by task `updated_at` (tie-break: id sort key), so the newest 5 survive truncation.

**Budget**: default output <= 8000 chars (2k tokens x 4 chars/token). **Selection is computed once on a canonical dataset, then rendered twice:** trim the dataset until BOTH renders (markdown and JSON) fit 8000 chars — i.e. measure against the larger of the two render lengths — so the two forms always retain identical item ids and identical omissions (single authoritative rule; no per-format budgeting). Every rendered scalar is bounded: titles hard-capped at 80 chars, goal lines at 120, summary lines at 120 (ellipsis on cut). Deterministic truncation tiers, applied in order until under budget: (1) drop oldest recent-completions beyond the newest, (2) drop memory one-liners (oldest first), (3) drop open-spec goal lines (keep id/title/status), (4) drop whole actionable-task rows (lowest-priority/oldest first, keep the count line), (5) drop whole open-spec rows (oldest first, keep the count line). Unreadable-item diagnostics are canonical dataset items too: each `[unreadable: <path>]` line renders the path REPO-RELATIVE and capped at 120 chars (middle-ellipsis), and tier (6) drops excess unreadable lines (oldest-path-sort first) down to an aggregate `[N unreadable files — use --full]` count line. Header repo/flow-root paths are likewise capped at 120 chars. Tiers 4-6 + bounded scalars guarantee the ceiling mathematically: header + count lines + markers are O(1). Each dropped tier appends one explicit `[truncated: <what> omitted — use --full]` marker line; aggregate counts always remain. `--full` lifts the budget (same sections, no drops, ALL diagnostics retained) on both forms; `--json` carries per-section `truncated` flags.

**Derivation**: dedicated TOLERANT collectors, not naive `cmd_*` capture — the existing readers do not fail open per item (`cmd_specs`/`cmd_list` raise on one malformed JSON; memory listing silently skips malformed frontmatter to stderr; `_anchor_capture` captures stdout only). Brief loads specs per-file (one bad file → that item degrades), uses `TaskInventory.load(..., collect_load_errors=True)` (or equivalent error-collecting load), and a memory scan that RETAINS malformed paths. Unreadable items render as `[unreadable: <path>]` lines at the END of their own section. No new state, no writes, no git invocation (see Decision context).

## Edge Cases & Constraints
<!-- scope: technical -->

- Error surface, enumerated: empty/fresh `.flow/` → useful short brief with "(none)" sections, exit 0 (the benchmark checkpoint-1 case); a spec/task/memory file that fails to parse → that item degrades to an inline `[unreadable: <path>]` note, never a crash (fail-open per section like anchor); `.flow/` absent entirely → the existing not-initialized error, unchanged; orphan tasks whose spec is closed → still listed under Actionable tasks.
- Large repos (100+ specs): budget must hold; fixture with 20 specs / 50 tasks / 30 memory entries pins the truncated output.
- Determinism: byte-identical output across two consecutive runs on identical `.flow/` state (test pins it). This is why git status/log are EXCLUDED (see Decision context).
- No writes: test snapshots the `.flow/` tree (paths + content hashes) before/after and asserts equality — new assertion pattern, no precedent in `test_anchor_bundle.py`.
- Distribution: `.flow/bin` propagation + tracker manifest + sync-codex.sh twice; teaching prose changes hit the token-budget-pinned snippets (`test_token_budgets.py` pins `claude-md-snippet*.md` + `usage.md`).
- Overlap: fn-163 and fn-160 touch the same setup snippets/usage.md — second lander rebases.

## Decision context
<!-- scope: technical -->

- **Verb = `brief`**, not `anchor --session`: anchor's contract is verbatim-no-truncation (pinned by the superset test in `test_anchor_bundle.py`); brief's contract is budgeted-deterministic. Two verbs, two clean contracts; docs cross-link them.
- **Git sections excluded**: the spec's determinism requirement ("stable across runs given identical state") and pinned fixtures are incompatible with live git output; a cold session gets git state from its own `git status` call (one the agent makes anyway). Brief is `.flow/`-state only; the Pointers section says so.
- **Locks/runs sections cut from v1**: no CLI reader exists for `.flow/locks/` or sync-runs/pilot-runs (all gitignored scratch); claim state — the actually useful signal — already rides the `cmd_list` runtime merge into Actionable tasks. Building new readers for low-orientation-value scratch dirs fails YAGNI; revisit only on demonstrated need.
- Budget formula fixed as chars/4 on the rendered default output (8000 chars), matching the spec's "~2k tokens-equivalent"; precedent is char-budget + explicit marker (`fit_cursor_*_to_budget`) and item-cap + flag (`_FINDINGS_DIGEST_MAX_ITEMS`) — brief combines both.

## Strategy Alignment

Active tracks served by this plan:
- **Ralph autonomous mode** — every pilot tick and Ralph iteration starts a cold session; brief-first re-anchor turns ~5+ orientation calls into one bounded call, directly cutting the per-tick overhead the decision log measures.

## Quick commands
```bash
cd plugins/flow-next/tests && python3 -m unittest test_brief test_anchor_bundle -q
```
(Final gate: full parallel suite + `uvx ruff@0.16.0 check .` + flowctl propagation + sync-codex.sh twice, per repo CLAUDE.md.)

## Acceptance Criteria
<!-- scope: both -->

- **R1:** One flowctl invocation (`flowctl brief`) yields the session brief; fixture test pins content and section order for a populated repo and an empty repo; unparseable individual files degrade to inline notes (repo-relative, 120-char-capped paths) that participate in the truncation tiers like any other item — never a crash, never a budget violation; all diagnostics retained under `--full`.
- **R2:** Default output <= 8000 chars on BOTH forms for ANY repository state (whole-row tiers 4-5 + bounded scalars guarantee the ceiling; O(1) floor of header/counts/markers). Fixtures: 20 specs / 50 tasks / 30 memory entries AND a pathological fixture whose mandatory rows alone exceed 8000 chars (long titles, 100+ rows) AND a many-corrupt-files/long-root-path fixture (both formats). Truncation markers appear; order deterministic; byte-identical across runs on identical state.
- **R3:** `--json` carries the same data machine-readably (per-section `truncated` flags); selection computed once on the canonical dataset against the larger render, so markdown and JSON retain IDENTICAL item ids and omissions (parity test pins retained ids + both lengths <= 8000); `--full` lifts the budget on both forms.
- **R4:** Setup snippets + relevant skills (pilot/guide cold-session entry points) teach brief-first re-anchor as the default cold-session step; GLOSSARY.md Re-anchoring entry covers session scope; snippet token budgets still pass.
- **R5:** No writes: test asserts `.flow/` byte-identical (paths + hashes) before/after `brief`, `brief --json`, `brief --full`.
- **R6:** Repo CHANGELOG `## Unreleased` entry; `docs/flowctl.md` gains a `### brief` section cross-linked with `### anchor`; docs-site live reference pages updated NOW (site build green) while the site's versioned changelog + version fields defer to the batched release; the standing downstream walk (`~/work/agent-instructions/downstream-properties.md`: docs-site → microsite → AIxSDLC guide → vault) executes in this workstream with per-property update-or-no-change evidence; no version bump (batched releases).

## Early proof point
Task fn-164-session-scope-re-anchor-brief-one-call.1 validates the core approach (deterministic budgeted brief composed from existing read paths, pinned by fixture). If deterministic pinning proves brittle (extraction rules too fragile), re-evaluate the extraction rules before writing the teaching prose.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | One-call brief, pinned fixtures, fail-open | .1 | — |
| R2  | 8000-char budget + deterministic truncation | .1 | — |
| R3  | --json / --full parity | .1 | — |
| R4  | Brief-first teaching + glossary | .2 | — |
| R5  | No-writes assertion | .1 | — |
| R6  | CHANGELOG + docs-site + CLI reference | .2 | — |

## Boundaries
<!-- scope: business -->

- NOT changing task-scope `anchor` semantics (its no-truncation superset test stays untouched).
- NOT summarizing via LLM — deterministic extraction only.
- NOT building locks/runs readers (cut from v1; claim state comes from the existing runtime merge).
- NOT the ceremony/write-path work (fn-163).
- Benchmark prompt adoption happens in gmickel/scb-flow-next after revendor, not here.
