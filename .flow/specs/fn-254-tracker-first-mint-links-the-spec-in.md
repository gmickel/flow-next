# Tracker-first mint links the spec in the same call

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 85% [paraphrase] (GitHub issue #464, reporter @sn-furali), 15% [inferred] -->

`flowctl spec create --tracker-first --tracker-identifier <KEY-N>` mints a spec that records only the display identifier. The durable `tracker.id` stays null, so the spec looks unlinked. The next lifecycle touchpoint takes the create-if-unlinked path and opens a second remote issue instead of adopting the one the caller named. The reporter hit it three times out of three on a live Linear bridge.

The only way to finish the link today is a second command, `sync set-tracker-id`, and nothing at runtime says it is needed. The hazard lives instead as a warning repeated in five skill references (ten files with the Codex mirror), which every call site has to remember.

Every caller can hold the durable id before minting: create-first returns `{id, identifier, url}` together, and a named-issue route can read the issue before it mints (today the references mint first and fetch after). So the fix is to let `spec create --tracker-first` write the whole identity in one call. It moves a repeated prose hazard into one deterministic write.

## Architecture & Data Models
<!-- scope: technical -->

- `spec create --tracker-first` gains two optional arguments beside `--tracker-identifier`: the durable tracker id and the issue URL. [paraphrase]
- When the durable id is supplied, the published sidecar carries `tracker.id`, `tracker.identifier`, `tracker.url` (when given) and `linkState: linked` in the same atomic publication the mint already performs. No second write, no window in which the spec exists unlinked. [paraphrase]
- The mint keeps its own identifier validation and synthetic-prefix reservation unchanged. It reuses only the durable-id collision rule from `sync set-tracker-id`: a tracker id another spec already holds is refused. When a durable id is supplied, the existing shared config writer lock is held across the collision check and the publication, alongside the allocation lock the mint already takes, so a concurrent link cannot slip between check and write. No new lock mechanism. [inferred]
- Caller order becomes: a named issue is read before the mint; a fresh idea uses create-first's returned identity; the mint then carries the id and URL; merge-base seeding, recovery, back-reference and receipts follow as today. Only the identity write moves into the mint. [paraphrase]

## Edge Cases & Constraints
<!-- scope: technical -->

- **Flags without `--tracker-first`** are refused; the flow-first path never reaches this branch and stays byte-identical. [paraphrase]
- **Durable id already linked to another spec**: the create is refused naming the owning spec, and nothing is minted. The message does not suggest `--force`, which the mint does not offer. [inferred]
- **Empty or whitespace-only values** for the new arguments are refused rather than stored. [inferred]
- **URL without an id** is refused: `--tracker-url` requires `--tracker-id`. [inferred]
- **No network.** The mint stays a local command; no transport call is added. [paraphrase]
- **No runtime advisory about id schemes** (the withdrawn R10 stays withdrawn), and no new output fields. [paraphrase]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `spec create --tracker-first --tracker-identifier <KEY> --tracker-id <id> [--tracker-url <url>]` publishes a sidecar with `tracker.id`, `tracker.identifier`, `tracker.url` (when given) and `linkState: linked` in one atomic write; a subsequent lifecycle touchpoint treats the spec as linked and creates no second remote issue. A regression test drives the real linkage decision after such a mint and asserts no remote create. [paraphrase] Errors: either new argument without `--tracker-first`, `--tracker-url` without `--tracker-id`, and empty or whitespace-only values are refused with a clear message and nothing is written.
- **R2:** A durable id already linked to another spec refuses the create before any file is written, under the shared config writer lock held through publication. Existing mint validation and prefix reservation are unchanged. [inferred] Errors: no error surface beyond the refusal.
- **R4:** The five skill references that restate the "minting stores the identifier but NOT the durable tracker.id" hazard (plan tracker-first mint, capture tracker integration, work spec-id mint, refine write-back, QA bug filing), and their Codex mirrors, read or create the issue first, pass the durable id and URL at mint, keep the seeding and recovery obligations, and drop the repeated warning and the stale Phase 2b/2d pointers. The tracker-sync identity reference and the flowctl reference document the new arguments. The prose test that pins the old attach wording is updated for the new sequence without pinning replacement sentences. [paraphrase] Errors: no error surface beyond doc drift tests.
- **R5:** A spec created without the new arguments (flow-first, or tracker-first with only `--tracker-identifier`) behaves exactly as today, and `sync set-tracker-id` is unchanged. [paraphrase] Errors: no error surface beyond existing behavior.

## Boundaries
<!-- scope: business -->

- Folding the fetch/attach/seed ceremony or any network call into the mint is out of scope. [paraphrase]
- Changes to `sync set-tracker-id` behavior, the seeding ceremony, or the flow-first path are out of scope; caller ordering and stale references in the five skill references are in scope (R4). A mechanical helper extraction shared with `set-tracker-id` is allowed. [paraphrase]
- A `--force` collision override on `spec create` is out of scope. [inferred]
- Open PR #467 addresses the same issue and is left untouched for now. [paraphrase]

## Decision Context
<!-- scope: both — conditionally substructured -->

The reporter's first option was chosen: optional arguments on the mint, because every caller already holds the values and one atomic write removes the unlinked window. The envelope marker (their weaker alternative) was dropped after review: with the flags, a successful call with an id is linked by construction, and the marker would not close the identifier-only window. Folding the ceremony into the mint was rejected, as the reporter also argued, because it would pull transport into a local command. Only the collision guard is reused, under the same writer lock; the relink-only checks (live operation claims) do not apply to a spec that does not exist yet. This fits the tracker-determinism track: a hazard restated in ten files becomes one deterministic write [strategy:Tracker determinism].

## Strategy Alignment

- **Tracker determinism** — repeatable tracker plumbing moves out of skill prose into flowctl; no host judgment changes. [strategy:Tracker determinism]
