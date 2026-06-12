---
title: Embedded self-check greps in reference docs need POSIX classes + whitespace tole
date: "2026-06-12"
track: bug
category: build-errors
module: plugins/flow-next/references/html-artifacts.md
tags: [fn-62, reference-doc, grep, portability, bsd-grep, self-check, copy-paste-blocks, review-feedback]
problem_type: build-error
symptoms: self-check grep missed spaced fetch(); print block contradicted the A4 hard rule
root_cause: PCRE shorthand in BSD grep -E + copy-paste block not diffed against its prose rule
resolution_type: fix
related_to: [bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11, bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10, bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11, bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
fn-62.2 shipped a disclosure reference (plugins/flow-next/references/html-artifacts.md) carrying an embedded bash self-check grep for external resources in generated HTML. RP impl-review flagged: the pattern `fetch\(` missed `fetch (` / spaced forms, and the copy-paste print-CSS block hardcoded `size: A4 landscape` while the hard rule said plain A4 unless a DAG is present — a contradiction an agent following the doc verbatim would replicate.

## What Didn't Work
Writing the embedded grep as PCRE-flavored shorthand (`fetch\(`, `\s*`) — `\s` is unreliable in BSD grep -E (macOS), and exact-token patterns miss legal whitespace variants of the call.

## Solution
Use POSIX classes + whitespace tolerance in any shell snippet agents will copy-run: `fetch[[:space:]]*\(`, `url\([[:space:]]*...`. Make every copy-paste block agree with the prose rule it implements (print block defaults `size: A4` with a comment to switch to landscape only with a DAG). Commit 5ba324d.

## Prevention
When a reference/skill doc embeds a checking command, test it against adversarial inputs before shipping (e.g. `fetch ("https://x")`), use `[[:space:]]` not `\s` for BSD/macOS grep, and diff every copy-paste block against the prose hard rule it encodes — copy-paste blocks ARE the spec for downstream agents; contradictions propagate verbatim.
