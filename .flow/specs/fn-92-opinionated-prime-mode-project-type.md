# Opinionated prime mode: project-type & structure-aware readiness (monorepo vs multi-repo, size, mapping)

> **STUB** — captured 2026-07-10 from external-team field feedback (an external team's AI-SDLC weekly; their head of software engineering + a backend lead). Today `/flow-next:prime` largely checks file/config **existence** across its criteria, so repos reach a top readiness level ("Level 5") without the substance behind it — and there's no way to hand-verify hundreds of repos across 10-11 tech stacks. Make prime **opinionated + structure-aware**: reason about what kind of project this is (single repo vs monorepo vs multi-repo constellation), its size/legibility, and recommend concrete next actions instead of ticking boxes. Refine via `/flow-next:interview` before planning.

## Goal & Context
<!-- scope: business -->

At scale, existence-checks lie. A repo can pass prime's criteria — a CLAUDE.md exists, a hook file exists, a script exists — yet be un-agentic in practice: the file is an empty template, the repo is too big to navigate, imports can't be resolved, or it's really one of 99 sibling repos that only make sense together. Leads/reviewers can't hand-verify at portfolio scale, so a top "readiness level" stops meaning anything. Prime should encode the judgment a senior applies on a first look — how big is this, can an agent find its way around, is this a monorepo or a swarm of repos, and what is the ONE next thing that makes it agent-ready — and say so **opinionatedly**, with a concrete recommendation rather than a pass/level.

Origin: a portfolio-company rollout (three product lines), 100+ repos across ~10-11 stacks, where "häufig nur Existenz geprüft → Level 5 erreicht, ohne dass es stimmt." Gordon owns the write-up.

## Architecture & Data Models
<!-- scope: technical -->

TBD (interview). Likely a **new prime mode / depth** — the existing 8-pillar / 48-criteria readiness scan stays; this adds a substance-and-structure lens on top (a `--deep` / `--opinionated` variant, or a second pass). Candidate pieces:

- **Project-type classification** — single repo | monorepo (one repo, many packages) | multi-repo constellation (N sibling repos that compose — e.g. a product's separate API + web-frontend repos). This drives everything downstream.
- **Structure-legibility probe** — repo size (LOC / file-count / tree depth) and: can the agent actually read the structure (resolve imports/exports, find entrypoints, see the build graph)? If NOT legible → recommend generating a **map** (`/flow-next:map` / clawpatch, or a hand-written map) and where to store it (master/parent repo + link in CLAUDE.md).
- **Multi-repo guidance** — detect sibling repos and recommend a structuring pattern (the **linked-siblings "fake monorepo"** pattern proven at a pilot team: sibling repos checked out under a parent, work in the parent dir, everything linked in CLAUDE.md, docs-update as Definition-of-Done) instead of priming each repo in isolation.
- **Substance-not-existence checks** — for hooks / scripts / central-instruction files, judge whether the file holds sensible content vs an empty template or bare header (bounded AI judgment, evidence-anchored); add a **"can I operate / compile / run this app end-to-end, and what's needed for that?"** baseline as the real readiness signal rather than "the file is present."
- **Opinionated next-action output** — emit a ranked, specific to-do ("write STRATEGY.md"; "generate a map — repo too large to navigate"; "you have 99 repos, consider a fake-monorepo"; "this pre-commit hook is a stub") instead of only a level. Reusable: carry the learnings and apply the same playbook across repos.

## API Contracts
<!-- scope: technical -->

TBD at planning. Anchor points to map first: the current prime skill's pillar/criteria model + its command-verification step (where existence-checks live today); `/flow-next:map` (clawpatch, provider-free) as the mapping recommendation seam; how prime assembles + emits its report (extend with a project-type/structure block + a ranked next-actions block). Cross-platform parity via `sync-codex.sh`.

## Edge Cases & Constraints
<!-- scope: technical -->

- Monorepo-vs-multi-repo detection is heuristic — degrade gracefully and let the human confirm.
- Size / legibility probes must be **bounded** — no full-repo LLM crawl on a huge repo (that is the exact case that breaks); prefer cheap structural signals + a "too big, map it" verdict.
- "Substance" judgment is the fabrication-risk surface — keep it anchored to the file's actual content, never invent.
- Do not regress the existing existence / readiness scan; this augments, it does not replace.
- Prime is provider-free by default (clawpatch map is too) — keep that.

## Acceptance Criteria
<!-- scope: both -->

- **R1 (STUB):** prime classifies project type (single | monorepo | multi-repo constellation) and reflects it in the report.
- **R2 (STUB):** prime probes structure legibility (size + import/export/entrypoint resolvability); when a repo isn't legible it recommends generating a map (`flow-next:map` / clawpatch or hand-written) and where to store it.
- **R3 (STUB):** for a multi-repo constellation prime recommends a concrete structuring pattern (e.g. fake-monorepo) instead of per-repo priming.
- **R4 (STUB):** readiness checks judge **substance not mere existence** for at least hooks / scripts / central-instruction files, and include a "can the app be operated / compiled" baseline.
- **R5 (STUB):** prime emits **ranked, specific next-actions** (opinionated), not just a level; reusable across repos.
- *(Real R-IDs assigned at planning.)*

## Boundaries
<!-- scope: business -->

- In: a more opinionated, structure- / type- / size-aware prime that detects monorepo-vs-multi-repo and recommends concrete next steps.
- Out: auto-**fixing** the repo structure (prime recommends; it does not restructure); the mapping engine itself (that is clawpatch / `flow-next:map` — this consumes it); turning readiness into a KPI / score surface (keep strictly separate from PSVI / any measurement — DX guidance only).
- Not a rewrite of the existing 8-pillar scan — additive.

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->
At portfolio scale the binary existence-check produces false "ready" signals and no actionable guidance, and leads cannot hand-verify hundreds of repos across many stacks. Encoding a senior's first-look judgment — size, legibility, repo topology, single most-valuable next action — makes prime trustworthy at scale and directly unblocks portfolio-scale multi-repo, multi-stack rollouts (the current bottleneck). Stub first: the exact mode shape and which checks move from existence to substance need an interview.

### Implementation Tradeoffs
<!-- scope: technical -->
TBD (interview). Open: new mode/flag vs deepening the existing criteria in place; how much structural analysis to do natively vs delegating to `flow-next:map`; heuristics + thresholds for "too big to navigate" and "monorepo vs multi-repo"; keeping the substance-judgment bounded and non-fabricating.

## Strategy Alignment
- **Agent-readiness / adoption-at-scale** track — makes prime a trustworthy gate for large multi-repo, multi-stack portfolios (the rollout bottleneck); pairs with `/flow-next:map`.

## Conversation Evidence
> Field origin — external-team AI-SDLC weekly, 2026-07-10 (head of software engineering + backend lead): "dadurch, dass häufig nur Existenz geprüft wird, haben die jetzt aus irgendeinem Grund Level 5 erreicht … es ist nicht möglich, dass wir das händisch überprüfen … hunderte Repositories, 10-11 verschiedene Tech-Stacks." Gordon's steer: check repo size + can it read structure / imports-exports → else recommend a mapping tool; if multiple repos, propose how to structure them (fake-monorepo); judge whether a pre-commit hook / script has sensible content vs just a template/header; baseline = "kann ich die App betreiben / kompilieren?" — "vielleicht braucht es einen neuen Mode … kann man wiederverwenden, Erfahrungen mitnehmen und überall applizieren." Detailed notes in the maintainer's vault (AI-SDLC weekly 2026-07-10).
