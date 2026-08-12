# capture — STRATEGY.md alignment (loaded on demand)

> Loaded ONLY when the Phase 0.3b gate fires (`flowctl strategy status --json` reports
> `sections_filled >= 1`, or the probe errored). A repo with no populated `STRATEGY.md` emits no
> `[strategy:*]` tags and skips the Phase 5.0 contradiction check entirely — it never reads this file.

Contents:

- [0.3b — Strategy snapshot](#03b--strategy-snapshot-advisory-grounding-input) — read the tracks, surface the footnote
- [5.0 — Strategy contradiction check](#50--strategy-contradiction-check-gate-runs-before-any-write) — refusal, `--override-strategy`, decision record, audit trail

---

## 0.3b — Strategy snapshot (advisory grounding input)

Read `STRATEGY.md` (when populated) so Phase 2's source-tagging can apply `[strategy:<track>]` to acceptance criteria that follow directly from strategic intent. Husk-vs-presence gate uses `sections_filled >= 1` from `flowctl strategy status --json`, NOT `[[ -f STRATEGY.md ]]`.

```bash
STRATEGY_STATUS_JSON=$("$FLOWCTL" strategy status --json 2>/dev/null || echo '{"exists":false,"sections_filled":0}')
STRATEGY_FILLED=$(jq -r '.sections_filled // 0' <<< "$STRATEGY_STATUS_JSON" 2>/dev/null || echo 0)

if [[ "$STRATEGY_FILLED" -ge 1 ]]; then
  STRATEGY_JSON=$("$FLOWCTL" strategy read --json 2>/dev/null || echo '{}')
  STRATEGY_PRESENT=true
  STRATEGY_NAME=$(jq -r '.name // "(unnamed)"' <<< "$STRATEGY_JSON")
  STRATEGY_PROBLEM=$(jq -r '.target_problem // ""' <<< "$STRATEGY_JSON")
  STRATEGY_APPROACH=$(jq -r '.approach // ""' <<< "$STRATEGY_JSON")
  STRATEGY_TRACKS_RAW=$(jq -r '.tracks // ""' <<< "$STRATEGY_JSON")
  STRATEGY_PATH=$(jq -r '.path // "STRATEGY.md"' <<< "$STRATEGY_JSON")
else
  STRATEGY_PRESENT=false
fi
```

Surface as a "Strategic context:" footnote — 3-5 lines total — when the agent presents Phase 0 results to the user. Format:

```
Strategic context (STRATEGY.md, last updated 2026-04-30):
  Approach: <verbatim approach line, capped to 1-2 sentences>
  Active tracks: <track-name-1>, <track-name-2>, <track-name-3>
```

`STRATEGY_TRACKS_RAW` is a **raw markdown string** with `### <track-name>` H3 sub-blocks. Parse the H3 names locally for the active-tracks list. Empty section bodies (any of `target_problem`, `approach`, `tracks`) surface as `""` — `(.field // "")` style fallbacks in the jq queries above keep parsing well-formed when an optional section is missing.

The strategy snapshot is **input**, not gating: even when `STRATEGY_PRESENT=true`, capture proceeds. Phase 2's source-tagging uses the snapshot to assign `[strategy:<track-name>]` to criteria that quote / paraphrase strategy content. Phase 5 uses it to detect contradictions (see §5.0 below) and refuse the write without `--override-strategy`.

When `STRATEGY_PRESENT=false`, Phase 2 emits no `[strategy:*]` tags and Phase 5's contradiction check is skipped entirely — there is no signal to align to.

---

## 5.0 — Strategy contradiction check (gate; runs before any write)

When the Phase 0 strategy snapshot was populated (`STRATEGY_PRESENT=true`), scan the drafted spec body for contradictions against the active tracks. A contradiction exists when:

1. The spec body has at least one `[strategy:<track>]` line AND the surrounding criterion / decision-context line negates the corresponding track body. Example: track `### CLI-only` says "we ship CLI tools, not SaaS"; spec criterion `[strategy:CLI-only]` reads "ship a managed dashboard service" — direct contradiction.
2. The spec body proposes an investment area that contradicts `approach` directly. Example: approach says "OSS-tools repo, no commercial SaaS"; spec body adds "stripe billing integration as a core feature" without `[strategy:*]` tagging — semantic contradiction even without a tag.

When a contradiction is detected AND `OVERRIDE_STRATEGY` is `0`:

```text
Error: spec contradicts active track "<track>" — pass --override-strategy to proceed.

Detected contradiction:
  Track: <track-name> (STRATEGY.md)
  Track says: "<canonical wording>"
  Spec says:  "<conflicting wording>"

Re-run with --override-strategy to write the spec anyway. You'll be prompted to
record the override as a decision entry (the override is exactly the kind of
load-bearing architectural choice the decisions track exists for).
```

In **interactive** mode, refuse with the message above (exit 2) — do NOT prompt the user to override here; require the explicit flag re-run so the override is intentional.

In **autofix** mode, refuse identically (exit 2). Autofix cannot resolve a strategy override.

When `OVERRIDE_STRATEGY=1` AND the snapshot is populated, capture proceeds with the write **AND** prompts the user to record the override as a decision entry. Pattern (mirrors `/flow-next:interview` behavior (d) — three-criteria decision-record gate):

```bash
# Interactive only — autofix never reaches this branch (5.0 exits 2 above when OVERRIDE_STRATEGY=0,
# and OVERRIDE_STRATEGY=1 in autofix is treated as "user already chose to override; record audit
# trail to stderr but don't prompt" — see logging branch below).
```

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

Use `plain-text numbered prompt` (lead-with-recommendation, `[high]` toward yes):

- **header**: `Record override?`
- **body**: `Override strategy track "<track>" — record as a decision? Recommended: yes — override decisions belong in the decisions track (load-bearing architectural choice). Confidence: [high].`
- **options**: frozen — `yes` (write decision entry), `no` (proceed without recording; audit trail logged to stderr only).

On `yes`, invoke `flowctl memory add` with the override rationale piped via `--body-file -` stdin:

```bash
"$FLOWCTL" memory add \
  --track knowledge \
  --category decisions \
  --title "Override strategy: <track-name>" \
  --module strategy \
  --tags strategy-override \
  --body-file - <<EOF
## Problem
Spec <spec-id> contradicts active track "<track-name>" in STRATEGY.md.

## What was chosen
<concise summary of the override decision>

## Why
<rationale — why the override is the right call given current context>

## Track being overridden
- **<track-name>** (STRATEGY.md): "<canonical track wording>"
- **Spec direction:** "<contradicting wording>"

## Considered alternatives
- Aligning with the strategy track (rejected because: <reason>)
- Updating STRATEGY.md instead of overriding here (rejected because: <reason>)

## Consequences
- This spec ships in tension with track "<track-name>".
- A future `/flow-next:strategy` run should re-evaluate the track; this decision feeds that conversation.
EOF
```

On `no`, proceed without writing the decision. Log an audit-trail line to stderr:

```bash
# On no:
echo "[STRATEGY OVERRIDE]: track=\"<track-name>\" decision-not-recorded spec=<spec-id>" >&2

# On yes (decision was recorded):
echo "[STRATEGY OVERRIDE]: track=\"<track-name>\" decision-recorded=<entry-id> spec=<spec-id>" >&2
```

The audit trail line appears in both interactive (after the user picks) and autofix (when `OVERRIDE_STRATEGY=1` was passed) — it is the minimum durable record that an override happened, surfaceable in CI logs / git hook output later. In autofix mode (where the plain-text numbered prompt is unreachable), the decision-not-recorded variant fires unconditionally.

When `STRATEGY_PRESENT=false`, this entire section is a no-op — there's no strategy snapshot to contradict.
