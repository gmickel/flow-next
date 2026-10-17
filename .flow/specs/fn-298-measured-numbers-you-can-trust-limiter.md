# Measured numbers you can trust: limiter, errors, work done

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 0% [user], 60% [paraphrase], 40% [inferred] -->

Three routes end in a number someone will act on: the one-off slowness route (baseline, change, post-change measurement), the hill-climb loop, and the prompt-change route's eval result. The hill-climb loop already freezes a proven harness, alternates runs and rejects wrong output; the slowness route has none of that, and none of the three asks the questions that catch a fake win:

- **What bounds the number?** Without naming the limiter (a core, a lock, the disk, the network, the load generator itself) nobody knows what was measured, or why a change did not move it. [paraphrase]
- **What else could it be measuring?** Errors that return fast, cached or skipped work, code that never ran inside the timed region, one side left on default settings, noise, or a piece too small to matter end to end. [paraphrase]
- **Is it even possible?** A 40% gain from removing a piece that takes 10% of the run is past what arithmetic allows, so it measured something else. [paraphrase]

The loop's hypothesis families are also unordered, so attempts start wherever the agent's eye lands instead of with the cheapest idea that could meet the target. [paraphrase]

Target user: whoever reads the PR or the eval verdict and has to decide whether the number is real. [inferred]

## Architecture & Data Models
<!-- scope: technical -->

- **One measured-number reference, read by three routes.** A gated reference holds the checks below. The slowness row, the hill-climb loop (at harness setup and at the final claim) and the prompt-change row (for its eval verdict) read it; nothing else does, so no always-loaded surface grows (G1). [paraphrase]
- **The checks.** Before a number is reported or acted on: name the limiter from a profile or system counters taken during a run, mapped to source (a guess from reading code is not a limiter); list what else the number could be measuring and rule each out with evidence; do the share-of-run and resource arithmetic; confirm the work happened inside the timed region (requests reached the server, rows were written, lazy results were consumed); run each side at least five times alternating, and report median and range, treating a gap inside the run-to-run spread as no measurable difference; run every side the way production runs it, or pick no winner. [paraphrase]
- **Verdicts.** A measured claim reads `faster`, `slower`, `no measurable difference` or `inconclusive`. It is `inconclusive` when the limiter is unnamed, a side ran untuned, or errors and work done were not checked. A quick ballpark the person asked for is one run, still checks errors and that the work happened, and says it is one run. For an eval result the same questions apply to the draws: did every draw do the task, and does the gap hold across draws. [paraphrase]
- **Hill-climb harness counts.** The frozen harness prints an error count and a count of work done next to the metric, so every keep-or-revert checks both without extra steps; a faster number with fewer units of work is rejected like a wrong output. [paraphrase]
- **Hill-climb harness proof on workloads.** The harness proof also runs contrasting realistic workloads: the chosen case must reproduce the complaint while easier cases separate as expected. When no case reproduces the complaint, the run fixes the reproduction before any attempt or stops and reports why. [paraphrase]
- **Cheapest idea first.** The loop orders its families by cost and stops as soon as an earlier one meets the target: do not do the work at all; do not do it again (reuse, cache); do less of it; do it later; do it where nobody waits; do it concurrently; do it cheaper (represent, tune, lighten). [paraphrase]
- **Records.** The hill-climb record and the slowness route's evidence line gain the limiter and the error and work counts; the prompt-change verdict gains the draw completion count. These are written after measuring. [inferred]

## Examples
<!-- scope: both -->

**Fake speedup caught.** "Export is 38% faster." The harness output for the candidate reads `median 410 ms (395-428), n=7, errors=0, rows=0`: the new code path returned early on an empty filter. Rejected as a wrong output; the ledger row reads `reverted (work=0)`. [inferred]

**Past the arithmetic.** Removing YAML parsing from startup claims a 30% faster cold start, but the profile shows parsing at 9% of startup; the most it can save is about 10%. The rerun shows the baseline had a cold disk cache and the candidate a warm one; alternated, the gain is 8.6% (median of 7, range 7.9-9.4). [inferred]

**Untuned side.** Comparing two databases for an import, one side commits per row. The limiter is the commit (fsync per row), a setting rather than the engine, so no winner is picked until both sides batch commits; the verdict for the first run reads `inconclusive: untuned side (commit per row)`. [inferred]

**Cheapest first.** A search page is slow because every keystroke re-ranks 40,000 rows. The first family tried is "do not do it again" (cache the ranking for an unchanged query prefix), which meets the target; "do it concurrently" is never needed. [inferred]

**Slowness evidence line.**

```text
- measured: p50 41 ms -> 33 ms, median of 7 runs per side, range 32-35 ms after; limiter: JSON parsing on one core; errors 0 both sides; work 60,000 rows both sides; verdict: faster
```

[inferred]

**Eval verdict.** A prompt change scores 58 of 60 against 46 of 60, but two candidate draws stopped before finishing; with completion checked, 56 of 58 completed draws pass against 46 of 60, the gap holds in each of the five draws per message, and the verdict is `promote`. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- A metric that cannot be profiled (an external service, a hosted judge) names the limiter as unknown and the verdict as `inconclusive` unless the gap is far outside the spread and the arithmetic holds; the record says which. [inferred]
- A busy machine: both sides are interleaved so they see the same noise, and the record says so. [paraphrase]
- Profilers slow the work, so the limiter comes from a run that is not reported. [paraphrase]
- The hill-climb loop's existing proof, freeze, ledger and stop rules are unchanged; this spec adds to them. [paraphrase]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** One gated measured-number reference holds the limiter, alternatives, arithmetic, work-happened, repetition and tuning checks and the four verdicts, and is read by the slowness row, the hill-climb loop and the prompt-change row only. Errors: unprofilable metric → limiter unknown, `inconclusive` unless the gap and arithmetic carry it, recorded. [paraphrase]
- **R2:** A reported measured claim on these routes carries one of `faster`, `slower`, `no measurable difference` or `inconclusive`, with run count, range and limiter; `inconclusive` whenever the limiter is unnamed, a side ran untuned, or errors and work done were unchecked. Errors: ballpark asked for → one run, labelled one run, errors and work still checked. [paraphrase]
- **R3:** The hill-climb harness prints error and work counts with the metric, and a candidate with fewer units of work or any new errors is rejected like a wrong output. No error surface beyond the existing harness-break rule. [paraphrase]
- **R4:** The hill-climb harness proof runs contrasting realistic workloads, and a run whose cases do not reproduce the complaint fixes the reproduction or stops before any attempt. Errors: no reproducing case → stop with the reason recorded. [paraphrase]
- **R5:** Hill-climb attempts take families in cost order and stop at the first that meets the target and the attempt floor. No error surface beyond the existing stop rules. [paraphrase]
- **R6:** A new perf case in the maintainer's end-to-end comparison harness, with a planted trap (a warm cache or an untuned side), shows the change reports the trap rather than a speedup, and the existing cases show no longer time to the first hand-back against a same-time control. No error surface beyond the harness's verdict. [inferred]

## Boundaries
<!-- scope: business -->

- No new flowctl verb, receipt field or validator; the counts and verdicts are written after measuring. [paraphrase]
- No change to routes that do not report a measured number. [paraphrase]
- No profiler, benchmark library or statistics dependency added to flowctl. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

A fast-looking number is the easiest false claim an agent can make, and the checks that catch it are a handful of questions answered from a real run. [paraphrase] Putting them in one reference read by the three routes that report numbers keeps them out of every other run's context and avoids three drifting copies. [inferred]

Depends on the router spec (fn-296), whose prompt-change row this reference serves. Delivery order: 3 of 6 in this set. Route: direct. [inferred]

## Strategy Alignment

Follows the **Agent first** design principle: the checks are guidance and the counts are records written after measuring. Serves the evidence-over-narration discipline named under the **Autonomous mode** track.

## Strategy Conflicts

None found.
