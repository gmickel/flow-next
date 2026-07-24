---
title: "YAML frontmatter writer: unescaped newlines lose the entry; frontmatter-only wri"
date: "2026-07-24"
track: bug
category: data
module: plugins/flow-next/scripts/flowctl.py
tags: [memory, yaml, frontmatter, round-trip]
problem_type: data
symptoms: "entry reads back as {} after a write; body blank lines change on a status-only mutation"
root_cause: control chars emitted unquoted in YAML scalars; write_memory_entry normalized the body on every write
resolution_type: fix
related_to: [bug/data/fence-preserving-writer-needs-fence-2026-07-02, bug/data/migrationrollback-cli-10-review-cycle-2026-05-08, bug/data/paired-snapshot-setter-must-write-both-2026-06-03]
---

## Problem
Adding a new `--gate-ref` string field to a memory entry exposed two latent
defects in the shared memory frontmatter writer, both flagged by impl-review:

1. A value containing a newline was emitted unquoted/unescaped, splitting the
   YAML scalar across lines. The write reported success; every later read
   returned `{}` (whole entry silently unreadable). Reachable from any string
   field - `mark-stale --reason` had the same hole.
2. Frontmatter-only mutations reflowed the body: `_memory_read_entry` strips
   leading newlines and `write_memory_entry` collapsed trailing ones, so a
   hand-written entry lost blank lines it never asked to lose.

## What Didn't Work
Arguing that both were pre-existing shared-writer behavior and documenting the
normalization in the docstring. The reviewer re-raised both as Major - correct
call: "the sibling command does it too" is not a contract, and a silent-read-as-
empty is data loss no matter which command triggers it.

## Solution
- `_quote_yaml_scalar` escapes `\n` / `\r` / `\t` and other C0/DEL characters;
  `_yaml_scalar_needs_quoting` returns True when any control char is present.
- The no-PyYAML inline fallback parser gained a matching `_unquote_yaml_double`
  helper so both parsers agree (they diverged before: PyYAML decoded escapes,
  the fallback returned them literally).
- `write_memory_entry` gained `raw_body=<verbatim post-frontmatter segment>`;
  `mark-stale` / `mark-fresh` / `mark-hardened` all pass it, so a
  frontmatter-only write is byte-identical below the closing `---`.

## Prevention
When a new CLI flag stores user text into YAML frontmatter, test the round-trip
with a hostile value (embedded newline, tab, leading/trailing spaces) through
the real argparse path AND through both parsers - not just the happy string.
For frontmatter-only mutations, assert on the raw post-frontmatter segment, not
on the parsed body: a parsed-body comparison passes while the file changes.
