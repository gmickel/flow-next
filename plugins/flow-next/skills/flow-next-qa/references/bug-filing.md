# Bug filing — turning live-app failures into actionable findings

A finding is only useful if engineering can act on it. **File immediately on FAIL** (not batched), with a complete repro and real captured evidence, into the bug memory track. Findings carry the R-ID(s) they trace back to, closing the **spec-AC ↔ scenario ↔ finding ↔ R-ID** loop.

> The P0/P1/P2 taxonomy, the evidence rules, the reproduce-before-file discipline, and the "never downgrade a P0" rule are a lean borrow from Ray Fernando's `running-bug-review-board` skill (Apache-2.0). flow-next adapts them to its own storage — the **bug memory track** (`track: bug`) and the **`qa_verdict` receipt** — rather than BRB's `BUG-NNN.md` files + HTML dashboard. (Full credit lives in the skill's CHANGELOG + the R8 lean-borrow reference.)

## Reproduce before you file (twice)

Agentic driving is non-deterministic — a single failed observation is not yet a finding. Re-run the scenario's failing step a **second** time (fresh `observe → snapshot → act → verify`, same persona + viewport). File only if it fails **both** times. A pass-on-retry is a flake: record it in the run notes (not a finding) and move on. This closes the GitHub-Eng gap — agent self-reported failure is ~82% accurate; reproduce-twice grounds the verdict in structural evidence, not narration.

## Severity (P0/P1/P2)

| Level | Definition | Verdict impact |
|-------|------------|----------------|
| **P0** | Blocks the core flow; data loss; auth bypass; security; crash — a real user cannot complete the scenario's goal | A single open P0 ⇒ verdict NEEDS_WORK |
| **P1** | Feature broken or wrong with a workaround; wrong-but-recoverable result | Any open P1 ⇒ verdict NEEDS_WORK |
| **P2** | Cosmetic, edge case, accessibility, dev-console noise | Does not by itself block SHIP |

**Tie-break:** when between two severities, take the **higher** if it touches the core flow or data integrity. **Never relabel a P0 as P1 to avoid stopping the pass** — that hides severity and tells the next reader the breakage is optional. Severity rests on observed user impact, never on convenience.

## Steps to reproduce — runnable cold

Must be executable by a fresh agent with no context:

- **Persona** (fresh user / member / admin) + the persona email/suffix used
- **Starting URL** (full, incl. query string)
- Each click / fill **verbatim**, with the exact input values
- **Wait conditions** ("after redirect to X", "when the Loading spinner disappears")
- Where the screenshot was taken

## Expected vs Actual — both mandatory

- **Expected** comes from the spec: the AC text and the resolved-default in `decision_context` (the Phase 2.4 mapping). Quote it; do not paraphrase the intent.
- **Actual** comes from the live observation — the snapshot / screenshot / observed state.

If Expected and Actual read the same in plain text but the bug is real, the difference is usually **invisible state** (URL, query string, storage, server row) — spell it out explicitly.

## Evidence — required for every finding

All evidence is captured in Phase 4 under `.flow/tmp/qa-<spec-id>/` (gitignored) and **referenced by path**, never inlined wholesale:

- **Console** — last ~30 lines, **verbatim** (`<sid>-console.log`). Strip auth tokens / PII.
- **Screenshot** — at least the moment of failure; sequence multi-step ones `01-…png`, `02-…png`.
- **URL at failure** — full URL including query string.
- **Write side-effects** — for any create/update/delete, the server/DB row or API response confirming the **actual persisted state** (the write path is where invisible-state bugs hide — check it first).

Optional but valuable: the failing network request (method, URL, status, sanitized body); the DOM/accessibility snapshot from the failing step.

## Title style — observed behavior, never the suspected fix

`<persona> can't <goal> — <one-line observed symptom>`. Describe what the user experiences, not what you think is wrong in the code.

- Good: `Fresh user can't complete signup — OTP step redirects to /500`
- Bad: `Fix the OTP cron job`

## Filing to bug memory

flow-next stores findings in the **bug memory track** (not `BUG-NNN.md` files). File the moment a FAIL is confirmed (after reproduce-twice), **with overlap scoring left ON** (never `--no-overlap-check`):

```bash
# No-op cleanly when memory is disabled — still record the finding in the run notes
# so Phase 6 can count it toward the verdict.
if [ "$($FLOWCTL config get memory.enabled --json | jq -r '.value')" = "true" ]; then
  mkdir -p .flow/tmp/qa-"$SPEC_ID"
  cat > .flow/tmp/qa-"$SPEC_ID"/finding-<sid>.md <<'EOF'
## Problem
<persona> attempting <goal> hit <observed failure> on the live app.

## Steps to reproduce (cold)
1. <starting URL incl. query string>
2. <verbatim action + input>
3. <wait condition>
4. <observe>

## Expected
<AC text + decision_context resolved-default — quoted from the spec>

## Actual
<observed state — incl. invisible state: URL / storage / server row>

## Evidence
- console: .flow/tmp/qa-<spec-id>/<sid>-console.log (last ~30 lines)
- screenshot: .flow/tmp/qa-<spec-id>/<sid>-fail.png
- url: <full URL at failure>
- write side-effect: <server/DB row or API response, if a write path>

## Traceability
- R-IDs: [R<i>, ...]   scenario: S<n>   driver_rung: <rung>   viewport: <wxh>
EOF

  $FLOWCTL memory add \
    --track bug --category "<ui|runtime-errors|integration|data|security|performance|...>" \
    --title "<persona> can't <goal> — <one-line symptom>" \
    --module "<surface / route / component>" \
    --tags "qa,<spec-id>,<surface>" \
    --symptoms "<observed actual, one line>" \
    --root-cause "(observed via live QA — unconfirmed)" \
    --body-file .flow/tmp/qa-"$SPEC_ID"/finding-<sid>.md
fi
```

### Category

Map the observed failure to a bug-track category (`docs/memory-schema.md`):

| Observed | Category |
|----------|----------|
| layout broken, wrong color, a11y, cosmetic | `ui` |
| crash, wrong value, null render at runtime | `runtime-errors` |
| API contract / wire-format / schema mismatch across a boundary | `integration` |
| data corruption, partial/lost write, wrong persisted row | `data` |
| auth bypass, leaked secret, injection | `security` |
| slow load, jank, memory growth | `performance` |

When ambiguous, pick the most specific that fits. `--root-cause` for a live finding is genuinely unconfirmed (QA observed a symptom, not a cause) — record `(observed via live QA — unconfirmed)` rather than guessing.

## Dedup — NEVER `--no-overlap-check`; caller decides update-vs-create

`memory add` always **creates** unless you pass explicit `--update <id>` (fn-113). Overlap scoring still runs and the JSON response always emits `matches` (with scores) as a retrieval signal (`docs/memory-schema.md`):

- **high** (`score >= 3`): surface "matches existing entry X" in the run notes. If this is the same finding (re-run / known prior id), re-run with `--update <match-id>` to fold body/tags into the existing entry. Prefer passing `--update` on the first call when you already know the prior entry id from this run's notes.
- **moderate** (`score == 2`): creates a new entry with `related_to: [existing-id]`.
- **Never** pass `--no-overlap-check` — that blanks the match signal and breaks re-run awareness.

## Promote to a spec/task (the fix loop)

A finding worth fixing is **promoted to a flow spec/task** — compose from `flowctl spec create` + `spec set-plan`, or `/flow-next:capture` from the finding body. That closes the loop: the QA finding becomes the intent for the fix, traceable back through its R-ID to the original spec. QA itself **does not fix product code** — it files, surfaces, and hands off (BRB's "test, document, file, hand off; don't fix unless asked").

## Anti-patterns

| Don't | Why |
|-------|-----|
| File before reproducing twice | Flake → false bug → wastes triage and corrupts the verdict |
| Use the suspected fix as the title | Pre-decides the solution; confuses the fixer |
| Skip console / write-side-effect evidence | Can't debug or confirm the actual state |
| "I think this is broken" with no concrete steps | Untestable — not a finding |
| File N separate findings for one root cause | File the highest-impact one; the overlap check links the rest |
| Mark a P0 as P1 to "not stop the pass" | Hides severity; the verdict reads green when it isn't |
| Pass `--no-overlap-check` | Blanks match signal; re-files the same finding every pass without awareness |
| Assert PASS by reading source | Forbidden (R1) — PASS rests on captured live-app evidence only |
