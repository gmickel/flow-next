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
- Closeout: NULL or INCONCLUSIVE -> close fn-148 with the outcome recorded as the result (R10). CONFIRMED -> author a follow-up spec in flow-next proposing the template prose change with its measured cost (R11) - do NOT edit the template in this spec.
- No public comparison copy on any surface; no upstream project named in anything that ships.

### Key context

INCONCLUSIVE (effect real but within draw noise) is a reportable outcome, not a failure to explain away. Within-cell spread was 4/13 questions last time; assume similar noise.

## Acceptance
- [ ] >=3 draws per cell for baseline and candidate on every fixture; all published
- [ ] Pre-registered rule executed once, complete cells only; verdict quoted verbatim in REPORT.md
- [ ] By-shape (bug vs greenfield) breakdown reported, addressing the standing hypothesis
- [ ] Null/inconclusive: fn-148 closed with outcome recorded, zero flow-next changes; confirmed: follow-up spec authored with measured cost, template untouched here
- [ ] agent-evals README study table updated; no comparative/public claims anywhere


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
