# Spec-template discovery — 4-tier cascade + walker

Single source of truth for HOW a skill resolves the spec-template file at runtime. The canonical scaffold itself lives at [`../templates/spec.md`](../templates/spec.md) (section list, scope-owner annotations, `## Decision Context` flat-vs-H3 conditional) — this reference owns only the resolution mechanics. Consumers: `flow-next-interview` (spec seeding), `flow-next-plan` (spec authoring), `docs/spec-template.md`.

Resolve the template via the 4-tier discovery cascade — first match wins;
do not read later tiers once a hit is found:

1. `<repo_root>/SPEC.md`           (user-customized, uppercase preferred)
2. `<repo_root>/spec.md`           (user-customized, lowercase honored)
3. `.flow/templates/spec.md`       (project-local copy from /flow-next:setup)
4. `${CLAUDE_PLUGIN_ROOT:-${DROID_PLUGIN_ROOT:-${CODEX_HOME:-$HOME/.codex}}}/templates/spec.md`
                                   (bundled — canonical source of truth)

Case-insensitive FS handling (macOS APFS, Windows NTFS): SPEC.md and
spec.md may resolve to the same inode. Probe via:

```bash
HITS=$(ls -1 SPEC.md spec.md 2>/dev/null | sort -u | wc -l | tr -d ' ')
```

where 0 → tier 1+2 miss, fall to tier 3; 1 → single hit (or case-insensitive
collapse) — use it; 2 → case-sensitive FS with both distinct, prefer
SPEC.md and print a stderr warning.

Walker (bash):

```bash
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
TEMPLATE_PATH=""
HITS=$(ls -1 "$REPO_ROOT/SPEC.md" "$REPO_ROOT/spec.md" 2>/dev/null | sort -u | wc -l | tr -d ' ')
if [ "$HITS" = "2" ]; then
  TEMPLATE_PATH="$REPO_ROOT/SPEC.md"
  echo "warn: both SPEC.md and spec.md exist at repo root; preferring uppercase." >&2
elif [ -f "$REPO_ROOT/SPEC.md" ]; then
  TEMPLATE_PATH="$REPO_ROOT/SPEC.md"
elif [ -f "$REPO_ROOT/spec.md" ]; then
  TEMPLATE_PATH="$REPO_ROOT/spec.md"
elif [ -f ".flow/templates/spec.md" ]; then
  TEMPLATE_PATH=".flow/templates/spec.md"
else
  TEMPLATE_PATH="${CLAUDE_PLUGIN_ROOT:-${DROID_PLUGIN_ROOT:-${CODEX_HOME:-$HOME/.codex}}}/templates/spec.md"
fi
TEMPLATE=$(cat "$TEMPLATE_PATH")
```

The template contains: frontmatter, the 7 canonical sections
(Goal & Context, Architecture & Data Models, API Contracts,
Edge Cases & Constraints, Acceptance Criteria, Boundaries,
Decision Context) with scope-owner HTML-comment annotations. Frontmatter +
HTML-comment scope-owner markers may be stripped from the final spec body —
they're authoring guidance, not user-visible spec content.
