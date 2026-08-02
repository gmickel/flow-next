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

- **Plumbing (R1-R3):** new `flowctl setup` command group. `setup detect --json` wraps the existing keyless-root `ConfigSnapshot` read (`flowctl.py:17307-17386`) and folds in CLI detection, tracker-active, criteria existence — one spawn replaces Step 6a. Batched `config set` (repeated `key=value` args) with validate-all-then-write-all semantics reusing the existing per-key validators (`flowctl.py:17388+`). `setup refresh` chains the Step 3/4 copy list → `verify_tracker_manifest` → `setup-block apply` per marker-bearing file (existing state machine at `flowctl.py:2737-2836`) → `setup_version` stamp on success.
- **Skill restructure (R4):** split `workflow.md` into a slim core + per-platform references (the `agent_docs/adding-skills.md` "backend-split workflow.md" + "gated references" patterns; prior art: flow-next-spec-completion-review commit b2f6f0e, flow-next-impl-review commit 06f6e6f). Core keeps step order, gates, and consent semantics; platform question sets and detection-fixture archaeology move to references read after `PLATFORM` resolves.
- **Gating (R5) + regrouping (R6):** staleness gate on the 6e ceremony via existing `models.verifiedAt` (no new config key); Codex-mirror regrouping of the UNCONDITIONAL pre-6d asks only.

## Plan decisions (gap-analysis + review-round-1 resolutions)

- **Refresh on plugin-mode repo: hard-refuse** with a message (plugin mode has nothing to refresh; updates land via the plugin). Never converts mode; stamp-last invariant (fn-121 / PR #227) untouched.
- **Refresh invocation contract (review R1 finding):** `setup refresh` is invoked from the LIVE plugin CLI with explicit, validated `--plugin-root <path>` and `--platform <claude-code|codex|droid|cursor|grok>` inputs supplied by skill prose (platform classification stays in prose — env-var visibility belongs to the host shell). The command REFUSES when the resolved copy source lives under the destination `.flow/bin` (self/local-snapshot source) and refuses a plugin root missing the expected manifest. Platform selects the correct docs snippet template for `setup-block apply` (Codex `$`-syntax AGENTS.md vs slash-syntax elsewhere; plugin-mode template never applies — refresh is copy-mode-only).
- **Refresh scope:** the full Step 4 copy list including `flowctl.cmd`, plus `templates/spec.md`, plus `.codex/agents/*.toml` re-copy when `--platform codex` AND `.codex/agents/` already exists (never created by refresh).
- **`.flow/usage.md` provenance (review findings R1+R2-1):** a dedicated flowctl write API (`flowctl setup usage-record` — exact name free) records the normalized hash of the usage.md just written into `.flow/meta.json` (`setup.usage_hash`, machine-written meta — not a config key). BOTH writers call it: `setup refresh` internally, AND the interactive `/flow-next:setup` prose (task .3 wires the call after every usage.md outcome that leaves a canonical file on disk — missing→written, identical→no-op-but-record, user-accepted overwrite). Refresh overwrites when the on-disk normalized hash matches the recorded hash (provably untouched), writes when missing, otherwise skips + lists as customized. Migration: when no recorded hash exists (pre-fn-160 installs), compare against the CURRENT bundled canonical only — identical → overwrite + record; different → skip + list (conservative; a full `/flow-next:setup` run resolves it with its ask). Acceptance covers first-setup→later-version-refresh continuity.
- **Refresh never asks.** A docs block whose `setup-block apply` returns `ask` is left untouched and listed; `kept` (recorded customized sentinel) is honored silently and listed for visibility; refresh continues for everything else. Zero-question guarantee holds.
- **Filesystem safety (review findings R1+R2-2):** every refresh write is containment-checked by the SAME existing helpers the rest of flowctl uses (`_flow_path_is_contained` / `_flow_leaf_is_safe`): the `.flow` root itself MAY be a symlink (supported worktree/shared-checkout layout — resolve it and treat the resolved dir as the storage root), while symlinked descendants and leaves beneath the resolved root are rejected. Writes are compare-before-write (identical content → no write, no mtime bump) and atomic temp+rename in the destination directory; `flowctl.cmd` self-update uses the same temp+rename. Fixtures cover BOTH the supported symlinked-`.flow`-root case and malicious/dangling descendant-symlink cases, proving no outside-repo writes.
- **Refresh state machine (review finding — exact outcomes):** copy phase (compare-before-write per file; outcome per file: `copied|unchanged|refused`) → tracker verify (fail → STOP, no docs writes, no stamp; prior `setup_version` stamp REMAINS — a failed upgrade keeps the old version stamped, it is never cleared) → docs blocks (`appended|refreshed|unchanged` proceed; `kept|ask` listed, untouched) → stamp `setup_version`+`setup_date` only when copy+verify succeeded (kept/ask blocks do NOT block the stamp; they are listed in output). Second run in a row: all `unchanged`, no mtime changes, same stamp. Output JSON enumerates every outcome class.
- **Batched config set:** validate every key first, write all or nothing.
- **`setup detect` failure contract:** per-field null/error markers, never whole-call failure (Step 6a tolerates individual probe failures today); output consumed once per run.
- **Staleness gate:** malformed or future `models.verifiedAt` is treated as absent (ceremony offered); skip outcome gets its own summary string `skipped (fresh — verified <date>)`; explicit user request always forces the ceremony.
- **Codex regrouping scope (review finding — no compound-prompt protocol invention):** only asks that are UNCONDITIONAL at their point in the flow and whose answers nothing between them consumes are regrouped (Step 4a SPEC.md offer + the usage.md overwrite ask when both fire). Conditional follow-ups (the HTML artifacts-in-git question exists only after HTML=Yes) and result-dependent asks (mode gate, model-pins propose, docs-overwrite) STAY sequential. Grouped-abort precedence is defined explicitly: `abort` in a grouped prompt takes effect as the earliest-step abort among the grouped questions (later grouped answers are discarded unprocessed; abort copy reflects pre-prompt state per the abort-option memory lesson). Post-transform transcript fixtures cover: both grouped questions answered, each abort position, skip, and malformed replies. Honest target: ~8 → ~5-6 blocking waits, not 4.
- **sync-codex.sh anchors:** the split retargets the literal-string awk/sed transforms (sync-codex.sh:478-537) to their new files and adds hard-fail guards for each moved anchor (fn-100 pattern) — never silently-passing transforms.
- **Behavior-parity evidence (review finding — spot-check insufficient):** parity is proven by (a) a deterministic question/option INVENTORY — extract every ask header, option label, and recommendation marker from the canonical skill and the post-transform mirror, before and after the change, and diff them (empty diff required except approved regrouping moves); and (b) a scenario walk of the fn-130 frozen matrix (first-install, refresh, customization, marker, question, stamp, host-specific rows) on canonical AND post-transform Codex output. Both artifacts are mandatory acceptance evidence in .3/.4, not a spot-check.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_setup_block_helper test_setup_mode_stamp test_setup_reference_routing test_setup_cursor_host test_setup_grok_host test_model_pin_ceremony_prose -q
```

## Boundaries / non-goals

- No question, option, recommendation, or explanation removed — latency/friction change, not a ceremony diet. [user]
- No change to what setup decides or writes: same config keys, same stamps, same consent semantics (fn-121 mode table and fn-130 frozen behavior matrix preserved).
- No redesign of the model-pins ceremony's judging content — only when it runs.
- No new compound-prompt protocol for conditional questions — conditional asks stay sequential (review round 1).
- Cursor/Grok/Droid host behavior contracts unchanged; no new config keys expected (`setup.usage_hash` lives in machine-written `.flow/meta.json`, not `.flow/config.json` — if a config key does appear it goes through the fn-138 schema TABLE + drift test).

## Strategy Alignment

Active tracks served by this plan:
- **Tracker determinism** — applies its "prose that grew into plumbing" extraction template to setup's mechanical steps (detection, batched writes, refresh), keeping every judgment/ask in the host.
- **Cross-platform parity** — the copy-mode refresh fast path directly serves the fn-121/fn-139 install-integrity contract that parity rests on; per-platform references make each host's reached path smaller without forking semantics.

## Decision context

The complaint has two heads: raw slowness (worst on Codex copy mode) and the upgrade treadmill. The refresh fast path (R3) kills the treadmill and is the highest-value single change; plumbing batching (R1/R2) and the doc split (R4) attack per-run latency; the staleness gate (R5) removes the slowest single step (live LLM probes) from routine runs. Prose trimming alone was rejected because questions and explanations are protected — wins come from plumbing, conditional loading, and gating. Capture's `[inferred]` criteria were scout-confirmed against the codebase and are planned as normal requirements. Review round 1 (codex:gpt-5.6-sol) tightened R3's state/provenance/safety contracts, scaled R6 to unconditional-asks-only, and upgraded R7's evidence from spot-check to deterministic inventory + matrix walk.

Process note: spec + plan land directly on main (isolated worktree) so the in-flight agent on `chore/review-cap-8` is undisturbed; implementation happens later on its own branch, sequenced after fn-156 (sync-codex.sh guard overlap). [user]

## Acceptance Criteria

- **R1:** A single deterministic flowctl call (`setup detect --json`) returns everything Step 6a currently gathers piecemeal (platform inputs, raw config values, tracker-active, criteria existence, CLI detection), replacing the per-key probe fences; individual probe failures degrade per-field, never fail the call.
- **R2:** Step 7's config persistence lands in at most 1-2 flowctl invocations (batched `config set` with validate-all-then-write-all), preserving today's per-key validation.
- **R3:** `flowctl setup refresh` exists for copy-mode upgrades: invoked from the live plugin CLI with validated `--plugin-root`/`--platform`; refuses self/local-snapshot sources and plugin-mode repos; one invocation re-copies the full Step 4 snapshot list (+ `.codex/agents` on codex when present) with compare-before-write, containment via the existing `_flow_path_is_contained`/`_flow_leaf_is_safe` helpers (symlinked `.flow` root supported, symlinked descendants rejected), and atomic temp+rename; verifies the tracker package (failure = stop, old stamp retained); re-applies marker-scoped docs blocks via the existing setup-block state machine with `kept`/`ask` listed-not-touched; resolves `.flow/usage.md` via recorded provenance hash (`setup.usage_hash`, written through the shared `setup usage-record` API that the interactive setup path also calls); stamps `setup_version` only on copy+verify success; asks zero questions ever; idempotent (second run all-unchanged, no mtime drift).
- **R4:** The mandatory pre-read for a setup run shrinks substantially (resolved platform reads well under half of today's ~75KB), with platform question sets and detection archaeology in conditionally-loaded references; the reached-path evidence fixture (`optimization/reached-path/setup-routing-evidence.json`) is regenerated in the same change.
- **R5:** The model-pins ceremony gates live CLI probes on staleness: fresh `models.verifiedAt` (within the existing ~90-day window) skips probes and the ask on routine re-runs with a distinct summary outcome; absent/malformed/future values still offer the ceremony; explicit request forces it.
- **R6:** On the Codex mirror, the unconditional pre-6d asks (Step 4a SPEC.md offer, usage.md overwrite) are regrouped into one numbered prompt with explicitly defined grouped-abort precedence; conditional and result-dependent asks stay sequential; post-transform transcript fixtures cover grouped answers, each abort position, skip, and malformed replies; blocking waits drop ~8 → ~5-6 with every question's content intact.
- **R7:** No question, option, recommendation, or explanation is removed, and all consent gates fire under the same conditions — proven by the deterministic question/option inventory diff (canonical + post-transform mirror, before/after) and a scenario walk of the fn-130 frozen matrix, both attached as acceptance evidence (fn-121 mode invariants hold). [user]
- **R8:** Full gate green: setup-related suites, `test_setup_reference_routing.py` (with regenerated evidence), sync-codex.sh run twice with no diff churn and its guards passing, symlink-safety fixtures for refresh, `test_flow_config_schema_drift` untouched or updated per fn-138, `uvx ruff@0.16.0 check .`.

## Early proof point

Task fn-160-setup-speed-batched-plumbing-refresh.1 validates the core approach (mechanical Step 6a/7 semantics can be captured in deterministic plumbing without changing any decision or ask). If `setup detect` cannot faithfully reproduce the per-platform probe semantics in one JSON shape, re-evaluate the plumbing-first strategy before the workflow split (.3) builds on it.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | One-call `setup detect --json` | fn-160-setup-speed-batched-plumbing-refresh.1 | — |
| R2  | Batched config writes | fn-160-setup-speed-batched-plumbing-refresh.1 | — |
| R3  | `setup refresh` fast path (contract per plan decisions) | fn-160-setup-speed-batched-plumbing-refresh.2 | — |
| R4  | workflow.md split + evidence regen | fn-160-setup-speed-batched-plumbing-refresh.3 | — |
| R5  | Model-pins staleness gate | fn-160-setup-speed-batched-plumbing-refresh.4 | — |
| R6  | Codex unconditional-ask regrouping + fixtures | fn-160-setup-speed-batched-plumbing-refresh.4 | — |
| R7  | Parity inventory + fn-130 matrix walk | fn-160-setup-speed-batched-plumbing-refresh.3, .4 | — |
| R8  | Full gate + mirror idempotency + symlink fixtures | every task; final sweep in .4 | — |

## References

- `plugins/flow-next/skills/flow-next-setup/workflow.md` (1000 lines; Step 6a probes ~L299-372, Step 7 writes ~L724-811, copy list L141-156, meta stamp L282-291)
- `plugins/flow-next/scripts/flowctl.py`: setup-block state machine :2737-2836 (incl. its symlink-target rejection), setup-mode set :17045-17156, config get root read :17307-17386, config set :17388+, parser registration :42209-42843
- `scripts/sync-codex.sh`: skill copy :205-208, setup-prose transforms :478-537
- `plugins/flow-next/skills/flow-next-setup/references/model-pins.md` (ceremony; probes A, gate at workflow.md:705-712)
- `plugins/flow-next/tests/test_setup_reference_routing.py` (evidence fixture :108-121), `test_setup_block_helper.py`, `test_setup_mode_stamp.py`, `test_setup_cursor_host.py`, `test_setup_grok_host.py`, `test_model_pin_ceremony_prose.py`, `test_model_routing_scaffold.py`
- `agent_docs/adding-skills.md` L26-81 (split + gated-reference patterns), `agent_docs/setup-modes.md`
- Prior art specs: fn-130 (reached-path harness + frozen matrix), fn-121 (plugin mode), fn-115 (pin ceremony), fn-126 (Grok detection), fn-138 (config schema), fn-139-141 (plumbing extraction template)
- Memory: abort-option-copy-must-reflect-pre-2026-05-18, audit-sync-codexsh-during-planning-for-2026-04-30, mirror-regen-exposes-latent-canonical-2026-06-11, skill-workflow-snippets-must-enforce-2026-06-11, spec-named-config-keys-must-be-checked-2026-07-15
