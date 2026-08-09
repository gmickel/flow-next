---
purpose: Canonical spec template — single source of truth for .flow/specs/<id>.md structure
consumers:
  - flow-next-capture        # synthesizes a spec from conversation context
  - flow-next-interview      # refines a spec via Q&A (--scope=business|technical|both)
  - flow-next-plan           # breaks a spec into tasks
  - CLAUDE.md                # "Creating a spec" guide cross-links here rather than embedding
canonical_sections:
  - Goal & Context           # scope: business
  - Architecture & Data Models  # scope: technical
  - API Contracts            # scope: technical
  - Edge Cases & Constraints  # scope: technical
  - Acceptance Criteria      # scope: both (co-authored; R-IDs append-only)
  - Boundaries               # scope: business
  - Decision Context         # scope: both (conditionally substructured)
auxiliary_sections:
  - Strategy Alignment       # written when STRATEGY.md has content
  - Strategy Conflicts       # written when STRATEGY.md has content
  - Glossary Conflicts       # written when doc-aware mode detects a vocabulary mismatch
  - Conversation Evidence    # written by /flow-next:capture (source-tagged AC trail)
  - Resolved via Codebase    # written by /flow-next:interview --scope=technical
  - Resolved via Project Docs  # written by /flow-next:interview --scope=business
  - Parked unknowns          # optional fog slot; one bullet per genuinely-unknown item, emptied as they resolve
template_kind: static-scaffold  # no {{var}} substitution; read for structure, write via flowctl spec set-plan
---

<!--
Scope ownership annotations on each section header below — each section has
one of three HTML-comment owner-markers immediately under the heading:

  scope: business   — owned by the business pass (PO / product owner)
  scope: technical  — owned by the technical pass (tech lead / impl agent)
  scope: both       — co-authored across passes; merge contract preserves
                      the other side byte-for-byte

(The literal HTML form is `<!__ scope: business __>` with two hyphens
on each side; underscores shown here only because HTML comments cannot
nest — see https://html.spec.whatwg.org/multipage/syntax.html#comments.)

R-IDs in `## Acceptance Criteria` are append-only across passes. Never renumber.
Never replace existing entries. A later pass appends new criteria with the next
unused number.
-->

<!--
To customize for your project, copy this file to `<repo-root>/SPEC.md` and edit there.

Discovery cascade (first match wins):
  1. <repo_root>/SPEC.md           (your customized scaffold — uppercase preferred)
  2. <repo_root>/spec.md           (lowercase honored when uppercase absent)
  3. .flow/templates/spec.md       (project-local copy from /flow-next:setup)
  4. bundled ${PLUGIN_ROOT}/templates/spec.md  (this file — canonical source of truth)

Customizing: adding sections and rewriting the guidance prose under any heading is
free. Renaming or removing `## Acceptance Criteria`, `## Boundaries`,
`## Goal & Context` or `## Decision Context` does NOT error - it silently degrades
the features that parse them (R-ID coverage, PR "Not in this PR", interview scope
routing, Decision Context shape detection).

Full guide, incl. the known limitation for custom sections under an interview pass:
flow-next docs, "Customizing the scaffold for your project"
(plugins/flow-next/docs/spec-template.md - https://flow-next.dev/docs/spec-template/).
-->

<!--
SCOPE DISCIPLINE (YAGNI — applies to the whole spec):
Specify the smallest system that satisfies the request. Every R-ID traces to
the request; every task traces to an R-ID. Capabilities the request never
asked for are not scope — name them in ## Boundaries as out-of-scope, one line
each. Prefer designs that ELIMINATE a risk structurally (closed schema, inert
format, unexposed capability) over machinery that manages it (trust layers,
scanners, caps, extra state stores). Rejected bigger designs get one line in
## Decision Context, never sections. This trims scope, never rigor: the
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
<!-- scope: business -->

Problem framing, motivation, why-now, target user / persona. The "why this
exists" statement that grounds every downstream decision. Implementing agents
read this section to disambiguate intent and pick defaults that match the PO's
priority.

## Architecture & Data Models
<!-- scope: technical -->

Component boundaries, integration points, data flow, key abstractions. The
"how it fits together" map that an implementation agent reads before touching
code. Cross-link to design docs (`docs/design/<topic>.md`, ADRs) when
load-bearing; the spec remains the single source of truth for R-IDs.

## API Contracts
<!-- scope: technical -->

Endpoints, interfaces, input / output shapes, error semantics. The wire
contract between the change in this spec and the rest of the system. Concrete
enough that tests can assert against it.

## Edge Cases & Constraints
<!-- scope: technical -->

Failure modes, limits, performance requirements, security boundaries,
backward-compatibility commitments. Business constraints (regulatory, budget,
deadline) feed in from `## Goal & Context` — call them out here only when they
shape a technical decision.

## Acceptance Criteria
<!-- scope: both -->

Numbered, testable predicates (R1, R2, ...). Business pass adds outcome
predicates ("user X can accomplish Y"); technical pass adds verifiable
predicates ("function Z returns shape W under condition V"). R-IDs are
append-only across passes — never renumber, never replace; a later pass takes
the next unused number.

Sub-scoped sibling criteria use single-letter suffixes (`R4a`, `R4b`) when one
logical parent splits during revision — siblings sort lexically (`R4a` before
`R4b` before `R5`). Multi-letter suffixes (`R4ab`) are not supported.

- **R1:** <Testable criterion>. Errors: <enumerated error/invalid-input/boundary cases, or "no error surface beyond X">
- **R2:** <Testable criterion>. Errors: <cases, or "no error surface beyond X">

**Error cases (negative-cases discipline):** each behavioral criterion states its
error / invalid-input / boundary handling *inside* the R-ID bullet (sub-clauses
or sub-bullets — not sub-R-IDs), **or** explicitly records
"no error surface beyond X". A one-line "none" declaration is complete; silence
is incomplete. Standing G-IDs in `.flow/criteria.md` are referenced, never restated.

Example:
- **R1:** Parse config file into typed settings. Errors: malformed JSON → clear
  message + non-zero exit; missing file → same; over size limit → reject.
- **R2:** Settings object is frozen after load (no error surface beyond R1).

## Boundaries
<!-- scope: business -->

What's explicitly out of scope. Owned by the PO because scope decisions are
priority decisions. Implementing agents read this section to avoid
gold-plating and to confirm "the thing we're NOT building" stays unbuilt.

## Decision Context
<!-- scope: both — conditionally substructured -->

Why this approach over alternatives. The reasoning record that future readers
(human or agent) need when revisiting the spec.

<!--
This section has TWO shapes. Pick exactly one:

(A) FLAT (default, R22 backward-compat):
    Used when only a technical-scope pass has run (zero-flag default for solo
    devs on 1.0.2-shape specs). Same shape as 1.0.2 — one body, no H3
    subsections. Do NOT introduce H3s here under a `--scope=technical` pass
    unless the spec already has them or a biz pass has run.

    Replace this comment block with prose:

    Why this approach over the alternatives. Trade-offs, constraints that
    pushed the decision, what we explicitly rejected and why.

(B) SUBSTRUCTURED (after a business pass has run, OR under `--scope=business` /
    `--scope=both`, OR when an existing spec already has the H3s).

    Two H3 subsections, each carrying its own scope-owner HTML comment
    (`scope: business` on Motivation, `scope: technical` on Implementation
    Tradeoffs):

    ### Motivation     [owner: business]
    Why this matters now. Business / product rationale. What outcome we're
    chasing and why this spec is the right vehicle.

    ### Implementation Tradeoffs     [owner: technical]
    Why this technical approach over alternatives. What we rejected and why.
    Constraints that shaped the design.
-->

---

<!--
OPTIONAL AUXILIARY SECTION — `## Parked unknowns`:
Written only when the spec actually carries fog. One bullet per genuinely-unknown
item, each passing the fog-or-ticket test: decidable now → decide it here and now,
so it never reaches this section; resolvable by scheduled work → make it a task or
a ticket; genuinely unknown (needs a decision, an experiment, or an outside answer
nobody has yet) → park it here, one line, naming what would resolve it.

Graduate-on-resolution: the moment interview or plan resolves a parked item, its
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
- `plugins/flow-next/skills/flow-next-interview/` — Q&A refinement (`--scope=business|technical|both`)
-->
