---
title: "fn-44.5 review: R17 enforcement beyond R21 awk drift-guard"
date: "2026-05-15"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-capture
tags: [fn-44, scope-flag, impl-review, codex-review, r17-cross-link, r21-drift-guard, capture-skill, canonical-template]
problem_type: build-error
symptoms: Codex review flagged §2.2 canonical-section enumeration as defeating R17 even though R21 awk drift-guard didn't trip
root_cause: R21's awk guard only catches  heading at column 1; R17's intent (skill markdown never structures around canonical section sequence) needs semantic review beyond structural regex
resolution_type: fix
related_to: [bug/build-errors/agent-rename-epic-id-prompt-key-changes-2026-05-08, bug/build-errors/codex-impl-review-false-positive-on-2026-05-09, bug/build-errors/fn-441-review-cycle-json-contracts-html-2026-05-15, bug/build-errors/fn-442-review-both-pass-policy-2026-05-15, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem

T5 of fn-44 (capture biz-context routing + R25 suggestion footer) hit one round of codex NEEDS_WORK before SHIP. One Major finding: `workflow.md` §2.2 enumerated the canonical spec section sequence (`Goal & Context` / `Architecture & Data Models` / `API Contracts` / `Edge Cases & Constraints` / `Acceptance Criteria` / `Boundaries` / `Decision Context`) as per-section bullets with biz-routing annotations, in the same paragraph that **claimed** to follow R17 "cross-link, never re-embed the section list."

The R21 awk drift-guard (`sync-codex.sh:874-928`) DID NOT catch this — the guard only fires on `^## ` headings at column 1 within a 30-line window. The §2.2 bullets used backticks (` - **`## Goal & Context`** — ... `), which is structurally fine for the awk regex but semantically equivalent for the reviewer.

## What Didn't Work

The pre-fn-44.5 §2.2 already had a bullet-list-per-canonical-section pattern (inherited from pre-fn-44 spec template days). My T5 edit added biz-routing annotations to the existing bullets ("Receives biz-context signal categories 1, 2, 9 (and optionally 5, 8 — see §2.6)") on the assumption that touching only the per-section commentary preserved the existing structure. The reviewer's correct read: keeping the section enumeration alive — even with new annotations — is exactly what R17 is trying to eliminate. The drift hazard isn't the headings themselves; it's any structured listing of "here's the canonical order" outside the template.

## Solution

Replaced §2.2's per-section bullets with two new lists:

1. **Per-tag application rules** — `[user]` / `[paraphrase]` / `[inferred]` / `[strategy:<track>]` apply across all sections; tag-driven not section-driven.
2. **Auxiliary section rules** — only mention destination sections (`## Decision Context`, `## Acceptance Criteria`, `## Requirement coverage`) when biz routing or R-ID allocation requires it. NEVER list `Architecture & Data Models` / `API Contracts` / `Edge Cases & Constraints` (the pure-tech sections that have no capture-specific rules beyond the template's own).

Cross-linked `plugins/flow-next/templates/spec.md` at the section opener; the template owns the sequence.

## Prevention

- **R17 isn't just "don't duplicate headings at column 1"** — it's "never structure your skill prose around the canonical section sequence." If your skill markdown has a bullet-per-canonical-section pattern (any format: `## X`, `**X**`, `` `## X` ``, etc.), you're duplicating the template's ownership even if R21's awk regex doesn't trip.
- **Audit pattern**: when editing capture/interview/plan skill prose, count the canonical-section names referenced. If you mention 5+ of the 7 canonical sections, you're enumerating — refactor to per-tag or per-rule organization. Mention only the destinations your specific section / phase needs.
- **R21 drift guard scope** — the awk-based guard is structural (catches the most obvious form: `^## Heading` at column 1 within 30 lines). Reviewers add semantic catch — the codex impl-review at `codex:gpt-5.5:high` reliably catches the looser pattern. Pair the two.
- **Codex catch rate** — `codex:gpt-5.5:high` caught this in one pass on first review. Same model class that worked for fn-44.1 (5 cycles), fn-44.2 (1 cycle), fn-44.3 (1 cycle), fn-44.5 (1 cycle). The right backend for fn-44-class documentation-merge-contract reviews.
