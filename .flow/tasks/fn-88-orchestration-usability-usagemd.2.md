---
satisfies: [R4, R13, R15]
---

## Description

Author the canonical opinionated model-routing scaffold as a new setup template file, and de-embed the full example from `docs/orchestration.md` (trimmed excerpt + cross-link).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-setup/templates/model-routing-snippet.md` (new), `plugins/flow-next/docs/orchestration.md`, `plugins/flow-next/codex/**` (regenerated)

## Approach

- New template sibling of `templates/claude-md-snippet.md` — same file conventions. Structure:
  - `<!-- flow-next:model-routing:start -->` opening marker + provenance line ("scaffolded by /flow-next:setup — edit freely; re-run setup to regenerate").
  - `## Picking models for flow-next workflows and subagents` heading.
  - Scores table `model | cost | intelligence | taste` (higher = better): session/frontier model, gpt-5.5 (codex CLI), composer-2.5 (cursor-agent), fast Claude tier. Framing line: "cost reflects what you actually pay (existing subscriptions), not list price" + re-rank invitation.
  - How-to-apply rules: defaults-not-limits + standing escalation permission; intelligence > taste > cost for anything that ships; bulk/mechanical → gpt-5.5; user-facing needs taste ≥ threshold; reviews cross-family; graceful degrade (routed CLI missing/unauthenticated/failing → report unavailable, fall back to session model — never block).
  - flow-next wiring: `/flow-next:work` worker + `delegate:codex`; reviews via `review.backend` (codex / cursor:composer-2.5 / per-task `review:`); scouts may shell out to `cursor-agent` for bulk reads; thin-wrapper pattern for gpt-5.5 inside subagent workflows.
  - Probe sentinels (structural requirement): every codex- or cursor-dependent route sits on its OWN line, prefixed `<!-- probe:codex -->` or `<!-- probe:cursor -->`. Composition (fn-88.3) is then a deterministic line transform: failing probe ⇒ comment out exactly its sentinel-tagged lines + append "not detected on this machine — uncomment after installing". This shape is what makes all four probe states mechanically testable (fn-88.4).
  - `<!-- flow-next:model-routing:end -->` closing marker.
- HARD BUDGET: ≤ ~45 lines including markers/provenance (R13). This is always-loaded context in target repos. If wiring can't fit, escalate per the spec's Early proof point (split block + on-demand reference) rather than shipping a bloated block.
- `docs/orchestration.md` "Durable routing" (L122-165): replace the full embedded example with a ~10-line illustrative excerpt + cross-link to the template file as canonical + one line noting `/flow-next:setup` offers it live (R15, R17 discipline).
- Regenerate Codex mirror after edits.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md` — sibling conventions incl. marker style
- `plugins/flow-next/docs/orchestration.md:122-165` — the current example to adapt + de-embed
- `plugins/flow-next/references/html-artifacts.md:30-34` — the `flow-next:` colon-namespaced marker family convention

**Optional:**
- `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md:170-176` — graceful-degrade message shape to echo

## Key context

- This is the spec's early proof point: if the full example can't hit ≤ ~45 lines without losing the wiring, STOP and re-evaluate the scaffold shape before fn-88.3 builds the ceremony around it.
- Scores are deliberately opinionated (user decision 2026-07-05) — ship real numbers, frame as editable starting opinions. Never present as maintained truth.

## Acceptance

- [ ] `templates/model-routing-snippet.md` exists: markers + provenance + scores table + rules (escalation + graceful-degrade always present) + flow-next wiring, ≤ ~45 lines
- [ ] Every CLI-dependent route on its own sentinel-prefixed line (`<!-- probe:codex -->` / `<!-- probe:cursor -->`); no active CLI reference outside sentinel lines
- [ ] `docs/orchestration.md` de-embedded: excerpt + cross-link + setup mention; no second full copy anywhere
- [ ] sync-codex regenerated + green; full pytest + smoke green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
