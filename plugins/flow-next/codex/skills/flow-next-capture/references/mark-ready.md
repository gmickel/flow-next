# capture — mark-ready consent (loaded on demand)

> Loaded ONLY when the Phase 4.2 pre-gate fires: `tracker.readyState` is unset (or its probe
> errored). A tracker-authoritative repo (`tracker.readyState` configured) never offers readiness
> here — readiness is a one-way tracker→local pull there — and never reads this file.
> The full target-aware predicate below still decides whether the question is asked at all.

## 4.2 — Mark-ready consent (interactive; only after `approve`)

Probe only after `approve`, before any Phase 5 write changes the rewrite target's state:

```bash
READY_STATE=""
READY_ADOPTED=0
REWRITE_WAS_READY=false
READINESS_PROBES_OK=true

READY_STATE_RAW=$("$FLOWCTL" config get tracker.readyState --json 2>/dev/null) || READINESS_PROBES_OK=false
if [[ "$READINESS_PROBES_OK" == true ]]; then
 READY_STATE=$(printf '%s' "$READY_STATE_RAW" | jq -r '.value // empty' 2>/dev/null) || READINESS_PROBES_OK=false
fi

READY_SPECS_RAW=$("$FLOWCTL" specs --json 2>/dev/null) || READINESS_PROBES_OK=false
if [[ "$READINESS_PROBES_OK" == true ]]; then
 READY_ADOPTED=$(printf '%s' "$READY_SPECS_RAW" | jq '[.specs[] | select(.ready == true)] | length' 2>/dev/null) || READINESS_PROBES_OK=false
fi

if [[ -n "$REWRITE_TARGET" && "$READINESS_PROBES_OK" == true ]]; then
 REWRITE_RAW=$("$FLOWCTL" show "$REWRITE_TARGET" --json 2>/dev/null) || READINESS_PROBES_OK=false
 if [[ "$READINESS_PROBES_OK" == true ]]; then
 REWRITE_WAS_READY=$(printf '%s' "$REWRITE_RAW" | jq -r '.ready // false' 2>/dev/null) || READINESS_PROBES_OK=false
 fi
fi

READY_OFFER=false
if [[ "$READINESS_PROBES_OK" == true && -z "$READY_STATE" ]]; then
 if [[ -n "$REWRITE_TARGET" ]]; then
 [[ "$REWRITE_WAS_READY" == true ]] && READY_OFFER=true
 elif [[ "$READY_ADOPTED" =~ ^[0-9]+$ && "$READY_ADOPTED" -ge 1 ]]; then
 READY_OFFER=true
 fi
fi
# Probe failures degrade to READY_OFFER=false (don't offer).
```

The shared tracker gate must hold, then the branch-specific gate applies:

- `READY_STATE` empty — `tracker.readyState` is NOT configured. Readiness is a one-way tracker→local pull when the tracker is authoritative; never invite a local edit the next sync would silently revert.
- **New capture:** offer only when `READY_ADOPTED >= 1`. Readiness is adopted in this repo (≥1 spec already marked ready). First adoption enters via `flowctl spec ready`, the tracker ceremony, or prime — never via this prompt. Non-adopters see no question anywhere (R7-style invisibility).
- **Rewrite:** offer only when `REWRITE_WAS_READY` is `true`. For a rewrite, an unrelated ready spec never triggers this question. The question is consent to restore the target's own readiness after §5.3 resets it; a draft target remains a draft without another interruption.

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

When `READY_OFFER=true`, one follow-up question via `plain-text numbered prompt` — the §4.2 read-back options stay frozen; this is a separate ask (same shape as the glossary consent):

- **header**: `Mark ready?`
- **body, new capture**: `Make this new spec eligible for Pilot or another autonomous driver once written? Readiness is adopted in this repo (<READY_ADOPTED> ready spec(s)). Recommended: keep-draft — choose mark-ready only when you want autonomous execution eligibility now. Confidence: [judgment-call].`
- **body, rewrite**: `Rewriting <REWRITE_TARGET> resets its readiness. Mark it ready again after writing the approved revision so Pilot or another autonomous driver may select it? Recommended: keep-draft — choose mark-ready only when you want autonomous execution eligibility now. Confidence: [judgment-call].`
- **options** (frozen): `mark-ready` (Phase 5.9 runs `spec ready` after the write), `keep-draft` (default — no readiness write)

Record the answer for Phase 5.9. `keep-draft` → no readiness write; the spec write proceeds regardless of this answer.

**Forbidden in Phase 4:** never write readiness there. Phase 4 collects the mark-ready consent only; the write happens in Phase 5.9, after the spec write. Never offer the question outside the target-aware predicate: no `tracker.readyState`, plus adopted local readiness for a new capture or an already-ready target for a rewrite.

## 5.9 — Mark-ready write (consent-gated; interactive only)

Runs only when Phase 4.2's mark-ready consent recorded `mark-ready` (which implies the target-aware predicate held — adopted local readiness for a new capture or a ready rewrite target, no `tracker.readyState` — and interactive mode; autofix never reaches here):

```bash
"$FLOWCTL" spec ready "$SPEC_ID" --json
```

Idempotent plumbing (fn-58.1) — re-running is a silent no-op. Best-effort: a failed write prints a warning and continues — never blocks the capture (the spec is already on disk). Report `Readiness: marked ready` for the Phase 6 footer; on `keep-draft` (or when the question never fired) report nothing — zero footer noise outside the consent path.

## Phase 6 — footer lines

When Phase 5.9 marked the spec ready, append one line after `Tracker sync:`: `Readiness: marked ready`. Omit entirely otherwise — `keep-draft`, predicate-not-met, and every non-consented run print no readiness line.

Autofix only: when the target-aware predicate yields `READY_OFFER=true` and the spec was written (`--yes`), append `Mark ready when blessed: flowctl spec ready <SPEC_ID>` (suggestion only — autofix never writes readiness).

## Forbidden behavior (readiness row)

| Forbidden | Why |
|-----------|-----|
| Marking a spec ready without consent, in autofix, or outside the target-aware predicate | Consent lives in Phase 4.2's `Mark ready?` question (new capture: adopted local readiness; rewrite: target itself was ready; both: no `tracker.readyState`); the write is Phase 5.9, interactive-only. An unrelated ready spec never prompts on a draft rewrite. Readiness is the human's gate — capture never infers it. Autofix prints the footer suggestion only. |
