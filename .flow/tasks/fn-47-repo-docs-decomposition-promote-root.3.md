---
satisfies: [R1, R7, R8]
---

## Description

Fill in the "How the flow works" 6-step narrative in the root `README.md` (Phase 2 left it as a placeholder), finalize the "Where to look" table, and produce a handover prompt for the flow-next.dev agent enumerating missing skill pages (prospect, capture, interview, audit, prime, make-pr, resolve-pr, memory) so they can be added to the website to back the workflow narrative's deep-link targets.

**Size:** S

**Files:**
- `README.md` (root) — fill in "How the flow works" section with the 6-step narrative + finalize "Where to look" table
- Handover prompt artifact — output to clipboard via `pbcopy` (per session pattern; matches the fn-46 docs-gap handover precedent)

## Approach

- **6-step workflow narrative in root README.** Pattern: each step = bold heading + 2-3 lines prose + tiny `/flow-next:<skill>` invocation line + "→ [flow-next.dev/<page>]" deep link. Target total: ~70 lines across 6 steps + optional Ralph note. Keep each step at 5-10 lines max — narrative is "shape of the workflow", not a tutorial.
  ```markdown
  ## How the flow works

  flow-next is spec-driven. The loop:

  ### 1. Capture or prospect a spec
  Synthesize an idea or recent conversation into a structured spec.
  Or, when starting from scratch, generate ranked candidate ideas
  grounded in the repo.
  ```bash
  /flow-next:capture                # from conversation
  /flow-next:prospect               # from a focus hint
  ```
  → [flow-next.dev/skills/capture](https://flow-next.dev/skills/capture) · [flow-next.dev/skills/prospect](https://flow-next.dev/skills/prospect)

  ### 2. Interview to refine
  ...
  ```

  Steps to include: 1. Capture / Prospect, 2. Interview, 3. Plan, 4. Work, 5. Make PR, 6. Resolve PR. Plus an optional 7. Ralph autonomous mode (~3-5 lines, footer to the narrative).

- **"Where to look" table finalization.** Existing Phase 2 table likely covers most surfaces; Phase 3 polishes. Final shape:
  | If you want to… | Read |
  |---|---|
  | Browse skills + workflows + concepts | **[flow-next.dev](https://flow-next.dev)** |
  | Install + 5-command happy path | This README, above |
  | flowctl CLI reference | `plugins/flow-next/docs/flowctl.md` |
  | Architecture + `.flow/` layout | `plugins/flow-next/docs/architecture.md` |
  | Spec template + discovery cascade | `plugins/flow-next/docs/spec-template.md` |
  | Ralph internals | `plugins/flow-next/docs/ralph.md` |
  | Adopting in a team | `plugins/flow-next/docs/teams.md` |
  | Memory schema | `plugins/flow-next/docs/memory-schema.md` |
  | Project glossary + strategy | `plugins/flow-next/docs/glossary.md` + `strategy.md` |
  | Codex mirror + sync-codex.sh | `plugins/flow-next/docs/sync-codex.md` |
  | Platforms (Codex / Droid / OpenCode) | `plugins/flow-next/docs/platforms.md` |
  | Troubleshooting | `plugins/flow-next/docs/troubleshooting.md` |
  | Adding a skill | `agent_docs/adding-skills.md` |
  | Cutting a release | `agent_docs/releasing.md` |
  | Local plugin dev | `agent_docs/local-dev.md` |

- **flow-next.dev gap handover.** flow-next.dev currently has pages for: introduction, flowctl/*, ralph/*, releases/*, review/*, specs/*, strategy/*, tasks/*, teams/*. **MISSING for Phase 3 deep-link targets:** prospect, capture, interview, audit, prime, make-pr, resolve-pr, memory. Produce a handover prompt for the docs-site agent enumerating exactly these gaps + what each page should cover at a high level (1 sentence per page). Copy to clipboard via `pbcopy`. Don't write to website — that's the other agent's lane.

- **R17 discipline** still applies: workflow narrative steps should not re-embed deep content from the website pages; they should be terse pointers that say what the skill does + when to use it + how to invoke + link out.

- **No version bump.** Docs-only.

## Investigation targets

**Required**:
- `README.md` post-Phase-2 (whatever shape it landed in) — verify the placeholder "How the flow works" section exists and is ready to be filled.
- `plugins/flow-next/skills/<skill>/SKILL.md` for each of the 6 (capture, interview, plan, work, make-pr, resolve-pr) + prospect, ralph — 2-3 lines from each SKILL.md's frontmatter `description` field is the natural source for "what the skill does" prose.
- `~/work/flow-next.dev/src/content/docs/` page inventory — confirm exact page list (introduction, flowctl/*, ralph/*, releases/*, review/*, specs/*, strategy/*, tasks/*, teams/*) so the gap enumeration is accurate.

**Optional**:
- README precedents for workflow narratives: astral-sh/uv (329 lines, progressive disclosure with deep links), oven-sh/bun (long-form narrative ~446 lines).

## Key context

- **Phase 3 is the smallest phase** because Phase 1 + 2 did the heavy structural work. This phase fills in the human-readable narrative + produces the handover.
- **Workflow narrative is self-contained.** A reader landing on github.com/gmickel/flow-next should understand the shape of the workflow from these ~70 lines without needing to leave. The website deep-links exist for "I want more depth", not "I need to leave to understand".
- **flow-next.dev gap handover format:** match the fn-46 docs-gap handover prompt structure (markdown, **Gap N — title**, "Where to add", "What to say", "Source of truth"). Copy to clipboard via `cat <<'EOF' | pbcopy`.
- **flow-next.dev MAY add the missing pages independently** of this PR. The handover is informational, not blocking. Phase 3 PR can land with website-deep-links pointing at not-yet-existing pages; once the website agent adds them, the links resolve.
- **Per-skill description sources:** every `plugins/flow-next/skills/<name>/SKILL.md` has a frontmatter `description:` field with the canonical 1-2 sentence pitch. Reuse those verbatim in the workflow narrative for consistency.
- **No version bump.** Docs-only changes.

## Acceptance

- [ ] Root `README.md` "How the flow works" section filled in: 6 numbered workflow steps + optional Ralph footer. Each step is 5-10 lines; total section ~70 lines.
- [ ] Each workflow step includes: bold heading; 2-3 lines prose; invocation snippet; flow-next.dev deep-link.
- [ ] "Where to look" table finalized with rows for each `plugins/flow-next/docs/<file>.md` + agent_docs/ entries + flow-next.dev top-level link.
- [ ] flow-next.dev gap handover prompt produced + copied to clipboard via `pbcopy`. Prompt enumerates: prospect, capture, interview, audit, prime, make-pr, resolve-pr, memory — 8 missing pages — with 1-sentence summary of what each should cover.
- [ ] Root README final length ≤ 400 lines (target ~350).
- [ ] R17 cross-link discipline verified: workflow narrative steps link to flow-next.dev for depth; do NOT re-embed website content.
- [ ] 612/612 unit tests + 130/130 smoke green.
- [ ] `./scripts/sync-codex.sh` runs cleanly; validation guards pass.
- [ ] No version bump.

## Done summary

*Populated by /flow-next:work on completion.*

## Evidence

*Populated by /flow-next:work on completion.*
