---
satisfies: [R4, R5]
---

## Description

Enrich `repo-scout` and `context-scout` agents to call `flowctl repo-map list --json` when `.clawpatch/` is present, emit an optional `features_anchored: [...]` field in their structured output (with `last_mapped` timestamp), and fall back gracefully to the current grep/glob flow when `.clawpatch/` is absent. The fallback contract is load-bearing — scouts must work without the map.

**Size:** M
**Files:**
- `plugins/flow-next/agents/repo-scout.md` — new Step 0 "Pre-computed feature index" + output schema `features_anchored` field
- `plugins/flow-next/agents/context-scout.md` — new Step 0 + output schema field (mirror context-scout's existing `Fallback: Standard Tools` idiom)
- `plugins/flow-next/tests/test_scout_fallback_contract.py` (new) — static contract test (Layer 1 of the two-layer fallback verification)
- `plugins/flow-next/tests/scout-fallback.sh` (new) — thin bash wrapper invoking the Python contract test for uniform test-runner entry
- `plugins/flow-next/tests/fixtures/scout-without-clawpatch/` (new) — minimal fixture dir without `.clawpatch/`

## Approach

**Decision lock-in (from spec):** scouts call `flowctl repo-map list --json` to centralize the schema-version check — they do NOT parse `.clawpatch/features/*.json` directly.

**repo-scout** changes:
- Insert new Step 0 "Pre-computed feature index" in the `Search Strategy` section (`agents/repo-scout.md:16-37`), before the existing 4 numbered steps. Step 0: *"If `.clawpatch/` present, call `flowctl repo-map list --json` first; use returned features to anchor R-IDs and decision-context references in subsequent steps. If absent or count=0, proceed to Step 1 unchanged."*
- Add `features_anchored: [...]` to the Output Format block (lines 53-82), positioned between `Related Code` and `Reusable Code`. Schema: `{ feature_id, title, kind, owned_files: [...], last_mapped: ISO8601 }[]`. Omit field entirely when `.clawpatch/` absent (don't emit empty array — absence signals "scout ran without map").
- Author the graceful-degrade prose fresh (no existing idiom). Mirror the phrasing from `flow-next-prospect/SKILL.md:57` Phase 1 "Ground" (*"scan repo with graceful degradation"*).

**context-scout** changes:
- Insert new Step 0 in the `Exploration Workflow` (lines 96-163) before `Get Overview`. Step 0 calls `flowctl repo-map list --json` and uses results to scope the rp-cli builder prompt. Skip when absent.
- The existing `Fallback: Standard Tools` section at lines 368-385 already establishes the graceful-degrade idiom for context-scout — extend it explicitly to mention `.clawpatch/` absence.
- Add the same `features_anchored` field to the output schema (lines 210-243), positioned consistently with repo-scout.

**Fallback verification — honest two-layer approach** (a single `flowctl repo-map list --json count=0` check would give false confidence that the scouts themselves degrade correctly; that's not testable without running a scout subagent in CI, which is out of scope):

Layer 1 — **static contract test** at `plugins/flow-next/tests/test_scout_fallback_contract.py`:
- Parses `plugins/flow-next/agents/repo-scout.md` and `agents/context-scout.md` as text.
- Asserts presence of: (a) `features_anchored` field documented in Output Format section, (b) an explicit fallback prose block naming `.clawpatch/` absence (e.g. matching regex `flowctl repo-map list --count.*0`/`absent`/`grep` near each other), (c) NO required-step language for `.clawpatch/` (regex: no `MUST.*\.clawpatch` or `required.*\.clawpatch` appears in workflow).
- Plus: `flowctl repo-map list --json` against `tests/fixtures/scout-without-clawpatch/` (a minimal fixture dir with NO `.clawpatch/`) returns `{success:true, count:0, features:[]}` with exit 0.
- This proves the contract (prose says scouts MUST degrade + plumbing supports it). It does NOT prove the scout LLM behavior — that's checked at manual smoke.

Layer 2 — **manual smoke** documented in task spec (NOT a CI test):
- Run `/flow-next:plan "test scope"` against this repo (no `.clawpatch/`); confirm scout output produced; confirm no `features_anchored` field in output; confirm no agent error about missing feature index.
- Logged once in the task's Done summary at completion time, not gated as a CI assertion.

Bash test file at `plugins/flow-next/tests/scout-fallback.sh` becomes a thin wrapper that invokes the Python test (so existing test runners pick it up uniformly):
```bash
#!/usr/bin/env bash
exec python3 -m pytest plugins/flow-next/tests/test_scout_fallback_contract.py -v
```

This re-framing follows the codex reviewer's note: "either build a minimal scout harness… or change acceptance to a static contract test plus manual scout smoke." Going with the static-contract + manual-smoke path because building an LLM scout harness in CI is a fn-50.3-bloating side-quest.

**Staleness signal:** scout output `features_anchored.last_mapped` carries the newest `updatedAt` from `features/*.json`. Scouts emit one informational line (not warning) `[repo-scout] feature map last updated {N} days ago` when N > 7. No refusal — staleness is signal, not block.

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/agents/repo-scout.md:16-37` (Search Strategy), `:53-82` (Output Format) — full file is < 100 lines
- `plugins/flow-next/agents/context-scout.md:96-163` (Exploration Workflow), `:210-243` (Output Format), `:368-385` (Fallback: Standard Tools)
- `plugins/flow-next/skills/flow-next-prospect/SKILL.md:57` — graceful-degrade idiom phrasing
- Output from fn-50.2: `flowctl repo-map list --json` shape (this task depends on .2)

**Optional**:
- `plugins/flow-next/agents/practice-scout.md`, `docs-scout.md` — confirm output-schema convention is consistent across the scout suite

## Key context

- Scout output is structured Markdown with confidence tags `[VERIFIED]` / `[INFERRED]`. `features_anchored` is an additive optional field.
- Downstream skills (`/flow-next:plan`, `/flow-next:capture`) consume scout output as-is. **They do NOT explicitly read or branch on `features_anchored` in fn-50** — that's tracked separately as future work. The field is purely scout-level enrichment in this spec.
- The CI smoke runs without clawpatch installed. Test correctness: scouts work + produce no `features_anchored` content. Not testing scout output quality (that's harder; cover at integration/manual-smoke time).

## Acceptance

- [ ] R4: `repo-scout.md` Step 0 calls `flowctl repo-map list --json` when `.clawpatch/` present; emits `features_anchored: [...]` with `last_mapped` ISO timestamp in output
- [ ] R4: `context-scout.md` Step 0 calls `flowctl repo-map list --json` when `.clawpatch/` present; emits `features_anchored: [...]` with `last_mapped` ISO timestamp; updates `Fallback: Standard Tools` to mention `.clawpatch/` absence
- [ ] R4: Output schema documents the `features_anchored` field (subfields: `feature_id`, `title`, `kind`, `owned_files`, `last_mapped`) in both scout files
- [ ] R4: Staleness signal: scout output emits one informational line `[scout] feature map last updated N days ago` when N > 7
- [ ] R5: Both scouts' agent prose explicitly documents the fallback path when `.clawpatch/` absent; no `MUST/required` language ties them to the feature index
- [ ] R5: Static contract test `plugins/flow-next/tests/test_scout_fallback_contract.py` asserts (a) `features_anchored` documented in scout Output Format, (b) fallback prose present in both agent files, (c) no `required .clawpatch/` language, (d) `flowctl repo-map list --json` against fixture returns `count:0` clean
- [ ] R5: `plugins/flow-next/tests/scout-fallback.sh` wraps the Python contract test (uniform test-runner entrypoint)
- [ ] R5: Fixture `plugins/flow-next/tests/fixtures/scout-without-clawpatch/` is minimal and intentionally has no `.clawpatch/`
- [ ] R5: Manual smoke logged in Done summary: run `/flow-next:plan "test scope"` against this repo; scout output produced cleanly with no `features_anchored` field and no agent error about missing feature index

## Done summary

_To be filled by `/flow-next:work` on completion._

## Evidence

_To be filled by `/flow-next:work` on completion._
