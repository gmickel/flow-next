# 9.11.0 final-audit fixes for issue start and intake

## Goal & Context

The final pre-release audit of 9.10.0..main (Codex gpt-6.1-sol, three lenses, after #609 merged) returned NEEDS_WORK with five defects in the unreleased issue-start and intake work. 9.11.0 does not ship until they are fixed and a re-audit passes. [user]

## Architecture & Data Models

- `find_linked_specs` (flowctl.py) must fail closed on every read it depends on: the ref listing, each ref's tree and each spec JSON blob. [inferred]
- Issue start resolves a remote-only link by bringing the fetched copy into the checkout, not by switching to whatever local branch shares the name. [inferred]
- The always-review rule for an issue start lives in the captured spec and in the shared working rules, so a worker or a later run that re-anchors on the spec applies it. [inferred]
- A question round's identity includes the source the run read, so an answer by comment or by body edit opens a new round while a crash-rerun on the same source still dedupes. [inferred]
- Intake reads the full issue before capture or fold; excerpts only drive the proposal table. [inferred]

## Acceptance Criteria

- **R1:** `specs --refs --tracker-id` fails (never `linked: []`) when the ref listing or any ref's tree cannot be read; a test injects an unreadable tree. [inferred]
- **R2:** Issue start, resuming a spec linked only on a remote branch, fast-forwards an existing local branch of that name to the fetched copy or stops `NEEDS_HUMAN` when it cannot, and confirms the checkout's spec JSON carries the link before continuing. [inferred]
- **R3:** A spec captured from an issue states that every task gets implementation review, and the shared working rules make such a spec's review unskippable by the risk rule; a worker re-anchoring on the spec applies it. [user]
- **R4:** After a person answers by editing the issue body and returns it to the ready state, a follow-up question is posted as a new round; rerunning the same round on the same source still does not double-post. [inferred]
- **R5:** Intake reads the full issue (body and comments) for each picked row before capture or fold, and hands it to capture as the source. [inferred]

## Boundaries

- No new flowctl verb or config key. [inferred]
- No change to the risk rule outside specs that state every task is reviewed. [user]

## Decision Context

- Always review an issue start (maintainer decision, 2026-11-15), now carried by the spec itself so dispatch boundaries cannot drop it. [user]
