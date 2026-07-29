---
satisfies: [R4, R8, R10, R11, R12]
---
# fn-148-eval-two-spec-prose-candidates-measured.3 Paired replication, pre-registered verdict, report + closeout

## Description
Paired replication of the screen's candidate (>=3 draws/cell), run the pre-registered rule ONCE, write the report, close out. All in ~/work/agent-evals; this repo gets only the spec closeout.

**Size:** M

### Approach

- Replication cells per PREREGISTER.md; analyzer refuses a verdict until all cells complete (analyze_paired.py pattern); no per-feature peeking or early stop.
- Verdict is whatever the rule returns: CONFIRMED / NOT CONFIRMED / INCONCLUSIVE. Report by-shape breakdown (R12, the standing bug-shape hypothesis from studies/NEXT.md).
- REPORT.md leads with the verdict; publish all draws; update agent-evals README study table.
- Closeout is a report + HUMAN HANDOVER, never an autonomous template edit (R11). NULL or INCONCLUSIVE -> recommend closing fn-148 with the outcome recorded as the result (R10). CONFIRMED -> the report carries the exact winning guidance prose as a ready-to-apply diff against `plugins/flow-next/templates/spec.md` plus its measured cost, and STOPS for the human go/no-go. On "go" the diff is applied directly (dual-copy `.flow/templates/spec.md`, sync-codex x2, CHANGELOG Unreleased, docs touchpoints) - the evidence is the justification; no further spec is authored.
- No public comparison copy on any surface; no upstream project named in anything that ships.

### Key context

INCONCLUSIVE (effect real but within draw noise) is a reportable outcome, not a failure to explain away. Within-cell spread was 4/13 questions last time; assume similar noise.

## Acceptance
- [ ] >=3 draws per cell for baseline and candidate on every fixture; all published
- [ ] Pre-registered rule executed once, complete cells only; verdict quoted verbatim in REPORT.md
- [ ] By-shape (bug vs greenfield) breakdown reported, addressing the standing hypothesis
- [ ] Report ends in an explicit human handover: null/inconclusive recommends close-with-no-change; confirmed carries a ready-to-apply template diff + measured cost and stops for go/no-go - no template edit happens without the human's go
- [ ] agent-evals README study table updated; no comparative/public claims anywhere


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
