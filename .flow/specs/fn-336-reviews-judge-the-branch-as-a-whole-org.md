# Reviews judge the branch as a whole; org criteria by reference

## Goal & Context

<!-- Source: 5% user / 65% [paraphrase] / 30% [inferred] -->

GitHub issue #619 reports two things an autonomous run lets through.

First, defects that only show across a branch. Each implementation review judges one task's diff, and the completion review sees every task together but is told to judge spec compliance, not code quality. Two field cases: five hand-written paging loops and three origin-URL parsers with different rules, each having passed its own review; and a 23-task spec meant to replace a set of routing rules that grew from 2,168 to 2,822 lines while 13 reviews each passed their step.

Second, rules that hold for a whole organisation. They are maintained in one shared guidelines repository, while flow-next reads standing criteria from `.flow/criteria.md` in each repository.

The issue proposes a new opt-in whole-branch review stage and layered user-level configuration. Both were declined in discussion: the stage repeats a review that already has the whole range in front of it, and a user-level layer breaks "everything lives in the repo" and lets a runner without the file skip the organisation's rules silently. This spec takes the agentic route instead: say what the existing reviewers should look at, and document how a repository points at shared rules.

The unattended failure this prevents: `flow --auto` hands over a branch where every step passed review and the whole is duplicated or grew where it was meant to shrink.

## Architecture & Data Models

- No new stage, receipt, verdict or config key. The change is wording in two review rubrics and one documentation section. [paraphrase]
- The completion review keeps spec compliance as its first job and gains a short whole-branch lens on specs with more than one task. [paraphrase]
- The implementation review's existing smell baseline already names duplicated code inside the diff; it gains the question of whether new code repeats something the repository already has outside the diff. [paraphrase]
- Shared organisation rules reach a reviewer through the repository's own criteria file, either as a link to the shared file or as a criterion that names it. The reviewer has a shell and reads the file it is pointed at. [paraphrase]

## Edge Cases & Constraints

- A whole-branch finding late in a long spec costs a fix round at the most expensive point. The measured round decides whether the wording earns that. [inferred]
- A criterion that points at a shared file gets one verdict in the receipt, with the violated rule named in its note. That is coarser than one G-ID per rule and is stated in the docs. [paraphrase]
- A shared file may sit outside the repository. Whether each review backend's reviewer can read such a path is checked live, not assumed. [paraphrase]
- Standing criteria are judged when a review runs on a spec. Work with no spec, and a small fix whose review the risk rule skips, are not covered; the docs say so. [paraphrase]
- A review skill's contract change updates that skill's conduct checklist in the same change. [inferred]

## Acceptance Criteria

- **R1:** On a spec with more than one task, the completion review also judges the branch as a whole and reports as ordinary findings: logic written again in a later task, a fix layered on an earlier fix instead of changing the cause, and code that grew where the spec meant to replace or shrink it. Its rubric no longer says it does not judge code quality. [paraphrase]
  Errors: a one-task spec is unchanged (its implementation review already sees the whole range); a branch with none of these yields no extra finding.
- **R2:** The implementation review checks new helpers and logic against what the repository already has outside the diff, and reports a repeat as a finding. [paraphrase]
  Errors: a repeat the repository's standards allow is not a finding.
- **R3:** R1 and R2 are measured before they ship, each against its absence, with bars written down before the round: seeded branches carrying cross-task duplication, a layered fix, and growth against a replace-intent spec for recall; clean branches for false findings; wall-clock and cost for both. The round and its results, negative ones included, are kept. [paraphrase]
  Errors: a line that misses its bars does not ship, and the spec records the result in place of the line.
- **R4:** The teams guide's standing-criteria section documents how a repository uses shared organisation rules: `.flow/criteria.md` as a link to a shared criteria file, and a criterion that names a shared guidelines file, with what each records in the receipt. It states that standing criteria are judged when a review runs on a spec. [paraphrase]
  Errors: a broken link already fails the review closed; the docs say so.
- **R5:** For every review backend, a live review confirms the reviewer read a criteria-referenced file outside the repository. The docs name any backend that cannot. [paraphrase]
  Errors: a backend that cannot be exercised is listed as unchecked, never as working.

## Boundaries

- No whole-branch review stage, gate or receipt. [paraphrase]
- No user-level or organisation-level config or criteria layer. [paraphrase]
- No `criteria.include` list or per-file ID namespaces in this change. [paraphrase]
- No change to the risk rule that decides which changes are reviewed. [paraphrase]
- Running an organisation's own review command is the command review backend's job (#592), not this spec's. [paraphrase]

## Decision Context

A dedicated `base..HEAD` stage would have caught the 23-task case, but so does the completion review once it is asked to look, at no extra dispatch. It would not clearly have caught the paging-loop case: each of those reviews saw its full diff, and the repeats were against code outside it, which is what R2 asks about.

A `criteria.include` list in the repository's config was held back until someone reports that a link or a pointing criterion is not enough.

## Parked unknowns

- Whether one coarse verdict per pointing criterion satisfies an audit that wants a verdict per rule; resolved by the issue's author trying the documented pattern.
