---
title: "Codex mirror audit must verify R2 block lands before a COMPLETE sentence, not ju"
date: "2026-06-05"
track: bug
category: build-errors
module: "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-qa/references/qa-discipline.md"
tags: [sync-codex, codex, mirror, fn-53, AskUserQuestion, plain-text-numbered-prompt, mid-sentence-injection, multi-line-ask, tool-rewrites, audit, review-feedback]
problem_type: build-error
symptoms: "RP impl-review NEEDS_WORK: R2 numbered-prompt block injected mid-sentence in a new skill's Codex mirror; wrong-article 'an plain-text numbered prompt'"
root_cause: "Canonical live-ask phrase spanned multiple lines; injector anchors on the verb-bearing line and inserts before it, splitting the sentence. Token-only audit missed the structural break."
resolution_type: fix
related_to: [bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05, bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
fn-53.5 registered the new flow-next-qa skill on the Codex side and audited the
AskUserQuestion→numbered-prompt rewrites in the generated mirror. The first audit
pass checked for surviving tokens and obvious nonsense and looked clean, but RP
impl-review (P1) caught that the R2 numbered-prompt INSTRUCTION block had been
injected MID-SENTENCE in `codex/skills/flow-next-qa/references/qa-discipline.md`.

## What Didn't Work
A token-level audit (grep for surviving `AskUserQuestion` / `request_user_input`,
"cannot call", "blocking question", dangling ToolSearch) passed clean — but missed
the structural break. The canonical live-ask phrase spanned multiple physical lines:
"...any payment / 3rd-party test\ncredentials), **ask the user via `AskUserQuestion`**
before...". The injector anchors on the verb-bearing LINE (`ask the user via ...`)
and inserts the block BEFORE that line, so it split the sentence: "...3rd-party test
[R2 BLOCK] credentials), ask the user via...". A secondary P2: canonical "an
`AskUserQuestion` info prompt" rewrote to the wrong-article "an `plain-text numbered
prompt`".

## Solution
Per the existing prevention rule (keep live-ask phrasing on ONE physical line):
rewrote the canonical qa-discipline.md ask as a single-line leading sentence ("When
the repo does not document test accounts, **ask the user via `AskUserQuestion`**
before writing scenarios that need auth — never guess credentials.") with the
condition list moved to its own following line. For P2, reworded "an `AskUserQuestion`
info prompt" → "by asking the user via `AskUserQuestion` as an info prompt" to avoid
the wrong-article artifact. Re-synced (byte-idempotent).

## Prevention
- Auditing a new skill's Codex mirror is NOT just a token sweep. For EACH R2
  injection site, visually verify the block lands before a COMPLETE sentence —
  inspect the preceding + following lines. A clean token grep does not prove clean
  prose (the validator's documented blind spot).
- Keep every canonical live-ask ("ask the user via `AskUserQuestion`") on a SINGLE
  physical line; the injector inserts before the anchor LINE, not the sentence.
- Avoid the article "an `AskUserQuestion`" in canonical prose — it rewrites to the
  ungrammatical "an `plain-text numbered prompt`". Reword to "ask the user via
  `AskUserQuestion`".
- Cheap mechanical check after sync for any synced file with ask prose:
  `grep -n "Ask the user via plain text" <mirror>` then eyeball the line above/below.
