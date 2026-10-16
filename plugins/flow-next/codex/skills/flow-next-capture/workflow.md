# /flow-next:capture workflow

Execute these phases in order; stop on a user-blocking error rather than continuing with bad state.

Under `from:goal`, the source named in [references/from-goal.md](references/from-goal.md) stands in for the conversation wherever this file reads the user's turns.

This file is the spine every run walks. Path-specific machinery (autofix, `--rewrite`, chart briefings, strategy, splits, glossary, readiness, tracker, must-ask detail) sits in `references/*.md` behind gates. When a gate sentinel prints, STOP and Read the named reference before the next step; when it is silent, read nothing.

## Preamble

```bash
set -e
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SPECS_DIR="$REPO_ROOT/.flow/specs"
TODAY="$(date -u +%Y-%m-%d)"
```

`jq` and `python3` must be on PATH. Mode and flags come from SKILL.md's mode detection. If `.flow/` does not exist, print `No .flow/ directory — run \`$FLOWCTL init\` first.` and exit cleanly.

Take ONE preflight snapshot for the run and derive every later gate from it with `jq`; no further `config get` for values it holds. Compose the literal path with an agent-chosen 4-char suffix and type it verbatim in later calls:

```bash
CAPTURE_CFG="${TMPDIR:-/tmp}/flow-capture-config-<suffix>.json"   # literal path
"$FLOWCTL" preflight --json > "$CAPTURE_CFG" 2>/dev/null || { printf '{"key":null,"value":{}}' > "$CAPTURE_CFG"; echo "[CAPTURE]: config snapshot empty — flowctl unreachable; snapshot-derived gates degrade to defaults" >&2; }
```

---

## Phase 0: Pre-flight

Catch what makes capture unsafe before drafting: a duplicate spec, relevant evidence lost to compaction, an overwrite conflict.

### 0.2 — Duplicate detection

Pull up to 10 distinctive keywords from the user's turns (repeated proper nouns, file paths, multi-word domain phrases, quoted terms). Compare them against the titles of open specs (`status == "open"`) in `.flow/specs/*.json`; a done spec is shipped work, not a duplicate. Count **strong matches** (shared proper nouns, paths, or phrases, not common words): 0-1 is no conflict, 2 is a potential duplicate (`proceed-anyway` recommended), 3+ is likely (`extend` or `supersede` recommended). Record the matched ids and titles for §0.5. (Pre-1.0 `.flow/epics/` repos: port first per `flowctl usage`.)

Then run `"$FLOWCTL" memory search "<keyword>" --json --limit 5` for the top three keywords. Hits are advisory: list them as `Related context:` in the summary; they never trigger the duplicate branch. Skip silently when memory is not initialized.

### 0.3b — Strategy gate

```bash
ACTIVE=0
# NO pipelines in the probe — capture raw first, rc-checked; parse separately.
RAW="$(jq -ce 'if .probes.strategy.status == "ok" then .probes.strategy.value else error("strategy probe") end' "${TMPDIR:-/tmp}/flow-capture-config-<suffix>.json" 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '.sections_filled // 0' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "${VAL:-0}" -ge 1 ] 2>/dev/null && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — STOP. Read references/strategy-alignment.md before continuing."
fi   # default branch: bare no-op — NO link, NO read path
```

On the sentinel, read [references/strategy-alignment.md](references/strategy-alignment.md) and take its snapshot; it also owns the §5.0 contradiction check. Silent: no `[strategy:*]` tags and no §5.0.

### 0.4 — Compaction detection

Look for compaction signals: `[compacted]` markers, truncated tool output, system-summary blocks, or later turns relying on a result that is not visible. Only when one is present: read [references/compaction.md](references/compaction.md) and decide
whether to proceed or refuse as it says. Under `from:goal` this check does not run: the source is read from disk or the invocation.

### 0.5 — Duplicate branch

Silent overwrite is never an option. With ≥2 strong matches and no `REWRITE_TARGET`: GATE ACTIVE — STOP. Read [references/duplicate-branch.md](references/duplicate-branch.md) and run its §0.5 branch (`extend` / `supersede` / `proceed-anyway` / `abort`; autofix exits 2) before drafting. When unsure whether matches are strong, treat the gate as active.

### 0.5b — Chart briefing gate

When the conversation or `$ARGUMENTS` names a chart briefing (a `.flow/charts/*-briefing*.md` path, a B-ID, or a chart id whose sidecar lists briefings): GATE ACTIVE — STOP and Read [references/chart-briefing.md](references/chart-briefing.md) before drafting. It owns admission (draft/stale fail closed; the risk override names the unresolved D-IDs), evidence extraction, the provenance-separation rule, and the `chart link-spec` handoff and its retry rules for Phase 5. Otherwise read nothing.

### 0.6 — Idempotency

- **`REWRITE_TARGET` set** → GATE ACTIVE — STOP. Read [references/rewrite-mode.md](references/rewrite-mode.md) and validate the target (an existing spec, not a task; otherwise exit 2). It also governs Phases 4-6 for the rewrite.
- **Otherwise**, if an earlier turn shows a prior capture (`Spec captured at .flow/specs/<id>.md`), run §0.6 in `references/duplicate-branch.md` (rewrite / proceed / abort; autofix exits 2).

---

## Phase 1: Extract conversation evidence

Build the evidence first; the draft cites it, not memory. It is always collected; whether it is written into the spec is the resolved template's call (§2.2).

### 1.1 — Verbatim user turns

For each user turn with spec content (goals, requirements, constraints, scope, rejected options, examples), emit `> user (turn <N>): "<verbatim text>"`, splitting long turns into verbatim parts. A chosen question option is `> user (turn <N>, selected): "<option label verbatim>"`. Only what the user typed counts: never agent narration, tool output, or capture's own process conclusions (a fabricated "This is a NEW spec. Do NOT mark ready." turn has broken this). Skip greetings and noise. Cap at ~30 lines; when older turns must go, open the block with `> [truncated: N earlier turns]`.

### 1.2 — Codebase verification

When the conversation references repo files or modules whose state matters for the spec (beyond one or two checked on the main thread): GATE ACTIVE — STOP. Read [references/codebase-verification.md](references/codebase-verification.md) and run its read-only investigation before drafting. A verified user-named component can be `[paraphrase]`; unverified ones stay `[inferred]`.

### 1.3 — Title

Draft the shortest noun phrase that names the goal (≤60 chars). A title the user never stated is inferred; Phase 3 case (a) fires only when several plausible titles compete.

---

## Phase 2: Source-tagged synthesis

Spec prose follows [docs/prose.md](../../docs/flow-next/prose.md) when present.

### 2.1 — Source tags

Tag only what capture authored: `[paraphrase]`, `[inferred]`, `[strategy:<track>]`. The user's verbatim words stay untagged and must be findable in the evidence. Meanings and examples: [phases.md](phases.md) §Source-tag taxonomy. When the chart gate fired, apply its provenance-separation rule (chart evidence is never tagged; existing criteria are never retagged).

### 2.2 — Apply the resolved template

The section structure comes from the canonical [the bundled `templates/spec.md`](../../templates/spec.md) (cross-link, never re-embed the list), resolved first-match from `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → the bundled file. Read only the template that resolves: when the repo has `SPEC.md` or `spec.md`, do not open the bundled file. **The resolved template decides what goes in the spec:** write the sections it names as headings or in `auxiliary_sections`, in its order and positions, follow its instructions, and add no section it leaves out (the bundled entries put `Conversation Evidence` at the top and `Requirement coverage` at the end). A section with no conversation signal stays absent; empty beats fabricated.

- **`## Acceptance Criteria`** — `- **R1:** ...` prose bullets, allocated from R1 (fresh spec, no renumber concern). When `.flow/criteria.md` exists, never restate a G-ID as an R-ID; reference it in prose and write an R only for what this spec adds.
- **`## Requirement coverage`** — only when the template names it, `NO_PLAN_OPT=0`, and §2.8 resolved to `plan`: each R-ID mapped to `fn-N.M (TBD - populate via /flow-next:plan)`. Omitted on the `direct` and `refine` routes: work's single implicit task is the coverage, and a placeholder nobody fills would mislead completion review. Capture writes no tasks.
- **`## Parked unknowns`** (optional) — only genuine fog, one bullet each, naming what would resolve it. Decidable now → decide it; resolvable by scheduled work → a task for plan; inferred fill-in stays tagged, not parked.

### 2.4 — Testability

Each criterion must let a reviewer point at behavior and say met or not. One that fails ("make it fast") triggers Phase 3 case (b). Count `[inferred]` lines for the summary.

### 2.5 — Spec-count gate

At 8+ criteria, or criteria serving more than one independently shippable outcome: GATE ACTIVE — STOP. Read [references/split-proposal.md](references/split-proposal.md) and decide 1 vs N specs (it owns the Phase 4 `split-as-proposed` choice, §5.2b, and the split close). Capture never auto-splits. Under `from:goal`, [references/from-goal.md](references/from-goal.md) decides instead.

### 2.6 — Business context

Only when the user stated business context (audience, problem or why-now, UX expectations,
success measures, MVP scope or non-goals, priorities, constraints or risks): read
[references/business-context.md](references/business-context.md) for where each piece goes.

### 2.7 — Glossary gate

```bash
ACTIVE=0
RAW="$(jq -ce 'if .probes.glossary.status == "ok" then .probes.glossary.value else error("glossary probe") end' "${TMPDIR:-/tmp}/flow-capture-config-<suffix>.json" 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '.total_terms // 0' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "${VAL:-0}" -gt 0 ] 2>/dev/null && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — STOP. Read references/glossary-terms.md before continuing."
fi   # default branch: bare no-op — NO link, NO read path
```

On the sentinel, read [references/glossary-terms.md](references/glossary-terms.md) and run its scan (it owns the §5.8 consent and write). Silent: no proposals.

### 2.8 — Route judgment

Once criteria are drafted, judge the spec once against [`plan-vs-no-plan.md`](../flow-next-flow/references/plan-vs-no-plan.md) (plus [`route-matrix.md`](../flow-next-flow/references/route-matrix.md) when product or authority questions or design risk remain). Record the route as `direct`, `refine` or `plan`, and `ROUTE_DIRECT=1` only for `direct`. It feeds the coverage rule, the summary's `Recommended next:`, §5.9b, and Phase 6. Re-judge only when an edit changes the criteria.

---

## Phase 3: Must-ask cases

| Case | Trigger | Interactive | Autofix |
|------|---------|-------------|---------|
| **(a) Ambiguous title** | Several plausible titles, none load-bearing | Pick from candidates or custom | exit 2 |
| **(b) Untestable acceptance** | §2.4 flagged a criterion | Per criterion: drop / reword / clarify | exit 2 |
| **(c) Scope-conflict** | After `supersede` or `proceed-anyway`, scope still overlaps the old spec | How to split the boundaries | exit 2 |

When any case fires: GATE ACTIVE — STOP. Read [references/must-ask-cases.md](references/must-ask-cases.md) for the question shape and autofix error text. Other `[inferred]` content is not asked about; it surfaces in the summary.

---

## Phase 4: Prepare the write

The interactive capture request authorizes saving once pre-flight and must-ask questions are resolved; do not ask for write approval. Autofix keeps its `--yes` gate.

### 4.1 — Materialize and check the body

Write the complete body once to `${TMPDIR:-/tmp}/flow-capture-draft-<working-title-slug>-<4-char suffix>.md` and use that literal path in Phase 5; never re-author it in a heredoc. The body opens with its own `# <title>` (the write replaces the whole file, placeholder heading included). Before writing, check every untagged criterion, decision, and boundary line is findable in the evidence; retag a restatement `[paraphrase]` and an unsupported line `[inferred]`, then recompute the tally. If a split was proposed, settle it per [references/split-proposal.md](references/split-proposal.md); a rewrite follows [references/rewrite-mode.md](references/rewrite-mode.md).

### 4.2 — Snapshot readiness before writing

Under `from:flow`, skip this step and §5.9: flow builds the spec in this session and never asks about readiness.

Otherwise read [references/readiness-snapshot.md](references/readiness-snapshot.md) and take its
snapshot before writing.

### 4.3 — Editor and correction handling

Runs from §5.6a, on the saved spec (never the temporary draft). Only after an `open in editor`
answer or a free-text correction: read
[references/editor-corrections.md](references/editor-corrections.md) and apply it. `continue` needs
nothing here.

### 4.4 — Autofix write gate

Autofix follows [references/autofix-mode.md](references/autofix-mode.md): print the draft summary and write only with `--yes`; without it, exit 0 with the draft path and no spec allocated.

---

## Phase 5: Write via flowctl

### 5.0 — Strategy contradiction check

When §0.3b's gate fired, run §5.0 of `references/strategy-alignment.md` before any write (refuses a contradiction unless `--override-strategy`, and records the override).

### 5.2 — New-spec branch

The §4.1 draft file is the body; tags stay in it as the audit trail.

```bash
SPEC_TITLE="<chosen title from Phase 3 or Phase 1.3>"

# Tracker-first mint gate (distributed id allocation). Probe raw, rc-checked; parse separately.
ACTIVE=0
RAW="$(jq -ce 'if .probes.tracker.status == "ok" then .probes.tracker.value else error("tracker probe") end' "${TMPDIR:-/tmp}/flow-capture-config-<suffix>.json" 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '.active' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "$VAL" = "true" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — STOP. Read references/tracker-integration.md before continuing."
fi   # default branch: bare no-op — NO link, NO read path

# SILENT degrade - the ONLY flow-first creation site, deliberately an
# unconditional post-check outside the tracker-first branch (rationale + the
# orphan-issue GUARD live in references/tracker-integration.md §5.2).
# Type the literal draft path verbatim (never a shell variable across prompt turns).
if [ -z "$SPEC_OUTPUT" ] && [ -z "$IDENTIFIER" ]; then
  SPEC_OUTPUT=$("$FLOWCTL" spec create --title "$SPEC_TITLE" --plan-file "${TMPDIR:-/tmp}/flow-capture-draft-<working-title-slug>-<suffix>.md" --json)
fi
SPEC_ID=$(printf '%s' "$SPEC_OUTPUT" | jq -r '.id')

if [[ -z "$SPEC_ID" || "$SPEC_ID" == "null" ]]; then
  echo "Error: spec create failed: $SPEC_OUTPUT" >&2
  exit 1
fi

# Run anchor for Phase 6's sync check — written BEFORE the 5.7 dispatch.
date -u +%Y-%m-%dT%H:%M:%SZ > "${TMPDIR:-/tmp}/flow-capture-anchor-${SPEC_ID}"
```

On the tracker sentinel, read [references/tracker-integration.md](references/tracker-integration.md) and run its §5.2 tracker-first mint (and later its §5.7 touchpoint). Silent: `spec create` mints locally and nothing tracker-related runs. `spec create` leaves nothing behind on failure; report the error and exit 1. When the chart gate fired, run its §5.2 `chart link-spec` handoff only after a successful create.

### 5.2b — Split branch

Only after `split-as-proposed`: `references/split-proposal.md` §5.2b (all N bodies, §5.2 per spec in dependency order, `spec add-dep` per edge). Autofix never reaches it.

### 5.3 — Rewrite branch

Only with `REWRITE_TARGET`: `references/rewrite-mode.md` §5.3 (`set-plan` over the existing body, idempotent `spec unready`, run anchor).

### 5.4 — Branch name

If the user named a feature branch, run `"$FLOWCTL" spec set-branch "$SPEC_ID" --branch "<slug>" --json`; otherwise the spec id default stands.

### 5.6a — Saved-spec review (interactive only)

Read only the § Summary payload section of [docs/read-back.md](../../docs/flow-next/read-back.md#summary-payload)
(its other sections cover plan/refine ratification and restate this step) for the summary shape: title, criteria count, source tally, warnings, related memory context, recommended route, and the saved path (plus the rewrite diff; one summary per spec for a split). The full body prints only on request.

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

Then use `plain-text numbered prompt` for one short editor question: `open in editor` opens the saved file(s); `continue` leaves them as written; free text is a correction. Apply §4.3 to either, then continue the remaining follow-ups without re-approval. Skip an offer already answered, and honor a request to review later. Saving or viewing grants no readiness, implementation, commit, or external-write authority; configured tracker behavior keeps its own scope.

### 5.7 — Tracker sync touchpoint

Only when §5.2's tracker gate fired: `references/tracker-integration.md` §5.7 (best-effort, `--event capture` receipt).

### 5.8 — Glossary term-adds (interactive only)

With glossary proposals, ask the separate `Glossary?` question in [references/glossary-consent.md](references/glossary-consent.md) unless already answered, and write only consented terms. Autofix never writes terms.

### 5.9 — Mark-ready write (interactive only)

With an eligible §4.2 snapshot, offer the separate `Mark ready?` question per [references/mark-ready.md](references/mark-ready.md) unless already answered: `mark-ready` writes, `keep-draft` leaves readiness unchanged. Autofix never writes readiness. Under `from:flow` the question is never asked: the conductor builds the spec in this session, so readiness does not matter and the spec stays as it is.

### 5.9b — No-plan write

Runs only on `NO_PLAN_OPT=1` (`--no-plan`, interactive or autofix) or `FROM_FLOW=1` with `ROUTE_DIRECT=1`. A user invocation without the flag never sets the field, whatever §2.8 judged.

```bash
# Capture raw first, rc-checked; parse separately so a non-task failure keeps its real reason.
if ! NO_PLAN_OUT="$("$FLOWCTL" spec set-no-plan "$SPEC_ID" --json 2>&1)"; then
  NO_PLAN_REASON="$(printf '%s' "$NO_PLAN_OUT" | jq -r '.error // empty' 2>/dev/null | head -1)"
  [ -z "$NO_PLAN_REASON" ] && NO_PLAN_REASON="$(printf '%s' "$NO_PLAN_OUT" | head -1)"
  echo "no_plan not set: ${NO_PLAN_REASON:-unknown error} — field left unchanged"
fi
```

Best-effort: a refusal (the spec already has tasks, reachable only on a `--rewrite` of a planned spec) prints that notice and the run continues.

---

## Phase 6: Close

**Tracker-sync check first.** Run a fresh `$FLOWCTL sync active --json` now (the preflight
snapshot can be stale). Only when it parses and reads `active: false`: skip the check and print no
`Tracker sync:` line. Otherwise, including a probe error: read
[references/tracker-integration.md § Phase 6 — sync check](references/tracker-integration.md#phase-6-sync-check)
and run it.

Then print:

```text
Spec captured at .flow/specs/<SPEC_ID>.md.
Tracker sync: <OK | MISSING:capture → retro-fired → OK | MISSING:capture (retro-fire failed: <reason>)>
Recommended next: <the §2.8 judgment, in plan-vs-no-plan.md's shape>
```

- `Tracker sync:` prints only when the bridge is active.
- `Recommended next:` is mandatory unless `/flow-next:flow` dispatched the run: the §2.8 line from [`plan-vs-no-plan.md`](../flow-next-flow/references/plan-vs-no-plan.md) with the spec id filled in, in this host's command spelling (route-matrix.md's host command form). It is a recommendation, never a readiness write or permission to execute. Under `from:flow`, omit it: the conductor's stop report owns the next step.
- Gate-owned lines follow only when their step ran: `Glossary: added N term(s) (…)` (§5.8), `Readiness: marked ready` (§5.9), and `No-plan: field set (flow --auto/work take the direct route)` or the refusal notice (§5.9b).

A rewrite and a split change the first line and repeat the block per spec; `references/rewrite-mode.md` and `references/split-proposal.md` own those variants.

---

