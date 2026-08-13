# Glossary scan (gated reference)

> **Loaded only when the workflow.md Phase 0.5 gate prints its active sentinel**
> — at least one `GLOSSARY.md` exists on the ancestor chain, or the gate's probe
> or parse errored (fail open). A repo with no glossary never reads this file:
> Phase 0.5 is a silent no-op and the report's Glossary counts are all zero.
> The Glossary section of the Phase 5 report schema itself stays inline in
> workflow.md and prints on every run.

Contents:

- [Phase 0.5: Glossary scan](#phase-05-glossary-scan) — pointer to the goal / when-it-applies rule in workflow.md
- [0.5.1 — Enumerate glossaries](#051--enumerate-glossaries) — `flowctl glossary list --json` shape
- [0.5.2 — Per-term code search](#052--per-term-code-search) — corpus, whole-word match, decision table
- [0.5.3 — Stale-marking via Edit tool](#053--stale-marking-via-edit-tool) — HTML comment, idempotency, never delete
- [0.5.4 — Husk awareness](#054--husk-awareness) — `count: 0` files
- [0.5.5 — Alias-creep handling](#055--alias-creep-handling) — interactive question vs autofix report
- [0.5.6 — Carry into Phase 5 report](#056--carry-into-phase-5-report) — the four glossary counts
- [4.4.1 — Glossary stale-marking (Phase 0.5 outcomes)](#441--glossary-stale-marking-phase-05-outcomes) — the Phase 4 execution half

## Phase 0.5: Glossary scan

The goal and the when-this-applies rule are stated once, in workflow.md §Phase 0.5 — the section you were reading when this gate fired. This file owns the execution.

### 0.5.1 — Enumerate glossaries

Use the flowctl helper as the single source of truth:

```bash
GLOSSARY_JSON="$("$FLOWCTL" glossary list --json 2>/dev/null || echo '{"groups":[],"file_count":0,"total_terms":0}')"
```

JSON shape (fn-38 task 2):

```json
{
  "groups": [
    {
      "path": "/abs/path/GLOSSARY.md",
      "entries": [
        {
          "term": "<canonical>",
          "definition": "<one-line>",
          "avoid": ["<alias-1>", "<alias-2>"],
          "relates_to": ["<other-term>"]
        }
      ],
      "count": 1
    }
  ],
  "file_count": 1,
  "total_terms": 1
}
```

When `file_count == 0`, skip Phase 0.5 entirely. When `total_terms == 0` but `file_count > 0`, every group is a husk (see §0.5.4).

### 0.5.2 — Per-term code search

For each `(group, entry)` where `count > 0`:

1. **Build the search corpus** — tracked source files only. Use `git ls-files` to honor `.gitignore`; exclude `.flow/`, the glossary file itself, and known build artifacts:

   ```bash
   git -C "$REPO_ROOT" ls-files -z \
     | grep -zvE '^\.flow/|/GLOSSARY\.md$|^GLOSSARY\.md$|/node_modules/|/\.git/' \
     > /tmp/glossary-corpus.zlist
   ```

   On platforms where Bash file ops gate behind permissions, the host agent should fall back to Glob with the equivalent exclusion pattern.

2. **Search for the term** — case-insensitive, whole-word match (matches T2's `_glossary_term_matches` invariant). Normalize whitespace in the term first (collapse runs of whitespace to a single space), then anchor with `\b`:

   ```bash
   TERM_NORM="$(printf '%s' "$term" | tr -s '[:space:]' ' ')"
   TERM_HITS=$(xargs -0 grep -liEw -- "$(printf '%s' "$TERM_NORM" | sed 's/[][\.*^$\/]/\\&/g')" \
                 < /tmp/glossary-corpus.zlist 2>/dev/null | wc -l | tr -d ' ')
   ```

   The agent may also use the Grep tool directly with an equivalent pattern; either path is fine.

3. **Search for each `_Avoid_` alias** — same matching rule. Aggregate alias hits per-alias so the report can name the offending alias.

4. **Decide:**

   | Term hits | Any alias hits | Outcome |
   |-----------|----------------|---------|
   | ≥1 | (n/a) | **Keep** — record reviewed-without-change |
   | 0 | 0 | **Mark stale** — Edit tool, append HTML comment after the term heading |
   | 0 | ≥1 | **Mark stale + alias-creep flag** — same Edit, plus surface to Phase 3 (interactive) or report (autofix) |
   | ≥1 | ≥1 | **Alias-creep flag only** — term is alive but an alias is being used in code; do not mark stale |

### 0.5.3 — Stale-marking via Edit tool

There is no `flowctl glossary mark-stale` subcommand. fn-38 task 2 shipped only `add / list / read / remove`; stale-marking is an Edit-tool operation on the glossary file directly.

The Edit appends an HTML comment immediately after the term heading line (preserves the body untouched, never deletes the entry). The comment lives between the heading and the definition paragraph so a casual reader sees it and `flowctl glossary list` still parses cleanly:

```text
## <Term>

<!-- stale: zero hits in tracked code on <YYYY-MM-DD> (audited-by: /flow-next:audit) -->

<one-line definition>

_Avoid_: alias-1, alias-2
```

Idempotency: when the heading already has a `<!-- stale: ... -->` comment immediately following, replace the comment in place rather than stacking. Use `Edit` with `old_string` matching the existing comment line.

**The agent must not delete the term entry on stale-detection.** Deletion is the operator's call. The audit surfaces it as a Phase 5 recommendation:

```
Recommended manual review: GLOSSARY.md term "<term>" has no code hits.
Stale comment added; consider `flowctl glossary remove <term>` if the concept is gone.
```

### 0.5.4 — Husk awareness

A glossary file with `count: 0` (the file is `# Glossary` H1 followed by no term entries — left intact after the last term was removed; see fn-38 task 2 R18) skips the per-term walk. Surface a single Phase 5 advisory per husk:

```
GLOSSARY.md at <relative path> is an empty husk (no terms defined).
flow-next keeps it as project state per fn-38 R18 — remove it manually if no
longer needed.
```

The audit never deletes the file.

### 0.5.5 — Alias-creep handling

When a term has alias hits in code (whether or not the canonical term also has hits):

- **Interactive (Phase 3):** present per alias as a question. Lead with the recommendation:

  ```
  Glossary term: "<term>" (defined in <relative path>)
  _Avoid_ alias "<alias>" appears in tracked code at <file:line> (and N other locations).

  Options:
    1. Rename the code uses to "<term>" (recommended)
    2. Drop "<alias>" from the _Avoid_ list (alias is now acceptable)
    3. Skip — surface in report only
  ```

  Option 1 is a code-edit recommendation only — the audit reports the locations; the operator handles the rename. (Mass-renaming code from a memory audit is out of scope.)
  Option 2 is an Edit on the glossary file: remove the alias from the `_Avoid_` list while preserving the rest of the entry.

- **Autofix:** never auto-rename code. Surface the alias-creep finding in the report under "Recommended" with file:line locations. The agent does not Edit the glossary unless the term itself is also stale (in which case the stale comment captures the alias-creep too).

### 0.5.6 — Carry into Phase 5 report

Capture the per-term outcomes into a glossary section of the report (see §5.1 below). Counts:

- `glossary_kept` — terms with code hits.
- `glossary_marked_stale` — terms with zero code hits and zero alias hits, stale comment applied.
- `glossary_alias_creep` — terms whose `_Avoid_` aliases hit code (regardless of canonical hit count).
- `glossary_husks` — files with `count: 0`.

### Done when

- Every glossary group with `count > 0` has every term decided (Keep / mark stale / alias-creep).
- Every husk file has a queued advisory.
- The orchestrator has a glossary-side decision map alongside the memory-side investigation map.
---

### 4.4.1 — Glossary stale-marking (Phase 0.5 outcomes)

For each glossary term flagged "Mark stale" in Phase 0.5, the orchestrator applies the Edit on the main thread (no subagent — short, focused edits):

1. Open the glossary file via Read.
2. Edit the line immediately after the `## <Term>` heading. If a `<!-- stale: ... -->` comment already exists there, replace it (idempotent re-mark). Otherwise insert it as a new line above the definition paragraph.
3. The comment text is `<!-- stale: zero hits in tracked code on <YYYY-MM-DD> (audited-by: /flow-next:audit) -->`.

Glossary edits stage in the same git context as memory edits (Phase 5 picks the commit strategy uniformly across both).

For alias-creep findings without a stale-flag (term has hits, but `_Avoid_` alias also has hits), the orchestrator does **not** edit the glossary in autofix mode. Interactive mode may edit only if the user picks "Drop the alias from `_Avoid_`" in Phase 3. Code renames are out of scope — the audit reports file:line locations and stops there.
