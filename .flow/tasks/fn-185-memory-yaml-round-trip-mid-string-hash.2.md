---
satisfies: [R4]
---
# fn-185-memory-yaml-round-trip-mid-string-hash.2 Repair the damaged memory entry (quote the truncating title)

## Description
Quote the title: value in .flow/memory/bug/integration/set-tracker-id-rejected-github-n-2026-06-03.md so a conforming YAML parser reads the full text "set-tracker-id rejected GitHub #N identifiers (Linear-only handle validator)". Use double quotes matching the writer's own output format for that value (verify by rendering through the fixed _format_yaml_value and using its exact rendering). No other frontmatter or body changes. Verify with a conforming parser (uv run --with pyyaml python3 -c ... or ruby -ryaml) that the full title round-trips.

## Acceptance
R4: title survives a conforming-parser read verbatim; file otherwise byte-identical; flowctl memory list/search still returns the entry.

## Done summary
Quoted the title of .flow/memory/bug/integration/set-tracker-id-rejected-github-n-2026-06-03.md using the fixed writer's rendering; verified verbatim round-trip under PyYAML (uv run --with pyyaml) and flowctl memory search still returns the entry. No other frontmatter/body changes.
## Evidence
- Commits: 0f23fe1e
- Tests: uv run --with pyyaml python3 -c 'yaml.safe_load frontmatter round-trip assert'
- PRs: