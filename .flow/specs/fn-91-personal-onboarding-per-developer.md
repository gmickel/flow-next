# fn-91 Personal onboarding: per-developer profile + adaptive interview/output calibration

> **STUB** (created from external-team field feedback, 2026-07-09; idea credited to two senior devs on the pilot team). Let a developer onboard into flow-next once, declare where they're strong and how AI-native they are, and have flow-next adapt its interviews, guard-rails, and suggestions accordingly. Refine via `/flow-next:interview` before planning.

## Goal & Context
<!-- scope: business -->

flow-next today runs the same interview depth, verbosity, and guard-rails for everyone. Two failure modes surfaced in the field (2026-07-09 external-team feedback session; detailed notes in the maintainer's vault):
- **Strong/AI-native seniors feel "entmachtet"** being walked through text they don't need — they'd skip ~50% of the interview in one prompt and want decision agency back. These are exactly the people you cannot afford to lose (they're the orchestrators).
- **Less tech-affine devs** need the opposite: deeper guard-rails, explicit ADR/architecture orientation, more scaffolding.

**The originating framing:** let people **onboard into flow-next / the project** — state how strong they are per area and how AI-native they are — and flow-next then **adjusts its outputs and suggestions** to match. A second senior's addition: a **depth setting** per developer (self-declared, team-lead-settable, honesty-dependent, a moving target). Reference implementation to study: an existing **Cursor-native per-project onboarding** from a sister team (artefact via Gordon) — adapt that into a Claude-Code/flow-next onboarding.

## Architecture & Data Models
<!-- scope: technical -->

TBD (interview). Shape to decide:
- An **onboarding interaction** (likely a new user-invoked skill, e.g. `/flow-next:onboard`, or an extension of `setup`/`prime`) that runs a short interview capturing a **developer profile**: strength areas (UI/UX, frontend, backend, REST/API, architecture, text/spec-writing) + a **depth/AI-nativeness level**.
- A **persisted profile** — open question: per-user at user scope (`~/.flow/…`, private, not committed) vs team-lead-set in-repo. Privacy + honesty both push toward user-scope self-profile with an optional team-lead override.
- A **calibration layer** flow-next reads: interview depth + question count (skip-rate for AI-native seniors), guard-rail/verbosity level, ADR/architecture prompting for less-tech-affine devs, and orchestration/model suggestions (ties to the "let flow-next pick the models/steps" orchestration idea from the same session).

## API Contracts
<!-- scope: technical -->

TBD (interview). Likely: an onboard skill + command wrapper (per `agent_docs/adding-skills.md`), a profile file schema, and a documented contract for how each consuming skill (interview first, then plan/work suggestions) reads the profile and what it changes. Cross-platform parity via `sync-codex.sh`.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Honesty risk:** self-declared skill is gameable → team-lead-settable override; consider calibrating from **observed behavior over time** (skip rate, answer depth) rather than trusting the one-time declaration.
- **Moving target:** profiles drift as people level up → re-onboarding / easy adjustment must be first-class, not a one-shot.
- **Don't dumb down or over-gate:** the strong path must genuinely reduce friction (fewer/skippable questions) without dropping the parts of the interview that catch real design decisions; the guarded path must not condescend.
- **No perf surveillance:** this is developer-experience calibration, NOT productivity measurement — keep it strictly separate from PSVI / any KPI or measurement surface.

## Acceptance Criteria
<!-- scope: both -->

- [ ] **R1:** An onboarding interaction captures a **developer profile** — strength areas + depth/AI-nativeness level — in a short, repeatable flow.
- [ ] **R2:** The profile is **persisted** at an agreed scope (user-scope vs repo/team-lead-set — decided in interview) and is easy to re-run/adjust.
- [ ] **R3:** At minimum **`/flow-next:interview` reads the profile and adapts** (interview depth + verbosity: shallower/skippable for AI-native seniors, deeper guard-rails + ADR orientation for less tech-affine devs).
- [ ] **R4:** A **team-lead can set/override** a developer's profile.
- [ ] **R5:** Documented (skill page + BOTH docs-site navbars + changelog) and cross-platform (`sync-codex.sh`); plugin version bumped per release process.

## Boundaries
<!-- scope: business -->

- In: a one-time-ish onboarding that produces a per-dev profile, and flow-next adapting interview/output/suggestions to it.
- Out: a full RBAC/skills/permissions system; productivity/perf measurement (PSVI/SapienXT — separate, confidential); the orchestration auto-model-selection engine itself (related but its own item; this only *feeds* suggestions).

## Decision Context
<!-- scope: both -->

- **Related:** pairs with **fn-67** (`/flow-next:guide` — the opinionated router could route by profile) and with the senior-dev "expert/free mode over the primitives" signal (same 2026-07-09 session). The orchestration passion-project from that session is the natural consumer of the profile's suggestion-calibration.
- **Plain-language question contract (2.10.1/2.10.2) — this spec is its natural next consumer.** The same field-feedback batch produced an eval-validated plain-language contract for agent questions (stakes sentence, glossed terms of art, consequence-bearing options, priorities-not-caps sizing) now duplicated in the interview and capture skills, with the audience currently *inferred from scope* (PM vs dev). fn-91's developer profile should (a) become the **audience parameter** for that contract — profile-driven register instead of scope-inferred (an AI-native senior gets terser questions than a less tech-affine dev, same required content), and (b) drive the **consolidation** of the duplicated contract into one shared reference the consuming skills load. Evidence + reusable eval harness: memory `plain-language-question-contract` + scratchpad `langeval/`.
- **Reference:** the Cursor-native per-project onboarding artefact (via Gordon) — adapt, don't reinvent.
- **Open questions for interview:** profile scope (user vs repo)? self-declared vs behaviorally-inferred vs both? which skills consume it in v1 (interview only, or plan/work suggestions too)? one global profile vs per-project?
