---
title: Heredoc-built JSON breaks on free-form interpolated values
date: "2026-06-05"
track: bug
category: integration
module: skills/flow-next-qa/workflow.md
tags: [json, shell, receipt, escaping, skill-authoring]
problem_type: integration
symptoms: "qa_verdict receipt emits malformed JSON / field injection when blocked_reason or na_reason contains a quote, backslash, or newline"
root_cause: cat<<EOF heredoc raw-interpolated free-form agent strings instead of JSON-encoding them
resolution_type: fix
related_to: [bug/integration/drop-receipt-to-break-codex-2026-05-09]
---

## Problem
A skill `workflow.md` documented building a JSON receipt with a `cat > "$FILE" <<EOF` heredoc that raw-interpolated shell variables — including free-form, agent-authored strings (`blocked_reason` / `na_reason` filled from observed driver errors or spec text). The moment such a reason contains a double-quote, backslash, or newline, the heredoc emits malformed JSON (or allows field injection), so the receipt fails downstream `json`/`jq` parsing and `ralph-guard` validation.

## What Didn't Work
The first pass mirrored the existing impl-review-RP / make-pr receipt-write idiom (`cat <<EOF` with `"$VAR"` interpolation). That precedent is safe there only because those receipts interpolate constrained values (enum verdicts, ISO timestamps, id slugs) — never free-form prose. Reusing the idiom verbatim for fields that carry arbitrary text inherited an unsafe assumption.

## Solution
Build the JSON with `python3` + `json.dump` instead of a heredoc: export the fields (including the free-form reasons) via `os.environ`, read them in a `python3 - "$OUT" <<'PY'` block, and let the JSON encoder escape them. Conditionally include a reason only for its matching outcome via `os.environ.get(...)` truthiness. `jq -n --arg`/`--argjson` is the equivalent fix when python isn't preferred. Verified: a reason with `"`, `\`, and an embedded newline serializes to valid JSON and passes `ralph-guard.validate_receipt_data` (returns '').

## Prevention
When a documented shell snippet writes JSON/YAML/SQL and ANY interpolated value is free-form (user/agent text, error messages, file paths), never use a heredoc/string-concat — serialize via `python3 -c`/`json.dump` or `jq -n --arg`. Reserve `cat <<EOF` for JSON whose every interpolated field is a constrained token (enum, timestamp, validated id). A quick test fixture with a hostile value (quote + backslash + newline) catches the whole class.
