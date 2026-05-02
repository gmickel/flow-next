# Strategy Template

Loaded by `SKILL.md` after each section is captured. Fill it in using the captured answers and write to `STRATEGY.md` via the `Write` tool. Per-section atomic writes mean each section lands on disk before the next interview prompt fires.

## Rules for filling in

- Use the user's own language where possible. Do not paraphrase into generic PM-speak.
- Each section stays compact. The whole doc should read in under 5 minutes.
- Section order is locked. Do not add new top-level sections (a `Marketing` section was considered and deliberately excluded — over-rotated for OSS-tools repos).
- Optional sections: delete entirely if unused. Do not leave empty headers.
- Set `last_updated` in the YAML frontmatter to today's ISO date (`YYYY-MM-DD`). Do not duplicate the date in prose.
- Set `name` in the frontmatter to the product or initiative name (the same value used in the H1 title).
- Set `generator: flow-next-strategy` in the frontmatter (foreign-file detection sentinel — required).
- After 2 rounds of pushback that didn't land, capture the user's words verbatim and append `<!-- worth revisiting -->` to that section's body. Phase 2 surfaces these markers as priority candidates on re-run.

## Template

The block below is the literal file shape (minus this line and the fences). Replace every `{{placeholder}}` with the captured answer. Delete any optional section whose placeholder wasn't answered.

~~~markdown
---
name: {{product_name}}
last_updated: {{YYYY-MM-DD}}
generator: flow-next-strategy
---

# {{product_name}} Strategy

## Target problem

{{1-2 sentence diagnosis. Names the user situation and the crux that makes it hard. No solution language.}}

## Our approach

{{1-2 sentence guiding policy. What this product commits to, so that the target problem becomes tractable.}}

## Who it's for

**Primary:** {{Persona name}} — {{one-sentence JTBD, e.g. "They're hiring {{product_name}} to..."}}

<!-- Duplicate the block above for additional personas only if truly necessary. Fewer is better. -->

## Key metrics

- **{{metric 1 name}}** — {{one-line definition; where it's measured}}
- **{{metric 2 name}}** — {{...}}
- **{{metric 3 name}}** — {{...}}

<!-- 3-5 total. Stop at 5. -->

## Tracks

### {{Track 1 name}}

{{One line: what this track is — the investment area, not a feature list.}}

_Why it serves the approach:_ {{one line}}

<!-- Duplicate the block above for 2-4 tracks total. If you can't keep it to 4, something is wrong — fold related tracks together. -->

## Milestones

- **{{YYYY-MM-DD}}** — {{milestone}}

<!-- Optional. Delete the section if unused. Only externally visible milestones: launches, fundraises, conferences, renewals. -->

## Not working on

- {{one line per item}}

<!-- Optional. Delete the section if unused. Use only for things the team keeps being tempted by. -->
~~~

## Post-write checklist

Before showing the read-back to the user, scan the draft for:

- [ ] Frontmatter present at the top with `name`, `last_updated`, and `generator: flow-next-strategy` keys.
- [ ] `last_updated` carries today's date in ISO format (YYYY-MM-DD).
- [ ] No section has more than 4 sentences except `Tracks` (where each track has its own short block).
- [ ] No placeholders remain (`{{...}}`).
- [ ] Optional sections with no content have been deleted, not left empty (the H2 header is gone — file does not contain `## Milestones` if it has no items).
- [ ] Metric count is between 3 and 5. Track count is between 2 and 4.
- [ ] `Target problem` and `Our approach` are connected — one clearly responds to the other.
- [ ] `<!-- worth revisiting -->` markers (if any) are inside the section body, after the captured prose — not in the header line.
- [ ] H1 title matches the frontmatter `name` value.
