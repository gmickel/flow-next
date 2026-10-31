# Refine — doc-aware behaviors (a)-(d) (gated reference)

> Read from [doc-aware.md](doc-aware.md) only when the sentinel printed `DOC_AWARE=1`.

### Glossary lookups (`DOC_AWARE=1`)

A question about a term with a canonical entry in the nearest-ancestor `GLOSSARY.md` is answered from the entry, silently. Log it under `## Glossary Conflicts` only when the person's wording diverges from the canonical term and the term is load-bearing (behavior (a)).

### Behavior (a) — Phase-zero glossary scan

Before drafting the first question batch, run a glossary scan against the user's request. The
glossary comes from the interview's preflight bundle; a failed probe there lists it live.

```bash
REFINE_PREFLIGHT="${TMPDIR:-/tmp}/flow-refine-preflight-<suffix>.json"   # the same literal path as Setup
jq -ce 'if .probes.glossary.status == "ok" then .probes.glossary.value else error("glossary probe") end' "$REFINE_PREFLIGHT" 2>/dev/null \
  || "$FLOWCTL" glossary list --json
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

For each defined term across `groups[].entries`, scan the user's request for occurrences. Term match is **case-insensitive whitespace-collapsed**, the same rule as `flowctl glossary read`: lowercase both sides, collapse runs of whitespace to one space, compare equal. Alias hits via `entries[].avoid`: if the user wrote `consumer` and the entry's `avoid` list contains `consumer`, that's a canonical-mismatch hit on `Worker`.

For each hit, evaluate one filter before surfacing:

- **Is the term load-bearing for this spec?** Casual passing mention does not trigger; mention that defines behavior or shapes acceptance does. The user wrote "the worker fetches the queue" mid-sentence about deployment — passing mention, no question. The user wrote "we need a new kind of worker that processes batches" — load-bearing, surface.

When a hit passes the load-bearing filter AND the user's wording conflicts with canonical (alias used instead of canonical, or definition contradicts), surface as the **first interview question** via `AskUserQuestion`:

- **header**: `Term mismatch?`
- **body**: `You used "<user-wording>"; GLOSSARY.md defines "<canonical>" as "<one-line definition>". Recommended: <use-canonical | redefine | this-is-different>. Confidence: [<tier>].`
- **options**: frozen — `use-canonical` (the user meant the existing term; spec uses canonical wording), `redefine` (user is updating the term meaning; spec proceeds with new wording, agent will re-write `GLOSSARY.md` via `flowctl glossary add` after the interview), `this-is-different` (the words collide but the concepts differ; spec uses a fresh disambiguating term — capture in `## Glossary Conflicts`).

Confidence tier: `[high]` when the canonical entry is recent and the user's wording cleanly maps to an `avoid` alias; `[judgment-call]` when meaning could plausibly have drifted; `[your-call]` when the term sits in user-domain territory the agent has no purchase on.

**Throttle:** at most one Phase-zero glossary question per interview round. If multiple terms hit, surface the most load-bearing one first; the rest fold into the natural conversation flow as they come up. Bombarding the user with vocabulary questions before the core spec questions is the failure mode this filter prevents.

### Behavior (b) — Fuzzy-term sharpening

Across the conversation, watch for overloaded language — words the user keeps using whose meaning could plausibly shift between turns ("workflow", "session", "task" when a Flow `task` already has meaning, etc.). When you spot one:

1. Propose a canonical via `AskUserQuestion`:
   - **header**: `Sharpen "<term>"?`
   - **body**: `You've used "<term>" in <count> replies. I'm reading it as "<agent's working definition>" but want to lock it in. Recommended: <X> — <one-sentence rationale>. Confidence: [<tier>].`
   - **options**: 2-4 candidate canonical wordings + `none-of-these` (user provides their own).

2. On user-pick, build the resolved entry and write it to the nearest-ancestor `GLOSSARY.md` via `flowctl glossary add`:

   ```bash
   "$FLOWCTL" glossary add "<term>" --definition-file - --json <<EOF
   <user-resolved one-line or short paragraph definition>
   EOF
   ```

   Use `--definition-file -` (stdin) so multi-sentence definitions and quoted phrasing round-trip cleanly. `glossary add` is upsert — case-insensitive match replaces the existing entry in full; new terms append at the end of the file. If the user picked `redefine` in behavior (a), this is the same call site (one path, one upsert).

3. Re-read the glossary on every doc-aware round that needs a canonical lookup; there is no cache to invalidate.

**When to skip behavior (b):** if a term is single-use, or if the user volunteered a clear definition the first time they used it, or if the conversation is short enough (≤6 user replies) that consolidation buys nothing yet. The behavior triggers when overloading is real and persistent, not on every undefined word.

### Behavior (c) — Code-versus-assertion contradiction

When grep / Read reveals the code disagrees with something the user asserted ("we already have X at path Y" but Y is gone, or "the auth flow uses OAuth" but the code uses API keys), do **not** silently log under `## Resolved via Codebase`. Surface the contradiction as an `AskUserQuestion`:

- **header**: `Code mismatch?`
- **body**: `Code shows <X> at <file:line>; you said <Y>. Recommended: <treat-code-as-source-of-truth | update-spec-to-match-code | revisit-the-area>. Confidence: [<tier>].`
- **options**: frozen — `match-code` (revise spec to align with what's there), `update-code` (treat the assertion as the goal; flag the divergence as a task), `clarify` (user explains; agent re-investigates with new context).

Confidence tier: `[high]` when grep evidence is unambiguous (file does not exist, function signature is clearly different); `[judgment-call]` when interpretation is at play (similar names, partial overlap, recent rename). Never silently pick a side — the user owns the resolution.

The bar for surfacing: a meaningful contradiction that affects spec correctness. If the user says "the validator returns boolean" and grep shows it returns `Result<bool, Error>`, surface. If the user paraphrases a function's role and grep shows the role matches but the implementation differs in unrelated detail, log under `## Resolved via Codebase` and move on.

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

   Entry title and body prose follows the artifact prose contract in [docs/prose.md](../../../docs/prose.md); proceed without it when the doc is absent.

2. **Print-then-ask before writing:**
   - **Print first:** emit the FULL decision-entry draft (title, body markdown, optional module/tags, optional Considered Options / Consequences blocks) as an ordinary assistant markdown message. Never embed the multi-paragraph body in the ask.
   - **Then short ask** via `AskUserQuestion`:
     - **header**: `Write decision?`
     - **body** (SHORT — pointer + tally/warnings + recommendation only): `Decision draft printed above (<title>). Recommended: approve — <one-sentence rationale why all three gate criteria hold>. Confidence: [<tier>].`
     - **options**: frozen — `approve` (write), `edit` (user revises title / body / module / tags via follow-up), `skip` (do not write; the choice stays in spec prose only).

   Never write silently — even when the gate cleanly passes, the user owns the final write. Never put the full decision body "inline in the question"; ask bodies render as collapsed plain text.

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

   The `decisions` category is registered in flowctl's memory schema. Optional fields `--decision-status` (default `accepted`), `--superseded-by`, and `--alternatives-considered` are available; pass them when the conversation supplies them and skip otherwise.

4. **On `edit`**, ask one follow-up `AskUserQuestion` for which field changes (title / body / module / tags), capture the revision, **reprint the full revised draft as ordinary markdown**, then re-issue the short approval ask; loop. Hard cap at 2 edit cycles before defaulting to `approve` / `skip`.

5. **On `skip`**, do nothing — the choice still appears in spec prose; only the memory entry is suppressed.

**At most one decision write per interview round.** Even if multiple gate-passing decisions surface, ask one at a time; subsequent asks adapt to the user's energy level for read-back.
