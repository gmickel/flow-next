<!--
To customize for your project, copy this file to `<repo-root>/SPEC.md` and edit there.

Discovery cascade (first match wins):
  1. <repo_root>/SPEC.md           (your customized scaffold — uppercase preferred)
  2. <repo_root>/spec.md           (lowercase honored when uppercase absent)
  3. bundled ${PLUGIN_ROOT}/templates/spec.md  (this file — canonical source of truth)
`flowctl spec create` and `flowctl spec skeleton` render this file through the same cascade (frontmatter stripped).

Customizing: adding sections and rewriting the guidance prose under any heading is
free. Renaming or removing `## Acceptance Criteria`, `## Boundaries`,
`## Goal & Context` or `## Decision Context` does NOT error - it silently degrades
the features that parse them (R-ID coverage, PR "Not in this PR", the PR
briefing's context and decision excerpts).

/flow-next:capture writes the sections this file names and adds none it leaves out.
Auxiliary sections are named in the frontmatter `auxiliary_sections` list. Drop an
entry (e.g. `Conversation Evidence`, which no tool reads) and captured specs stop
carrying it. A SPEC.md with no such list gets no auxiliary sections.

Full guide:
flow-next docs, "Customizing the scaffold for your project"
(https://flow-next.dev/guides/spec-scaffold/).
-->

<!--
SCOPE DISCIPLINE (YAGNI — applies to the whole spec):
Specify the smallest system that satisfies the request. Every R-ID traces to
the request; every task traces to an R-ID. Capabilities the request never
asked for are not scope — name them in ## Boundaries as out-of-scope, one line
each. Prefer designs that ELIMINATE a risk structurally (closed schema, inert
format, unexposed capability) over machinery that manages it (trust layers,
scanners, caps, extra state stores). Rejected bigger designs get one line
in ## Decision Context, never sections. This trims scope, never rigor: the
error/negative-cases discipline below, Boundaries, and R-ID coverage are
EXEMPT and stay complete. So are filesystem-identity, permission, and
concurrency guards (realpath/symlink containment, lock-guarded writes, forced
excludes of runtime state) — an eliminated guard is not an eliminated feature.
-->

<!--
EXAMPLES ARE EXHAUSTIVE (applies to every shape this spec shows):
When the spec shows an output, event, or API shape, the fields shown ARE the
contract — implementations must not add fields to a shown shape. If a field is
intended, show it in the example. A deviation the example doesn't license is a
review finding, not implementer discretion.
-->

# fn-292-avoid-caching-failed-fallback-review Avoid caching failed fallback review executions

## Goal & Context

Fallback resolution currently treats reaching a lower model rung as evidence
that the CLI execution succeeded. A terminal nonzero result from a fallback
model, including the CLI-default floor, can therefore be cached for 24 hours
and reported as a temporary resolution. The next review skips stronger models
and repeats a known failed choice. Cache entries must reflect successful CLI
execution so later invocations only skip models after a fallback actually ran.

## Architecture & Data Models

All four review CLI adapters share one fallback dispatcher. It owns the
versioned routing cache, ladder progression, floor selection, warnings, and
resolution receipt data. Adapter parsers normalize backend-specific
unavailable signals and preserve terminal execution errors. Cache writes and
warnings depend on the returned execution code; verdict parsing and receipt
finalization remain downstream.

## API Contracts

The fallback dispatcher returns the selected execution tuple unchanged and
records the model and floor flag for the existing receipt path. It caches and
warns only after exit code 0. A failed cached floor is invalidated and returned
without another dispatch. A failed cached model rung is invalidated; terminal
failures return unchanged, while a model-unavailable signal retains bounded
re-resolution from the ranking top.

## Edge Cases & Constraints

Preserve explicit-pin bypass, cache key and 24-hour TTL, lazy version lookup,
two-step ladder bound, successful fallback behavior, and receipt/reserve/refund
paths. Claude's exit-zero valid unavailable envelope may step down; its
nonzero exits and malformed envelopes remain terminal. A zero-exit response
without a verdict remains a finalizer concern and is not reclassified here.

## Acceptance Criteria

Numbered, testable predicates (R1, R2, ...): outcome predicates ("user X can
accomplish Y") and verifiable predicates ("function Z returns shape W under
condition V"). R-IDs are append-only — never renumber, never replace; a later
edit takes the next unused number.

Sub-scoped sibling criteria use single-letter suffixes (`R4a`, `R4b`) when one
logical parent splits during revision — siblings sort lexically (`R4a` before
`R4b` before `R5`). Multi-letter suffixes (`R4ab`) are not supported.

- **R1:** Every fallback cache write and its cached-choice warning occurs only when the selected CLI execution returns exit code 0, across Cursor's listed candidate and floor plus shared intermediate and floor paths. Errors: nonzero terminal output propagates without cache write or cached-resolution warning; malformed Claude envelopes remain terminal.
- **R2:** A nonzero execution of a cached floor invalidates the entry and returns that failure without another dispatch. A nonzero terminal failure from a cached model rung also invalidates and returns without same-call retry; a cached model-unavailability signal retains bounded re-resolution from the ranking top. Errors: cache invalidation remains best-effort and does not replace the dispatch result.
- **R3:** Successful fallback caching and warning behavior remain intact, while preferred-model success and explicit pins remain uncached. Cache key, expiry, lazy version lookup, two-step bound, resolution output, and downstream receipt and review-cap handling remain unchanged. Errors: no verdict/error reinterpretation beyond existing adapter normalization.
- **R4:** Mocked adapter regressions cover Codex, Copilot, Cursor, and Claude calls, exact model order and exit results, cache state, diagnostics, Cursor's one availability query, malformed Claude envelopes, and next-invocation re-resolution. Errors: tests invoke no provider or real review CLI.
- **R5:** Public CLI documentation describes the floor as a CLI-default fallback that can fail and states the success-only cache contract. Errors: retain the existing model-resolution heading anchor.

**Error cases (negative-cases discipline):** each behavioral criterion states its
error / invalid-input / boundary handling *inside* the R-ID bullet (sub-clauses
or sub-bullets — not sub-R-IDs), **or** explicitly records
"no error surface beyond X". A one-line "none" declaration is complete; silence
is incomplete. Standing G-IDs in `.flow/criteria.md` are referenced, never restated.

<!--
Example:
- **R1:** Parse config file into typed settings. Errors: malformed JSON → clear
  message + non-zero exit; missing file → same; over size limit → reject.
- **R2:** Settings object is frozen after load (no error surface beyond R1).
-->

## Boundaries

No retry-policy, cache-schema, routing-config, or verdict-finalization changes;
no new fallback abstraction; no provider calls or smoke reviews.

## Decision Context

The failure is in shared cache ownership: a selected model can be a valid
availability choice while its execution still fails. Exit code 0 is the
existing execution-success signal. Keeping verdict checks in finalization
preserves backend contracts and avoids changing review outcomes beyond the
failed-cache behavior.

Standing criteria: G2, G4.

<!--
One body of prose. Specs written by capture or by older refine runs may split it
into `### Motivation` (product rationale) and `### Implementation Tradeoffs`
(technical); keep whichever layout the spec already has.
-->

---

<!--
OPTIONAL AUXILIARY SECTION — `## Resolved via Research`:
Written by `/flow-next:refine --scope=research`, or by plan when its Step 1 ran
docs-scout or practice-scout (then with every research scout that ran:
docs-scout, practice-scout, docs-gap-scout, memory-scout; github-scout when
gated on). One `###` sub-block per scout that ran, one bullet
per finding (library version, changed API, gotcha, doc that must change, memory
entry that applies), each ending in `Source: <url|path|entry-id>`; a provenance
line under the heading names the writer and the scouts. Its presence is the skip
signal for both writers, so neither runs the scouts twice. Research lands here
when a human should see it before ratifying and when it must survive the route
choice; what only the implementer needs stays with the worker. Preserved
byte-for-byte by every other writer; only `refine --scope=research --force`
replaces it.
-->

<!--
OPTIONAL AUXILIARY SECTION — `## Parked unknowns`:
Written only when the spec actually carries fog. One bullet per genuinely-unknown
item, each passing the fog-or-ticket test: decidable now → decide it here and now,
so it never reaches this section; resolvable by scheduled work → make it a task or
a ticket; genuinely unknown (needs a decision, an experiment, or an outside answer
nobody has yet) → park it here, one line, naming what would resolve it.

Graduate-on-resolution: the moment refine or plan resolves a parked item, its
answer moves into the canonical section that owns it and the bullet is DELETED
from here. A parked bullet that survives its own answer is stale fog and reads as
an open question the spec has in fact closed. Empty section → omit it entirely.

DURABILITY (applies to the whole spec, not just this section):
Specs state contracts — types, signatures, behaviors, invariants — never file
paths or line numbers. Paths and line numbers rot on the first refactor and feed
plan-sync churn. ONE exception: a decision-rich snippet whose exact location IS
the decision (the reason the reader needs the spec is "here, not there"). TASKS
are exempt and unchanged — `**Files:**` / `**Touches:**` are a task's job.
-->

<!--
Quick commands convention: per-task Quick commands list FOCUSED suites for the
files the task touches; the FULL suite runs only when the repository's
instructions or the person ask for it (prefer the repo's parallel entrypoint
when one exists). See the project instruction file.
-->

<!--
Cross-links:
- flow-next docs, teams guide — "Symmetric interview" pattern (PO → tech-lead handover)
- `CLAUDE.md` / `AGENTS.md` — the flow-next section's "Creating a spec" line
- `/flow-next:capture` — automated spec capture from conversation
- `/flow-next:refine` — Q&A refinement (one interview, optional `--scope` lens) and the external-docs research pass (`--scope=research`, writes `## Resolved via Research`)
-->
