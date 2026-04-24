# fn-30-memory-schema-upgrade.1 Schema + directory tree + YAML frontmatter + entry templates

## Description

Define and implement the new memory directory structure, YAML frontmatter schema (bug + knowledge tracks), and entry templates. Foundation task for the rest of the epic.

**Size:** M

**Files:**
- `plugins/flow-next/scripts/flowctl.py` — schema constants, category enums, frontmatter read/write helpers
- `.flow/bin/flowctl.py` (mirror)
- `plugins/flow-next/templates/memory/README.md.tpl`
- `plugins/flow-next/templates/memory/bug-track-entry.md.tpl`
- `plugins/flow-next/templates/memory/knowledge-track-entry.md.tpl`

## Schema constants (in flowctl.py)

```python
MEMORY_TRACKS = ("bug", "knowledge")

MEMORY_CATEGORIES = {
    "bug": [
        "build-errors",
        "test-failures",
        "runtime-errors",
        "performance",
        "security",
        "integration",
        "data",
        "ui",
    ],
    "knowledge": [
        "architecture-patterns",
        "conventions",
        "tooling-decisions",
        "workflow",
        "best-practices",
    ],
}

MEMORY_REQUIRED_FIELDS = {"title", "date", "track", "category"}
MEMORY_OPTIONAL_FIELDS = {"module", "tags", "status", "stale_reason", "stale_date", "last_updated", "related_to"}

MEMORY_BUG_FIELDS = {"problem_type", "symptoms", "root_cause", "resolution_type"}
MEMORY_KNOWLEDGE_FIELDS = {"applies_when"}

MEMORY_PROBLEM_TYPES = (
    "build-error",
    "test-failure",
    "runtime-error",
    "performance",
    "security",
    "integration",
    "data",
    "ui",
)

MEMORY_RESOLUTION_TYPES = ("fix", "workaround", "documentation", "refactor")
MEMORY_STATUS = ("active", "stale")
```

## Frontmatter helpers

```python
def parse_memory_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a memory entry. Returns dict (empty on absent/malformed)."""

def write_memory_entry(path: Path, frontmatter: dict, body: str) -> None:
    """Write entry with deterministic field order. Validates required fields."""

def validate_memory_frontmatter(frontmatter: dict) -> list[str]:
    """Return list of validation errors (empty = valid)."""
```

Minimal inline YAML parser for read (triple-dash delimited, flat key: value with list support). Write uses hand-formatted output with fixed field order. PyYAML is optional; `import yaml` is wrapped in try/except and falls back to the inline parser. This keeps zero-dep.

## Directory creation on `memory init`

When `flowctl memory init` runs:

```
.flow/memory/
  README.md                 (from README.md.tpl)
  bug/
    build-errors/.gitkeep
    test-failures/.gitkeep
    runtime-errors/.gitkeep
    performance/.gitkeep
    security/.gitkeep
    integration/.gitkeep
    data/.gitkeep
    ui/.gitkeep
  knowledge/
    architecture-patterns/.gitkeep
    conventions/.gitkeep
    tooling-decisions/.gitkeep
    workflow/.gitkeep
    best-practices/.gitkeep
```

If legacy flat files (`pitfalls.md`, `conventions.md`, `decisions.md`) exist, `init` leaves them in place and prints a one-line hint:

> Legacy memory files detected. Run `flowctl memory migrate` to convert to the new categorized schema.

## Entry templates

### bug-track-entry.md.tpl

```markdown
---
title: {{title}}
date: {{date}}
track: bug
category: {{category}}
module: {{module}}
tags: [{{tags}}]
problem_type: {{problem_type}}
symptoms: {{symptoms}}
root_cause: {{root_cause}}
resolution_type: {{resolution_type}}
---

## Problem

{{problem}}

## What Didn't Work

{{what_didnt_work}}

## Solution

{{solution}}

## Prevention

{{prevention}}
```

### knowledge-track-entry.md.tpl

```markdown
---
title: {{title}}
date: {{date}}
track: knowledge
category: {{category}}
module: {{module}}
tags: [{{tags}}]
applies_when: {{applies_when}}
---

## Context

{{context}}

## Guidance

{{guidance}}

## When to Apply

{{when_to_apply}}

## Examples

{{examples}}
```

### README.md.tpl

Describes the tree, schema, and commands. One page. Static prose — no mustache templating needed; just a literal file.

## Entry ID convention

Entry ID = `<track>/<category>/<slug>-<YYYY-MM-DD>`. Matches filepath from `.flow/memory/` root.

Slug rules: lowercase, hyphenated, max 60 chars, derived from title.

## Acceptance

- **AC1:** `flowctl memory init` creates the full tree structure with `.gitkeep` placeholders.
- **AC2:** Category enum constants defined in flowctl.py; `MEMORY_CATEGORIES["bug"]` returns 8 entries, `MEMORY_CATEGORIES["knowledge"]` returns 5 entries.
- **AC3:** Inline YAML parser reads frontmatter correctly for valid entries; returns empty dict on malformed.
- **AC4:** `validate_memory_frontmatter()` returns error list for missing required fields, unknown fields, invalid enum values.
- **AC5:** Entry templates at `plugins/flow-next/templates/memory/*.md.tpl` exist and are self-contained.
- **AC6:** `memory init` on a repo with legacy flat files prints migration hint and preserves legacy files.
- **AC7:** PyYAML is optional — flowctl runs the same with or without it installed.
- **AC8:** Unit tests cover frontmatter round-trip (write → parse → equality).

## Dependencies

None — this is the foundation.

## Done summary
Schema + directory tree + YAML frontmatter + entry templates shipped.

- `.flow/memory/` tree: `bug/<category>/` and `knowledge/<category>/` with fixed category lists baked into flowctl.
- YAML frontmatter schema with track-specific fields (problem_type/root_cause/resolution_type for bug; applies_when for knowledge).
- Entry templates in `plugins/flow-next/templates/memory/`: bug-track-entry.md.tpl, knowledge-track-entry.md.tpl, README.md.tpl.
- `plugins/flow-next/tests/test_memory_schema.py` (371 lines) covers schema validation.
- Smoke extended; 74/74 pass.
- `flowctl memory init` creates tree + README.md using templates.
## Evidence
- Commits: 95bf5b8
- Tests: plugins/flow-next/scripts/smoke_test.sh (74/74), plugins/flow-next/tests/test_memory_schema.py
- PRs: