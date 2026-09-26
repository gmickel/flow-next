---
title: Relaxing a validator must only admit values the writer round-trips
date: "2026-09-26"
track: bug
category: data
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-257, memory, frontmatter, validation, round-trip]
problem_type: data
symptoms: mark-* stamp rewrote a mapping-valued custom field as a quoted dict string
root_cause: allow_unknown checked key shape only; the YAML writer serializes only scalars and flat lists
resolution_type: fix
---

## Problem
fn-257 R15 let the memory `mark-*` stamps keep frontmatter fields outside the schema by relaxing `validate_memory_frontmatter` (`allow_unknown`). The writer (`_format_yaml_value`) only round-trips scalars and flat lists, so a mapping-valued custom field was rewritten as a quoted Python-dict string. Before the change validation refused the entry and nothing was written; after it, the stamp silently corrupted data. All three review draws found it.

## What Didn't Work
Admitting every unknown key that is a plain identifier: it checked the key's shape but not whether the value survives the write.

## Solution
Admit an unknown field only when its value is a scalar or a flat list (no dict, no nested list/dict items); anything else stays an "unknown fields" error, so the stamp refuses and the file is untouched (`plugins/flow-next/scripts/flowctl.py`, `validate_memory_frontmatter`). Regression: `test_memory_schema.test_allow_unknown_rejects_values_the_writer_cannot_round_trip`.

## Prevention
When loosening a validator in front of a writer, derive the admitted set from what the writer can serialize and test a round trip of each value shape (scalar, list, mapping, nested list), not just the key shape.
