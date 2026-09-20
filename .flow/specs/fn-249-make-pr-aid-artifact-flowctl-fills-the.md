# make-pr aid artifact: flowctl fills the diff metadata

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 40% [paraphrase], 60% [inferred] -->

`/flow-next:make-pr` has the host agent compose one JSON object, the PR cognitive aid, and flowctl validates it, stores it, and renders part of the PR body from it. The question behind this spec was whether people who use flow-next on its own pay for structured output that only a downstream projector needs, and whether make-pr should split into a markdown path and a JSON path.

A read of the skill, the validator, and 111 stored aid artifacts says a split would not help. One authoring pass feeds the PR body, the HTML lens and any downstream projector, and the judgment in it (thesis, grouping, per-file summaries) is needed by all of them. The cost is in what the agent has to type to produce it. The stored artifacts average 28.7 KB and about 63 file rows each. 57% of their bytes are mechanical file-row fields (line counts, change type, diff link) that flowctl already computes and then checks the agent's copy against, and only 24% is per-file judgment. Every changed path needs a row today, including files nobody would write a sentence about, and on a single-task spec every row repeats the same task reference.

This spec is the input side: the agent writes only what needs judgment, and flowctl fills in everything it can derive. The stored artifact stays a complete v1 object, so no reader changes. A sibling spec changes what the PR body renders from that artifact.

No wall-clock or token measurement of make-pr exists today; the figures in this section are bytes on disk and file counts. This spec takes the first baseline, before anything changes.

Field evidence from one downstream run: the first write of an artifact failed because git's copy detection reported a new spec sidecar as copied with 20 lines added and 20 removed, a value an agent cannot know, and the validator stopped at that first error.

Three smaller costs sit beside the typing. The validator stops at the first error, so a wrong artifact is corrected one error per attempt. Aid artifacts and their write-lock files end up tracked in git, although make-pr states that a current aid stays local so it cannot stale its own head-bound input; this repository tracks 69 such files, 30 of them lock files. And 15 of 76 specs hold more than one generation, 5 of them more than one at the same head, where the existing artifact should have been reused.

## Architecture & Data Models
<!-- scope: technical -->

- The persisted artifact stays the complete v1 object with one row per changed path and explicit references on every row. Every reader of a stored artifact sees the same fields as today. [inferred]
- The change is on the input side of the existing validate and write operations. Input may be sparse in four ways: a row may omit its mechanical fields, a changed path may have no row, a row may omit references its group already carries, and a row may omit its attention class where the path pattern decides it. flowctl expands sparse input into the complete stored form. [inferred]
- The fields an agent still authors are the thesis, proof cells, groups, the sources table, and, for each file worth a sentence, its path and summary plus any attention class or reference that differs from the default. [inferred]
- A row that flowctl added for an unlisted path carries no summary, which is how a reader tells "not described" from "described". [inferred]
- Ignore rules for aid artifacts live in flowctl's managed ignore block, the same mechanism that already covers receipts, temporary files, and locks. [inferred]

## API Contracts
<!-- scope: technical -->

- Validate and write accept complete input, as today, and sparse input. Output of write is always the complete form. [inferred]
- Validation failure output lists every independent violation found in that call, each with its location in the artifact, in a stable order. The exit status stays non-zero on any violation. [inferred]
- No new subcommand, flag, or config key. [paraphrase]

## Edge Cases & Constraints
<!-- scope: technical -->

- A supplied mechanical value that disagrees with the diff is still rejected, as today. Filling applies only to what was omitted. [inferred]
- An authored row whose path is not in the diff is still rejected. Only the other direction relaxes: a diff path with no authored row is filled. [inferred]
- A file the agent left out must never be labelled safe to skim by default. Only zero-judgment path patterns (flow state files, lockfiles, generated output) default to the mechanical or generated class; every other unlisted path keeps the canonical class. [paraphrase]
- An explicit value on a row always wins over an inherited or pattern-derived one. [inferred]
- Input that cannot be parsed as JSON yields the single parse error, since nothing else can be checked. [inferred]
- The managed ignore block must not swallow artifact kinds that have a committed mode, such as the HTML lens, or unrelated files kept under the artifacts home. User patterns below the managed marker stay untouched. [inferred]
- Files already tracked are not untracked by flowctl. Removing them from the index is a maintainer action in each repository. [inferred]
- Ignored artifacts are per-clone state. A pull request made on another host or clone shows no stored walkthrough to a projector that reads the artifact home. This limit exists today wherever the artifacts are not committed, and it is stated so that nobody later assumes the artifact travels. [paraphrase]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A file row that omits additions, deletions, change type, or diff link validates and writes successfully, and the stored artifact carries those fields with the values flowctl derives from the diff, including paths that git reports as copied or renamed. Errors: an omitted field that flowctl cannot derive (no diff metadata available) fails validation naming the row and field; a supplied value that disagrees with the diff fails as it does today. [inferred]
- **R2:** A complete artifact that validates today validates unchanged, the stored schema version stays 1, the artifact path is unchanged, and the stored form written from sparse input is identical to the stored form written from the equivalent complete input. Errors: no error surface beyond R1. [inferred]
- **R3:** One validation call reports all independent violations in the artifact, each with its location, in a stable order, in both human and JSON output. Errors: unparseable JSON reports the parse error alone; a violation that makes later checks meaningless (a file row with no path) is reported without cascading follow-on errors for the same row. [inferred]
- **R4:** A changed path with no authored row gets a row from flowctl, with no summary. Its attention class is mechanical or generated only where a zero-judgment path pattern decides it, and canonical otherwise. An authored row may omit its attention class on the same terms. The make-pr instructions tell the agent to write rows only for files worth a sentence and to author only judgment fields, and the aid instruction text does not grow in line count as a result of this spec. Errors: an authored row for a path outside the diff is rejected as today; a row that omits its attention class where no pattern decides it is rejected naming the row; an explicit class always wins. [paraphrase]
- **R5:** A row inherits its group's source, requirement and task references unless it states its own, and the stored artifact carries them explicitly on every row. Errors: a row with a summary whose group has no references and which states none is rejected as today; a row reference that names an unknown source, requirement or task is rejected as today. [inferred]
- **R6:** After flowctl refreshes its managed ignore block, aid generation files and aid write-lock files are ignored by git in a fresh repository and in an existing one, while HTML lens output and other artifact kinds remain trackable. The step that stages aid artifacts today is identified and recorded in the PR; if a flow-next skill or flowctl command stages them, it stops doing so and a regression test covers it. The release notes give the one-time step for untracking files already in the index, and the consumer documentation states the per-clone limit. Errors: a hand-edited managed block is handled by the existing refresh behavior; user patterns below the marker are preserved; if the staging cause is a user's or another tool's broad stage, the ignore rule is the fix and the finding is recorded as such. [inferred]
- **R7:** A second make-pr run at an unchanged base and head, with a valid current artifact present, authors no new generation. The cause of the existing same-head generations is recorded in the PR. Errors: a moved head, a missing artifact, or an artifact that fails validation produces a new generation as today. [inferred]
- **R8:** Before any change from this spec merges, make-pr as it stands today is measured on one fixed pull request with the model held constant: output tokens, tool calls and wall-clock time, at least three runs, medians recorded. The same measurement is repeated after this spec's changes. Both sets of figures, and the reduction in agent-authored bytes recomputed over the aid artifacts already stored in this repository, are reported in this spec's pull request and kept in a committed measurement record that the sibling briefing spec compares against. Negative results are kept. Errors: no error surface. [paraphrase]

## Boundaries
<!-- scope: business -->

- No split of make-pr into a markdown path and a JSON path. [paraphrase]
- No change to what the PR body renders, and no trimming of the make-pr instructions beyond R4. Both belong to the sibling briefing spec. [inferred]
- No new authored fields. They belong to the sibling briefing spec. [inferred]
- No change to the v1 stored schema that readers see. [paraphrase]
- No pruning or retention policy for superseded generations. [inferred]
- flowctl does not untrack files on the user's behalf. [inferred]
- The per-clone limit of ignored artifacts is stated, not fixed. [paraphrase]

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
<!-- scope: business -->

- The land redesign comes first; this spec is worked after it. That order is a priority, not a technical need: the input plumbing does not touch land, so if the land redesign stalls this spec can go ahead without it. [paraphrase]
- The aim is the same as the land work: make flow-next simpler for its own users while keeping what it can do. Zero-judgment copying moves out of the agent's lane and into flowctl, and nothing a reader of the artifact relies on changes. [paraphrase]
- The work is split in two: this spec ships the plumbing nobody sees, and the sibling spec carries the visible change to the PR body so it can be reviewed by itself. [paraphrase]

### Implementation Tradeoffs
<!-- scope: technical -->

- Rejected: a machine-only path and a human-only path. Both audiences need the same judgment, and the artifact is what lets one authoring pass serve both. [inferred]
- Rejected: the agent writes markdown and a parser recovers the structure. Earlier parser-based exports in this repository dropped content silently. [inferred]
- Rejected: filing every unlisted path as mechanical. It gives the smallest input, and it labels a forgotten file as safe to skim. [paraphrase]
- Rejected: ignoring the whole artifacts home. The HTML lens has a committed mode and other artifacts are kept there on purpose. [inferred]
- Expanding sparse input is a join between things flowctl already holds: the submitted rows, the group they sit in, the diff metadata, and fixed path patterns. It involves no reading or weighing and gives the same answer with no agent present, which is the repository's test for putting work in flowctl. [inferred]

## Strategy Alignment

- Design principle "flowctl grows only under burden of proof": the change adds no subcommand and moves only zero-judgment expansion into existing commands.
- Design principle "Receipts are the portable product boundary" and the track "flow-swarm preparation (contract pillars SHIPPED)": the stored artifact keeps its versioned v1 shape and its path, so downstream readers are unaffected.
- Design principle "Remember the bitter lesson": nothing here compensates for model quality; it removes transcription that no model should be doing.

## Parked unknowns

- Whether the same-head generations come from a reuse miss or from a legitimate trigger (for example a base change). Reading the generation chains of the affected specs resolves it; R7 records the answer.
- Which v1 group carries the rows flowctl adds for unlisted paths without breaking the rule of one to seven step groups. Reading the v1 group rules against a fixture with seven authored steps resolves it.
