# Defect route: legitimate-state fixes and the reported surface

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 0% [user], 60% [paraphrase], 40% [inferred] -->

The defect route already checks for prior fixes, reproduces, eliminates candidate causes with runtime evidence, bisects and proves on base and head. Three gaps remain where a careful fix still goes wrong:

- **A guard that hides the bug.** The route confirms a mechanism, then the fix adds a null check, a retry, a clamp or a swallowed error where the crash surfaced. That is right only when the state reaching that point is legitimate. When the state should never exist, the guard hides the fault and leaves it free to surface elsewhere. [paraphrase]
- **Restart-only failures.** A failure that appears only after a restart is almost always persisted state (a config file, a cache, a lock, a serialized record), yet diagnosis often starts in the code. [paraphrase]
- **Proof on the wrong surface.** The route covers live apps; a defect reported through a command line, an HTTP endpoint or a library call can still be "proven" by a unit test of the branch, which shows the branch behaves and not that the reported path no longer fails. [paraphrase]

Target user: the person who reads the fix's PR and needs to trust that it removed the fault rather than its symptom. [inferred]

## Architecture & Data Models
<!-- scope: technical -->

All changes live in the defect route's gated reference, which only defect work reads; no always-loaded surface grows (G1). [inferred]

- **Diagnosis, step 2: is the state legitimate?** Before designing the fix, decide whether the state that triggered the symptom may legitimately occur. If it may, the code that broke on it is the cause and handling the state there is the fix. If it should never exist, a check where it surfaced is not the fix: trace what produced the state and fix that. Guards, retries, swallowed errors, clamped values and discarded state are where such faults usually hide, so a fix of that shape names why the state is legitimate. [paraphrase]
- **Diagnosis, step 2: restart-only failures.** When the failure appears only after a restart, a reload or a second run, persisted state (config files, caches, lock files, serialized records, migrations) is the first candidate, eliminated with evidence before code is suspected. [paraphrase]
- **Proof, step 4: the reported surface.** The base and head observations run through the surface the report came from: the command for a CLI report, the request for an API report, the call for a library report, the app for a UI report (the existing live-surface reference). A passing unit test of the changed branch supports the fix and is never the only proof when the report named another surface. [paraphrase]

## Examples
<!-- scope: both -->

**Guard that would hide the bug.** `render_invoice` crashes on `customer.address == None`. Adding `if customer.address is None: return ""` would stop the crash. Diagnosis asks whether a customer without an address may legitimately reach invoicing: the signup form requires an address, and the import job is the only writer that can skip it. The fix makes the import reject rows without an address and backfills the three existing records; the renderer is unchanged. [inferred]

**Legitimate state, fix where it broke.** The same crash in a product where guest checkouts have no address by design: the state is legitimate, so the renderer is the cause and handling a missing address there is the fix. [inferred]

**Restart-only.** A desktop app shows the old theme only after a restart. Code is unchanged between runs, so the first candidate is persisted state: the settings file holds both `theme` and a stale `theme_override` written by an older version. Eliminated with evidence (delete the override, restart, the bug is gone), the fix migrates the old key on load. [inferred]

**Reported surface.** A report says `tool export --since 2026-01-01` drops the first day. The base observation runs that command against a fixture and shows 0 rows for January 1; the head observation shows 42. The new unit test of the date-boundary helper passes too, and is listed as supporting evidence, not as the proof. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- A state whose legitimacy cannot be determined from code, docs or history is a product question: attended, it is asked; unattended, the route records the evidence-backed default it took, as the working rules already require. [inferred]
- A report with no named surface uses the surface a user would meet first; the record says which. [inferred]
- The local-defect scaling rule still applies: a clear local defect records the new parts in one line each. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Diagnosis decides whether the triggering state is legitimate; when it is not, the fix targets what produced the state, and a fix shaped as a guard, retry, swallowed error or clamp states why the state is legitimate. Errors: legitimacy undecidable from evidence → asked attended, recorded default unattended. [paraphrase]
- **R2:** A failure that appears only after a restart, reload or second run makes persisted state the first candidate, eliminated with evidence before code is suspected. No error surface beyond step 2's existing not-reproduced stop. [paraphrase]
- **R3:** Base and head observations run through the surface the report came from; a unit test of the changed branch is supporting evidence only when the report named another surface. Errors: no surface named → the first surface a user meets, recorded. [paraphrase]
- **R4:** On the defect cases of the maintainer's end-to-end comparison harness, a same-time control against the change shows no worse judge score and no longer time to the first hand-back. No error surface beyond the harness's own verdict. [inferred]

## Boundaries
<!-- scope: business -->

- No new stop, label, check or flowctl verb. [paraphrase]
- No change to step 1 (prior-fix check) or step 3 (bisect). [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

These three rules close the remaining ways a defect fix treats the symptom or proves the wrong path, at the cost of a few sentences in a reference only defect work loads. [paraphrase] A record line naming the always-on signal that would have shown a hard-to-find cause was built and measured, then dropped: agents wrote it in under half the cases it targeted, its payoff falls on a later defect the comparison cannot measure, and the stronger wordings that raised its uptake slowed the first hand-back. [inferred] A broader "question the premise after two failed fixes" rule was considered and not added: a review of recorded CI histories found no confirmed case of two fixes failing on the same false premise, and the working rules already carry one sentence for it. [paraphrase]

Delivery order: 2 of 6 in this set (router rows, defect discipline, measured numbers, worker effort, land catch-up, focused QA re-check); independent. Route: direct. [paraphrase]

## Strategy Alignment

Follows the **Agent first** design principle: diagnosis judgment stays with the agent, and the record gains no new line.

## Strategy Conflicts

None found.
