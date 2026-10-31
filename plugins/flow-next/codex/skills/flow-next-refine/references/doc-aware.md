# Refine — doc-aware behaviors

Read when the doc-aware gate sentinel prints. The four doc/strategy flags and their matrix are in [doc-flags.md](doc-flags.md).

Contents:

- [Doc-aware behaviors](#doc-aware-behaviors) — glossary lookups, (a) phase-zero glossary scan, (b) fuzzy-term sharpening, (c) code-versus-assertion contradiction, (d) decision-record write, (e) code-versus-strategy contradiction.

## Doc-aware behaviors

These behaviors layer onto the interview when their gate is open:

- Behaviors (a)-(d) are gated on `DOC_AWARE=1` (glossary + decisions signal). When `DOC_AWARE=0`, skip them.
- Behavior (e) is gated on `STRATEGY_AWARE=1` (strategy signal). When `STRATEGY_AWARE=0`, skip it.

The two gates are independent (see the flag matrix in [doc-flags.md](doc-flags.md)) — `DOC_AWARE` and `STRATEGY_AWARE` may differ within the same interview session.

When `DOC_AWARE=1`: read [doc-aware-docs.md](doc-aware-docs.md) for the glossary lookups and behaviors (a)-(d).

### Behavior (e) — Code-versus-strategy contradiction (`STRATEGY_AWARE=1` only)

Parallel structure to behavior (a) — Phase-zero glossary scan. Before drafting the first question batch in a `STRATEGY_AWARE=1` session, run a strategy scan against the user's request.

```bash
"$FLOWCTL" strategy read --json
```

JSON shape (selected fields used here):

```json
{
  "name": "<product-name>",
  "target_problem": "...",
  "approach": "...",
  "tracks": "### track-a\nOne line on track A.\n_Why it serves the approach:_ ...\n\n### track-b\n...",
  "last_updated": "2026-05-01",
  "path": "STRATEGY.md"
}
```

`tracks` is a **raw markdown string** — H3 sub-blocks of the form `### <track-name>` followed by a one-line description and a `_Why it serves the approach:_` line. Parse the H3 names locally. Empty section bodies (any of `target_problem`, `approach`, `tracks`) surface as `""` (empty string), not null — `(.field // "")` style fallbacks keep parsing well-formed when an optional section is missing.

Walk the user's request looking for two patterns:

1. **Track-name mismatch** — the user uses a noun-phrase that names a track-like investment area, but the wording diverges from a canonical track in `STRATEGY.md` (e.g. user says "Initiative" but `tracks` defines "### Track"). Treat the user's wording as a candidate alias for the closest canonical track and surface as a question if load-bearing for the spec.
2. **Direction conflict** — the user describes a goal or constraint that contradicts the `approach` or one of the active tracks (e.g. approach says "we ship CLI tools, not SaaS" but the user is asking the spec to add a managed dashboard service).

For each hit, evaluate the same load-bearing filter as behavior (a): casual passing mention does not trigger; mention that defines behavior or shapes acceptance does.

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

When a hit passes the filter, surface via `plain-text numbered prompt`:

- **header**: `Strategy mismatch?`
- **body**: `You said "<user-wording>"; STRATEGY.md (<path>) <track|approach> says "<canonical-wording>". Recommended: <align-with-strategy | flag-as-drift | this-is-different>. Confidence: [<tier>].`
- **options**: frozen — `align-with-strategy` (the user meant the existing track / honors the approach; spec uses canonical wording), `flag-as-drift` (the spec is intentionally pushing back on the strategy; capture in `## Strategy Conflicts` and proceed), `this-is-different` (the words collide but the concepts differ; spec uses a fresh disambiguating term — also capture in `## Strategy Conflicts`).

Confidence tier: `[high]` when the strategy entry is recent and the user's wording cleanly maps to a canonical track or directly contradicts the verbatim approach; `[judgment-call]` when meaning could plausibly have drifted; `[your-call]` when the strategic direction sits in user-domain territory the agent has no purchase on.

**Throttle:** at most one strategy-conflict question per interview round (parallel to behavior (a)'s glossary throttle). If multiple strategy mismatches hit, surface the most load-bearing one first; the rest fold into the natural conversation flow as they come up. Bombarding the user with strategy-alignment questions before the core spec questions is the failure mode this throttle prevents. Combined with the (a) and (d) throttles, the per-round doc-aware question budget is **3 max** (1 glossary + 1 decision-record + 1 strategy).

The output of behavior (e) lands in a new spec section, `## Strategy Conflicts`, parallel to `## Glossary Conflicts`. Format: per-line entries with user-wording / canonical-strategy-wording / STRATEGY.md path / resolution-chosen. Lets reviewers see where the spec aligns or pushes back on strategic intent. The interview never edits `STRATEGY.md`.
