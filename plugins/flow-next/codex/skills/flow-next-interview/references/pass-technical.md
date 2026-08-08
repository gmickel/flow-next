# Interview — technical pass (loaded when `SCOPE == technical`, the default; or for phase 2 of `both`)

> Read at the pass-routing branch point in SKILL.md. A business-only interview never reads this file.

## Technical pass

Doc-aware default: the autodetect cascade in SKILL.md Setup runs as usual.

Run BEFORE the first plain-text numbered prompt call:

1. **Read biz sections when populated** — if `## Goal & Context`, `## Boundaries`, `### Motivation` (under `## Decision Context`), or outcome-AC R-IDs are populated, read them as constraint context. Cite them in the interview opener (e.g., "Reading from the existing business layer: target user is X, MVP boundary excludes Y. Tech questions below..."). When biz sections are absent (default solo-dev 1.0.2-shape spec), proceed silently with technical-only questions — no opener about missing biz context.
2. **Codebase investigation** — the "Investigate Before Asking" rule in SKILL.md applies unchanged. Items resolved via Read/Grep/Glob land in `## Resolved via Codebase`.

Per-section write behavior (per the write-policy):

- **Writable tech sections** (`Architecture & Data Models`, `API Contracts`, `Edge Cases & Constraints`, verifiable-AC): write/refine from interview answers. May overwrite `*Pending technical-scope interview pass.*` placeholder strings.
- **Preserved biz sections** (`Goal & Context`, `Boundaries`): MUST be preserved byte-for-byte.
- **`## Decision Context`** (per `decision_context` shape):
 - When `shape == "flat"` (no H3s exist, no biz pass has run — default zero-flag-tech case on a fresh/legacy spec): write/refine the flat body in place. Do NOT introduce `### Motivation` / `### Implementation Tradeoffs` H3 substructure. Preserves R22 1.0.2 backward compat.
 - When `shape == "substructured"` (`### Motivation` already exists from a prior biz pass, or the existing spec has the substructure): preserve `### Motivation` body byte-for-byte; write/refine ONLY `### Implementation Tradeoffs`.
- **`## Acceptance Criteria`**: append verifiable-AC R-IDs (R-IDs are append-only — never renumber). Source-tag each criterion you append (`[user]` = the tech lead answering in this pass, `[paraphrase]`, `[inferred]`, `[strategy:<track>]`); never tag or retag a criterion another pass wrote — see `write-back.md` § Source tags on acceptance criteria.
- **Auxiliary sections**: preserve byte-for-byte per the auxiliary-sections rule in SKILL.md; tech pass adds `Resolved via Codebase` only.
