# Defect route: legitimate-state fixes and the missing signal

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 0% [user], 60% [paraphrase], 40% [inferred] -->

The defect route already checks for prior fixes, reproduces, eliminates candidate causes with runtime evidence, bisects and proves on base and head. Four gaps remain where a careful fix still goes wrong:

- **A guard that hides the bug.** The route confirms a mechanism, then the fix adds a null check, a retry, a clamp or a swallowed error where the crash surfaced. That is right only when the state reaching that point is legitimate. When the state should never exist, the guard hides the fault and leaves it free to surface elsewhere. [paraphrase]
- **Restart-only failures.** A failure that appears only after a restart is almost always persisted state (a config file, a cache, a lock, a serialized record), yet diagnosis often starts in the code. [paraphrase]
- **The dig nobody makes cheaper.** When the deciding fact took a long dig to find, the next person digs again, because nothing makes that fact visible at first look. [paraphrase]
- **Proof on the wrong surface.** The route covers live apps; a defect reported through a command line, an HTTP endpoint or a library call can still be "proven" by a unit test of the branch, which shows the branch behaves and not that the reported path no longer fails. [paraphrase]

Target user: the person who reads the fix's PR and needs to trust that it removed the fault rather than its symptom. [inferred]

## Architecture & Data Models
<!-- scope: technical -->

All changes live in the defect route's gated reference, which only defect work reads; no always-loaded surface grows (G1). [inferred]

- **Diagnosis, step 2: is the state legitimate?** Before designing the fix, decide whether the state that triggered the symptom may legitimately occur. If it may, the code that broke on it is the cause and handling the state there is the fix. If it should never exist, a check where it surfaced is not the fix: trace what produced the state and fix that. Guards, retries, swallowed errors, clamped values and discarded state are where such faults usually hide, so a fix of that shape names why the state is legitimate. [paraphrase]
- **Diagnosis, step 2: restart-only failures.** When the failure appears only after a restart, a reload or a second run, persisted state (config files, caches, lock files, serialized records, migrations) is the first candidate, eliminated with evidence before code is suspected. [paraphrase]
- **Proof, step 4: the reported surface.** The base and head observations run through the surface the report came from: the command for a CLI report, the request for an API report, the call for a library report, the app for a UI report (the existing live-surface reference). A passing unit test of the changed branch supports the fix and is never the only proof when the report named another surface. [paraphrase]
- **Record: the signal that would have shown it.** When the deciding fact took instrumentation or a long elimination to find, the record names the cheap, always-on signal that would have shown it at first look (a log line, a doctor check, an error message that names the value, a metric). It is a follow-up the person can pick up, never built inside the fix. When the cause was visible at first look, there is no signal line: a measured A/B showed a mandatory line on every defect handoff slowed small fixes. [paraphrase]

## Examples
<!-- scope: both -->

**Guard that would hide the bug.** `render_invoice` crashes on `customer.address == None`. Adding `if customer.address is None: return ""` would stop the crash. Diagnosis asks whether a customer without an address may legitimately reach invoicing: the signup form requires an address, and the import job is the only writer that can skip it. The fix makes the import reject rows without an address and backfills the three existing records; the renderer is unchanged. [inferred]

**Legitimate state, fix where it broke.** The same crash in a product where guest checkouts have no address by design: the state is legitimate, so the renderer is the cause and handling a missing address there is the fix. [inferred]

**Restart-only.** A desktop app shows the old theme only after a restart. Code is unchanged between runs, so the first candidate is persisted state: the settings file holds both `theme` and a stale `theme_override` written by an older version. Eliminated with evidence (delete the override, restart, the bug is gone), the fix migrates the old key on load. [inferred]

**Reported surface.** A report says `tool export --since 2026-01-01` drops the first day. The base observation runs that command against a fixture and shows 0 rows for January 1; the head observation shows 42. The new unit test of the date-boundary helper passes too, and is listed as supporting evidence, not as the proof. [inferred]

**Signal line.** Finding that a worker read a stale `.env.local` took twenty minutes of instrumentation. The record reads:

```text
- signal: log the resolved env file path at startup; it would have shown `.env.local` overriding `.env` at first look
```

A cause visible in the first stack trace gets no signal line.

[inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- A state whose legitimacy cannot be determined from code, docs or history is a product question: attended, it is asked; unattended, the route records the evidence-backed default it took, as the working rules already require. [inferred]
- A report with no named surface uses the surface a user would meet first; the record says which. [inferred]
- The signal line never adds logging, checks or metrics to the fix's diff. [paraphrase]
- The local-defect scaling rule still applies: a clear local defect records the new parts in one line each. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Diagnosis decides whether the triggering state is legitimate; when it is not, the fix targets what produced the state, and a fix shaped as a guard, retry, swallowed error or clamp states why the state is legitimate. Errors: legitimacy undecidable from evidence → asked attended, recorded default unattended. [paraphrase]
- **R2:** A failure that appears only after a restart, reload or second run makes persisted state the first candidate, eliminated with evidence before code is suspected. No error surface beyond step 2's existing not-reproduced stop. [paraphrase]
- **R3:** Base and head observations run through the surface the report came from; a unit test of the changed branch is supporting evidence only when the report named another surface. Errors: no surface named → the first surface a user meets, recorded. [paraphrase]
- **R4:** When finding the cause took instrumentation or a long elimination, the defect handoff (and the record, when there is a task) carries one line naming the always-on signal that would have shown the cause at first look; a cause visible at first look gets no signal line. The fix's diff never builds that signal. No error surface. [paraphrase]
- **R5:** On the defect cases of the maintainer's end-to-end comparison harness, a same-time control against the change shows no worse judge score and no longer time to the first hand-back, and the signal line appears on the case whose cause took a long dig. No error surface beyond the harness's own verdict. [inferred]

## Boundaries
<!-- scope: business -->

- No new stop, label, check or flowctl verb; the record line is written after acting. [paraphrase]
- No change to step 1 (prior-fix check) or step 3 (bisect). [inferred]
- Signals are proposed, never implemented inside the fix. [paraphrase]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

These four rules close the remaining ways a defect fix treats the symptom or proves the wrong path, at the cost of a few sentences in a reference only defect work loads. [paraphrase] A broader "question the premise after two failed fixes" rule was considered and not added: a review of recorded CI histories found no confirmed case of two fixes failing on the same false premise, and the working rules already carry one sentence for it. [paraphrase]

Delivery order: 2 of 6 in this set (router rows, defect discipline, measured numbers, worker effort, land catch-up, focused QA re-check); independent. Route: direct. [paraphrase]

## Strategy Alignment

Follows the **Agent first** design principle: diagnosis judgment stays with the agent, and the one new record line is written after acting.

## Strategy Conflicts

None found.
