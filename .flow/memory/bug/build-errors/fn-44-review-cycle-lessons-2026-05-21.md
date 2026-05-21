---
title: "fn-44 review-cycle lessons (10+ NEEDS_WORK rounds across 4 tasks)"
date: "2026-05-21"
track: bug
category: build-errors
module: "plugins/flow-next/skills/flow-next-interview, plugins/flow-next/skills/flow-next-capture, plugins/flow-next/scripts/flowctl.py, scripts/sync-codex.sh, plugins/flow-next/templates/spec.md"
tags: [fn-44, scope-flag, impl-review, codex-review, json-contract, html-comments, r17-cross-link, r21-drift-guard, merge-contract, auxiliary-sections, scoped-diff, relative-paths, codex-mirror]
problem_type: build-error
symptoms: "10+ NEEDS_WORK rounds across fn-44 tasks (T1/T2/T5/T7) from codex:gpt-5.5:high impl-review backend"
root_cause: "Multiple invariants treated as happy-path concerns rather than enforced patterns across contract surfaces (JSON, HTML, merge, scoped diff, R17/R21 guards)"
resolution_type: fix
related_to: [bug/build-errors/template-rewrite-env-var-cascade-2026-05-09, bug/test-failures/test-production-path-not-parallel-construction-2026-05-21]
audit_consolidates: [bug/build-errors/fn-441-review-cycle-json-contracts-html-2026-05-15, bug/build-errors/fn-442-review-both-pass-policy-2026-05-15, bug/build-errors/fn-445-review-r17-enforcement-beyond-2026-05-15, bug/build-errors/fn-447-review-cycle-scoped-diff-false-2026-05-15]
---

## Problem

The fn-44 (symmetric `--scope=business|technical|both` interview) implementation went through 10+ NEEDS_WORK rounds with codex review across four tasks (T1 / T2 / T5 / T7). Same backend, same reviewer, repeated patterns. This entry consolidates the four per-task lessons into reusable invariants.

## Lessons by surface

### `--json` and CLI exit-code contracts (from T1)

- `--json` must be threaded through every subcommand in a parser tree — not just the top-level. Codex flags missing-`--json` as Major because contract-violation is the whole point of the flag.
- `argparse choices=[...]` rejects unrecognized values BEFORE the handler runs, so any test that sends an exotic value to a `--json` command gets a stderr error, not a JSON error envelope. Either accept the value and route inside the handler, or document that the choice list IS the contract.
- Plain-mode vs JSON-mode exit-code semantics diverge: plain mode may exit 1 to communicate "no-fire" via signal; JSON mode must exit 0 with `{"fired": false}` because the JSON IS the signal. Don't propagate plain-mode exit codes through to `--json` callers.

### HTML comments and templates (from T1)

- Markdown HTML comments do NOT nest. A comment block `<!-- outer <!-- inner --> -->` renders the inner `-->` as the outer's close, leaving stray `-->` text visible. If you need a "two levels of authorial commentary" pattern, use a single comment with prose-only conventions inside.
- A snippet that references `templates/spec.md` requires that templates be installed by the skill that emits the snippet — file existence is not the snippet's responsibility, it's the install workflow's responsibility. R20 (install-step physical-copy) catches this.

### Multi-phase merge contracts (from T2)

- Per-phase write-policy recomputation is mandatory when scope is multi-phase. A single upfront `scope-policy` call applied to all phases is wrong because each phase recomputes effective_write_policy against its own scope context (BUSINESS-pass vs TECHNICAL-pass under `--scope=both`).
- R21 awk drift-guard (in `sync-codex.sh`) catches **duplication** of canonical section sequence at column 1 (`^## Goal & Context` co-occurring with `^## Architecture & Data Models` co-occurring with `^## API Contracts`). It does NOT catch **stale-layout contradictions** — e.g. heredoc section names that pre-date the canonical template. Add semantic review beyond structural regex when a task touches skill prose that references canonical sections.
- Auxiliary-section enumeration copy-pasted across 4+ preservation lists will inherit an incomplete original. Enumerate once (the canonical template's frontmatter `auxiliary_sections:` list IS the source of truth) and reference; never copy.

### R17 semantic enforcement vs R21 structural (from T5)

- R17 = semantic: "skill markdown never structures itself around the canonical section sequence". Defeated by §2.2-style enumeration even when each individual section name is wrapped in backticks (which evades R21).
- R21 = structural: awk-guard for `^## ` co-occurrence at column 1. Misses prose enumeration and backtick-quoted lists.
- Both guards together do NOT replace human-judgment review. When a skill talks ABOUT the canonical sections, prefer cross-linking the template over enumerating sections inline. Cross-link discipline is the R17 enforcement.

### Scoped-diff review false-positives (from T7)

- `flowctl codex impl-review --base <commit>` only sees diffs since `BASE_COMMIT`. Commit-message explanations of pre-`BASE_COMMIT` state don't satisfy the reviewer.
- Workaround: include the files in the current diff (touch them harmlessly or document the satisfied state IN the diff via a comment), or pass `--base` further back to widen the window.

### Codex mirror relative-path drift (from T7)

- Mirror lives at `plugins/flow-next/codex/skills/<name>/` — one directory deeper than canonical at `plugins/flow-next/skills/<name>/`. Any `../../foo` link from a skill resolves wrong in the mirror (resolves to `plugins/foo` instead of repo root). Use `../../../foo` for repo-root targets so the mirror works. Verified in fn-47 docs decomposition: 33 broken links caught by codex review.

## Prevention

1. **Contract surfaces are honored end-to-end.** When you add `--json` or any contract flag, grep all sites that thread the flag and verify it threads through. Same for HTML-comment depth, merge-policy recomputation, R17 cross-link discipline.
2. **Enumerate canonical sections ONCE.** The canonical template's frontmatter is the source of truth. Skill prose links; never copies.
3. **Plain vs JSON output diverge intentionally.** Document the exit-code contract per output mode; don't reuse plain-mode signaling through `--json`.
4. **Scoped review knows only the diff.** When a review needs context from before BASE_COMMIT, surface it IN the diff (file touches, inline comment) or widen the base.
5. **3-up relative paths from `plugins/flow-next/docs/<file>.md`** to reach repo-root targets. From `plugins/flow-next/skills/<name>/<file>.md` it's 4-up. Test via `[[ -e "$path" ]]` before committing.
6. **R21 is necessary but not sufficient.** Add R17 cross-link discipline as a manual review item on any task touching skill prose that references canonical sections.

## See also

- `[[template-rewrite-env-var-cascade]]` — env-var cascade discipline + config.env knob alignment
- `[[test-production-path-not-parallel-construction]]` — test-discipline lessons from the same era (json output via cmd_*, argparse wire form)
- `scripts/sync-codex.sh` lines 1466+ — R21 drift guard (still active)
- `plugins/flow-next/templates/spec.md` — canonical scaffold; never re-embed its section list inline (R17)
