# flow --auto: pilot adopts the routing reference and runs long-horizon over the same rails

<!-- STUB. Sequenced after fn-238. Captured from the fn-238 discussion; refine with /flow-next:interview before work. -->

## Goal & Context
<!-- Goal & Context: 70% [user], 30% [paraphrase] -->

After fn-238 ships the attended conductor and the shared routing reference, the only difference between flow and pilot is attended versus unattended. Pilot still classifies the next stage from state; flow classifies from content and context through the routing reference. This spec makes the unattended driver the same judgment behind a second entry shape, `flow --auto`, and retires pilot as a separate skill.

Frontier models handle long-horizon work well enough that pilot's one-stage-per-tick discipline is now compensation for a limit that no longer exists. Two things survive because they are harness limits, not model limits. Fresh-context separation between writer and reviewer stays. Externalised state (receipts, evidence, the strikes ledger) stays so a run that dies at hour six resumes from disk. The tick contract with its terminal verdict line stays as the portable floor for hosts without wake primitives, and as the audit trail on every host.

MergeFoundry (the maintainer's flow-swarm orchestrator) owns its own scheduler and does not need these primitives. Flow-Next does, because it runs inside third-party harnesses with flaky session and wake boundaries.

## Architecture & Data Models
<!-- Architecture & Data Models: 40% [user], 60% [paraphrase] -->

- `flow --auto` runs the whole route for one item in a single long-horizon session on hosts with wake and background primitives, checkpointing through the receipts each stage already writes. On hosts without those primitives it degrades to tick mode: one item, one stage, terminal verdict line, driven by the host loop.
- Pilot's rails move unchanged: dirty-tree refusal, strikes ledger and its human clear verb, never nest with Ralph, never merge, never author a spec, backlog mode's park-and-ask, the ready flag or tracker ready state as the consent boundary.
- Classification reads the routing reference sections that fn-238 defines. No second copy of the rules.
- Backlog mode becomes `flow --auto --backlog`. Land stays separate because merge authority is its own boundary.
- `/flow-next:pilot` remains as an alias for one release with the verdict grammar unchanged, then is removed. The verdict line keeps its name so existing loops, the Ralph template, and docs keep parsing.

## Acceptance Criteria

- **R1:** `flow --auto` advances a ready item through its full route in one session on a host with wake primitives, and in tick mode elsewhere, with the same terminal verdict grammar pilot emits today. [paraphrase]
- **R2:** Every pilot rail listed above is preserved byte-for-byte in behaviour and covered by the existing tests, re-pointed at the new entry. [paraphrase]
- **R3:** Classification comes from the routing reference; pilot's own stage table is deleted. [user]
- **R4:** The pilot alias exists for one release, its docs point at `flow --auto`, and the changelog states the retirement. [inferred]
- **R5:** Ralph, `/loop`, and `/goal` recipes in docs are rewritten as optional wrappers for hosts without wake primitives. [paraphrase]

## Boundaries

- No change to land. [user]
- No new flowctl subcommand that reads, weighs, or decides. [paraphrase]
- No attribution of the routing rules to any external system. [user]

## Decision Context

- Direction stated during fn-238 capture: the router is the smallest new piece; everything it routes to already exists and proves its work. Pilot retires once its judgment and flow's are the same reference. [user]
- Keep tick mode because harness boundaries are flaky and Flow-Next does not own the orchestrator. [user]
