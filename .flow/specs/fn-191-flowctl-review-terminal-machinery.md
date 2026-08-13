# fn-191-flowctl-review-terminal-machinery flowctl review-terminal machinery: extract to a package on the proven pattern

## Goal & Context
<!-- scope: business -->

The review-terminal machinery — round reservations, journal lifecycle, replay gating, hash epochs, supersession, stall rules, ratchet rendering — lives inline in a ~51.7k-line module, and that location has cost real review rounds: a fix landed on one dispatch path while a byte-identical sibling stayed wrong, because nothing made the sibling visible. The same monolith also makes every downstream artifact fragile: no agent reads the file (it is well past a million tokens), so all navigation is grep plus offset reads, and plan-sync repeatedly re-anchors coordinates as the file shifts by hundreds of lines per task. This session's own re-verification is the cheapest possible illustration: the region boundary moved 366 lines in nine days, and the earlier spec's own line references had all rotted.

The extraction pattern is already proven in this repository by the tracker package — a deterministic package with a generated manifest and an integrity test, propagated by the existing distribution mechanism. This spec applies that template to the most parity-sensitive region in the file.

**Honest scope statement, because it changes how the value should be judged:** the region is roughly a twentieth of the module. After this lands, flowctl is still a large single file and agents still navigate it by grep. What this spec delivers is one drift-prone subsystem made cohesive, plus the extraction contract paid for once — manifest, propagation, injection wiring, integrity test, three-load-identity coverage — so any later extraction is mechanical. The navigation payoff arrives with the *sequence*, not with this spec. If the sequence is not intended, the honest expected return is one parity fix and some added indirection, and this spec should be declined rather than trimmed.

## Architecture & Data Models
<!-- scope: technical -->

**Boundary by symbol, never by coordinate.** The moved region is defined as an explicit symbol list, re-derived by grep at implementation time. Adjacent symbols that stay behind are named explicitly, including the re-review preamble builder and the prompt-template loaders and builder — those stay so that prompt-pinned constants never move, which keeps their hashes identical by construction rather than by careful editing.

**One-directional wiring, injected.** The host module loads the package behind a lazy path guard with a soft-fail message, exactly as the tracker package is loaded. The package never imports the host by name. This is not a style preference: under direct script invocation the host module is `__main__`, so importing it by name would execute a *second* module instance with its own lock and cache singletons — a silent split-brain whose symptom is corrupted concurrency behavior, not an import error. The host therefore passes itself (or a narrow context object of the callables the region needs) into the package at wiring time, and the host keeps facade re-exports of every extracted symbol so its own call sites stay verbatim.

**The reachable-symbol set is derived, not guessed.** The moved region reaches further than the obvious helpers — receipt recovery paths, receipt locking and preservation, findings validation, criteria parsing. A mechanical cross-boundary inventory (an AST or linter pass over the moved code) precedes the move; a hand-written list is how a missing import becomes a runtime failure in a rarely-taken branch.

**Three load identities, all real.** The code must work when the host is imported through the new entry, when it is run directly as a script, and when the authenticated static-help path exec's it in memory. These are different module identities, so they are separate test cases, not one.

**Distribution is a contract, not a copy.** The package ships with a generated manifest, propagates to the committed dogfood copy and every install channel by the mechanism that already carries the tracker package, and an integrity test asserts the distribution. Two failure directions matter: a stale install missing the package must soft-fail naming it, and a tampered or absent manifest must make installers fail closed. The manifest literal must not appear in the host module's source — per-command hashing there is pinned against, and the manifest check belongs to the generator and installers.

## API Contracts
<!-- scope: technical -->

Externally observable behavior is unchanged: same subcommands, same flags, same exit codes, same JSON shapes, same marker strings, same receipt and journal file formats on disk. Internally, the contract added is the package boundary:

- the host injects a context providing the helpers the region needs; the package declares what it requires and never reaches back by module name;
- the host re-exports every extracted public symbol under its original name;
- the package's own failure to load produces a message naming the package and the remedy, not a traceback.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Split-brain under direct invocation** — covered above; the test for it is behavioral (two instances would not share a lock), not an import assertion.
- **Stale or partial install** missing the package → soft-fail naming it, mirroring the tracker package's message shape.
- **Tampered or absent manifest** → installers fail closed.
- **Prompt-pinned constants** do not move; their hashes stay identical, and the pinning test needs no edit.
- **Concurrency invariants are the risky half.** The region owns lock-guarded writes, atomic replacement, and reservation accounting. These are pinned today by white-box tests that import internals; those tests must keep passing against the new import path without weakening — a test that gets easier to satisfy after a move is a regression, not a cleanup.
- **One-time anchor churn** across open specs and task files that reference coordinates in the moved region: land in one change, run plan-sync afterwards, and note the churn in the change entry so the next reader does not treat rotted anchors as a defect.
- **Windows and the OS smoke matrix** must stay green — the package rides the same propagation the smoke exercises.
- Standing criteria in `.flow/criteria.md` apply as written and are not restated here.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The review-terminal region lives in its own package, with the boundary recorded as a symbol list (re-derived at implementation time, not inherited from stale coordinates), and the host module shrinks by at least the moved region. Symbols named as staying behind — the re-review preamble builder, the prompt-template loaders and builder — remain in the host. Errors: a symbol that cannot move without taking a pinned prompt constant with it stays behind and is recorded as such.
- **R2:** The package never imports the host by module name; the host injects the required context, derived from a mechanical cross-boundary symbol inventory rather than a hand-written list, and re-exports every extracted symbol under its original name. Behavior is verified under all three load identities — imported entry, direct script, authenticated static path. Errors: a missing injected symbol surfaces at wiring time with the symbol named, never as an attribute error inside a rare branch.
- **R3:** Distribution integrity holds: generated manifest, propagation to the dogfood copy and every install channel by the existing mechanism, and an integrity test in the shape of the tracker package's. Errors: stale install missing the package → soft-fail naming the package and remedy; tampered or absent manifest → installers fail closed; the manifest literal never appears in the host module's source.
- **R4:** Zero behavior change: subcommands, flags, exit codes, JSON shapes, marker strings, and on-disk receipt and journal formats are identical; prompt-pin hashes unchanged; the white-box tests covering locks, reservations, epochs, and atomicity pass against the new import path **without being weakened**. Errors: no error surface beyond the gate itself.
- **R5:** Full suite, lint, and the OS smoke matrix are green; docs that describe the module layout and the propagation recipe are updated; plan-sync runs after landing; the change entry records the one-time anchor churn and names the specs affected. Errors: no error surface beyond R4.

## Boundaries
<!-- scope: business -->

- **This spec extracts exactly one subsystem.** Backend dispatch, receipts and findings, and the gate helpers are explicitly not in scope; each is its own later decision, taken with this extraction's outcome as evidence.
- No behavior change, no new config keys, no CLI additions, no schema changes.
- No startup-performance work — that is the launcher spec, and this spec makes no startup claim.
- No renaming or re-homing of the tracker package, and no change to its manifest contract beyond reusing the mechanism.
- No language port.

## Decision Context
<!-- scope: both -->

Split out of an earlier combined spec 2026-08-13 so that the measured startup win could ship on its own risk profile. This half's justification is different in kind: parity and navigation, evidenced by a review ledger where sibling sites drifted, not by a benchmark.

**Why this region first:** it is where the drift actually bit, and it is the newest and most parity-sensitive machinery in the file. Picking by evidence beats picking by size.

**Why injection rather than an import:** direct script invocation makes the host `__main__`, so a by-name import silently creates a second module instance with separate lock and cache singletons. Injection makes that impossible rather than forbidden.

**Why a symbol list rather than line ranges:** the earlier spec's coordinates rotted within days — the boundary moved 366 lines in nine days while the symbols stayed put. Coordinates in a spec are a durability violation for exactly this reason.

**Rejected: extracting several subsystems in one pass.** It multiplies the anchor churn and makes "zero behavior change" unverifiable in one review. The pattern gets proven once, cheaply, then repeats.

## Parked unknowns

- Whether the follow-on extractions are worth doing at all. It is decidable only after this one lands and we can see whether the parity class actually stops recurring in review — not before, and not by argument. What would resolve it: the next few review cycles touching this subsystem, plus whether plan-sync anchor churn measurably drops for work in the extracted region.
