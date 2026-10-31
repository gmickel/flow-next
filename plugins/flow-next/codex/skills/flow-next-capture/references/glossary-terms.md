# capture — glossary term-adds (loaded on demand)

> Loaded ONLY when the §2.7 husk-aware gate is open (`flowctl glossary list --json` reports
> `total_terms > 0`) or its probe errored. An absent glossary, a `# Glossary` husk, or a flowctl
> error means **silent skip**: `GLOSSARY_PROPOSALS` stays empty and nothing downstream changes —
> bootstrap is `/flow-next:prime`'s job, never capture's.

## 2.7 — New-vocabulary scan (glossary term-add proposals)

Capture joins `/flow-next:refine` as a glossary writer. Gate first — same husk-aware autodetect as refine's doc-aware mode (`total_terms`, never `[[ -f ]]` — a `# Glossary` husk must not open the gate):

```bash
# The preflight snapshot holds the glossary; a failed probe there lists it live.
GLOSSARY_TERMS=$(jq -er '.probes.glossary | if .status == "ok" and (.value.total_terms | type) == "number" then .value.total_terms else error("glossary probe") end' "${TMPDIR:-/tmp}/flow-capture-config-<suffix>.json" 2>/dev/null) \
  || GLOSSARY_TERMS=$("$FLOWCTL" glossary list --json 2>/dev/null | jq -r '.total_terms // 0')
```

- `GLOSSARY_TERMS == 0` (absent, husk, or flowctl error) → **silent skip**: `GLOSSARY_PROPOSALS` stays empty, nothing downstream changes. Bootstrap is `/flow-next:prime`'s job, never capture's.
- `GLOSSARY_TERMS > 0` → scan the conversation evidence for genuinely NEW project vocabulary. A term qualifies when ALL hold:
  1. **Used repeatedly** — appears in ≥2 user turns (or once + load-bearing for an acceptance criterion).
  2. **Project-specific** — a coined noun / flow / distinction, not generic English ("receipt gate" yes; "function" no).
  3. **Absent from the glossary** — no existing entry matches on `term` or `avoid` aliases (case-insensitive, whitespace-collapsed — the `_glossary_term_matches` contract; do not reinvent matching logic).

Collect at most **5** proposals (`GLOSSARY_PROPOSALS`), each with a one-line definition drawn from how the user actually used the term. Definition prose follows the artifact prose contract in [docs/prose.md](../../../docs/flow-next/prose.md); proceed without it when the doc is absent. Proposals surface in the saved-spec summary; writes happen only in Phase 5.8 after consent.

Only when `GLOSSARY_PROPOSALS` is non-empty: read [glossary-consent.md](glossary-consent.md) for the summary line, the separate `Glossary?` question and the §5.8 write.
