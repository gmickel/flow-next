# fn-39-project-strategy-strategymd-anchor.4 Interview + capture + plan-sync grounding (autodetect + Strategy Conflicts + override-strategy + drift)

## Description
Wire `STRATEGY.md` grounding into `/flow-next:interview` (doc-aware autodetect extension, `## Strategy Conflicts` section, ≤1/turn throttle), `/flow-next:capture` (Phase 0 input, `[strategy:<track>]` source tagging, `--override-strategy` flag with decision-record prompt), and `/flow-next:sync` (plan-sync agent Step 5 strategy context, `## Strategy drift flagged for review`). All three consume `flowctl strategy read --json` and surface advisory output (read-only).

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` (autodetect extension lines 81-106; `## Strategy Conflicts` Phase-zero behavior)
- `plugins/flow-next/skills/flow-next-capture/SKILL.md` + `phases.md` (Phase 0 strategy input, source tagging, `--override-strategy` flag handling)
- `plugins/flow-next/agents/plan-sync.md` (Step 5 strategy context gather + drift surface block)

Depends on Task 1 (consumes flowctl strategy plumbing) and Task 2 (skill file authored — flag matrix documented in CLAUDE.md).

## Approach

**Interview** (extends existing 0.39.0 doc-aware mode):

- Extend autodetect block at `flow-next-interview/SKILL.md:81-106`. Currently checks `glossary.total_terms > 0` AND `decisions/ entries`. Add third condition: `flowctl strategy status --json | jq '.sections_filled >= 1'`. Activate doc-aware mode when ANY of the three returns true.
- Add `--strategy` / `--no-strategy` flag parsing parallel to existing `--docs` / `--no-docs` (lines 61-79). Independent flags — 5-row matrix:

  | Flags | Glossary | Decisions | Strategy |
  |-------|----------|-----------|----------|
  | (default) | autodetect | autodetect | autodetect |
  | `--docs` | on | on | on |
  | `--no-docs` | off | off | off |
  | `--no-docs --strategy` | off | off | on |
  | `--docs --no-strategy` | on | on | off |
- Add behavior (e) — code-versus-strategy contradiction surfacing — parallel to behavior (a) glossary-conflict at lines 192-249. When user input or research conflicts with active track, write `## Strategy Conflicts` spec section. Format: user-wording + canonical-strategy-wording + STRATEGY.md path + resolution chosen.
- Throttle: ≤1 strategy-conflict question per interview turn (parallel to existing glossary-question throttle at line 410-412). Total per-turn doc-aware question budget is now 1 glossary + 1 decision-record + 1 strategy = 3 max; existing throttles enforce per-category, so no global limit needed.

**Capture** (extends Phase 0 pre-flight):

- `flow-next-capture/phases.md` (or workflow.md) Phase 0 — add `STRATEGY.md` read alongside existing `.flow/epics/` scan and `flowctl memory search`. Surface in chat as "Strategic context:" footnote with approach + tracks list (3-5 lines).
- Source tagging: add `[strategy:<track-name>]` source tag to the existing `[user]` / `[paraphrase]` / `[inferred]` taxonomy. When acceptance criterion is derived from STRATEGY.md (e.g., approach line states "X approach", spec criteria says "use X approach"), tag it. Read-back loop displays the count of `[strategy:*]` criteria alongside `[inferred]` count.
- New flag: `--override-strategy`. When capture detects the spec contradicts an active track (criterion is `[strategy:<track>]` AND spec body contradicts that track), refuse the write with stderr message "Spec contradicts active track `<track>` — pass `--override-strategy` to proceed."
- On `--override-strategy` flag fire: prompt user via `AskUserQuestion` "Record this override as a decision?" with lead-with-recommendation `[high]` toward yes (the override is a load-bearing architectural choice — exactly what the decisions track was added for). On yes: invoke `flowctl memory add --track knowledge --category decisions --title "Override strategy: <track>" --module strategy --tags strategy-override --body-file <stdin>` with the override rationale. On no: proceed with capture but log the override in stderr for audit trail.

**plan-sync** (extends Step 5 context gather):

- `agents/plan-sync.md` Step 5 (lines 97-128 — currently builds `GLOSSARY_JSON` and `DECISIONS_JSON`). Add `STRATEGY_CONTENT` variable: `STRATEGY_CONTENT="$($FLOWCTL strategy read --json 2>/dev/null || echo '{}')"`. Pass into the plan-sync prompt under a `STRATEGY_CONTENT:` key alongside the existing keys.
- Husk short-circuit at line 110-112 pattern: when both glossary husk AND no decisions AND `strategy.sections_filled == 0`, skip the entire context-gather (no signal to align to).
- Track-rename handling: when plan-sync detects an existing spec uses an old track name (matches a verbatim quote-pattern from a previous STRATEGY.md `tracks` section), replace inline with `<canonical-name> <!-- Updated by plan-sync: track rename from "<old>" -->`. Mirror the existing glossary rename pattern documented in CLAUDE.md "Plan-sync contract" section.
- Add `## Strategy drift flagged for review` block to spec output when plan-sync detects spec scope contradicts an active track. Read-only — never auto-supersedes. Format mirrors existing "Decision overrides flagged for review" at lines 101-105: bulleted list with spec line + STRATEGY.md track citation + "Review and run `/flow-next:strategy` if intended."

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:61-79` — `--docs` / `--no-docs` flag parsing (model for `--strategy` / `--no-strategy`)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:81-106` — doc-aware autodetect block (extend with third condition)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:187-271` — behaviors (a)+(b) glossary-conflict + fuzzy-term sharpening (model for behavior (e) strategy-conflict)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:273-318` — behavior (d) decision-record three-criteria gate (model for `--override-strategy` decision-record prompt)
- `plugins/flow-next/skills/flow-next-capture/phases.md` — Phase 0 pre-flight scans
- `plugins/flow-next/skills/flow-next-capture/workflow.md` — source-tagging convention `[user]` / `[paraphrase]` / `[inferred]`
- `plugins/flow-next/agents/plan-sync.md:95-128` — Step 5 context gather + husk short-circuit
- `plugins/flow-next/agents/plan-sync.md:200-245` — read-only-surface convention for drift flagging

**Optional:**
- `CLAUDE.md` "Plan-sync contract" section — glossary rename + decision overrides plumbing convention
- `CLAUDE.md` "Project glossary" subsection — flag matrix documentation pattern (apply same shape to strategy)

## Key context

- `--strategy` / `--no-strategy` are NEW flags, NOT subordinate to `--docs`. The 5-row matrix is the contract.
- Throttle: ≤1 strategy-conflict question per interview turn. Total doc-aware budget per turn is 3 (1 each for glossary / decisions / strategy).
- `--override-strategy` decision-record prompt: lead-with-recommendation `[high]` toward yes. User retains override authority — no on prompt is allowed.
- plan-sync NEVER auto-supersedes. Track-rename inline replacement is the ONLY auto-edit; everything else is surfaced read-only.
- Husk semantics: same `sections_filled >= 1` rule across all three skills. NOT `[[ -f STRATEGY.md ]]`.
## Acceptance
- [ ] `flow-next-interview/SKILL.md:81-106` autodetect block extended: third OR condition `flowctl strategy status --json | jq '.sections_filled >= 1'` joins existing glossary + decisions checks. Doc-aware mode activates when ANY of the three is true.
- [ ] `flow-next-interview/SKILL.md:61-79` flag parsing extended: `--strategy` / `--no-strategy` flags strip from `RAW_ARGS`. 5-row flag matrix documented inline in SKILL.md (or referenced from CLAUDE.md):

      | Flags | Glossary | Decisions | Strategy |
      | (default) | auto | auto | auto |
      | --docs | on | on | on |
      | --no-docs | off | off | off |
      | --no-docs --strategy | off | off | on |
      | --docs --no-strategy | on | on | off |
- [ ] New behavior (e) — code-versus-strategy contradiction. Activates only when strategy condition is on. Surfaces conflicts in `## Strategy Conflicts` spec section (parallel to existing `## Glossary Conflicts`). Format: user-wording / canonical-strategy-wording / STRATEGY.md path / resolution-chosen.
- [ ] Throttle: ≤1 strategy-conflict question per interview turn. Verified via per-turn count check in skill prose (parallel to existing glossary-question throttle).
- [ ] `flow-next-capture/phases.md` (or workflow.md) Phase 0 reads `STRATEGY.md`. Surfaces "Strategic context:" footnote with approach (verbatim) + active tracks (names + bodies, capped 3-5 lines total). <!-- Updated by plan-sync: fn-39-project-strategy-strategymd-anchor.3 emits `tracks` from `flowctl strategy read --json` as a raw markdown string containing `### <track-name>` H3 sub-blocks (not a pre-parsed list); capture must handle H3 parsing locally. Empty section bodies surface as `""` (empty string), not null. -->
- [ ] Source tagging: `[strategy:<track-name>]` joins the existing `[user]` / `[paraphrase]` / `[inferred]` source-tag taxonomy. Acceptance criteria derived from STRATEGY.md content (verbatim or near-verbatim quote of approach/track) get this tag.
- [ ] Read-back loop displays count of `[strategy:*]` criteria alongside `[inferred]` count. Format: `Source: [user] N · [paraphrase] M · [strategy] K · [inferred] L`.
- [ ] `--override-strategy` flag implemented in capture. When capture detects spec body contradicts an active track AND no `--override-strategy` is passed, exits non-zero with stderr `Spec contradicts active track "<track>" — pass --override-strategy to proceed.`
- [ ] On `--override-strategy` fire, capture prompts user via `AskUserQuestion` "Record this override as a decision?" with lead-with-recommendation pattern (body: "Recommended: yes — override decisions belong in the decisions track. Confidence: [high]"). Options: yes / no.
- [ ] On yes: invokes `flowctl memory add --track knowledge --category decisions --title "Override strategy: <track-name>" --module strategy --tags strategy-override` with override rationale piped via `--body-file -` stdin (mirrors existing decision-record three-criteria gate at `flow-next-interview/SKILL.md:273-318`).
- [ ] On no: capture proceeds with the spec write but logs `[STRATEGY OVERRIDE]: track="<track>" decision-not-recorded` to stderr for audit trail.
- [ ] `agents/plan-sync.md` Step 5 (lines 97-128) extended: adds `STRATEGY_CONTENT="$($FLOWCTL strategy read --json 2>/dev/null || echo '{}')"` variable. Passes into plan-sync prompt under `STRATEGY_CONTENT:` key alongside existing `GLOSSARY_JSON` and `DECISIONS_JSON`.
- [ ] Husk short-circuit at plan-sync line 110-112: when ALL of glossary husk AND no decisions AND `strategy.sections_filled == 0`, the entire Step 5 context gather skips. When ANY of the three has signal, Step 5 runs.
- [ ] Track-rename handling: when plan-sync detects an existing spec body uses a track name absent from current STRATEGY.md but historically present (heuristic: match a track-name pattern from prior file content), replace inline with `<canonical-name> <!-- Updated by plan-sync: track rename from "<old>" -->`. Mirrors glossary rename pattern in CLAUDE.md "Plan-sync contract" section. <!-- Updated by plan-sync: track names parsed from the `tracks` raw markdown string (H3 `### <track-name>` sub-blocks); plan-sync greps prior STRATEGY.md content using the same H3 pattern. -->
- [ ] `## Strategy drift flagged for review` block added to plan-sync output spec when scope contradicts active track. Format mirrors existing "Decision overrides flagged for review": bulleted list with spec line + STRATEGY.md track citation + `Review and run /flow-next:strategy if intended.` line.
- [ ] Plan-sync NEVER edits `STRATEGY.md`. Read-only consumption. Drift block, track-rename inline replacement (in spec body, not in STRATEGY.md), and STRATEGY_CONTENT prompt input only.
- [ ] All bash that calls `flowctl strategy ...` uses portable `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl` form per existing flow-next conventions.
## Done summary
Wired STRATEGY.md grounding into `/flow-next:interview` (autodetect third condition + 5-row flag matrix + `## Strategy Conflicts` section + ≤1/turn throttle), `/flow-next:capture` (Phase 0 strategy input + `[strategy:<track>]` source-tag taxonomy + `--override-strategy` flag with decision-record prompt + audit-trail stderr), and `/flow-next:sync` plan-sync agent (Step 5 STRATEGY_CONTENT input + extended husk short-circuit + `## Strategy drift flagged for review` block + track-rename inline replacement). Codex mirror regenerated via sync-codex.sh; CI test suite + glossary smoke test green.
## Evidence
- Commits: 971d24b0237df6b299246ea3d746a48546e08268
- Tests: plugins/flow-next/scripts/ci_test.sh (56/56 pass), doc-aware autodetect /tmp fixture test — STRAT activates only on populated STRATEGY.md (no-strategy / husk-strategy / populated-strategy), 5-row flag matrix verbatim block test (default / --docs / --no-docs / --no-docs --strategy / --docs --no-strategy — all rows verified), scripts/sync-codex.sh validation (22 skills, 21 agents, all required openai.yaml present, no Claude-native tool refs in Codex mirror), glossary_smoke_test.sh regression (80/80 pass)
- PRs: