# fn-122-harden-verdict-graduate-recurring Harden verdict: graduate recurring memory entries into enforced gates

## Goal & Context
<!-- scope: business -->

An agent that re-fixes the same class of issue every run wastes tokens and misses cases. The durable move (Boris Cherny, Jul 2026) is graduating that knowledge into a lint rule, CI step, or CLAUDE.md rule so the whole class is automated forever. flow-next memory entries are the soft form of this knowledge: today they are re-injected as context each run (memory-scout at plan time, worker re-anchor at work time) and never hardened. The lesson keeps riding the context window instead of becoming a gate.

This spec adds a sixth audit outcome, **Harden**, to `/flow-next:audit` (current outcomes: Keep / Update / Consolidate / Replace / Delete). When an entry shows recurrence -- the same correction re-learned or re-reinforced across specs/runs -- the audit proposes graduating it into one of three gate types: (a) a lint rule, (b) a CI step/check, (c) a CLAUDE.md/AGENTS.md rule (a fourth, review-checklist item, is deferred -- see Architecture). On user acceptance, the graduation artifact is generated/staged and the memory entry is demoted to a pointer referencing the enforced gate, so provenance survives.

This lands squarely on the product's "bias towards verification" claim: don't have the agent re-fix -- encode the gate. Same gates whether interactive or autonomous.

**Honest baseline (verified against current code, Jul 2026):** there is NO read-side usage telemetry. `memory-scout` retrieval and worker re-anchor reads leave zero trace on the entry; nothing records "this entry fired during a run". The only recurrence signals that exist today are write-side:

1. `flowctl memory add --update <id>` appends a `## Update YYYY-MM-DD` body section, stamps `last_updated`, and unions tags (`_memory_update_entry`, flowctl.py ~L9820). Count of `## Update` headings = a crude reinforcement count.
2. Overlap scoring on every `memory add` emits `matches`; moderate overlap sets `related_to: [ids]` on the new entry -- a cluster of near-duplicate entries is the same lesson re-learned under different titles.
3. Git history of the entry file (commit count, authorship spread across spec branches).

Detecting "recurring" is therefore an inference over these artifacts plus LLM judgment, not a counter read. Whether to ALSO add a write-time reinforcement counter is a prerequisite decision this spec carries (see Decision Context); the feature must work from the existing artifacts alone so the whole historical store is eligible, not just future writes.

## Architecture & Data Models
<!-- scope: technical -->

Standard flow-next split (CLAUDE.md "SKILL + thin flowctl plumbing"): the skill owns all judgment, flowctl owns persistence.

**Skill side (`plugins/flow-next/skills/flow-next-audit/`):**

- `phases.md`: new `## Harden` outcome section in the 5-outcomes lookup (becomes 6), with decision criteria: (1) recurrence signal present (thresholds over `## Update` heading count, `related_to` cluster size, git-log commit count -- exact thresholds are a plan-time decision, but the criteria must name which artifacts they read), AND (2) the lesson is mechanizable -- expressible as a deterministic check a gate can run. A one-off lesson or a judgment-only lesson ("prefer X style when ambiguous") stays Keep. Decision tree at the bottom of phases.md gains the Harden branch.
- `workflow.md`: Phase 1 investigation gathers the recurrence artifacts per entry; Phase 2 classification may emit Harden; Phase 3 (Ask) presents Harden candidates individually (like Replace/Delete today) with the proposed gate type, a draft artifact, and evidence bullets; Phase 4 (Execute) generates/stages the artifact and demotes the entry; Phase 5 report gains a Hardened bucket.
- `SKILL.md`: description + outcome list updated (Keep / Update / Consolidate / Replace / Delete / Harden); Forbidden list gains "Harden never auto-applies in autofix".

**Gate targets (per repo, discovered at audit time, cheapest-fitting first):**

- (a) Lint rule: append/extend the repo's existing linter config (biome, ruff, eslint, etc. -- discovered from repo files, not assumed). If no linter exists, this target is unavailable; fall through.
- (b) CI step: a check in the repo's existing CI workflow (e.g. `.github/workflows/`). If no CI exists, unavailable; fall through.
- (c) CLAUDE.md / AGENTS.md rule: a one-to-two-line rule appended to the substantive project instruction file (the one not just `@`-including the other -- same discovery as audit Phase 6 discoverability check).
- (d) Review-checklist item: **DECIDED (2026-07-22): out of v1.** No canonical review-checklist artifact exists in flow-next (verified -- impl-review builds prompts from spec state; there is no per-repo checklist file it consumes), and inventing a consumed-by-nothing file is banned. In v1, review-shaped lessons degrade to (c) an instruction-file rule. A first-class checklist home wired to impl-review is a possible follow-up spec, not this one. Everywhere else in this spec, gate types are (a)/(b)/(c).

**Data model (flowctl):**

- `MEMORY_STATUS` extends from `("active", "stale")` to `("active", "stale", "hardened")`.
- New optional frontmatter field `hardened_into: <gate-ref>` (free-text: file path + one-line description of the gate). Permitted on both tracks.
- Demotion preserves the file: status flips to `hardened`, `hardened_into` + `last_audited` set, body untouched (provenance survives; the entry becomes a pointer). Never `git rm` on Harden.
- Default `memory list` / `memory search` exclude `hardened` (same treatment as `stale`); `--status hardened` / `--status all` include it. memory-scout therefore stops re-injecting the entry -- the gate has replaced the context injection.

**Recurrence detection inputs (audit Phase 1, per entry):**

```bash
grep -c '^## Update ' <entry-file>          # reinforcement writes
# frontmatter: related_to length, last_updated
git log --oneline -- <entry-file> | wc -l   # write history
```

Plus LLM judgment: entries in the same `related_to` cluster count toward one candidate (the cluster, not each member, is the Harden unit -- consolidate first if needed).

**Proposal thresholds (DECIDED 2026-07-22, documented in phases.md, overridable by judgment in either direction with evidence stated):** an entry (or cluster) becomes a Harden CANDIDATE when ANY of: (i) >= 2 `## Update` headings; (ii) `related_to` cluster of >= 3 entries; (iii) >= 4 commits touching the entry file. Thresholds gate PROPOSING only; the human gates APPLYING. Mechanizability is a separate AND condition and is always LLM-judged.

### Worked example (normative for shape, illustrative values)

Assume a Python repo with ruff configured. Entry `.flow/memory/conventions/timestamps-utc.md`, lesson "always stamp timestamps UTC ISO-8601; naive `datetime.now()` broke receipt comparisons", carrying two `## Update` sections (re-learned in fn-97 and fn-104) and 4 commits.

1. Phase 1 evidence: `grep -c '^## Update '` -> 2; `git log --oneline -- <file> | wc -l` -> 4; `related_to: []`. Candidate (threshold (i) met). Mechanizable: yes -- naive-datetime use is grep/lint-detectable.
2. Duplication guard: grep ruff config for `DTZ` -> absent. Proceed.
3. Ask step shows: gate type (a) lint rule; draft artifact = add `DTZ` to the ruff `select` list in `pyproject.toml`; evidence bullets from step 1; options accept / different gate type / decline.
4. On accept: edit `pyproject.toml`; then `flowctl memory mark-hardened conventions/timestamps-utc --gate-ref "pyproject.toml [tool.ruff] DTZ rules -- bans naive datetimes" --audited-by "/flow-next:audit"`.
5. Entry frontmatter after (body untouched):

```yaml
status: hardened            # was: active
hardened_into: "pyproject.toml [tool.ruff] DTZ rules -- bans naive datetimes"
last_audited: 2026-07-22T09:00:00Z
```

6. Report: `Hardened: 1` with detail line `conventions/timestamps-utc -> lint (pyproject.toml ruff DTZ)`. `memory list` no longer shows the entry; `memory list --status hardened` does; memory-scout stops injecting it.

## API Contracts
<!-- scope: technical -->

New thin plumbing, mirroring `mark-stale` / `mark-fresh`:

```bash
flowctl memory mark-hardened <id> --gate-ref "<path or description>" [--json]
flowctl memory mark-hardened <id> --gate-ref "..." --audited-by "/flow-next:audit"
```

- Sets `status: hardened`, `hardened_into: <gate-ref>`, stamps `last_audited` (UTC), records optional `audit_notes`. Body never modified. Idempotent -- re-marking replaces `hardened_into` and re-stamps.
- Errors: unknown id (exit nonzero, message names the id); missing `--gate-ref` (usage error). Legacy flat-file ids rejected with the migrate-first message (same as mark-stale).
- `flowctl memory mark-fresh <id>` also clears `hardened` back to `active` and drops `hardened_into` (un-graduation escape hatch, e.g. gate later removed).
- `memory list` / `search` / `read` JSON output includes `hardened_into` when present.
- No other flowctl surface changes. Artifact generation (lint rule text, CI step YAML, instruction-file line) is skill-side prose written via Edit/Write -- no `flowctl gate` subcommand (would violate the agentic-vs-deterministic rule: judging what the gate should say is intelligence).

## Edge Cases & Constraints
<!-- scope: technical -->

- **Autofix never applies Harden.** `mode:autofix` (and therefore any pilot/Ralph invocation) reports Harden candidates under Recommended only -- no artifact writes, no demotion. Rationale: graduation edits files outside `.flow/memory/` (lint config, CI, CLAUDE.md); silent edits there from an autonomous sweep are unacceptable. Audit proposes; a human accepts.
- **Duplication guard.** Before proposing, grep the candidate gate surfaces (linter config, CI workflows, CLAUDE.md/AGENTS.md) for an existing rule covering the class. Already enforced -> propose demote-to-pointer only (entry retires, no new artifact), citing the existing gate as `--gate-ref`.
- **Decision-track entries** (`knowledge/decisions/`): supersede-not-delete semantics are untouched. Harden on a decision entry demotes via `mark-hardened` (file stays on disk, consistent with "decision history stays on disk"); most decisions are judgment records, not mechanizable checks -- expect Harden to be rare here, and the calibrated judging question stays primary.
- **Repos without linter or CI** (or non-code repos like an Obsidian vault): targets (a)/(b) unavailable; (c) instruction-file rule is the universal floor. The skill must not scaffold a linter or CI pipeline to satisfy a Harden -- gate lands in what exists.
- **Legacy flat files**: skipped, as today (migrate first).
- **Artifact staging, not blind writes**: generated lint/CI edits are shown as a draft in the Ask step (interactive) before Edit/Write executes; instruction-file edits stay minimal (1-2 lines) and never restructure the file. Existing "auto-committing without user awareness" rule covers the commit.
- **Cross-platform** (CLAUDE.md checklist): canonical prose uses `AskUserQuestion`/`Task`; run `./scripts/sync-codex.sh` twice and commit the mirror diff. Cursor/Droid get no rewrite pass -- new prose needs no Claude-only phrases beyond what the audit skill already carries.
- **Version discipline**: land code + docs + `## Unreleased` CHANGELOG entry; no version bump (batched releases).
- **Retroactivity constraint**: recurrence detection must work from existing artifacts (Update headings, related_to, git log) so pre-existing entries are eligible. Any new counter (if adopted, see Decision Context) only helps future entries.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `phases.md` documents Harden as a sixth outcome with explicit decision criteria: recurrence signal (named artifacts: `## Update` heading count, `related_to` cluster size, git-log write count) AND mechanizability; the quick-reference decision tree includes the Harden branch.
- **R2:** Audit Phase 1 gathers the recurrence artifacts per entry; the spec of thresholds states plainly that no read-side usage telemetry exists and detection is write-side + LLM judgment.
- **R3:** Interactive mode presents each Harden candidate individually with: proposed gate type ((a)/(b)/(c)), draft artifact content, evidence bullets, and accept / pick-different-gate-type / decline options via the blocking-question tool.
- **R4:** On acceptance, the graduation artifact is written to the chosen surface and the entry is demoted via `flowctl memory mark-hardened <id> --gate-ref "..."`; the entry file remains on disk with body intact and `hardened_into` pointing at the gate.
- **R5:** In `mode:autofix`, Harden candidates appear ONLY under Recommended in the report; no gate artifact is written and no entry is demoted.
- **R6:** `flowctl memory mark-hardened` exists with the contract in API Contracts (status flip, `hardened_into`, `last_audited`, idempotent, `--json`); `mark-fresh` reverts a hardened entry to active and drops `hardened_into`; unit tests cover round-trip, idempotency, unknown id, legacy rejection.
- **R7:** Default `memory list` / `memory search` exclude `hardened`; `--status hardened` and `--status all` include; memory-scout consequently no longer surfaces hardened entries (verified via the existing status-filter path, no scout change needed).
- **R8:** Duplication guard: when the class is already enforced by an existing gate, the audit proposes pointer-demotion citing that gate instead of generating a duplicate artifact.
- **R9:** Audit report gains a `Hardened: N` count plus per-entry detail (gate type, artifact path, gate-ref); autofix report shows Harden under Recommended.
- **R10:** Decision-track entries are never `git rm`'d by Harden; supersession fields are preserved alongside `hardened` status.
- **R11:** Docs updated in the same workstream: `docs/memory-schema.md` (audit lifecycle + status values + `hardened_into`), `docs/flowctl.md` (mark-hardened), audit `SKILL.md`/`workflow.md`/`phases.md`; `scripts/sync-codex.sh` run twice with mirror diff committed; CHANGELOG entry under `## Unreleased`.

## Boundaries
<!-- scope: business -->

Out of scope:

- **Read-side usage telemetry.** No instrumentation of memory-scout or worker re-anchor reads, no hit counters, no analytics. If ever wanted, that is its own spec.
- **Auto-apply anywhere.** No autofix application, no pilot-stage auto-acceptance, no Ralph pathway that writes gates unattended. Harden is propose-and-confirm by design.
- **A gate-synthesis engine.** No deterministic generator for lint rules across arbitrary languages/linters; the draft artifact is host-agent-authored prose/config for THIS repo, user-reviewed. No `flowctl gate` subcommand.
- **Scaffolding missing infrastructure.** Never creates a linter setup or CI pipeline to have somewhere to put a gate.
- **Retro-hardening sweep of this repo's own store** as part of the feature work (running the new verdict over flow-next's ~40 entries is a follow-up, not acceptance).
- **Docs-site (flow-next.dev) changes** are the maintainer's downstream pass, tracked outside this spec.
- **Task breakdown** -- this spec is scope definition only; `/flow-next:plan` runs separately.

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
<!-- scope: business -->

Boris Cherny's Jul 2026 framing: re-fixing the same issue class every run is the anti-pattern; the durable move is encoding the class into an automated gate. flow-next already claims "bias towards verification" -- receipts, evidence JSON, no self-grading. Memory entries that keep getting re-learned are exactly the knowledge that should stop being context and start being a gate. Harden closes that loop inside the existing audit ritual instead of inventing a new ceremony, and keeps the "same gates interactive or autonomous" story true: the gate fires in CI/lint regardless of who or what wrote the code.

### Implementation Tradeoffs
<!-- scope: technical -->

**Decisions (made 2026-07-22, maintainer; planning executes, does not reopen without new evidence):**

1. **Recurrence signal source: (ii) derive at audit time from existing artifacts** (`## Update` headings + `related_to` clusters + git log). Retroactive over the whole store, zero schema change. (i) a write-time `reinforced_count` was considered (precise going forward, blind to history, extra schema) -- NOT in v1; revisit only if the derived signals prove too noisy in practice. (iii) pure LLM judgment alone is rejected: unfalsifiable evidence bullets.
2. **Gate type (d) review-checklist: dropped from v1, degrades to (c).** No canonical checklist artifact exists and a consumed-by-nothing file is banned; a checklist home wired to impl-review is follow-up-spec material.
3. **Threshold values: fixed defaults** -- >=2 `## Update` headings OR >=3-entry `related_to` cluster OR >=4 write commits (see Architecture). Sanity-check against this repo's real store during planning; if the store shows the defaults are badly calibrated, adjust the numbers in phases.md and note it in the plan, keeping the same structure (any-of, propose-only, judgment-overridable).
4. **Status vs separate field.** Chose extending `MEMORY_STATUS` with `hardened` over a boolean `hardened: true` on stale entries: hardened is not stale (the lesson is MORE alive, just relocated), and the existing status-filter plumbing gives list/search/scout exclusion for free.

**Rejected alternatives:** a standalone `/flow-next:harden` skill (audit already walks every entry with evidence in hand; a second sweep duplicates Phase 0-2); deleting graduated entries (loses provenance -- the pointer answers "why does this lint rule exist" forever); auto-applying under pilot with a strike system (gate surfaces are shared repo infrastructure; wrong lint rules block every future run -- the failure mode is much worse than a wrong stale-mark).
