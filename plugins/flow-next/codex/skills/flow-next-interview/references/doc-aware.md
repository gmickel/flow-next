# Interview — doc-aware behaviors (loaded on demand)

> Loaded ONLY when `DOC_AWARE=1` or `STRATEGY_AWARE=1` (from the `--docs`/`--strategy` flags or
> autodetect in SKILL.md Setup). On the default technical-scope, no-docs path this file is never read.

## Doc-aware behaviors

Five behaviors layer onto the standard interview workflow when their respective gate is open:

- Behaviors (a)-(d) are gated on `DOC_AWARE=1` (glossary + decisions signal). When `DOC_AWARE=0`, skip them.
- Behavior (e) is gated on `STRATEGY_AWARE=1` (strategy signal). When `STRATEGY_AWARE=0`, skip it.

The two gates are independent (see flag matrix above) — `DOC_AWARE` and `STRATEGY_AWARE` may differ within the same interview session.

### Behavior (a) — Phase-zero glossary scan

Before drafting the first question batch, run a glossary scan against the user's request.

```bash
"$FLOWCTL" glossary list --json
```

JSON shape:

```json
{
 "groups": [
 {
 "path": "GLOSSARY.md",
 "entries": [
 { "term": "Worker", "definition": "...", "avoid": ["consumer"], "relates_to": ["Queue"] }
 ],
 "count": 1
 }
 ],
 "file_count": 1,
 "total_terms": 1
}
```

For each defined term across `groups[].entries`, scan the user's request for occurrences. Term match is **case-insensitive whitespace-collapsed** — the same rule as `flowctl glossary read` (see `_glossary_term_matches` in `flowctl.py`). Do NOT reinvent matching logic; the canonical contract is "lowercase both sides, collapse runs of whitespace to single space, compare equal." Alias hits via `entries[].avoid`: if the user wrote `consumer` and the entry's `avoid` list contains `consumer`, that's a canonical-mismatch hit on `Worker`.

For each hit, evaluate one filter before surfacing:

- **Is the term load-bearing for this spec?** Casual passing mention does not trigger; mention that defines behavior or shapes acceptance does. The user wrote "the worker fetches the queue" mid-sentence about deployment — passing mention, no question. The user wrote "we need a new kind of worker that processes batches" — load-bearing, surface.

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

When a hit passes the load-bearing filter AND the user's wording conflicts with canonical (alias used instead of canonical, or definition contradicts), surface as the **first interview question** via `plain-text numbered prompt`:

- **header**: `Term mismatch?`
- **body**: `You used "<user-wording>"; GLOSSARY.md defines "<canonical>" as "<one-line definition>". Recommended: <use-canonical | redefine | this-is-different>. Confidence: [<tier>].`
- **options**: frozen — `use-canonical` (the user meant the existing term; spec uses canonical wording), `redefine` (user is updating the term meaning; spec proceeds with new wording, agent will re-write `GLOSSARY.md` via `flowctl glossary add` after the interview), `this-is-different` (the words collide but the concepts differ; spec uses a fresh disambiguating term — capture in `## Glossary Conflicts`).

Confidence tier: `[high]` when the canonical entry is recent and the user's wording cleanly maps to an `avoid` alias; `[judgment-call]` when meaning could plausibly have drifted; `[your-call]` when the term sits in user-domain territory the agent has no purchase on.

**Throttle:** at most one Phase-zero glossary question per interview turn. If multiple terms hit, surface the most load-bearing one first; the rest fold into the natural conversation flow as they come up. Bombarding the user with vocabulary questions before the core spec questions is the failure mode this filter prevents.

### Behavior (b) — Fuzzy-term sharpening

Across the conversation, watch for overloaded language — words the user keeps using whose meaning could plausibly shift between turns ("workflow", "session", "task" when a Flow `task` already has meaning, etc.). When you spot one:

1. Propose a canonical via `plain-text numbered prompt`:
 - **header**: `Sharpen "<term>"?`
 - **body**: `You've used "<term>" in <count> turns. I'm reading it as "<agent's working definition>" but want to lock it in. Recommended: <X> — <one-sentence rationale>. Confidence: [<tier>].`
 - **options**: 2-4 candidate canonical wordings + `none-of-these` (user provides their own).

2. On user-pick, build the resolved entry and write it to the nearest-ancestor `GLOSSARY.md` via `flowctl glossary add`:

 ```bash
 "$FLOWCTL" glossary add "<term>" --definition-file - --json <<EOF
 <user-resolved one-line or short paragraph definition>
 EOF
 ```

 Use `--definition-file -` (stdin) so multi-sentence definitions and quoted phrasing round-trip cleanly. `glossary add` is upsert — case-insensitive match replaces the existing entry in full; new terms append at the end of the file. If the user picked `redefine` in behavior (a), this is the same call site (one path, one upsert).

3. The next question can re-read the glossary. There is no in-memory cache to invalidate — re-read on every doc-aware turn that needs canonical lookup. The cost is one stat + one file read per turn; sub-millisecond at typical sizes.

**When to skip behavior (b):** if a term is single-use, or if the user volunteered a clear definition the first time they used it, or if the conversation is short enough (≤6 turns) that consolidation buys nothing yet. The behavior triggers when overloading is real and persistent, not on every undefined word.

### Behavior (d) — Decision-record write (three-criteria gate)

When the interview surfaces a choice the user is making — not just a fact about the system, a real **decision** — evaluate the three-criteria gate before drafting a memory entry.

**The three-criteria gate** (all three must hold):

1. **Hard-to-reverse** — undoing this later costs more than redoing it now. Schema choices, public API shapes, integration boundaries qualify; cosmetic preferences and easily-toggled flags do not.
2. **Surprising-without-context** — a future maintainer reading the result without history would ask "why this and not the obvious thing?". Anything that follows the standard pattern of the surrounding code is not surprising.
3. **Real trade-off** — there was a genuine alternative that lost. If there was no real alternative, it isn't a decision; it's a fact.

If any of the three fails, do NOT write a decision entry. Note the choice in the spec's prose body (e.g. `## Decision Context`) and move on. The bar exists because the decisions store decays fast when filled with non-decisions.

When all three hold:

1. **Draft the entry** in agent memory (do not write yet). Shape:
 - **Title** (1 line, ≤80 chars): the decision in noun-phrase form (e.g. "Nearest-ancestor walk for glossary lookup").
 - **Body** (1-3 sentences floor; longer when warranted):
 - 1 sentence on what was chosen.
 - 0-1 sentences on why.
 - Optional `## Considered Options` block listing rejected alternatives with one-line reasons each.
 - Optional `## Consequences` block listing what this commits the project to.
 - **Module** (optional): the file or subsystem the decision shapes.
 - **Tags** (optional): comma-separated, e.g. `glossary,resolution,walk`.

2. **Show the draft via `plain-text numbered prompt` before writing** — same pattern as `/flow-next:capture` Phase 4 read-back:
 - **header**: `Write decision?`
 - **body**: `Drafted decision entry: <title>. Body: <one-line summary>. Recommended: approve — <one-sentence rationale why all three gate criteria hold>. Confidence: [<tier>].`
 - **options**: frozen — `approve` (write), `edit` (user revises title / body / module / tags via follow-up), `skip` (do not write; the choice stays in spec prose only).

 Show the full body inline in the question or in the message preceding it; the user must be able to read what they're approving. Never write silently — even when the gate cleanly passes, the user owns the final write.

3. **On `approve`**, call:

 ```bash
 "$FLOWCTL" memory add \
 --track knowledge \
 --category decisions \
 --title "<title>" \
 --module "<module>" \
 --tags "<tags>" \
 --body-file - <<EOF
 <body markdown>
 EOF
 ```

 The `decisions` category is registered in flowctl's memory schema (Task 1 of the original decisions epic). Optional fields `--decision-status` (default `accepted`), `--superseded-by`, and `--alternatives-considered` are available; pass them when the conversation supplies them and skip otherwise.

4. **On `edit`**, ask one follow-up `plain-text numbered prompt` for which field changes (title / body / module / tags), capture the revision, re-show the draft, loop. Hard cap at 2 edit cycles before defaulting to `approve` / `skip`.

5. **On `skip`**, do nothing — the choice still appears in spec prose; only the memory entry is suppressed.

**At most one decision write per interview turn.** Even if multiple gate-passing decisions surface, ask one at a time; subsequent asks adapt to the user's energy level for read-back.

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

When a hit passes the filter, surface via `plain-text numbered prompt`:

- **header**: `Strategy mismatch?`
- **body**: `You said "<user-wording>"; STRATEGY.md (<path>) <track|approach> says "<canonical-wording>". Recommended: <align-with-strategy | flag-as-drift | this-is-different>. Confidence: [<tier>].`
- **options**: frozen — `align-with-strategy` (the user meant the existing track / honors the approach; spec uses canonical wording), `flag-as-drift` (the spec is intentionally pushing back on the strategy; capture in `## Strategy Conflicts` and proceed), `this-is-different` (the words collide but the concepts differ; spec uses a fresh disambiguating term — also capture in `## Strategy Conflicts`).

Confidence tier: `[high]` when the strategy entry is recent and the user's wording cleanly maps to a canonical track or directly contradicts the verbatim approach; `[judgment-call]` when meaning could plausibly have drifted; `[your-call]` when the strategic direction sits in user-domain territory the agent has no purchase on.

**Throttle:** at most one strategy-conflict question per interview turn (parallel to behavior (a)'s glossary throttle). If multiple strategy mismatches hit, surface the most load-bearing one first; the rest fold into the natural conversation flow as they come up. Bombarding the user with strategy-alignment questions before the core spec questions is the failure mode this throttle prevents. Combined with the (a) and (d) throttles, the per-turn doc-aware question budget is **3 max** (1 glossary + 1 decision-record + 1 strategy).

The output of behavior (e) lands in a new spec section, `## Strategy Conflicts`, parallel to `## Glossary Conflicts`. Format: per-line entries with user-wording / canonical-strategy-wording / STRATEGY.md path / resolution-chosen. Lets reviewers see where the spec aligns or pushes back on strategic intent. Strategy conflicts are read-only signal for `/flow-next:sync`'s plan-sync agent — the interview never edits `STRATEGY.md`.
