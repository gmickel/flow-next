# fn-78 Gate RepoPrompt proposal on macOS-or-rp-cli — plan & plan-review skip the rp path when it can't run

## Goal & Context
<!-- scope: business -->

RepoPrompt is a **macOS-only GUI app**; its `rp-cli` bridge only exists there. Two skills still *proactively offer* the RepoPrompt path in their interactive setup:

- `/flow-next:plan` — the "Research — Use RepoPrompt for deeper context? → context-scout" question (the **subagent that uses RepoPrompt**), and the "Review → RepoPrompt" backend option in the same setup block.
- `/flow-next:plan-review` — the backend guidance / ASK-error that lists `rp` as a choice and frames it as the "Primary backend".

On Linux/Windows with no `rp-cli` on PATH, choosing that path is a **guaranteed runtime failure** (`flowctl.py:1593 require_rp_cli()` → `rp-cli not found in PATH`, exit 2) or a context-scout that silently degrades to grep anyway. Dangling an option that cannot possibly run is confusing UX and wastes a round-trip.

**This spec:** when the host **cannot** run RepoPrompt — i.e. **not on macOS AND `rp-cli` not on PATH** — `plan` and `plan-review` must **never surface the RepoPrompt option** in their interactive proposals (questions, menus, override hints, defaults). They silently fall through to the always-available paths (`repo-scout` for research; the cross-platform review backends `codex`/`copilot`/`cursor`/`none`, with `export` still available as an explicit one-off review mode). Nothing else changes.

Target user: anyone running flow-next on Linux/Windows/WSL (CI, non-Mac dev boxes, Ralph hosts) who today sees — and can accidentally pick — an option that only works on a Mac.

## Architecture & Data Models
<!-- scope: technical -->

**One eligibility predicate, computed inline in each skill** (mirrors the existing `HAVE_RP` idiom at `flow-next-setup/workflow.md:322`, extended with an OS check):

```
RP_ELIGIBLE  ⟺  (uname == "Darwin")  OR  (command -v rp-cli succeeds)
Suppress the RepoPrompt proposal  ⟺  ¬RP_ELIGIBLE  ⟺  (not macOS) AND (rp-cli absent)
```

Rationale for the `OR`: on macOS we keep proposing even when `rp-cli` is momentarily off PATH (the user has a Mac; the GUI/CLI can be installed/launched — matches today's "errors at runtime if missing" behavior, which is at least actionable for a Mac user). We only *hide* the option in the one case where it can never work: a non-Mac host with no `rp-cli`.

**No new flowctl surface.** The predicate is a 3-line bash guard added at the top of each skill's interactive-setup step. This keeps the change small and stays inside the existing "skill computes a soft signal, prose branches on it" idiom already used for `HAVE_RP`/`HAVE_CODEX`/`HAVE_COPILOT` in setup.

**Gated proposal surfaces:**

| Skill | File (canonical) | Surface today | When `¬RP_ELIGIBLE` |
|---|---|---|---|
| plan | `skills/flow-next-plan/SKILL.md:122-124` | "Quick setup: Use RepoPrompt for deeper context? a) context-scout / b) repo-scout" (already-configured branch) | omit the RepoPrompt research question; default research = repo-scout |
| plan | `skills/flow-next-plan/SKILL.md:140-143` | "2. Research — Use RepoPrompt for deeper context?" (unconfigured branch) | drop item 2's RepoPrompt option; research goes straight to repo-scout |
| plan | `skills/flow-next-plan/SKILL.md:144-148` | "3. Review — b) RepoPrompt" | drop the RepoPrompt review choice from the offered list |
| plan-review | `skills/flow-next-plan-review/SKILL.md:14` (Backends summary) + `:28,36-41` (`--review=` grammar) + ASK-error hint | steering/recommendation drops rp and lists only the runnable **configured** backends (`codex`, `copilot`, `cursor`, + `none`); `export` stays an explicit one-off review MODE, never presented as a configured backend; the `--review=rp` flag itself stays *accepted* (R6) |
| plan-review | `skills/flow-next-plan-review/SKILL.md:~61` | "**rp** — … Primary backend." at-a-glance line | when ineligible, rp is not presented as the recommended/primary choice in interactive guidance (the flag stays accepted) |

**Codex mirror:** all edits land in the **canonical** Claude-native skill files; `scripts/sync-codex.sh` regenerates `plugins/flow-next/codex/**`. The mirror is never hand-edited (per CLAUDE.md cross-platform rule). `uname` / `command -v` are POSIX and behave identically on the Codex/Droid mirrors.

## API Contracts
<!-- scope: technical -->

**Eligibility guard (canonical bash, both skills):**

```bash
# RepoPrompt is macOS-only (rp-cli bridges the GUI). Only offer the rp path
# when it can actually run: on macOS, or when rp-cli is already on PATH.
if [ "$(uname 2>/dev/null)" = "Darwin" ] || command -v rp-cli >/dev/null 2>&1; then
  RP_ELIGIBLE=1
else
  RP_ELIGIBLE=0
fi
```

**Proposal contract:**
- `RP_ELIGIBLE=1` → **byte-for-byte current behavior** (rp appears in every place it does today).
- `RP_ELIGIBLE=0` → every *interactive proposal* omits the RepoPrompt option; the enumerated non-rp options renumber cleanly (no dangling "b)"); defaults resolve to a runnable path.

**Override contract (unchanged — proposal-suppression is not a ban):**
- `plan`: an explicit `--research=rp` / "use repoprompt" / "context-scout" argument is still honored and still errors at runtime if `rp-cli` is missing (`SKILL.md:100` behavior preserved).
- `plan-review`: an explicit `--review=rp`, `FLOW_REVIEW_BACKEND=rp`, or `.flow/config.json review.backend=rp` still resolves to rp (and errors at runtime via `require_rp_cli()` as today). The gate only affects what is *proposed*, never how an explicit prior choice *resolves*.

## Edge Cases & Constraints
<!-- scope: technical -->

- **macOS without rp-cli on PATH** → still eligible (proposes rp; runtime-errors if the user picks it and rp-cli truly absent). Unchanged from today; intentionally not "fixed" here.
- **Non-macOS *with* rp-cli on PATH** (e.g. a shim / future Linux port) → eligible; rp is proposed. The gate keys on capability, not on OS alone.
- **Explicit rp already configured on a non-Mac host** → resolves to rp and runtime-errors; NOT silently rewritten. Suppression governs proposals, not resolution.
- **Autonomous / programmatic invocation** (pilot/land/`AUTONOMOUS=1`) → no interactive proposal exists; backend comes from config. The guard is a no-op on these paths — zero behavior change.
- **`uname` unavailable** (extremely rare) → `uname 2>/dev/null` yields empty → not "Darwin" → falls to the `command -v rp-cli` arm. Safe default (suppress unless rp-cli is genuinely present).
- **`steps.md:160` already degrades** ("If user chose repo-scout … OR rp-cli unavailable") — that is the *dispatch* fallback; this spec fixes the earlier *proposal*, so the two now agree (a non-Mac user is no longer offered a choice that the dispatcher would override anyway).
- **Codex mirror drift** — the change is only valid once `scripts/sync-codex.sh` has been run and the regenerated `codex/**` committed; hand-editing the mirror is forbidden.
- **No plugin version bump** (per CLAUDE.md batched-release rule) — land code + docs + an `## Unreleased` CHANGELOG entry only.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A single eligibility predicate `RP_ELIGIBLE = (uname == "Darwin") OR (command -v rp-cli succeeds)` is computed at the start of the interactive-setup step in **both** `flow-next-plan/SKILL.md` and `flow-next-plan-review/SKILL.md`, using POSIX-portable bash (`uname`, `command -v`).
- **R2:** In `/flow-next:plan`, when `RP_ELIGIBLE=0`, the Research question does **not** offer the RepoPrompt / context-scout option in either the already-configured branch (`SKILL.md:122-124`) or the unconfigured branch (`SKILL.md:140-143`); research defaults to `repo-scout` without asking about RepoPrompt.
- **R3:** In `/flow-next:plan`, when `RP_ELIGIBLE=0`, the Review question (`SKILL.md:144-148`) does **not** list "RepoPrompt" as a choice; remaining choices (Codex / Export / None) are presented as a clean, correctly-lettered list.
- **R4:** In `/flow-next:plan-review`, when `RP_ELIGIBLE=0`, the backend guidance the user is *steered toward* — the Backends summary line (`SKILL.md:14`), the "Backend at a glance" list (`~:61`), and the ASK-error recommendation — drops `rp` and presents only the runnable **configured** review backends `codex`, `copilot`, `cursor` (plus `none`). `export` is an explicit one-off review MODE (`--review=export`), **not** a configured `review.backend`, so it is never presented as a configured backend. The `--review=rp` flag itself remains *accepted* (R6) — only the proactive steering/recommendation drops rp. On `RP_ELIGIBLE=1` the full set including rp renders unchanged.
- **R5:** When `RP_ELIGIBLE=1` (macOS, or rp-cli present), **all** proposal surfaces render exactly as they do today — no wording, ordering, or option change (byte-for-byte for the eligible path).
- **R6:** Proposal-suppression is not a ban: an explicit `--research=rp` (plan) or `--review=rp` / `FLOW_REVIEW_BACKEND=rp` / `review.backend=rp` (plan-review) is still honored and reaches the existing runtime `require_rp_cli()` error path — behavior identical to today.
- **R7:** All edits are made in the canonical Claude-native skill files; `scripts/sync-codex.sh` is run and the regenerated `plugins/flow-next/codex/**` is committed, with no hand-edits to the mirror.
- **R8:** No plugin version bump. A repo `CHANGELOG.md` `## Unreleased` entry describing the gate is **required** (task acceptance). The **docs-site changelog is a downstream maintainer step — noted, NOT a blocking task acceptance.** Docs that describe rp as the "Primary/macOS backend" (`docs/platforms.md`, `docs/troubleshooting.md`) are checked and, where they imply rp is always offered, annotated that non-Mac hosts without rp-cli are not proposed it. **`flow-next-setup` is NOT edited** (its menu already gates on `HAVE_RP` with a "macOS only (not detected)" label — read-only reference only, see Boundaries).
- **R9:** Verification is explicit, not prose-only: (a) `RP_ELIGIBLE=0` path — inspect the canonical plan / plan-review skill text AND the regenerated Codex mirror to confirm the rp research/review option is absent and remaining options render as a clean, correctly-lettered list; (b) `RP_ELIGIBLE=1` path — confirm the eligible rendering is byte-for-byte the current wording (rp present); (c) run `scripts/sync-codex.sh` and confirm canonical↔mirror parity (no drift, no hand-edits); (d) run the repo's existing skill/mirror smoke check green (e.g. the sync-codex verification CI runs — `git diff --exit-code plugins/flow-next/codex/` after regen).

## Boundaries
<!-- scope: business -->

- **In scope:** interactive *proposal* surfaces of `/flow-next:plan` and `/flow-next:plan-review` only.
- **Out of scope — backend resolution / flowctl:** no change to `flowctl review-backend`, `require_rp_cli()`, or any `flowctl rp *` runner. The runtime error stays as the backstop for explicit choices.
- **Out of scope — hard-blocking:** we do not forbid an explicit rp request on a non-Mac host; we only stop *proposing* it. (Escape hatch preserved.)
- **Out of scope — `flow-next-setup` (NOT edited):** already gates its review-backend menu via `HAVE_RP` + a "macOS only (not detected)" label (`workflow.md:325,471`). It is a **read-only reference** for the `HAVE_RP` idiom — task .2 must NOT edit it. (A later cleanup could extract one shared helper across setup/plan/plan-review — noted, not built.)
- **Out of scope — `impl-review` & `spec-completion-review`:** they share the same rp backend pattern but the user scoped this to plan + plan-review. Applying the same gate there is a fast follow, deliberately not bundled.
- **Out of scope — a new `flowctl` subcommand** for eligibility. Considered and rejected for footprint (see Decision Context).

## Decision Context
<!-- scope: both — conditionally substructured -->

**Boolean shape — literal to the request.** The suppress condition is exactly the user's phrasing: *not on Mac **and** can't find rp-cli*. Equivalently, propose iff `macOS OR rp-cli-present`. This deliberately keeps proposing on a Mac that lacks rp-cli on PATH (the Mac user can install/launch it; today's runtime error is actionable there) and only hides the option where it is provably dead (non-Mac + no rp-cli). An OS-only or rp-cli-only gate was rejected as either too aggressive (hides rp from Mac users mid-setup) or too weak (still dangles it on bare Linux).

**Inline bash over a flowctl helper.** A `flowctl rp eligible --json` primitive would be more DRY (plan, plan-review, impl-review, spec-completion-review, setup all touch rp). But this spec is intentionally small and scoped to two skills, and the `HAVE_RP=$(which rp-cli …)` inline pattern already exists in setup — mirroring it (plus a `uname` arm) is the lowest-risk, smallest-diff change and adds zero Python/test surface. Centralizing into one helper is left as a follow-up if/when the gate spreads to the other review skills.

**Suppress proposals, don't ban.** "Never propose" is read faithfully as *never dangle it in an interactive menu/question/default* — not *forbid it outright*. A user who explicitly types `--research=rp` / `--review=rp` on a non-Mac host is making an informed choice and still hits the existing, clear runtime error. This is the least-surprising behavior and the smallest behavioral delta (only proactive UI changes).

**Why now.** Non-Mac adoption (Linux CI, Ralph hosts, Windows/WSL after the fn-77 python-stub fix) makes the dead RepoPrompt option a recurring papercut; the `steps.md:160` dispatcher already treats non-Mac as "rp unavailable", so the proposal was the last place still implying rp was a real choice.
