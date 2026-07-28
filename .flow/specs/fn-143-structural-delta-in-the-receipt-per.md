# fn-143 Structural delta in the receipt: per-module erosion and verbosity trend

## Goal & Context
<!-- scope: business -->

Receipts prove the change works. They say nothing about what the change did to the structure it touched, and a test suite structurally cannot tell you. [SlopCodeBench](https://arxiv.org/html/2603.24755v1) (Orlanski et al., Mar 2026) is the measurement: agents extending their own prior code degrade structural quality in 80% of trajectories and verbosity in 89.8%, and the divergence from maintained human code widens every iteration while human repositories plateau. The failure is invisible to pass rates by construction - one benchmark function grew from 84 lines and CC 29 to 1,099 lines and CC 285 across eight checkpoints with the tests still passing.

Flow-Next holds something no other tool does: `.flow/` already contains the **ordered sequence of completed specs per module**. The trajectory that the benchmark had to build an entire Docker harness to observe is reconstructable from our own history. This spec turns that latent advantage into a recorded number, so that "when did this module start getting harder to change" is answerable from git rather than from memory.

What this is: two deterministic measures, computed on the surface a change touched, stored per module, reported as a **trend**, and surfaced in the receipt and the PR. What this is not: a score, a gate, or a target.

## Architecture & Data Models
<!-- scope: technical -->

**The two measures**, both from the paper so they are comparable to published readings:

```
mass(f)   = CC(f) * sqrt(SLOC(f))
erosion   = sum(mass(f) for f where CC(f) > 10) / sum(mass(f) for all f)
verbosity = |flagged_lines UNION clone_lines| / LOC
```

Erosion catches new logic being patched into existing functions rather than distributed. Verbosity catches growth that adds nothing. The CC > 10 cutoff follows Radon's bands; keep it, so our numbers sit on the same axis as the paper's human panel (erosion 0.31, verbosity 0.15) and its agent panel (0.68 / 0.33).

**Two design calls that decide whether this is signal or noise:**

1. **Scope to the touched surface, not the repo.** Repo-wide aggregates hide exactly the inflection the paper found at checkpoint 3, where new requirements start fighting the initial design. Measure the files the change touched.
2. **Slope over level.** A single reading is close to meaningless; the direction of travel across the sequence of specs that touched the same module is the whole signal. This forces a **per-module cumulative store**, not a per-PR isolate.

**Components:**

- **Analyzer** - computes the two measures for a file set. Needs per-function CC and SLOC, plus duplicate detection.
- **Store** - `.flow/quality/<module-key>.json`: append-only readings keyed by spec id and commit, so the trajectory survives rebases and reads back in order.
- **flowctl surface** - `quality measure <paths>`, `quality record --spec <id>`, `quality trend <module-key>`.
- **Receipt integration** - the delta rides in the existing evidence JSON at task done, additive and optional.
- **PR integration** - `export-cognitive-aid` gains the module trend so the PR body can show direction of travel, not an absolute.

**The dependency-policy question this spec must answer first (see Decision Context).** `flowctl` is pure-stdlib by promise, and per-function CC across TypeScript, Go, Rust, C# and Java is not a stdlib problem. Three candidate routes, the recommendation being route 1:

1. **Optional external analyzers when present** (radon / lizard / ast-grep), degrading to a loud `not_measured` otherwise. Precedent: RepoPrompt, Codex, Copilot and Cursor are already optional external CLIs. Cost: absent on many enterprise repos, which is where it matters most.
2. **Stdlib language-agnostic proxy** (branch-token counting plus normalized duplicate-line hashing). Universal and scientifically weak. Publishing a weak measure as a quality signal is the exact Goodhart failure we warn portcos about.
3. **Out of core**, as an opt-in hook.

## API Contracts
<!-- scope: technical -->

```
flowctl quality measure <path>... [--json]
  -> {status: measured|not_measured, reason?, files: N,
      erosion: float|null, verbosity: float|null, analyzer: <name@version>|null}

flowctl quality record --spec <spec-id> --paths <path>... [--json]
  -> appends a reading to .flow/quality/<module-key>.json; idempotent per (spec, commit)

flowctl quality trend <module-key> [--last N] [--json]
  -> {readings: [...], direction: rising|flat|falling|insufficient_data,
      span: {from_spec, to_spec, n}}
```

Evidence JSON gains an optional sibling of the existing test/commit fields:

```
structural_delta:
  status: measured | not_measured
  reason: <why, when not_measured>
  before: {erosion, verbosity} | null
  after:  {erosion, verbosity} | null
  analyzer: <name@version> | null
```

**Contracts that must hold:**

- `not_measured` is a first-class, loud state. It is never rendered as zero, never omitted silently, never imputed.
- Absence of `structural_delta` on an older evidence file is valid and reads as "not asked".
- `direction: insufficient_data` until there are at least three readings for the module. Two points are not a trend.
- No command in this spec returns a pass/fail, and no exit code encodes quality.
- The analyzer name and version are recorded with every reading; readings from different analyzers are never compared as one series.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Pure-stdlib promise.** Whatever route wins, the base install must keep working with zero external dependencies, and the README requirements line must stay true.
- **Cross-platform.** Windows path handling and the `py` launcher path both covered; the store must round-trip byte-identically (CRLF discipline as in the memory-rewrite work).
- **Module key stability.** Renames and moves must not silently start a new series; key derivation needs an explicit, tested rule and a documented behavior on rename (carry forward vs restart).
- **Rebase and squash.** Readings keyed by spec id survive a squash even when the commit sha changes; keying only by sha would lose the series.
- **Generated and vendored code** must be excludable, or the numbers are dominated by things nobody maintains.
- **Cost.** Analysis runs on a touched file set, not the tree; it must not add meaningful wall-clock to `task done`. Measure it.
- **Never a gate.** No merge block, no CI failure, no threshold. If a future spec wants a gate, that is a separate decision with its own evidence.
- **Never a target.** The paper's own author found a majority of generated lines tripping at least one static rule and most of 41 metrics failing to separate models. Rendering must present direction, not a grade.
- **No dashboard.** Nothing in this spec exports to a leadership-visible scoreboard.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `flowctl quality measure` returns erosion and verbosity for a Python file set, matching the paper's formulas (verified against a hand-computed fixture).
- **R2:** For a language with no available analyzer, the command returns `status: not_measured` with a reason, exit code 0, and no null-as-zero rendering anywhere.
- **R3:** `flowctl quality record` appends a reading keyed by (spec id, commit) and is idempotent under re-run.
- **R4:** `flowctl quality trend` reports `insufficient_data` below three readings and a direction at or above three.
- **R5:** Readings carry `analyzer` name and version; a series mixing analyzers is reported as separate series, never merged.
- **R6:** Evidence JSON at task done carries `structural_delta` when measurable and `not_measured` with a reason otherwise; older evidence files without the field remain valid.
- **R7:** Module key derivation is documented and tested, including the rename case.
- **R8:** A reading survives a squash merge (spec-id keying proven by test, not asserted).
- **R9:** Generated and vendored paths are excludable via config, with a tested default.
- **R10:** Measured overhead added to `task done` on a representative touched-file set is recorded in the evidence, with a stated ceiling.
- **R11:** The base install has zero new required dependencies; the README requirements line remains accurate.
- **R12:** No command added by this spec can fail a build, block a merge, or return a non-zero exit code on a quality reading.
- **R13:** `export-cognitive-aid` exposes the module trend as direction plus span, never as a bare number or grade.
- **R14:** Windows CI green, including store round-trip byte-identity.
- **R15:** Docs state the honest limit: these measures are repeatable, and their link to "this codebase is easy to change" is not established - directional signals only.
- **R16:** The claim sentence shipped by fn-142 is narrowed in the same pass that ships this, from "does not prove" to "records the delta", across all surfaces that carry it.

## Boundaries
<!-- scope: business -->

- **No gate, no score, no threshold, no dashboard.** Explicitly and permanently out of scope for this spec.
- **No plan-review prose changes.** fn-142 owns that and ships independently.
- **No canary / weak-model extension test.** fn-144, deferred.
- **No public benchmark run and no readiness-trigger page.** Declined (Gordon, 27 Jul 2026).
- **No cross-repo or cross-portco aggregation.** Per-repo only; aggregation is a product decision nobody has made.
- **Not a replacement for review.** The measure informs the human at merge; it never stands in for reading the change.

## Decision Context
<!-- scope: both -->

**The open decision this spec must close before implementation: the analyzer dependency route.** Recommendation is route 1 (optional external analyzers, loud `not_measured` fallback), because a missing measurement is honest and a bad measurement is not, and because the optional-external-CLI pattern is already established for review backends. Route 2's universality is a trap: shipping a weak proxy as a quality signal is precisely the Goodhart failure this project warns portcos about, and it would be quoted back at us. Route 3 keeps core clean but guarantees nobody turns it on. Decide explicitly at plan, record the choice here, and note that route 1 makes the feature's value uneven across languages - stated up front rather than discovered.

**Why the paper's exact formulas rather than our own.** Comparability. Using `CC * sqrt(SLOC)` with the CC > 10 cutoff puts our readings on the same axis as a published human panel (erosion 0.31, verbosity 0.15) and agent panel (0.68 / 0.33), which turns a local number into a calibrated one. Inventing a variant would forfeit that for no gain.

**Why per-module cumulative storage rather than per-PR.** The signal is the slope. Per-PR isolates cannot express it, and the sequence of specs that touched a module is already in `.flow/` - this is the one place the architecture hands us the benchmark's own protocol for free.

**Why advisory and never a gate.** The link from either measure to real changeability is unestablished, most of the benchmark's metrics failed to separate models, and its own author reads the majority-of-lines-flagged result as the ruleset being partly over-aggressive. A gate on a measure that weak converts review rounds into ceremony. The human at merge is the decision-maker; this gives them a trend they did not have.

**Why not ask a model to judge maintainability instead.** The paper's logic settles it: a model that could reliably distinguish good structure from bad would have produced the good structure. Deterministic and weak beats judged and circular.

**Source:** [[Agentic SDLC - SlopCodeBench (Orlanski et al., Mar 2026)]]; paper arXiv 2603.24755v1, formulas in section 2.3, human calibration in table 2.
