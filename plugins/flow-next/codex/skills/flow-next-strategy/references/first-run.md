# Strategy first-run workflow

Loaded only after `SKILL.md` classifies the file as absent, a generated husk, or
a foreign file whose destructive rewrite the user confirmed.

## Phase 1: First-run interview

### 1.1 — Load interview rules (non-optional)

Read `references/interview.md`.

This load is non-optional. The interview reference carries the pushback rules,
anti-pattern examples, and section quality bars. Improvising it from memory
risks passive transcription.

### 1.2 — Run the interview in section order

For each of the 5 required sections (in order: `Target problem` → `Our approach` → `Who it's for` → `Key metrics` → `Tracks`), follow the per-section rule in `references/interview.md`:

- Ask the **opening question** verbatim from the references file.
- Evaluate the answer against the **strong-answer signature**.
- If the answer falls into a named anti-pattern, push back with the **sharper follow-up** — quoting the user's words back at them, NOT paraphrasing. Anti-pattern label names (`vanity`, `fluff`, `feature-list`, etc.) are internal-only — never appear in question bodies.
- **2 rounds maximum.** After round 2, capture the user's words verbatim and append the HTML comment `<!-- worth revisiting -->` to the section body. Do not let the interview spiral.
- Use **free-form responses** — no menu options, no recommendation in the question body.

### 1.3 — Per-section atomic writes

After the first section is captured, read `references/strategy-template.md`
before building the draft. This load is non-optional once a write is reached;
the reference carries the exact document shape and post-write checklist.

After each section is captured, build the partial draft and write to `STRATEGY.md` via `Write` tool **before the next question fires**. `last_updated` bumps on every save. No draft state file. Mid-flow abandonment leaves a partially-populated file readable on disk; resume is via Phase 0 → update routing.

The partial-draft shape: frontmatter + H1 + the captured section(s) + placeholder bodies (`_Not yet captured._`) for unfilled required sections. Optional sections are absent until Phase 1.4.

### 1.4 — Optional sections (gated by routing question)

After all 5 required sections land, ask once per optional section whether to include it. **Routing question** with lead-with-recommendation:

For `Milestones`:

- `body`: "Do you want a `Milestones` section? It's only worth adding if there are externally visible dated anchors — launches, fundraises, conferences, renewals. Recommended: `skip` — internal schedules don't belong here. Confidence: [your-call]."
- `options`: `include`, `skip`.

For `Not working on`:

- `body`: "Do you want a `Not working on` section? Only useful for things the team keeps being tempted by — a clarity tool, not a backlog. Recommended: `skip` — most repos don't need it. Confidence: [your-call]."
- `options`: `include`, `skip`.

A `Marketing` section is **deliberately not offered** — over-rotated for OSS-tools repos.

If `include`, run the per-section interview from `references/interview.md` (same 2-round-cap rule), then atomic-write that section. If `skip`, omit the section entirely from the file (do not leave an empty header).

### 1.5 — Mandatory read-back before final commit

After all sections captured (required + any included optional), run:

```bash
"$FLOWCTL" strategy read --json
```

Apply the post-write checklist in `references/strategy-template.md`, then show
**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

the final draft body in chat. Offer one round of edits via `plain-text numbered prompt`:

- `body`: "Draft complete. <N>-section strategy doc, <last_updated>. Recommended: `commit` — the draft reflects the captured answers verbatim. Confidence: [judgment-call]."
- `options`: `commit`, `edit-section`, `abandon`.

On `edit-section`, ask which section via single-select (5 required + included optional names), re-run the per-section interview, atomic-write, return to read-back.

On `commit`, the file is already on disk (per-section atomic writes) — this is a confirmation step, not a new write. Acknowledge with one stdout line: `Strategy doc written to <file_path>. last_updated: <date>.`

On `abandon`, leave the file as-is (partially populated is fine), exit 0.
