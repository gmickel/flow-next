---
purpose: Canonical spec template — single source of truth for .flow/specs/<id>.md structure
consumers:
  - flow-next-capture        # synthesizes a spec from conversation context
  - flow-next-refine         # refines a spec via one Q&A interview (optional --scope lens) or external docs (--scope=research)
  - flow-next-plan           # breaks a spec into tasks
  - CLAUDE.md                # "Creating a spec" guide cross-links here rather than embedding
canonical_sections:
  - Goal & Context
  - Architecture & Data Models
  - API Contracts
  - Edge Cases & Constraints
  - Acceptance Criteria      # R-IDs append-only
  - Boundaries
  - Decision Context
auxiliary_sections:
  - Strategy Alignment       # written when STRATEGY.md has content
  - Strategy Conflicts       # written when STRATEGY.md has content
  - Glossary Conflicts       # written when doc-aware mode detects a vocabulary mismatch
  - Conversation Evidence    # written by /flow-next:capture (source-tagged AC trail); opens the body unless you place it as a heading
  - Resolved via Codebase    # written by /flow-next:refine when the code answered a question
  - Resolved via Project Docs  # written by /flow-next:refine when the project docs answered a question
  - Resolved via Experiment  # written by /flow-next:refine when a question was settled by running something
  - Resolved via Research    # written by /flow-next:refine --scope=research, or by plan when its research scouts ran
  - Parked unknowns          # optional fog slot; one bullet per genuinely-unknown item, emptied as they resolve
  - Requirement coverage     # written by /flow-next:capture on a planned route; /flow-next:plan fills it; closes the body unless you place it as a heading
template_kind: static-scaffold  # no {{var}} substitution; read for structure, write via flowctl spec set-plan
---

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
(plugins/flow-next/docs/spec-template.md - https://flow-next.dev/guides/spec-scaffold/).
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

# <spec-id> <Title>

## Goal & Context

Problem framing, motivation, why-now, target user / persona. The "why this
exists" statement that grounds every downstream decision. Implementing agents
read this section to disambiguate intent and pick defaults that match the PO's
priority.

## Architecture & Data Models

Component boundaries, integration points, data flow, key abstractions. The
"how it fits together" map that an implementation agent reads before touching
code. Cross-link to design docs (`docs/design/<topic>.md`, ADRs) when
load-bearing; the spec remains the single source of truth for R-IDs.

## API Contracts

Endpoints, interfaces, input / output shapes, error semantics. The wire
contract between the change in this spec and the rest of the system. Concrete
enough that tests can assert against it.

## Edge Cases & Constraints

Failure modes, limits, performance requirements, security boundaries,
backward-compatibility commitments. Business constraints (regulatory, budget,
deadline) feed in from `## Goal & Context` — call them out here only when they
shape a technical decision.

## Acceptance Criteria

Numbered, testable predicates (R1, R2, ...): outcome predicates ("user X can
accomplish Y") and verifiable predicates ("function Z returns shape W under
condition V"). R-IDs are append-only — never renumber, never replace; a later
edit takes the next unused number.

Sub-scoped sibling criteria use single-letter suffixes (`R4a`, `R4b`) when one
logical parent splits during revision — siblings sort lexically (`R4a` before
`R4b` before `R5`). Multi-letter suffixes (`R4ab`) are not supported.

<!--
Placeholder shape (write real criteria in their place; a comment-wrapped
bullet is never read as a live R-ID):
- **R1:** <Testable criterion>. Errors: <enumerated error/invalid-input/boundary cases, or "no error surface beyond X">
- **R2:** <Testable criterion>. Errors: <cases, or "no error surface beyond X">
-->

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

What's explicitly out of scope. Scope decisions are priority decisions,
usually the product owner's. Implementing agents read this section to avoid
gold-plating and to confirm "the thing we're NOT building" stays unbuilt.

## Decision Context

Why this approach over alternatives. The reasoning record that future readers
(human or agent) need when revisiting the spec.

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
files the task touches; the FULL suite runs once at the final gate (prefer the
repo's parallel entrypoint when one exists). See the project instruction file.
-->

<!--
Cross-links:
- `plugins/flow-next/docs/teams.md` — "Symmetric interview" pattern (PO → tech-lead handover)
- `CLAUDE.md` — "Creating a spec" guide (manual + automated paths)
- `plugins/flow-next/skills/flow-next-capture/` — automated spec capture from conversation
- `plugins/flow-next/skills/flow-next-refine/` — Q&A refinement (one interview, optional `--scope` lens) and the external-docs research pass (`--scope=research`, writes `## Resolved via Research`)
-->
