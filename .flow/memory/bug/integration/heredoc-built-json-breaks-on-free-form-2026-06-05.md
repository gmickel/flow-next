---
title: Heredoc-built JSON breaks on free-form interpolated values
date: "2026-06-05"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-work/references/worker-handover.md
tags: [json, shell, receipt, escaping, skill-authoring]
problem_type: integration
symptoms: "Receipt or evidence JSON is malformed (or open to field injection) when an interpolated reason or test command contains a quote, backslash, or newline"
root_cause: cat<<EOF heredoc raw-interpolated free-form agent strings instead of JSON-encoding them
resolution_type: fix
last_updated: "2026-10-05"
last_audited: "2026-10-05"
---

## Problem
A skill `workflow.md` (qa) documented building a JSON receipt with a `cat > "$FILE" <<EOF` heredoc that raw-interpolated shell variables, including free-form, agent-authored strings (`blocked_reason` / `na_reason` filled from observed driver errors or spec text). As soon as such a value contains a double quote, backslash, or newline, the heredoc emits malformed JSON (or allows field injection) and downstream `json`/`jq` parsing fails.

The 2026-10 audit found the same shape in the work skill's handover evidence snippet (`worker-handover.md`), which wrote test commands into `tests[]` through an unquoted `cat <<EOF`; a test command containing a quote breaks the evidence JSON.

## What Didn't Work
Mirroring an existing receipt-write idiom (`cat <<EOF` with `"$VAR"` interpolation). That idiom is safe only where every interpolated value is constrained (enum verdicts, ISO timestamps, id slugs), never free-form prose or commands. Reusing it for arbitrary text inherited an unsafe assumption.

## Solution
qa built the JSON with `python3` + `json.dump` instead: the fields (including the free-form reasons) are exported via `os.environ` and read in a `python3 - "$OUT" <<'PY'` block, so the encoder escapes them; a reason is included only for its matching outcome. Verified: a reason with `"`, `\` and an embedded newline serializes to valid JSON.

## Prevention
When a documented shell snippet writes JSON/YAML/SQL and any interpolated value is free-form (user or agent text, error messages, test commands, file paths), never use a heredoc or string concatenation:
- Prefer a flowctl writer that takes the values as arguments: `flowctl done --test <cmd>` (repeatable) for test commands, `flowctl qa receipt --from-json` for QA receipts.
- Otherwise serialize with `jq -n --arg` / `--argjson` (or `python3` + `json.dump`).
- Reserve `cat <<EOF` for JSON whose every interpolated field is a constrained token (enum, timestamp, validated id). A fixture with a hostile value (quote + backslash + newline) catches the whole class.
