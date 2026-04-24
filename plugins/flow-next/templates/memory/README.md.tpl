# .flow/memory/

Categorized project memory — searchable store of bugs, patterns, and decisions.

Structure:

```
.flow/memory/
  bug/
    build-errors/
    test-failures/
    runtime-errors/
    performance/
    security/
    integration/
    data/
    ui/
  knowledge/
    architecture-patterns/
    conventions/
    tooling-decisions/
    workflow/
    best-practices/
```

Each entry is a markdown file with YAML frontmatter. Filename convention:
`<slug>-YYYY-MM-DD.md`. Entry ID = `<track>/<category>/<slug>-<YYYY-MM-DD>`.

## Tracks

- **bug** — post-mortem entries. Problem / What Didn't Work / Solution / Prevention.
  Auto-captured by Ralph on NEEDS_WORK verdicts.
- **knowledge** — human-curated guidance. Context / Guidance / When to Apply / Examples.

## Frontmatter

Required (all tracks): `title`, `date`, `track`, `category`.
Bug track adds: `problem_type`, `symptoms`, `root_cause`, `resolution_type`.
Knowledge track adds: `applies_when`.
Optional: `module`, `tags`, `status`, `stale_reason`, `stale_date`, `last_updated`, `related_to`.

## Commands

```bash
flowctl memory init                                     # create the tree
flowctl memory add --track bug --category build-errors \
  --title "..." [--module <mod>] [--tags "a,b"] \
  --problem-type build-error --body-file entry.md      # add entry (with overlap detection)
flowctl memory list [--track <t>] [--category <c>]      # list entries
flowctl memory read <entry-id>                          # read one entry
flowctl memory search <query> [--track <t>] [--category <c>]
flowctl memory migrate [--dry-run] [--yes]              # convert legacy flat files
```

Legacy flat files (`pitfalls.md`, `conventions.md`, `decisions.md`) remain readable
until `flowctl memory migrate` runs.
