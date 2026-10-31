# capture — glossary consent and write (gated reference)

> Read from [glossary-terms.md](glossary-terms.md) only when `GLOSSARY_PROPOSALS` is non-empty.

## Saved-spec summary and separate consent

**Summary line — glossary term-add proposals** (only when §2.7 collected any) — compact one-liner of term names; full definitions live in the printed glossary proposal (or a short glossary block printed above the ask), never multi-paragraph in the ask body:

```
New glossary terms proposed: <term>, <term> (definitions above).
```

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

**Glossary term-add consent (only when `GLOSSARY_PROPOSALS` is non-empty).** At §5.8, after the spec is saved, ask separately through `plain-text numbered prompt` unless the user already answered. Print definitions above the short question.

- **header**: `Glossary?`
- **body**: `Add <N> new term(s) to GLOSSARY.md? <comma-separated terms>. Definitions printed above. Recommended: add — they surfaced repeatedly in this conversation. Confidence: [judgment-call].`
- **options**: `add-all`, `pick` (follow-up multi-select / serial yes-no per term), `skip`

Record the approved subset for Phase 5.8. `skip` → no glossary writes; the saved spec remains available regardless of this answer.

Never infer glossary consent from capturing or editing the spec. The separate question and consented writes happen in §5.8.

## 5.8 — Glossary term-adds (consent-gated; interactive only)

Runs only when the separate glossary question approved ≥1 term (which implies `GLOSSARY_TERMS > 0` — the §2.7 gate — and interactive mode; autofix never reaches here). For each approved term:

```bash
"$FLOWCTL" glossary add "<term>" --definition-file - --json <<EOF
<one-line definition from the read-back, as approved>
EOF
```

Same call site as refine's behaviour (b) — `glossary add` is a case-insensitive upsert; stdin keeps quoted phrasing intact. Best-effort: a failed add prints a warning and continues — never blocks the capture (the spec is already on disk). Report `Glossary: added N term(s) (<terms>)` for the Phase 6 footer.

## Phase 6 — footer line

When Phase 5.8 wrote terms, append one line to the Phase 6 close: `Glossary: added N term(s) (<comma-separated terms>)`. Omit entirely otherwise (including every autofix run).
