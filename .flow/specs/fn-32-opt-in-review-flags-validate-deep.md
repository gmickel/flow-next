# Opt-in review flags: --validate, --deep, --interactive for impl-review

## Overview

Three opt-in flags that layer additional review capabilities on top of the existing Carmack-level review. All off by default; power users enable them per-invocation or via env var. Each addresses a specific friction point without changing the default review shape.

**Critical framing: the existing Carmack-level review is preserved as the default and remains the primary review.** These flags only add passes / layers / UI on top. Nothing here replaces the current single-chat rp/codex/copilot review.

Depends on Epic 1 (fn-29) for the confidence-anchor and pre-existing-classification conventions that `--validate` and `--deep` leverage.

Inspired by MergeFoundry upstream's validator pattern, multi-persona specialization, and per-finding walk-through routing.

## Constraints (CRITICAL)

- All three flags are **opt-in**; default review behavior unchanged
- Ralph mode remains silent on these flags unless user explicitly enables via env (`FLOW_VALIDATE_REVIEW=1`, `FLOW_REVIEW_DEEP=1`)
- `--interactive` is Ralph-incompatible — if `REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` is set, the flag errors out: "--interactive requires a user at the terminal; not usable in Ralph mode."
- Cross-backend (rp, codex, copilot) — all three backends must support all three flags
- Receipt contract stable: new optional fields (`validator: {dropped, reasons}`, `deep_passes: [...]`) — existing Ralph scripts read by key, unknowns ignored
- No new dependencies

## Design

### `--validate` — validation pass

**Goal:** drop false-positive findings before Ralph's (or user's) fix loop fires.

**Behavior:**

1. Primary review runs normally (Carmack-level, unchanged).
2. If verdict is NEEDS_WORK and `--validate` is active, spawn a validation pass:
   - **Codex backend:** second `codex` call with `--receipt` (continues session), prompt asks "for each finding, independently re-check against the current code; return `validated: true|false` + one-sentence reason."
   - **Copilot backend:** same with Copilot session continuation.
   - **RP backend:** re-send in same chat with validator framing.
3. Parse validator output. Findings marked `validated: false` are dropped, reason logged.
4. If all findings drop → verdict upgrades to SHIP.
5. Otherwise → verdict remains NEEDS_WORK with validated-only findings.
6. Receipt gains:

   ```json
   {
     "validator": {
       "dispatched": 8,
       "dropped": 3,
       "reasons": [
         {"file": "src/x.ts", "line": 42, "reason": "null check already at line 40"},
         ...
       ]
     }
   }
   ```

**Opt-in:**
- `/flow-next:impl-review --validate` — per-invocation
- `FLOW_VALIDATE_REVIEW=1` env var — session-wide, works in Ralph

**Cost:** ~1 extra backend call per NEEDS_WORK verdict. Trivial when SHIP (not invoked). Worthwhile on long Ralph runs where false-positive churn is expensive.

**Conservative bias:** validator prompt instructs "only drop if clearly wrong; when uncertain, keep." Mitigates over-drops.

### `--deep` — additional specialized passes on top of primary review

**Goal:** layer specialized deep-dive analysis (adversarial, security, performance) AFTER the primary Carmack-level review, with the primary review's output as context. Not a replacement — additive enrichment.

**Behavior:**

1. Primary review runs normally (Carmack-level, unchanged).
2. If `--deep` is active, run additional passes:
   - **Adversarial pass:** prompt framed around "construct failure scenarios; break this implementation" — assumption violation, composition failures, cascade construction, abuse cases. See primary findings first, then probe for what wasn't caught.
   - **Security pass:** prompt framed around auth, authz, input handling, secrets, permission boundaries. Only when diff touches relevant files (auto-detected from changed file list).
   - **Performance pass:** prompt framed around hot paths, DB queries, loop-heavy transforms, cache coherency. Auto-enabled when diff touches performance-sensitive paths (detected heuristically).

3. Each pass uses the same backend + same chat session (for continuity + cheaper context — the model already has the diff loaded).
4. Each pass returns findings tagged with `pass: adversarial|security|performance`.
5. Findings from deep passes merge with primary findings via confidence anchors (reuse Epic 1 rubric). Cross-pass agreement (same finding flagged by primary + deep pass) promotes confidence one anchor step — this is the only place cross-reviewer promotion applies inside a single-chat backend.
6. Verdict computed over merged findings.
7. Receipt gains:

   ```json
   {
     "deep_passes": ["adversarial", "security"],
     "deep_findings_count": {"adversarial": 2, "security": 1, "performance": 0}
   }
   ```

**Opt-in:**
- `/flow-next:impl-review --deep` — per-invocation
- `FLOW_REVIEW_DEEP=1` env var — session-wide, works in Ralph for power users who want deep on every review

**Which passes run:**
- Adversarial: always runs when `--deep` set
- Security: auto-enabled when diff matches security-sensitive globs (`**/auth*`, `**/permissions*`, `**/*Token*`, `routes/*`, `*Controller.rb`, etc.) OR when `--deep=security` explicit
- Performance: auto-enabled when diff matches perf-sensitive paths OR when `--deep=performance` explicit

Explicit form: `--deep=adversarial,security` restricts to listed passes.

**Cost:** adds 1-3 backend calls per review. Ralph users enable only when they want rigorous autonomous reviews; trades cost for catch-rate.

### `--interactive` — per-finding walk-through

**Goal:** user-triggered reviews benefit from per-finding control. Ralph can't stop for decisions, so flag errors in Ralph mode.

**Behavior:**

1. Primary review runs normally.
2. If verdict is NEEDS_WORK and `--interactive` is active (and no Ralph env vars set):
   - For each finding, present blocking question:

     ```
     Finding 3/8:
     [P1, confidence 75, introduced] src/auth.ts:42 — null deref in middleware

     What should the agent do?
       1. Apply — implement the suggested fix
       2. Defer — leave unresolved; log for later handling
       3. Skip — ignore this finding
       4. Acknowledge — note it but take no action
       5. LFG the rest — apply recommended action for this and all remaining
    ```

   - Use platform blocking question tool (`AskUserQuestion` / `request_user_input` / `ask_user`).
   - Accumulate user decisions: Apply list, Defer list, Skip list, Acknowledge list.
3. After walk-through:
   - Apply list → dispatch fixer for those findings
   - Defer list → write to `.flow/review-deferred/<pr-or-branch>.md` as a durable record
   - Skip / Acknowledge → no action, logged in receipt
4. Receipt gains:

   ```json
   {
     "walkthrough": {
       "applied": 3,
       "deferred": 2,
       "skipped": 1,
       "acknowledged": 0
     }
   }
   ```

**Opt-in:**
- `/flow-next:impl-review --interactive` — per-invocation only
- No env var — always per-invocation to prevent accidental Ralph engagement

**Ralph-block:**

```bash
if [[ -n "$REVIEW_RECEIPT_PATH" || "${FLOW_RALPH:-}" == "1" ]]; then
  echo "Error: --interactive requires a user at the terminal; not compatible with Ralph mode."
  exit 2
fi
```

**Defer sink:** `.flow/review-deferred/<branch-slug>.md` — a durable per-branch record of deferred findings that the user can revisit. Plain markdown, not a new state primitive.

## Flag interaction matrix

| Combo | Behavior |
|-------|----------|
| `--validate` alone | Run primary; validate on NEEDS_WORK; drop confirmed-false |
| `--deep` alone | Run primary + deep passes; merged findings; standard verdict |
| `--interactive` alone | Run primary; walk through findings on NEEDS_WORK |
| `--validate --deep` | Primary + deep passes; validate on merged NEEDS_WORK |
| `--validate --interactive` | Primary + validate; walk through validated findings only |
| `--deep --interactive` | Primary + deep; walk through merged findings |
| All three | Primary + deep + validate + walk — maximum signal + human control |

## Ralph compatibility

| Flag | Default in Ralph | Env opt-in | Notes |
|------|-----------------|-----------|-------|
| `--validate` | off | `FLOW_VALIDATE_REVIEW=1` | Opt-in saves cycles by dropping false positives before fix loop |
| `--deep` | off | `FLOW_REVIEW_DEEP=1` | Opt-in increases rigor at cost; good for long Ralph runs on critical code |
| `--interactive` | **blocked** | none | Hard error if Ralph env detected |

Ralph's receipt-gate logic unchanged. The new receipt fields (validator, deep_passes, walkthrough) are optional — existing Ralph scripts ignore unknowns.

## File change map

### Skills
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md` — parse `--validate`, `--deep`, `--interactive` flags; Ralph-block for interactive
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md` — three new sections documenting each flag's flow + receipt additions
- `plugins/flow-next/skills/flow-next-impl-review/validate-pass.md` (new) — validator prompt template
- `plugins/flow-next/skills/flow-next-impl-review/deep-passes.md` (new) — adversarial / security / performance prompt templates + auto-enable heuristics
- `plugins/flow-next/skills/flow-next-impl-review/walkthrough.md` (new) — per-finding question flow

### flowctl
- `plugins/flow-next/scripts/flowctl.py` — `flowctl codex validate`, `flowctl copilot validate` subcommands; `flowctl codex deep-pass`, `flowctl copilot deep-pass` (receive pass name + primary findings, invoke backend with tailored prompt)
- `.flow/bin/flowctl.py` (mirror)
- Receipt writers extended (all backends) with new optional fields

### Docs
- `CHANGELOG.md`
- `plugins/flow-next/README.md` — new section on opt-in review flags
- `CLAUDE.md` — bullet references
- `~/work/mickel.tech/app/apps/flow-next/page.tsx`

### Codex mirror + bump
- `scripts/sync-codex.sh` run after edits
- `scripts/bump.sh minor flow-next` — minor bump (additive new flags)

## Acceptance criteria

- **R1:** `--validate` flag parsed in impl-review skill; on NEEDS_WORK, dispatches validator pass; drops false-positive findings with logged reason; receipt carries `validator` object.
- **R2:** `FLOW_VALIDATE_REVIEW=1` env enables validate without explicit flag.
- **R3:** `--deep` flag runs primary review THEN additional passes (adversarial always + security/performance auto-enabled or explicit).
- **R4:** Deep passes use same backend session (continuity); findings tagged `pass: <name>`; merged with primary via confidence anchors.
- **R5:** Cross-pass agreement (primary + deep flagged same finding) promotes confidence one anchor step.
- **R6:** `FLOW_REVIEW_DEEP=1` env enables deep without explicit flag.
- **R7:** `--deep=adversarial,security` restricts to listed passes.
- **R8:** `--interactive` flag presents per-finding blocking question (Apply / Defer / Skip / Acknowledge / LFG-rest) using platform's blocking question tool.
- **R9:** `--interactive` errors out cleanly when Ralph env detected (`REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1`).
- **R10:** Deferred findings written to `.flow/review-deferred/<branch-slug>.md` as a durable record.
- **R11:** Apply list dispatches fixer for confirmed findings; Skip/Acknowledge logged but no action.
- **R12:** Receipt extensions (`validator`, `deep_passes`, `walkthrough`) are optional and additive — existing Ralph scripts work unchanged.
- **R13:** All three flags work independently and in combination per the interaction matrix.
- **R14:** Existing default review (no flags) is unchanged — same Carmack-level single-chat behavior as before.
- **R15:** Docs updated: CHANGELOG, plugin README, CLAUDE.md, website.
- **R16:** sync-codex regenerates cleanly; bump.sh updates manifests.
- **R17:** Ralph smoke tests pass unchanged without flags; with `FLOW_VALIDATE_REVIEW=1` env, smoke still passes and receipts carry validator data.

## Boundaries

- Not adding multi-persona parallel dispatch (18 agents). Deep is still single-chat, just with additional prompt passes — preserves rp/codex/copilot parity.
- Not adding tracker-defer integration for deferred findings (separate future epic).
- Not persisting walkthrough decisions across re-reviews (each invocation starts fresh).
- Not adding a `--deep=all` shorthand beyond the auto-enable heuristic — keep flag surface small.
- Not changing the Carmack-level primary review prompt.

## Risks

| Risk | Mitigation |
|------|------------|
| Validator over-drops real findings | Conservative prompt ("when uncertain, keep"); Ralph fix loop still runs tests — real bugs fail tests regardless |
| Deep passes cost too much on every Ralph cycle | Opt-in only; `FLOW_REVIEW_DEEP=1` requires explicit choice |
| `--interactive` accidentally used in Ralph | Hard error with clear message on env detection |
| Cross-pass agreement promotion double-counts same-chat findings | Dedupe by fingerprint before agreement check (reuse Epic 1 fingerprint convention) |
| Security/performance auto-enable heuristic false positives | Opt-out via explicit `--deep=adversarial` only |
| Receipt schema growth | New fields optional; existing consumers ignore unknowns |

## Decision context

**Why additive, not replacing:** the existing review works. Users (and Ralph) build mental models around its shape. Replacing primary review with multi-pass would break muscle memory and risk regressing review quality while the new shape stabilizes. Layer on top.

**Why `--interactive` has no env var:** Ralph should never accidentally engage it. Per-invocation only eliminates the foot-gun.

**Why validate is per-backend (not a generic post-processor):** validator needs to call the backend LLM with session context. Generic post-processor would have to shoulder session management; cleaner to keep it in the backend-specific flowctl subcommand.

**Why deep is additive, single-chat:** preserves the rp/codex/copilot architecture. Multi-persona parallel dispatch (like MergeFoundry upstream does) would require Claude-Code-specific subagent orchestration and wouldn't work cleanly for rp/codex/copilot users. Sequential passes in same chat give most of the signal gain without the architecture tax.

## Testing strategy

- Unit tests for flag parsing: `--validate`, `--deep`, `--interactive` all combinations
- Unit tests for Ralph-block on `--interactive`
- Integration smoke: `impl-review --validate` on a branch with known false-positive-prone diff; verify validator drops reasonable items
- Integration smoke: `impl-review --deep` on a security-sensitive diff; verify security pass auto-enables and produces additional findings
- Integration smoke: `impl-review --interactive` on a branch; walk through decisions; verify fixer dispatches for Apply set only
- Regression: existing impl-review smoke (no flags) passes unchanged

## Follow-ups (not in this epic)

- Tracker-defer: when `--interactive` produces Defer items, file them to Linear/GitHub Issues
- Cross-invocation walkthrough memory (remember prior decisions on same branch)
- `--deep=all` or richer pass selection DSL if demand emerges
