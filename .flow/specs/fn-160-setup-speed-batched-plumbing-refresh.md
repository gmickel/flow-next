# fn-160-setup-speed-batched-plumbing-refresh Setup speed: batched plumbing, refresh fast path, per-platform workflow split

## Goal & Context

`/flow-next:setup` is really slow in practice — worst in copy mode on a Codex host — and the copy-mode upgrade path (re-run setup per repo after every plugin update) feels like massive friction. [user]

Analysis (2026-08-02 session) attributes the wall clock to four compounding costs, none of which is the questions themselves:

1. **Context bulk.** `skills/flow-next-setup/workflow.md` is ~75KB (~30k tokens) and must be read before step 1; it embeds all five platform variants of the Review/Docs questions plus detection-rationale archaeology, so every host reads ~5x what one platform needs.
2. **Subprocess churn.** ~7 separate raw `config get` probes (Step 6a) plus ~13 `config set` calls (Step 7), plus init / sync-active / setup-block / verify / stamp invocations — each a separate Python spawn and agent tool-call round-trip.
3. **Live LLM probes in the model-pins ceremony** (`references/model-pins.md`): foreground `codex exec` accept-probes (20s timeout each), `copilot -p "/model"`, `cursor-agent --list-models` on every re-run — no staleness gate on `models.verifiedAt`.
4. **Codex ask serialization.** The mirror's plain-text numbered prompts are stop-and-wait; asks outside the grouped 6d prompt add up to ~8 blocking round-trips per run.

Hard constraint: optimize without removing any question or any explanation. [user]

## Overview / Approach

Prose-that-grew-into-plumbing extraction (the fn-139-141 template) applied to setup, plus a continuation of fn-130's reached-path conditional loading:

- **Plumbing (R1-R3):** new `flowctl setup` command group. `setup detect --json` wraps the existing keyless-root `ConfigSnapshot` read (`flowctl.py:17307-17386`) and folds in CLI detection, tracker-active, criteria existence — one spawn replaces Step 6a. Batched `config set` (repeated `key=value` args) with validate-all-then-write-all semantics reusing the existing per-key validators (`flowctl.py:17388+`). `setup refresh` chains the Step 3/4 copy list → `verify_tracker_manifest` → `setup-block apply` per marker-bearing file (existing state machine at `flowctl.py:2737-2836`) → `setup_version` stamp LAST.
- **Skill restructure (R4):** split `workflow.md` into a slim core + per-platform references (the `agent_docs/adding-skills.md` "backend-split workflow.md" + "gated references" patterns; prior art: flow-next-spec-completion-review commit b2f6f0e, flow-next-impl-review commit 06f6e6f). Core keeps step order, gates, and consent semantics; platform question sets and detection-fixture archaeology move to references read after `PLATFORM` resolves.
- **Gating (R5) + regrouping (R6):** staleness gate on the 6e ceremony via existing `models.verifiedAt` (no new config key); Codex-mirror ask regrouping where step ordering already permits.

## Plan decisions (gap-analysis resolutions)

- **Refresh on plugin-mode repo: hard-refuse** with a message (plugin mode has nothing to refresh; updates land via the plugin). Never converts mode; stamp-last invariant (fn-121 / PR #227) untouched.
- **Refresh scope:** the full Step 4 copy list including `flowctl.cmd`, plus `templates/spec.md`, plus `.codex/agents/*.toml` re-copy when `.codex/agents/` already exists in the repo. `.flow/usage.md` refreshed only when byte-identical to a prior canonical (customized → skipped + listed).
- **Refresh never asks.** A docs block whose `setup-block apply` returns `ask` is left untouched and listed in the output ("resolve via /flow-next:setup"); refresh continues for everything else and still stamps. Zero-question guarantee holds.
- **Ordering/atomicity:** copy → verify (STOP loudly on corrupt install, no rollback — same contract as today's Step 4) → docs-block apply → stamp `setup_version` last. Interrupted run leaves the stamp absent → re-run; refresh is idempotent (run twice → no drift, no mtime bumps on unchanged files).
- **Batched config set:** validate every key first, write all or nothing.
- **`setup detect` failure contract:** per-field null/error markers, never whole-call failure (Step 6a tolerates individual probe failures today); output consumed once per run.
- **Staleness gate:** malformed or future `models.verifiedAt` is treated as absent (ceremony offered); skip outcome gets its own summary string `skipped (fresh — verified <date>)`; explicit user request always forces the ceremony.
- **sync-codex.sh anchors:** the split retargets the literal-string awk/sed transforms (sync-codex.sh:478-537) to their new files and adds hard-fail guards for each moved anchor (fn-100 pattern) — never silently-passing transforms.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_setup_block_helper test_setup_mode_stamp test_setup_reference_routing test_setup_cursor_host test_setup_grok_host test_model_pin_ceremony_prose -q
```

## Boundaries / non-goals

- No question, option, recommendation, or explanation removed — latency/friction change, not a ceremony diet. [user]
- No change to what setup decides or writes: same config keys, same stamps, same consent semantics (fn-121 mode table and fn-130 frozen behavior matrix preserved).
- No redesign of the model-pins ceremony's judging content — only when it runs.
- Cursor/Grok/Droid host behavior contracts unchanged; no new config keys expected (if one appears, it goes through the fn-138 schema TABLE + drift test).

## Strategy Alignment

Active tracks served by this plan:
- **Tracker determinism** — applies its "prose that grew into plumbing" extraction template to setup's mechanical steps (detection, batched writes, refresh), keeping every judgment/ask in the host.
- **Cross-platform parity** — the copy-mode refresh fast path directly serves the fn-121/fn-139 install-integrity contract that parity rests on; per-platform references make each host's reached path smaller without forking semantics.

## Decision context

The complaint has two heads: raw slowness (worst on Codex copy mode) and the upgrade treadmill. The refresh fast path (R3) kills the treadmill and is the highest-value single change; plumbing batching (R1/R2) and the doc split (R4) attack per-run latency; the staleness gate (R5) removes the slowest single step (live LLM probes) from routine runs. Prose trimming alone was rejected because questions and explanations are protected — wins come from plumbing, conditional loading, and gating. Capture's `[inferred]` criteria were scout-confirmed against the codebase (repo-scout verified every extension point) and are planned as normal requirements.

Process note: spec + plan land directly on main (isolated worktree) so the in-flight agent on `chore/review-cap-8` is undisturbed; implementation happens later on its own branch, sequenced after fn-156 (sync-codex.sh guard overlap). [user]

## Acceptance Criteria

- **R1:** A single deterministic flowctl call (`setup detect --json`) returns everything Step 6a currently gathers piecemeal (platform inputs, raw config values, tracker-active, criteria existence, CLI detection), replacing the per-key probe fences; individual probe failures degrade per-field, never fail the call.
- **R2:** Step 7's config persistence lands in at most 1-2 flowctl invocations (batched `config set` with validate-all-then-write-all), preserving today's per-key validation.
- **R3:** `flowctl setup refresh` exists for copy-mode upgrades: one invocation re-copies the full Step 4 snapshot list (+ `.codex/agents` when present), verifies the tracker package, re-applies marker-scoped docs blocks via the existing setup-block state machine, and restamps `setup_version` last — asking zero questions ever (ambiguous blocks are skipped and listed); hard-refuses on plugin-mode repos; idempotent.
- **R4:** The mandatory pre-read for a setup run shrinks substantially (resolved platform reads well under half of today's ~75KB), with platform question sets and detection archaeology in conditionally-loaded references; the reached-path evidence fixture (`optimization/reached-path/setup-routing-evidence.json`) is regenerated in the same change.
- **R5:** The model-pins ceremony gates live CLI probes on staleness: fresh `models.verifiedAt` (within the existing ~90-day window) skips probes and the ask on routine re-runs with a distinct summary outcome; absent/malformed/future values still offer the ceremony; explicit request forces it.
- **R6:** On the Codex mirror, blocking plain-text round-trips per fresh copy-mode run are reduced by regrouping asks where step ordering permits, without dropping or merging away any question's content.
- **R7:** No question, option, recommendation, or explanation is removed: every ask reachable today remains reachable with equivalent copy, and all consent gates fire under the same conditions (fn-130 frozen matrix + fn-121 mode invariants hold). [user]
- **R8:** Full gate green: setup-related suites, `test_setup_reference_routing.py` (with regenerated evidence), sync-codex.sh run twice with no diff churn and its guards passing, `test_flow_config_schema_drift` untouched or updated per fn-138, `uvx ruff@0.16.0 check .`.

## Early proof point

Task fn-160-setup-speed-batched-plumbing-refresh.1 validates the core approach (mechanical Step 6a/7 semantics can be captured in deterministic plumbing without changing any decision or ask). If `setup detect` cannot faithfully reproduce the per-platform probe semantics in one JSON shape, re-evaluate the plumbing-first strategy before the workflow split (.3) builds on it.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | One-call `setup detect --json` | fn-160-setup-speed-batched-plumbing-refresh.1 | — |
| R2  | Batched config writes | fn-160-setup-speed-batched-plumbing-refresh.1 | — |
| R3  | `setup refresh` fast path | fn-160-setup-speed-batched-plumbing-refresh.2 | — |
| R4  | workflow.md split + evidence regen | fn-160-setup-speed-batched-plumbing-refresh.3 | — |
| R5  | Model-pins staleness gate | fn-160-setup-speed-batched-plumbing-refresh.4 | — |
| R6  | Codex ask regrouping | fn-160-setup-speed-batched-plumbing-refresh.4 | — |
| R7  | Nothing removed, gates unchanged | .3 and .4 acceptance (cross-cutting) | — |
| R8  | Full gate + mirror idempotency | every task; final sweep in .4 | — |

## References

- `plugins/flow-next/skills/flow-next-setup/workflow.md` (1000 lines; Step 6a probes ~L299-372, Step 7 writes ~L724-811, copy list L141-156, meta stamp L282-291)
- `plugins/flow-next/scripts/flowctl.py`: setup-block state machine :2737-2836, setup-mode set :17045-17156, config get root read :17307-17386, config set :17388+, parser registration :42209-42843
- `scripts/sync-codex.sh`: skill copy :205-208, setup-prose transforms :478-537
- `plugins/flow-next/skills/flow-next-setup/references/model-pins.md` (ceremony; probes A, gate at workflow.md:705-712)
- `plugins/flow-next/tests/test_setup_reference_routing.py` (evidence fixture :108-121), `test_setup_block_helper.py`, `test_setup_mode_stamp.py`, `test_setup_cursor_host.py`, `test_setup_grok_host.py`, `test_model_pin_ceremony_prose.py`, `test_model_routing_scaffold.py`
- `agent_docs/adding-skills.md` L26-81 (split + gated-reference patterns), `agent_docs/setup-modes.md`
- Prior art specs: fn-130 (reached-path harness + frozen matrix), fn-121 (plugin mode), fn-115 (pin ceremony), fn-126 (Grok detection), fn-138 (config schema), fn-139-141 (plumbing extraction template)
- Memory: abort-option-copy-must-reflect-pre-2026-05-18, audit-sync-codexsh-during-planning-for-2026-04-30, mirror-regen-exposes-latent-canonical-2026-06-11, skill-workflow-snippets-must-enforce-2026-06-11, spec-named-config-keys-must-be-checked-2026-07-15
