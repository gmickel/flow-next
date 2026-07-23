# P5 sealed holdout provenance

- Frozen: 2026-07-23, before any task 130.7 Plan prompt mutation.
- Subject input: `input.md`.
- Scorer-only answer key: `oracle.md`; never pass it to the subject.
- Baseline: V1/B1 commit `8ed71a73ccc593a8a018dcdb805a86f396dcf76f`.
- B1 fixture: `optimization/reached-path/fixtures/b1/plan/sealed-holdout-nocode-research-mermaid.json`.
- B1 fixture hash: `f03475d1f439d64803d35247e710708ebaa72d2fc84e5ac333df60cc56e199ae`.
- B1 Plan prompt hashes:
  - `SKILL.md`: `282258022307f61c7a4de648b881b52d6b84ae644cbe83f5e085ba1a57e52d6a`
  - `steps.md`: `e1755d3dbbc6aa9afeeb7ccb93b7022edf0c7337b95fb800b443ff165b498794`
  - `examples.md`: `6b85095e565bb57fb4199ddd451d4417100433392c666b97d0a2848b9201a419`
- Baseline deterministic reached path: 50,243 characters / 12,560.75
  chars-per-four token-equivalent (`SKILL.md` + `steps.md`; the holdout reaches
  `examples.md` later at Step 5, recorded separately from this router-only
  measurement).
- Backend telemetry: unavailable in this Codex-session-only worker run; never
  substituted with deterministic source size or wall time.

The fixture and answer key are immutable for task 130.7. A prompt candidate
that fails any baseline-pass H-cell is reverted independently. A flat candidate
is discarded. P4 remains contaminated by the earlier sizing example and is not
the sole evidence for an examples mutation.

