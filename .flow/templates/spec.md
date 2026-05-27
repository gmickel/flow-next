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

- **R1:** <Testable criterion>
- **R2:** <Testable criterion>

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
Cross-links:
- `plugins/flow-next/docs/teams.md` — "Symmetric interview" pattern (PO → tech-lead handover)
- `CLAUDE.md` — "Creating a spec" guide (manual + automated paths)
- `plugins/flow-next/skills/flow-next-capture/` — automated spec capture from conversation
- `plugins/flow-next/skills/flow-next-interview/` — Q&A refinement (`--scope=business|technical|both`)
-->
