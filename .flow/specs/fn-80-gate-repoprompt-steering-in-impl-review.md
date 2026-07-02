# fn-80 Gate RepoPrompt steering in impl-review & spec-completion-review on macOS-or-rp-cli (fn-78 fast-follow)

## Goal & Context
<!-- scope: business -->

fn-78 (released in 2.5.3) gated the RepoPrompt *proposal* in `/flow-next:plan` and `/flow-next:plan-review`: on a host that cannot run RepoPrompt — not macOS AND no `rp-cli` on PATH — the rp option is no longer offered, while explicit choices still resolve. The remaining two review skills were deliberately left as a fast-follow (fn-78 Boundaries): **`/flow-next:impl-review`** and **`/flow-next:spec-completion-review`** still steer users toward rp on every host — their "Backend at a glance" lists call rp "**Primary backend**", and their ASK-error / override hints lead with `--review=rp`. On Linux/Windows without `rp-cli`, following that steering is a guaranteed runtime failure (`require_rp_cli()` → exit 2).

This spec applies the **same `RP_ELIGIBLE` gate, same semantics** to those two skills. Nothing else changes.

## Architecture & Data Models
<!-- scope: technical -->

Reuse fn-78's exact pattern (see the shipped gate in `flow-next-plan-review/SKILL.md` for the canonical wording):

```
RP_ELIGIBLE ⟺ (uname == "Darwin") OR (command -v rp-cli succeeds)
Suppress rp STEERING ⟺ ¬RP_ELIGIBLE
```

**Gated steering surfaces (canonical files):**

| Skill | Surface today | When `¬RP_ELIGIBLE` |
|---|---|---|
| impl-review | `SKILL.md` Backends summary + "Backend at a glance" ("**rp** — … Primary backend."), `--review=rp\|…` override hints, ASK-error hint (`SKILL.md:63`, `workflow-common.md:35,39`) | steering lists only `codex`/`copilot`/`cursor` (+ `none`); rp not presented as primary/recommended |
| spec-completion-review | same shape (`SKILL.md:35,43,61,65,70,115`, `workflow-common.md:35`) | same |

These skills are usually dispatched with an already-resolved backend (config / `--review` flag / per-task override), so the gate touches only *guidance text the user sees* (glance lists, ASK-error hints, override-hint echoes) — resolution logic is untouched. Note both files already carry fn-78's "Foreground rule" additions nearby — integrate cleanly, don't disturb them.

**Codex mirror:** canonical Claude-native edits only; `scripts/sync-codex.sh` regenerates `plugins/flow-next/codex/**`; never hand-edit the mirror.

## API Contracts
<!-- scope: technical -->

Same guard block as fn-78 (byte-compatible wording where it makes sense):

```bash
if [ "$(uname 2>/dev/null)" = "Darwin" ] || command -v rp-cli >/dev/null 2>&1; then
  RP_ELIGIBLE=1
else
  RP_ELIGIBLE=0
fi
```

- `RP_ELIGIBLE=1` → all steering renders byte-for-byte as today (rp listed, "Primary backend" intact).
- `RP_ELIGIBLE=0` → glance lists / ASK-error hints / override-hint echoes omit rp and steer to `codex|copilot|cursor|none`.
- **Resolution unchanged:** `--review=rp`, `FLOW_REVIEW_BACKEND=rp`, `review.backend=rp`, per-task/spec `review: rp` all still resolve to rp and reach the existing runtime `require_rp_cli()` error. `flowctl review-backend` and all `flowctl rp *` runners untouched.

## Edge Cases & Constraints
<!-- scope: technical -->

- Same edge semantics as fn-78: macOS without rp-cli → still eligible; non-macOS with rp-cli → eligible; explicit rp on ineligible host → resolves + runtime-errors (not rewritten); `uname` failure → falls to the `command -v` arm.
- `workflow-rp.md` files (the rp execution workflows) are NOT gated — they run only after rp was explicitly resolved.
- Autonomous paths (pilot/land/worker) pass a resolved backend; the gate is a no-op there.
- No flowctl change, no version bump in this spec (batched release decided separately).

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The `RP_ELIGIBLE` guard (identical predicate to fn-78) is computed **locally in every file whose text it gates** — `flow-next-impl-review/SKILL.md`, `flow-next-spec-completion-review/SKILL.md`, AND each skill's `workflow-common.md` Phase 0 (those files are self-contained "Run this first" docs; a guard referenced but not computed there would render ineligible guidance on eligible hosts when Phase 0 executes standalone). The guard is 3 lines — duplication is intentional, matching fn-78's inline-over-helper decision.
- **R2:** When `RP_ELIGIBLE=0`, steering omits rp, listing only `codex`/`copilot`/`cursor` (+ `none`). Per-file: **impl-review** — SKILL.md Backends summary, "Backend at a glance" (rp/"Primary backend" line), ASK-error message, override hints, plus `workflow-common.md:35` (ASK-error hint) AND `:39` (override echo `--review=rp|…`); **spec-completion-review** — SKILL.md same shape (`:35,43,61,65,70,115`), plus `workflow-common.md:35` ONLY — its backend echo prints just the resolved `Review backend: $BACKEND` with no backend list, so it is NOT gated and stays byte-for-byte (R3).
- **R3:** When `RP_ELIGIBLE=1`, all surfaces render byte-for-byte as today.
- **R4:** Resolution is untouched: explicit `--review=rp` / env / config / per-task override still resolves to rp and reaches `require_rp_cli()`; `--review=rp` remains in the accepted-flag grammar (only steering drops it).
- **R5:** `scripts/sync-codex.sh` run; regenerated `plugins/flow-next/codex/**` committed; `git diff --exit-code plugins/flow-next/codex/` clean after a second regen; no hand-edits.
- **R6:** Verification mirrors fn-78 R9a/b: inspect canonical + mirror text for both skills in both eligibility states (rp absent + clean lists when 0; byte-identical when 1).
- **R7:** CHANGELOG `## Unreleased` entry; no version bump (batched). Docs check: any doc line implying impl-review/spec-completion-review always offer rp gets the same non-Mac annotation used in fn-78 (docs/platforms.md already carries the general note — extend only if these skills are named).

## Boundaries
<!-- scope: business -->

- **In scope:** steering/guidance text of `flow-next-impl-review` + `flow-next-spec-completion-review` (SKILL.md + workflow-common.md), mirror regen, CHANGELOG, minimal docs check.
- **Out of scope:** plan/plan-review (done in fn-78); backend resolution, flowctl, `require_rp_cli()`; `workflow-rp.md` execution files; `flow-next-setup` (already gated via `HAVE_RP`); extracting a shared eligibility helper across the four skills (consider only if the diff turns out trivially better — default is copy the fn-78 block verbatim for consistency).

## Decision Context
<!-- scope: both — conditionally substructured -->

Fast-follow explicitly reserved by fn-78's Boundaries ("Applying the same gate there is a fast follow, deliberately not bundled"). Same propose-iff-`macOS OR rp-cli` boolean, same suppress-don't-ban stance, same inline-bash-over-flowctl-helper trade-off — all argued in fn-78's Decision Context; nothing new to decide. Copying the shipped fn-78 guard verbatim (rather than centralizing into a helper file) keeps the four skills self-contained and the diff mechanically reviewable; centralization remains a future cleanup if the pattern spreads further.
