# capture — glossary term-adds (loaded on demand)

> Loaded ONLY when the §2.7 husk-aware gate is open (`flowctl glossary list --json` reports
> `total_terms > 0`) or its probe errored. An absent glossary, a `# Glossary` husk, or a flowctl
> error means **silent skip**: `GLOSSARY_PROPOSALS` stays empty and nothing downstream changes —
> bootstrap is `/flow-next:prime`'s job, never capture's.

## 2.7 — New-vocabulary scan (glossary term-add proposals)

Capture joins `/flow-next:interview` as a glossary writer. Gate first — same husk-aware autodetect as interview's doc-aware mode (`total_terms`, never `[[ -f ]]` — a `# Glossary` husk must not open the gate):

```bash
GLOSSARY_TERMS=$("$FLOWCTL" glossary list --json 2>/dev/null | jq -r '.total_terms // 0')
```

- `GLOSSARY_TERMS == 0` (absent, husk, or flowctl error) → **silent skip**: `GLOSSARY_PROPOSALS` stays empty, nothing downstream changes. Bootstrap is `/flow-next:prime`'s job, never capture's.
- `GLOSSARY_TERMS > 0` → scan the conversation evidence for genuinely NEW project vocabulary. A term qualifies when ALL hold:
  1. **Used repeatedly** — appears in ≥2 user turns (or once + load-bearing for an acceptance criterion).
  2. **Project-specific** — a coined noun / flow / distinction, not generic English ("receipt gate" yes; "function" no).
  3. **Absent from the glossary** — no existing entry matches on `term` or `avoid` aliases (case-insensitive, whitespace-collapsed — the `_glossary_term_matches` contract; do not reinvent matching logic).

Collect at most **5** proposals (`GLOSSARY_PROPOSALS`), each with a one-line definition drawn from how the user actually used the term. Definition prose follows the artifact prose contract in [docs/prose.md](../../../docs/flow-next/prose.md); proceed without it when the doc is absent. Proposals surface at Phase 4 read-back; writes happen only in Phase 5.8 after consent.

## Phase 4 — read-back surface + consent

**Summary-payload item 6 — glossary term-add proposals** (only when §2.7 collected any) — compact one-liner of term names; full definitions live in the printed draft message (or a short glossary block printed above the ask), never multi-paragraph in the ask body:

```
New glossary terms proposed: <term>, <term> (definitions in draft above).
```

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

**Glossary term-add consent (only when `GLOSSARY_PROPOSALS` is non-empty AND the user picked `approve`).** One follow-up question via `plain-text numbered prompt` — the §4.2 read-back options stay frozen; this is a separate ask (short — definitions already printed above if present):

- **header**: `Glossary?`
- **body**: `Add <N> new term(s) to GLOSSARY.md? <comma-separated terms>. Definitions in the draft printed above. Recommended: add — they surfaced repeatedly in this conversation. Confidence: [judgment-call].`
- **options**: `add-all`, `pick` (follow-up multi-select / serial yes-no per term), `skip`

Record the approved subset for Phase 5.8. `skip` → no glossary writes; the spec write proceeds regardless of this answer.

**Forbidden in Phase 4:** never write glossary terms there. Phase 4 collects consent only; the writes happen in Phase 5.8, after the spec write.

## 5.8 — Glossary term-adds (consent-gated; interactive only)

Runs only when Phase 4.2's glossary consent approved ≥1 term (which implies `GLOSSARY_TERMS > 0` — the §2.7 gate — and interactive mode; autofix never reaches here). For each approved term:

```bash
"$FLOWCTL" glossary add "<term>" --definition-file - --json <<EOF
<one-line definition from the read-back, as approved>
EOF
```

Same call site as interview's behavior (b) — `glossary add` is a case-insensitive upsert; stdin keeps quoted phrasing intact. Best-effort: a failed add prints a warning and continues — never blocks the capture (the spec is already on disk). Report `Glossary: added N term(s) (<terms>)` for the Phase 6 footer.

## Phase 6 — footer line

When Phase 5.8 wrote terms, append one line after `Tracker sync:`: `Glossary: added N term(s) (<comma-separated terms>)`. Omit entirely otherwise (including every autofix run).

## Forbidden behavior (glossary row)

| Forbidden | Why |
|-----------|-----|
| Glossary term-adds without read-back consent, or in autofix | Consent lives in Phase 4.2's `Glossary?` question; autofix prints suggestions only. Husk-aware gate (`total_terms > 0`) — seeding an empty glossary is `/flow-next:prime`'s job. |
