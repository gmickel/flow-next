# Hill-climb route (gated reference)

> **Loaded only when** the spec carries a `## Hill-climb pre-registration` section, or its goal is one metric moved against a target through repeated attempts (flow's hill-climb row). The worker reads it before the first change (worker Phase 1.5); on the bridged path the child is pointed at it. Other tasks never read it.

The loop runs inside the one task work mints for the spec. It replaces the single change of worker Phase 2: each kept attempt is its own Phase 3 commit, and review (Phase 4) runs once over the kept commits at the end. Attempts are serial, so each measurement compares against a known best. Hypotheses, profiles and the arithmetic are your judgment; flowctl adds no statistics engine and the harness is the user's command.

## 1. Pre-registration, before anything is measured

The spec states every value below as a bullet list under `## Hill-climb pre-registration`, with these exact labels:

```text
- Metric: <what is measured, with its unit>
- Direction: lower | higher
- Target: <the value that counts as done>
- Attempt floor: <minimum attempts before the run may stop on the target>
- Budget: <n> attempts | <n> minutes
- Harness: <command that measures the metric and checks the output is correct>
- Regression gate: <command that must stay green for a kept attempt>
- Runs per measurement: <N>
- Minimum detectable effect: <the smallest difference that counts>
```

A spec with a Quick commands section and no `Regression gate:` uses its Quick commands as the gate. Every other missing or placeholder field stops the route before any measurement: escalate `BLOCKED: SPEC_UNCLEAR` naming every missing field. Attended, work surfaces it as a question naming the field; unattended (`flow --auto`, `mode:autonomous`), it becomes `NEEDS_HUMAN` under work's existing rule. Capture or refine may draft the section; the target, the attempt floor and the budget are the human's values. Never invent, relax or reinterpret them, including when the budget runs out.

## 2. Measuring

Work in a run directory, `.flow/tmp/hill-climb/<spec-id>/` (gitignored), holding the ledger and a detached worktree of the current best commit (`git worktree add --detach <run-dir>/best HEAD`, moved to each new best).

One measurement is `Runs per measurement` runs of the harness per side, after warm-up runs that are discarded (three unless the harness discards its own). Baseline and candidate runs alternate (best, candidate, best, candidate...) so drift hits both sides alike; run the harness from the best worktree and from the working tree. Each side reports its median and its range (lowest to highest run). Medians and ranges are plain arithmetic, done by you or by the harness.

The effective minimum detectable effect is the larger of the pre-registered value and the width of the baseline's range. When that effect is larger than the gap between the baseline and the target, the instrument cannot resolve the goal: stop before any attempt and report it.

## 3. Prove the harness, then freeze it

Before the first attempt:

1. Measure the baseline and run the regression gate on the unchanged tree. A red gate here is a red baseline (worker Phase 1), not something the loop fixes.
2. Make a **known-worse** throwaway change (an injected delay, a duplicated step) and a **known-better** one (skip work the metric pays for), and measure each. The harness must rank worse, baseline and better in the right order, with every gap larger than the baseline's range.
3. Make a change that produces a **wrong output** (a wrong value, a skipped result). The harness must reject it: a non-zero exit or a failed output check, never a score. A harness that scores a wrong output would reward a change that skips the work.
4. Revert every probe, confirm a clean tree, and freeze: record the harness command and a `sha256` of the harness files and any inputs it reads in the ledger header.

A failed ranking, gaps inside the noise, or a harness that accepts a wrong output means no attempts run. Attended, revise the harness or the workload with the user; unattended, `BLOCKED: SPEC_UNCLEAR` becomes `NEEDS_HUMAN`. Re-check the hash before every measurement. A changed harness or input invalidates earlier measurements: record a `break` row in the ledger, then repeat this section against the current best (baseline, probes, wrong-output check, new hash) before the next attempt.

## 4. One attempt

Read the ledger before each attempt, so a refuted idea is never retried unchanged. Then:

1. **Pick a hypothesis from a family the evidence supports.** A family earns an attempt only when a profile or trace shows its signal (an import-time profile, a sampling profile, a trace, a syscall count). The families:
   - **delete** work nobody consumes;
   - **defer** work off the measured path until something needs it;
   - **reuse** results for identical inputs, naming what invalidates them;
   - **coalesce** many small calls that each pay a fixed overhead;
   - **shrink** the input the cost scales with;
   - **parallelise** independent units onto idle cores;
   - **represent** differently: a cheaper data structure or algorithm;
   - **move** work nobody waits for off the waited path;
   - **lighten** heavy dependencies that dominate startup;
   - **tune** the environment (interpreter flags, caches, pools).

   Name the specific mechanism, not just the family ("the YAML parser loads at startup but only `export` uses it").
2. **Make one change** for that one hypothesis. Never stack a second change on an unmeasured one.
3. **Measure** the candidate against the current best (section 2).
4. **Apply the keep rule.** Keep only when all four hold:
   - the candidate's median beats the best's by at least the effective minimum detectable effect, in the pre-registered direction;
   - the candidate's range does not overlap the best's;
   - one fresh replicate measurement clears the same two bars;
   - the regression gate is green.

   Anything less is `inconclusive` (inside the noise) or `reverted` (worse, or a win that breaks the gate), and both are reverted.
5. **Kept:** commit it as exactly one commit. The tree was clean before the attempt, so the worker's `git add -A` stages only the attempt's files (the ledger lives in the gitignored run directory). Subject: `perf(<scope>): <mechanism> (hill-climb attempt <n>)`. Move the best worktree to the new commit.
6. **Not kept:** restore the files the attempt touched and remove the files it created, then check `git status --porcelain` is empty. A revert that does not restore a clean tree stops the run: every later measurement would be meaningless.
7. **Write one ledger row**, whatever the verdict.

## 5. The ledger

`<run-dir>/ledger.md` starts with the pre-registration, the harness proof and the frozen hash, then one row per attempt:

```text
| # | Family | Mechanism | Change | Before (median, range) | After (median, range) | Delta | Gate | Verdict | Reason | Commit |
```

`Verdict` is `kept`, `reverted` or `inconclusive`. Rows that are not attempts carry `-` in `#`: a `break` (the harness changed and was proven again), a `pivot` (a plateau changed the family or triggered a re-profile, with the reason), or a `review-fix` (section 7).

## 6. Stop rules

Stop only when one of these holds, and record which:

- the target is met **and** the attempt floor is reached (one lucky early win does not end the run);
- the budget is spent;
- every family the profile supports has been tried;
- the harness breaks (it fails on the unchanged best, or cannot be restored): stop at once.

Three non-kept attempts in a row are a plateau, not a stop. Change the hypothesis family, combine near misses into one new hypothesis, or re-profile, and write the pivot into the ledger.

When the run stops with the target unmet, the task still completes honestly: the record reports the gap, the target's criterion stays unverified and is never marked satisfied, and under `flow --auto` the draft PR carries the gap. Before review, add the outcome to the task's description (`flowctl task set-description`): the stop rule, the gap, and that the target criterion is reported unverified. Review then judges the kept commits and the record; a finding that only restates the unmet target is answered from the record, never with attempts past the budget.

## 7. Verify, then record

Before `flowctl done`, check the range `$(cat .flow/tmp/base_commit)..HEAD` against the ledger:

- every attempt has exactly one row, and the row count matches the attempts made;
- every kept row names exactly one commit, and that commit touches only the attempt's files;
- no commit in the range changes measured code without a kept row. Setup before the loop, such as adding the harness, is named in the record. A review fix that changes measured code gets a `review-fix` row: it is measured against the best like an attempt and kept only when its median is not worse by the effective minimum detectable effect and the gate is green;
- the final value is measured at the final head, after any review fix, and the regression gate is green there.

A missing row, an unmeasured change, or a kept change spread over several commits fails this check; fix the record or the history before done.

Add this block, then the full ledger table, to the done summary. Every line is present; a value that cannot be shown reads `unverified: <reason>` rather than being left out. make-pr summarizes it in the PR briefing; the full ledger stays with the task.

```text
Hill climb:
- metric: <metric> (<direction> is better); target <target>
- baseline: <median> (<range>) | final: <median> (<range>) at <sha> | change: <signed percent>
- attempts: <n> (kept <k>, reverted <r>, inconclusive <i>); floor <f>; budget <b>
- kept commits: <sha> <subject>; ... (in order)
- harness: <command>, sha256 <hash>; proof: worse <median>, baseline <median>, better <median>; wrong output rejected (<how>)
- gate: <command> green | red at <final sha>
- stop: <which stop rule>
- target: met | unverified (<gap>)
- best untried: <mechanism> (<family>)
```

Pass the harness and gate commands to `done` as `--test` lines, plus one line summarizing the ledger: `--test "hill-climb ledger: <n> attempts (kept <k>, reverted <r>, inconclusive <i>); <baseline> -> <final>"`.

When memory is enabled, add one knowledge entry for each mechanism that proved out or proved useless on this codebase (`flowctl memory add --track knowledge --category best-practices`, with the module and the measured delta), so the next climb starts from it.

## Worked example

A spec asks to cut `mycli --version` cold start below 120 ms, with an attempt floor of 6, a budget of 20 attempts, 15 runs per measurement, and a pre-registered minimum detectable effect of 30 ms.

The baseline, after 3 discarded warm-ups, reads a median of 410 ms, range 395 to 430 ms, so the effective minimum detectable effect is 35 ms (the range width beats the 30 ms floor). To prove the harness, a 40 ms sleep reads 450 ms, a throwaway change that skips plugin discovery reads 250 ms, and a change that prints the wrong version is rejected by the output check. The order is right and the gaps exceed 35 ms, so the harness is frozen with its hash and the unit suite is confirmed green as the regression gate.

Attempt 1, **defer**: an import profile shows the HTTP client and the YAML parser load at startup, but only two subcommands use them. Moving those imports inside the subcommands reads 290 ms (280 to 300). It clears the bar, a replicate reads 292 ms, the gate is green, and it is kept as one commit.

Attempt 2, **reuse**: caching the plugin registry to disk reads 284 ms against the best of 290 ms. That is inside the noise, and the cache adds invalidation logic: inconclusive, reverted, reason logged. Attempts 3 and 4 try two more reuse ideas and are reverted too. Three non-kept attempts in a row is a plateau, so the agent re-profiles instead of stopping, and writes the pivot into the ledger.

The new profile shows 150 ms spent scanning package entry points. Attempt 5, **lighten**: a metadata lookup filtered to one entry-point group reads 160 ms. Kept. Attempt 6, **delete**: removing an unused startup telemetry probe reads 112 ms. Kept.

The target is met and six attempts have run, so the loop stops. The PR shows 410 ms to 112 ms (a 73% reduction), 6 attempts with 3 kept and 3 not kept, the three kept commits in order, the harness proof, the green gate on the final head, and the best idea not yet tried.
