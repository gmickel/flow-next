# Interview Question Categories (Business)

Business-scope question bank. Loaded by `flowctl scope bank business` and during the business phase of `--scope=both`.

Shared blocks — `Pre-Question Taxonomy` and `Interview Guidelines` — live in [questions-shared.md](questions-shared.md). Read that first; the buckets below are user-judgment-required topic prompts only (the taxonomy classifier in shared decides whether to ask vs investigate vs project-docs-lookup).

Ask NON-OBVIOUS questions only. Expect 40+ questions for complex specs.

## Problem Framing

- The underlying problem this solves (not just the surface request)
- Why-now: what changed to make this worth doing
- Who feels the pain today and how it shows up
- Cost of not building this

## Target User / Persona

- Primary user persona and their context
- Technical literacy assumption (jargon vs plain-language)
- Frequency of use (one-time, daily, mid-flow)
- Anti-personas — who this is explicitly NOT for

## Success Metrics

- What "winning" looks like 90 days after ship
- Leading vs lagging indicators we can observe
- Threshold for "good enough" vs "needs rework"
- Counter-metrics — what we'd hate to regress

## MVP Scope

- Smallest version that proves the bet
- Path-from-MVP for the features we cut
- Definition of "shippable" for this pass
- Concrete cuts the PO would accept if scope must shrink (framed by feature value, NOT by time pressure)

## Business Constraints

- Regulatory / compliance obligations (data residency, retention, audit)
- Budget envelope (infra cost, vendor spend, licensing) — NOT engineering time / duration
- Brand / partner / contractual commitments
- External dependencies that must be honored (third-party APIs, partner releases, regulatory windows)

**Do NOT ask about deadlines, sprint cadence, hours/days/weeks budgets, or "ship before X" timing.** Agents can't estimate their own work, and time-pressure framing collapses the interview into prioritization debates. If the user volunteers a deadline, acknowledge it without chasing it through MVP-Scope and What-NOT-to-Build re-asks.

## What NOT to Build

- Adjacent features that look in-scope but aren't
- Extensibility hooks the PO has not asked for
- Use cases we explicitly decline to support
- Existing behaviour to preserve untouched

## Prioritization Rationale

- Ranked trade-off — speed vs robustness vs extensibility
- Which axis we sacrifice first when pressure hits
- How this stacks against parallel work
- Decision-rights — who breaks ties mid-implementation

## Business Risks

- Failure modes that hurt the business, not just the system
- Reputational / trust risks if it ships rough
- Reversibility — can we roll back without user pain
- Risks we accept and risks we hedge against

## UX Expectations

- Tone for user-facing copy (errors, empty states, success)
- Acceptable friction (taps, confirmations, sign-in)
- Loading / waiting expectations under real-world conditions
- Accessibility floor (keyboard, screen reader, contrast)
