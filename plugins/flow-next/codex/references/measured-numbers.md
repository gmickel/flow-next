# Measured numbers (gated reference)

> **Read only when** a route reports a number someone will act on: a measured slowness moved
> once (the baseline and the post-change measurement), the hill-climb loop (when setting up its
> harness and before its final claim), or a prompt or skill eval's verdict. Other routes never
> read it.

A fast-looking number is the easiest false claim to make. Before a number is reported or acted
on, answer these from a real run, not from reading code:

1. **What bounds it.** Name the limiter: what the run waits on (a core, a lock, the disk, the
   network, an external service, the load generator itself), from a profile or system counters
   taken during a run and mapped to the source that spends it. A guess from reading code is not
   a limiter. Profilers slow the work, so take the limiter from a run you do not report.
2. **What else it could be measuring.** List the alternatives and rule each out with evidence:
   errors or early returns that finish fast; cached or skipped work (a warm cache on one side
   and a cold one on the other, a result memoised between runs); code that never ran inside the
   timed region; one side on default, debug or per-item settings; noise; a piece too small to
   matter end to end.
3. **Whether it is possible.** Do the arithmetic. Removing a piece saves at most its share of the
   run, and nothing goes faster than the limiter allows. A 40% gain from removing a piece that
   takes 10% of the run measured something else: find what before reporting.
4. **That the work happened.** Inside the timed region, requests reached the server, rows were
   written, lazy results were consumed. Count errors and units of work on every side.
5. **Repetition.** Run each side at least five times, alternating, and report the median and
   range. A gap inside the run-to-run spread is no measurable difference. On a busy machine,
   interleaving keeps both sides under the same noise; say so in the record.
6. **Tuning.** Run every side the way production runs it: release builds, production settings,
   batching, and caches warm or cold the way users meet them. With one side untuned, pick no
   winner.

## Verdicts

A measured claim reads `faster`, `slower`, `no measurable difference` or `inconclusive`, with its
run count, range and limiter. It is `inconclusive` whenever the limiter is unnamed, a side ran
untuned, or errors and work done were not checked.

- **A metric you cannot profile** (an external service, a hosted judge): the limiter is
  `unknown`, and the verdict is `inconclusive` unless the gap is far outside the spread and the
  arithmetic holds; the record says which.
- **A ballpark the person asked for** is one run. It still checks errors and that the work
  happened, and says it is one run.
- **An eval verdict** asks the same questions of its draws: count the draws on each side that did
  the task, and check the gap holds draw by draw (per message or case), not only in the total.
  The verdict carries the completion count.

## Record

Write the line after measuring, in the done summary or the hand-back:

```text
- measured: <metric> <before> -> <after>, median of <n> runs per side, range <lo>-<hi> after; limiter: <what bounds it>; errors <n> both sides; work <units> both sides; verdict: <verdict>
```

Example: two storage engines are compared for a bulk import, and one is four times faster. The
profile shows the slower side waiting on a disk flush after every row, which is a setting
(commit per row), not the engine. The first line reads `verdict: inconclusive: untuned side
(commit per row)`; with both sides batching commits the gap is 6%, inside the spread over seven
alternated runs, and the line reads `verdict: no measurable difference`.
