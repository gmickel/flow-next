# Four new attended routes and a visual-parity pin

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 0% [user], 70% [paraphrase], 30% [inferred] -->

Attended `/flow-next:flow` routes intake from its shared matrix. Four kinds of request reach it today with no row of their own, so flow either picks a row that starts the wrong work or answers ad hoc:

- **A captured artifact to explain.** Someone hands over a CPU profile, a performance trace, a heap snapshot or a crash dump and asks why. The slowness row assumes a fix is wanted and starts one; the read-only question row says nothing about reading an artifact.
- **The same agent mistake, again.** Someone says agents keep doing X. Today the correction is repeated by hand or lands as advice in memory or an instruction file, which the next agent can skip.
- **A change to text a model reads.** A prompt, a skill, an agent instruction or an LLM feature's system prompt changes, and the open question is whether behaviour actually improves. Today it ships on review alone; nothing measures it.
- **A diff whose risk should be proven.** Someone asks what a change could break. Implementation review is a gate on the change, not an answer to that question, and nothing asks for the one fact the change is safe because of, proven by running code.

The refactor row also pins behaviour only through tests, snapshots or an equivalence check; a UI restyle or styling-system migration has no visual pin.

This spec adds four matrix rows and one refactor-row clause, all attended. `flow --auto` never takes free text, so none of these rows can fire unattended; work they produce (a captured spec) runs unattended like any other spec.

Target user: the engineer at the terminal who hands flow an artifact, a complaint about repeated agent mistakes, a prompt change or a diff, and expects the right route without naming a skill.

## Architecture & Data Models
<!-- scope: technical -->

Every row uses the matrix's existing five columns (starting state, route, positive signal, safe skip or narrow, skip kind) and its existing reading rules. Rows are prose the conductor reads; no judge preset, flowctl verb, receipt field or label changes. Three rows are common enough for the main matrix; the prompt-change row is rarer and sits in the continuation file. [paraphrase]

### Row: a captured artifact to explain (diagnosis)

- **Route.** Load the artifact into a form that can be queried with tools the repo or host already has (the profiler's own export or CLI, `jq`, a throwaway SQLite table, the runtime's developer tools). Name what bounds the observed cost, or what holds the memory, or where the crash happened. Map findings to source and state any revision difference between the artifact and the checkout. A cause is confirmed only by a before-and-after pair or a reproduction; otherwise it is the strongest supported hypothesis and is called that. Quote from a sensitive dump only what the diagnosis needs. Write no fix, no `.flow/` file and no PR. End with `Next:` naming the route that would act on it (measured slowness, hill climb, or the defect route). [paraphrase]
- **Positive signal.** An artifact is handed over together with a why or what question. [paraphrase]
- **Safe skip.** The person asks for the fix itself: route to the slowness or defect row and use the artifact as its baseline evidence. Skip kind: signal absent. [inferred]

### Row: the same mistake, again (hardening)

- **Route.** Collect the mistake class from evidence: commits and reverts, review threads, memory entries, and comments that exist to excuse a workaround. A class counts once it has two recorded occurrences. Then capture a spec with one R-ID per class whose acceptance is "this check fails on the recorded past occurrence", and let work and review build it. Each class is fixed at the highest level of the hardening ladder that works (below). [paraphrase]
- **Positive signal.** "Agents keep doing X", the same correction given twice, or the same review remark on two pull requests. [paraphrase]
- **Safe skip.** One occurrence is a defect or a direct change, not a class. A lesson already re-taught in memory routes to audit's Harden path, which reads the same ladder. Skip kind: signal absent. [inferred]

### The hardening ladder (one shared reference)

One reference, read by the hardening row and by audit's Harden path, replaces Harden's current lint-then-CI-then-instruction list so the ladder exists in one place: [paraphrase]

1. **Remove the opening.** One owner per piece of state; one supported way to do the task; internals that cannot be imported from outside their module; one list with every other copy derived from it, or a build failure when copies disagree; the old way an agent would copy deleted. [paraphrase]
2. **Make the bad state unwritable** with the type system where the language has one. [paraphrase]
3. **A lint or CI check whose message names the fix** ("use `load_config()`; reading `os.environ` directly here bypasses validation"). When the pattern is already common, the check fails only when a change adds a new occurrence. [paraphrase]
4. **A behaviour test** that fails on the recorded occurrence. [paraphrase]
5. **Instruction text, last,** only for a class that needs judgment no check can encode, written with an example of the failure. [paraphrase]

Every new check is proven against a recorded past occurrence (checked out or replayed) and runs through the same command locally and in CI. An exception sits on the offending line with its reason, an expiry date and the approving person. [paraphrase]

### Prime pointer

When prime's history read shows a repeated class (the same review remark on two pull requests, a fix reverted and re-applied, a memory entry re-taught twice), its ranked next actions may name the hardening route. Prime itself still fixes agent readiness only. [paraphrase]

### Row: a prompt or skill change to measure (continuation file)

- **Route.** Use the repository's own eval harness when one exists. Otherwise build a small blinded one in scratch: one organic task prompt a real user might send; directory, file and prompt names that do not reveal the test; a rubric only the judge sees; baseline and candidate run with N draws each; one judge from another model family that sees outputs only by neutral label and scores both arms in one pass; grading from what the candidates did (transcripts, files, output), never from what they say they did. Before trusting the gap, check that every draw did the task and that the gap is larger than the run-to-run spread inside each arm. The verdict is `promote`, `do not promote` or `inconclusive`, with the evidence. A promoted change continues to work and review. Draws spend money and need credentials, so the route asks once for N and a budget before the first draw. [paraphrase]
- **Positive signal.** A change to text a model reads, where the question is whether it behaves better. [paraphrase]
- **Safe skip.** A wording fix with no behaviour claim is a direct change. A target score to push over many attempts is the hill-climb row, with this eval as its frozen harness. Skip kind: signal absent. [inferred]

### Row: what could this diff break (proven safety fact)

- **Route.** Read the change, including what it now does differently that the diff does not spell out. Find the one fact the change is safe because of; most risky-looking changes are safe because of a single fact, and proving it clears most cases at once. Look where text search stops: the dependency's own source at the pinned version, serialized formats and stored columns, feature flags, another language reading the same bytes, scheduling and teardown order. Prove the fact by running the real code in a small script or test, and in the running app when it is reachable. The answer gives what the change does, the safety fact and how far its proof got (stated, pointed at the line, walked through the failure, ran it, reproduced it in the app), each risk with its location, likelihood, cost and the check that would catch it, a separate list of what was checked and cleared, and the cheapest check to run before merging. Read-only: no fix, no `.flow/` write. Implementation review stays the gate. [paraphrase]
- **Positive signal.** "What could this break", "is this safe to merge", or a diff handed over with doubt about its reach. [paraphrase]
- **Safe skip.** A request to review the change routes to implementation review; a request to build routes to its own row. Skip kind: signal absent. [inferred]

### Refactor row: visual-parity pin

The refactor row's pin gains one clause: for a UI change meant to look the same (a restyle, a styling-system migration, a component swap), the pin is a set of baseline screenshots of named states captured before the change and compared by pixel diff, zero unless the person names a tolerance. The baseline is never regenerated or edited during the change; a baseline that looks wrong is reported, not fixed. [paraphrase]

### Trigger words

Flow's skill description names the four starting states in plain words, so the host loads flow for them without the person naming a skill. Existing trigger phrasings keep working. [paraphrase]

## Examples
<!-- scope: both -->

**Captured artifact.** A user drops `boot.cpuprofile` and asks why the desktop app takes six seconds to show its first window. The agent loads the profile into per-function rows: a synchronous directory walk takes 2.1 s and a settings-cache parse 1.4 s. The walk maps to the plugin loader scanning the whole user data folder; the profile shows thousands of per-file stat calls but only a handful of plugin loads, so the strongest supported hypothesis is an over-broad scan. The profile is two weeks old; the loader is unchanged since, the cache code is not, and the answer says so. Nothing is confirmed without a before-and-after pair. `Next:` the hill-climb route on first-window time. [inferred]

**Same mistake, again.** "Agents keep adding config keys without registering them in the schema." History shows two reverts and three review remarks on unregistered keys. The captured spec has one R-ID: settings are read only through one typed accessor generated from the schema, so an unregistered key does not compile; acceptance is that the old commit that added `retry_jitter` unregistered fails the build. The fallback, had no typed accessor been possible, is a CI check whose message reads "`retry_jitter` is not in settings.schema.json; add it there and read it through `settings.get()`". [inferred]

**Same mistake, fixed at the top of the ladder.** Two scripts and a test fixture each keep their own list of the files a release must copy, and agents adding a file update one list. The fix derives all three from one manifest and deletes the hand-kept lists; acceptance is that replaying the commit that added a file to one list only now fails the release smoke. [inferred]

**Prompt change.** A team rewrites the support bot's system prompt to stop it promising refunds. The repo has no eval harness, so the route asks for N and a budget, then builds a scratch harness: twelve organic customer messages, the rubric ("never promises a refund; offers the refund form when the order qualifies") held back from the candidates, five draws per arm per message, and a judge from another family that sees replies as `set-a` and `set-b`. Baseline promised a refund in 14 of 60 replies, candidate in 1 of 60, with every draw completing; both arms offered the form when due. Verdict `promote`, then work and review ship the prompt. [inferred]

**Diff risk.** A pull request swaps a cache's eviction from time-based to size-based. The safety fact is "only entries already past their expiry are evicted early; nothing reads an evicted entry without reloading it". The agent proves it with a script that fills the real cache past its size bound and asserts every read after eviction reloads from source (ran it). It lists one risk (a background job holds an entry reference across eviction, low likelihood, stale read for one cycle, caught by the job's integration test) and clears two (the serializer, unchanged; the metrics exporter, reads counts only). [inferred]

**Visual parity.** Migrating buttons from hand-written CSS to the design-token system: the agent captures the settings, checkout and empty-cart states at two widths before touching styles, migrates, and compares; the checkout state differs by 3 pixels of focus-ring offset, which is reported and fixed in the migration, never by recapturing the baseline. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- An artifact flow cannot read (unknown format, truncated, encrypted) is named as unreadable, with the export that would work or a live reproduction as the next route. [inferred]
- An artifact recorded at another revision: findings that depend on changed code are marked as such. [inferred]
- A repository with too little history for two occurrences: the request is treated as one occurrence. [inferred]
- A class no check can encode reaches instruction text with a failure example, and the answer says the class stays judgment-only. [inferred]
- The prompt-change route with no credentials or a declined budget designs the harness, records the verdict as not run, and reports no result. Without a judge from another family it says so, and the verdict is `inconclusive`. [inferred]
- A safety fact that cannot be proven without production or live shared state stops at the highest proof level reached and is called unproven. [inferred]
- None of the rows change the route of any existing starting state. [paraphrase]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The matrix has a row for a captured artifact to explain, routing to a read-only diagnosis that writes no fix, `.flow/` file or PR and ends with a `Next:` route; a request for the fix routes to the slowness or defect row instead. Errors: unreadable artifact → named unreadable with the next route; revision mismatch → stated in the answer. [paraphrase]
- **R2:** The matrix has a row for a repeated mistake class, routing to capture of a spec whose R-IDs each require a check that fails on a recorded past occurrence. Errors: one occurrence → no class, routed as a defect or direct change; a lesson already in memory → audit's Harden path. [paraphrase]
- **R3:** One hardening-ladder reference is read by the hardening row and by audit's Harden path; Harden's previous lint-first list is removed, not kept beside it. Errors: a class with no enforceable form → instruction text with a failure example, reported as judgment-only. [paraphrase]
- **R4:** Prime's ranked next actions name the hardening route when its history read shows a repeated class, and nothing changes when it does not. No error surface beyond an unreadable history, which leaves the pointer out. [paraphrase]
- **R5:** The continuation file has a row for a prompt or skill change to measure, using the repository's harness when one exists, else a blinded scratch harness, and returning `promote`, `do not promote` or `inconclusive` with evidence; it asks once for N and a budget before any draw. Errors: no credentials or declined budget → verdict not run, no result reported; no cross-family judge → `inconclusive`, stated. [paraphrase]
- **R6:** The matrix has a row for a diff whose risk should be proven, answering read-only with the safety fact and its proof level, risks, a cleared list and the cheapest pre-merge check. Errors: proof needs live or production state → stops at the highest level reached, marked unproven. [paraphrase]
- **R7:** The refactor row's pin covers UI parity through baseline screenshots and a pixel diff that is never satisfied by changing the baseline. Errors: a baseline that looks wrong → reported, not regenerated. [paraphrase]
- **R8:** Flow's description names the four starting states; a trigger probe shows the new phrasings load flow and the existing phrasings still do. No error surface beyond the probe. [paraphrase]
- **R9:** A routing-accuracy study run with the new starting states added routes them correctly, every existing starting state keeps its route, and the routing tests (matrix links resolve) pass. No error surface beyond the study's own verdict. [paraphrase]
- **R10:** The flow-next.dev route pages describe the four rows and the visual pin with one short example each. No error surface. [inferred]

## Boundaries
<!-- scope: business -->

- Attended only; no change to `flow --auto`, pilot snapshot selection or its stage set. [paraphrase]
- No new judge kind, label, enum, receipt field, validator rule, flowctl verb or skill. [paraphrase]
- The diagnosis and diff-risk rows never edit code; the prompt-change row never spends on draws without the one-time ask. [paraphrase]
- No resident list of named principles and no requirement to cite principles in replies. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

On 2026-10-15 the maintainer chose separate matrix rows for these routes rather than sentences inside existing rows, judging that new routes make the router more capable. The same day STRATEGY.md's "Agent first" principle and G4 were amended to say so: a row describing a new starting state is guidance the agent reads while routing, adds no field, check or stop, and is judged by whether requests route correctly (R9). [paraphrase] Each row prevents a misroute: an artifact starting a fix nobody asked for; a repeated mistake answered with more skippable advice; a prompt change shipped with no behaviour measurement; a risk question answered by a review gate instead of a proven fact. [inferred]

fn-269 (diagnose a captured profile, trace or dump) is superseded by R1. Its 2026-09-28 trim removed a new judge kind, mandatory confidence labels with a failing check, and a row; this spec keeps the first two removed and restores only the row. fn-269 closes as superseded when this spec is ready. [paraphrase]

Rejected: a row for taking over another agent's in-flight work. A branch with a spec already resumes through its spec, a branch without one already routes on intent (capture to make it a spec, or the row that fits the remaining work), and work already treats an inherited trail as authoritative and its pass or fail claims as unproven. [paraphrase]

Delivery order: 1 of 6 in this set (router rows, defect discipline, measured numbers, worker effort, land catch-up, focused QA re-check). Route: direct. [paraphrase]

## Strategy Alignment

Follows the **Agent first** design principle as amended on 2026-10-15: every route is guidance the agent applies, with no field to fill. The hardening row serves the **Self-improving through normal work** track, turning repeated corrections into checks instead of advice. The rows extend the approach line that attended flow "reads whatever the user has".

## Strategy Conflicts

None found.
