# Interview — spec write-back templates (loaded at completion)

> Loaded at the Completion step to write the refined spec, per input type. Only ONE branch runs
> (NEW IDEA / EXISTING SPEC / Flow Task / File Path). Split out of the always-loaded SKILL.md so
> its ~160 lines are not held in context across the whole interview.

**Host command form:** print every copy-pasteable flow-next command here in the spelling this host invokes — the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install — the same signal setup's host detection uses); on any other or indeterminate host, exactly as spelled here.

## Write Refined Spec

After interview complete, write everything back — **scope depends on input type**.

Spec prose written back here follows the artifact prose contract in [docs/prose.md](../../../docs/flow-next/prose.md); proceed without it when the doc is absent.

**Single-emission write pattern (all branches below):** compose the body and Write it ONCE via the **Write tool** to a **literal unique path** (the file is what flowctl `--file` consumes; Write is plumbing). Path-persistence rule: bash vars do NOT survive across prompt turns, and that applies to the draft path itself — compose the path in agent context (`${TMPDIR:-/tmp}/flow-interview-<kind>-<id>-<agent-chosen 4-char suffix>.md`) and type it verbatim in the Write call AND the flowctl `--file <path>` call; never a shell variable across prompt turns (`mktemp` only for paths created and consumed within one bash block).

**Print-then-ask approval (R13 — same contract as capture Phase 4):** before handing the draft to flowctl, obtain write-back approval:

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

1. **Print first:** emit the FULL draft markdown as an ordinary assistant message (the user-visible read-back — real markdown, real newlines). Never embed multi-paragraph drafts/diffs/criteria lists in the `plain-text numbered prompt` body (they render as collapsed plain text).
2. **Then short ask** via `plain-text numbered prompt`: one-line pointer (`Full write-back draft printed above.`) + the source-tag tally **when this pass wrote spec `## Acceptance Criteria` bullets** (the NEW IDEA and EXISTING SPEC branches): `Source: [user] N · [paraphrase] M · [strategy] K · [inferred] L`. **Omit the tally entirely for a Flow Task or File Path target** — those branches carry no source tags by design, so a tally there would read as an all-zero "nothing classified" and mislead. Then any compact warnings (e.g. open-questions count) + options only — e.g. `approve` / `edit` / `abort`. No multi-paragraph content in the ask.

**Edit-cycle rule:** if the user picks `edit`, apply revisions via the Edit tool (deltas only), then **Read the FULL draft file**, **reprint the full revised draft as ordinary markdown**, and re-issue the short approval ask. The full-file Read also satisfies Edit's read-before-edit for the next cycle. Loop until `approve` or `abort`.

Done when: exactly one input-type branch below has run; the body was Written once to its literal path, printed in full, and approved; flowctl consumed that same literal path; and every section the write-policy listed as preserved is byte-identical to the copy read at Detect Input Type.

The canonical spec section structure lives in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) (the single source of truth — never re-embed the section list inline per R17). The templates below show the additional **interview audit sections** that layer onto the canonical structure; the underlying spec sections (`## Goal & Context`, `## Architecture & Data Models`, ...) come from the template.

**The `flowctl scope write-policy` result is the source of truth for which sections this scope writes and which it preserves** — it governs the whole write-back, together with the section-write rules from the scope-aware pass behavior (SKILL.md plus the pass reference read for the resolved scope). A section rewritten that this pass's `writable` list does not name has broken this. The `## Decision Context` substructure / FLAT-vs-substructured promotion logic is in the write-policy; do not invent inline.

**Project-added sections.** `write-policy` enumerates the canonical sections only, so a spec may contain sections this project added via its own repo-root `SPEC.md` scaffold (a risk register, user stories, a rollout runbook). Never treat a section's absence from the write-policy lists as permission to drop it. Decide ownership from the section's own scope-owner marker in the body, and default to caution:

- marker names **your** scope (e.g. `<!-- scope: business -->` under a `--scope=business` pass) → **writable**: fill and refine it exactly as you would a canonical section of that scope.
- marker names the **other** scope → **preserve byte-for-byte**, same as any other-scope canonical section.
- **no marker, or a marker you cannot parse** → **preserve byte-for-byte**, and mention in the read-back that it was left untouched so the user can add a marker if they wanted it filled.

`scope: both` on a project-added section is writable under any pass. A project-added section carrying an empty body is still preserved unless it is writable under this scope - an empty section you do not own is the user's placeholder, not litter.

### Source tags on acceptance criteria (same vocabulary as `/flow-next:capture`)

Every acceptance criterion **this pass newly writes** carries a trailing source tag - the last `[...]` token on the bullet. The **tag name** is lowercase with no spaces (`user` / `paraphrase` / `inferred` / `strategy`). For `[strategy:<track>]` the part after the colon is the track's H3 heading **copied literally** - keep its casing AND its spaces, so a track named `### Cross-platform parity` becomes `[strategy:Cross-platform parity]`. Never slugify, lowercase, or strip spaces from a track name; the literal text is what links the criterion back to `STRATEGY.md`.

```markdown
- **R7:** Errors include the request id for trace correlation. [inferred]
- **R9:** Windows paths resolve without a shell. [strategy:Cross-platform parity]
```

| Tag | Meaning |
|-----|---------|
| `[user]` | Verbatim from conversation evidence (exact quote or close paraphrase preserving meaning). "The user" is the human in THIS pass: the PO under `--scope=business`, the tech lead under `--scope=technical`. |
| `[paraphrase]` | User intent restated in spec language (semantic equivalence; no new constraints introduced) |
| `[inferred]` | Agent fill-in (most-scrutinized; user must confirm at read-back) |
| `[strategy:<track>]` | Derived from `STRATEGY.md` content (verbatim or near-verbatim from `approach` or a `### <track-name>` H3 sub-block); track name lives literally in the tag |

Hard rules:

- **Tag only criteria this pass authors.** Never add, change, or remove a tag on a criterion an earlier pass wrote - provenance is frozen exactly like the R-ID number. Untagged legacy criteria stay untagged; absence means unknown provenance, never `[user]`.
- **Never ask about tagging.** The tag records how a criterion got written down; it is not an extra interview question.
- **Uniform tagging is a failure, not a safe default.** A criterion the interviewee answered is `[user]` or `[paraphrase]`; only genuine gap-fill is `[inferred]`. If everything you wrote came out `[inferred]`, the tally carries no signal - re-check which criteria came from actual answers.
- **No self-blessing on unasked guesses** (capture's rule, narrowed for interview): if any criterion you wrote is `[inferred]` AND no interview question covered it, do NOT recommend `approve` in the ask above - state the count and let the user check those lines. Criteria settled by an answered question are verified by construction and do not trigger this.
- **Standing criteria stay out of the R list.** When `.flow/criteria.md` exists, do not restate its standing criteria (G-IDs) as R-IDs - completion review already judges every G-ID against the spec. Reference a relevant G-ID in prose when useful; append an R only for what this spec adds beyond the standing rule.

### For NEW IDEA (text input, no Flow ID)

Create spec with interview output. **This branch writes a spec and zero tasks** — task creation is `/flow-next:plan`'s job. A run that leaves `flowctl tasks --spec <id>` non-empty has broken this.

The canonical section layout for the spec body is in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) — the **template file is the seed** for the canonical 7-section structure (`Goal & Context`, `Architecture & Data Models`, `API Contracts`, `Edge Cases & Constraints`, `Acceptance Criteria`, `Boundaries`, `Decision Context`). `flowctl spec skeleton` is **NOT** the seed here — it returns a 1.0.2-shape skeleton (`Overview` / `Scope` / `Approach` / `Quick commands` / `Acceptance` / `References`) for R22 byte-for-byte backward-compat with the pre-1.1.0 `flowctl spec create` output, which uses different section names than the new canonical template. Reading from `flowctl spec skeleton` here would seed sections the scope-aware write-policy doesn't recognize. Read the template file directly. Fill the scope-owned canonical sections per the write-policy above, then append the auxiliary interview-audit sections below the canonical body (the R21 sync-codex drift guard forbids re-embedding the canonical section sequence in any skill markdown — the template file is the only allowed location).

**Spec-id scheme.** When minting a brand-new spec here, route on `tracker.specIds` from the interview run's **single** root config snapshot (fn-110). Interview holds no earlier snapshot, so this write-back is where it is taken - one root read for the run, never a per-leaf `config get tracker.specIds` and never a second snapshot. Tracker-first is the team default when the bridge is active (`tracker.specIds=tracker`): create-first then mint. Explicit user override always wins; bridge inactive / no transport degrades **silently** to flow-first. No runtime nag (withdrawn R10). Network cost is conditional: when `tracker.perEvent.interview` is already active, tracker-first reorders that write; when the leaf is off (default), it adds an earlier remote write.

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
# ONE root snapshot for this mint (fn-110). Literal path.
INTERVIEW_CFG="${TMPDIR:-/tmp}/flow-interview-config-<suffix>.json"
$FLOWCTL config get --json > "$INTERVIEW_CFG" 2>/dev/null || printf '{"key":null,"value":{}}' > "$INTERVIEW_CFG"
SPEC_IDS=$(jq -r '.value.tracker.specIds // "flow"' "$INTERVIEW_CFG" 2>/dev/null)
BRIDGE_ACTIVE=$($FLOWCTL sync active --json 2>/dev/null | jq -r '.active // false')

if [ "$SPEC_IDS" = "tracker" ] && [ "$BRIDGE_ACTIVE" = "true" ]; then
  # Named existing issue → $FLOWCTL spec create --tracker-first --tracker-identifier "<key>" --title "..." --json
  #   then attach + seed too (tracker-sync steps.md Phase 2b): minting stores the
  #   identifier but NOT the durable tracker.id, and an unlinked spec makes a later
  #   touchpoint create a SECOND remote issue instead of linking the named one.
  # Fresh idea → skill: flow-next-tracker-sync (operation: create-first, title, body)
  #   then mint + attach + seed (tracker-sync steps.md Phase 2d "Enabled caller sequence")
  # Assign SPEC_OUTPUT on every path that succeeds here.
  :
fi

# SILENT degrade - the ONLY flow-first creation site, deliberately OUTSIDE the
# branch above. On a create-first noop / unreachable transport SPEC_OUTPUT is
# unset INSIDE the tracker arm, where an `else` can never run, so the
# fall-through has to be an unconditional post-check.
# GUARD: degrade ONLY when nothing was created remotely - a failed mint AFTER
# create-first made an issue must surface identifier + url + retryKey and stop,
# never silently create an fn-N spec that leaves the issue orphaned.
if [ -z "$SPEC_OUTPUT" ] && [ -z "$IDENTIFIER" ]; then
  SPEC_OUTPUT=$($FLOWCTL spec create --title "..." --json)
fi

# Build the spec body in-memory:
#   1. Seed from the canonical template FILE (not `flowctl spec skeleton` —
#      that command stays 1.0.2-compatible per R22; its section names
#      (Overview / Scope / Approach / Quick commands / Acceptance / References)
#      don't match the scope-aware write-policy's canonical section names).
#
#      Resolve the template via the 3-tier discovery cascade. The full walker
#      (cascade order, case-insensitive FS probe, both-exist warning, plugin-root
#      fallback) is single-sourced in ../../references/spec-template-discovery.md —
#      Read it and run its walker to set TEMPLATE_PATH + TEMPLATE.
#      Fill section bodies from interview answers under your scope's writable
#      sections per the write-policy (frontmatter + scope-owner markers may be
#      stripped from the final spec body — authoring guidance, not spec content).
#   2. Append the auxiliary interview-audit sections (only those that fired):
```

**Source-tag every acceptance criterion written here** (`[user]` / `[paraphrase]` / `[inferred]` / `[strategy:<track>]`, trailing token - see "Source tags on acceptance criteria" above). This branch mints the spec, so every criterion in it is one you authored this pass: an answered question yields `[user]` or `[paraphrase]`, agent gap-fill yields `[inferred]`.

Compose the full body and Write it ONCE to a literal unique path (e.g. `${TMPDIR:-/tmp}/flow-interview-spec-<id>-<suffix>.md`) via the **Write tool** — per the single-emission write pattern above. The body:

```markdown
<canonical body from skeleton, with interview-answered prose under each
 writable section per the write-policy — biz pass fills biz-owned sections,
 tech pass fills tech-owned, placeholders under empty other-side sections;
 every acceptance criterion carries its trailing source tag>

## Resolved via Codebase
(optional — written by the technical pass when codebase-investigation resolved items)
Items the agent answered via Read / Grep / Glob, with file:line evidence. Separate from items the user answered. Lets reviewers spot-check assumptions later.

## Resolved via Project Docs
(optional — written by the business pass per R26 when project-docs investigation resolved items)
Items the agent answered via README / CHANGELOG / STRATEGY / GLOSSARY / knowledge decisions / .flow specs / docs, with `path` or `path:line` evidence. Symmetric to `## Resolved via Codebase` but biz-pass-only.

## Glossary Conflicts
(optional — only when DOC_AWARE=1 surfaced behavior-(a) hits during the interview)
Per-term: user-wording vs. canonical term, the resolution chosen (use-canonical / redefine / this-is-different), file:line of the canonical entry. Lets reviewers see where vocabulary tightened.

## Strategy Conflicts
(optional — only when STRATEGY_AWARE=1 surfaced behavior-(e) hits during the interview)
Per-line: user-wording vs. canonical-strategy-wording (track name or approach), STRATEGY.md path, resolution chosen (align-with-strategy / flag-as-drift / this-is-different). Lets reviewers see where the spec aligns or pushes back on strategic intent. Read-only signal for plan-sync — the interview never edits STRATEGY.md.

## Parked unknowns
(optional — only when the interview surfaced fog nothing in this pass could resolve)
One bullet per genuinely-unknown item, each naming what would resolve it. Fog-or-ticket test: decidable now → decide it in the section that owns it; resolvable by scheduled work → it is a task, not fog; genuinely unknown → park it here. Omit the heading when the list is empty.

## Open Questions
Unresolved items that need research during planning, plus every skipped interview question (owner hint + the agent's unconfirmed leaning — SKILL.md skip contract). When the write-back checkpoint chose fill-assumptions, the filled prose carries inline `*(assumed — unconfirmed)*` markers and one entry here points at them.
```

Then hand flowctl the draft file — the literal path typed verbatim (never a shell variable across prompt turns):

```bash
$FLOWCTL spec set-plan <id> --file "${TMPDIR:-/tmp}/flow-interview-spec-<id>-<suffix>.md" --json
```

Then suggest: "Run `$flow-next-plan fn-N` to research best practices and create tasks."

### For EXISTING SPEC (fn-N that already has tasks)

**First check if tasks exist:**
```bash
$FLOWCTL tasks --spec <id> --json
```

**If tasks exist:** Only update the spec (add edge cases, clarify requirements). **Do NOT touch task specs** — plan already created them.

**If no tasks:** Update spec, then suggest `$flow-next-plan`.

The canonical section layout for the spec body is in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md). Read the existing spec, refine sections under your scope per the write-policy (preserving sections owned by the other scope byte-for-byte, and project-added sections per the ownership rule above), and append/update the auxiliary interview-audit sections. The R21 drift guard forbids re-embedding the canonical section sequence in this skill - read the existing body, do not regenerate from a template.

**Reuse the spec body already fetched at Detect Input Type** (`$FLOWCTL cat <id>` ran there) — do NOT re-fetch here. Re-fetch only if the interview mutated the spec on disk since that read (e.g. an earlier partial write-back in this run).

**Source-tag only the acceptance criteria this pass appends** (`[user]` / `[paraphrase]` / `[inferred]` / `[strategy:<track>]`, trailing token - see "Source tags on acceptance criteria" above). Criteria already in the spec keep their bullet exactly as read: never add a tag to an untagged legacy criterion, never change or drop an existing one.

Refine canonical sections under your scope's writable list (per write-policy) while preserving sections owned by the other scope byte-for-byte, apply the project-added-section ownership rule above, append the auxiliary interview-audit sections (only those that fired), and Write the merged body ONCE to a literal unique path (e.g. `${TMPDIR:-/tmp}/flow-interview-spec-<id>-<suffix>.md`) via the **Write tool** - per the single-emission write pattern above. The body:

```markdown
<merged body: EVERY section present in the Detect-Input-Type read, in its
 original order, with this scope's writable sections refined from interview
 answers, other-scope sections preserved byte-for-byte per the write-policy,
 and project-added sections written or preserved per their scope-owner marker.
 Acceptance criteria: newly appended R-IDs carry a trailing source tag;
 pre-existing bullets keep their tag, or stay untagged, byte-for-byte>

<then the auxiliary interview-audit sections — same headings, same contents,
 and same only-when conditions as the NEW IDEA branch above (Resolved via
 Codebase / Resolved via Project Docs / Glossary Conflicts / Strategy
 Conflicts / Parked unknowns / Open Questions); emit only those that fired.
 One difference on this branch: `## Parked unknowns` is the pre-existing list
 minus every bullet this pass resolved, plus any new fog — omit the heading
 when it empties out.>
```

### Parked unknowns — the one auxiliary section a pass takes from

Read `## Parked unknowns` before composing the merged body. For each bullet: **this pass resolved it** → move the answer into the canonical section that owns it (under this scope's writable list) and DELETE the bullet from `## Parked unknowns`; **still unknown** → carry the bullet back byte-for-byte. Never leave a parked bullet standing next to its own answer — that is the stale fog this section exists to prevent. New fog the interview surfaced is appended as a bullet naming what would resolve it. The section empties out to nothing → drop the heading with it.

A parked item is not a skipped question: a skip is a question the user declined to answer and belongs in `## Open Questions` with its owner hint. Fog is a question nobody can answer yet.

Then hand flowctl the draft file — the literal path typed verbatim:

```bash
$FLOWCTL spec set-plan <id> --file "${TMPDIR:-/tmp}/flow-interview-spec-<id>-<suffix>.md" --json
```

### For Flow Task ID (fn-N.M)

**First check if task has existing spec from planning:**
```bash
$FLOWCTL cat <id>
```

**If task has substantial planning content** (description with file refs, sizing, approach):
- **Do NOT overwrite** — planning detail would be lost
- Only ADD new acceptance criteria discovered in interview: read the existing acceptance (already fetched via `$FLOWCTL cat <id>` above), append the new criteria, and Write the merged list ONCE via the **Write tool** to a literal unique path (e.g. `${TMPDIR:-/tmp}/flow-interview-acc-<id>-<suffix>.md`) — per the single-emission write pattern above. **No source tags here:** task acceptance is plain `- [ ]` checklist items, not R-ID spec criteria; tagging is for the spec's `## Acceptance Criteria` bullets only. Then:
  ```bash
  $FLOWCTL task set-acceptance <id> --file "${TMPDIR:-/tmp}/flow-interview-acc-<id>-<suffix>.md" --json
  ```
- Or suggest interviewing the spec instead: `$flow-next-interview <spec-id>`

**If task is minimal** (just title, empty or stub description):
- Update task with interview findings
- Focus on **requirements**, not implementation details
- Write the description and acceptance each ONCE via the **Write tool** to literal unique paths (e.g. `${TMPDIR:-/tmp}/flow-interview-desc-<id>-<suffix>.md` / `${TMPDIR:-/tmp}/flow-interview-acc-<id>-<suffix>.md`) — per the single-emission write pattern above. Then:

```bash
$FLOWCTL task set-spec <id> --description "${TMPDIR:-/tmp}/flow-interview-desc-<id>-<suffix>.md" --acceptance "${TMPDIR:-/tmp}/flow-interview-acc-<id>-<suffix>.md" --json
```

Description should capture:
- What needs to be accomplished (not how)
- Edge cases discovered in interview
- Constraints and requirements

Do NOT add: file/line refs, sizing, implementation approach — that's plan's job.

### For File Path

Rewrite the file with refined spec:
- Preserve any existing structure/format
- Add sections for areas covered in interview
- Include edge cases, acceptance criteria
- Keep it requirements-focused (what, not how)
- **No source tags here:** this is the user's own document, not a `.flow` spec — preserving its structure outranks injecting our tag grammar. Tags start when `/flow-next:plan <file>` promotes it to a spec.

This is typically a pre-spec doc. After interview, suggest `$flow-next-plan <file>` to create spec + tasks.
