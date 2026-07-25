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
- New optional frontmatter field `hardened_into: <gate-ref>`. **Not free text** -- a later audit has to re-find the gate to check it is still live (R13), and a prose description gives it nothing to look at. The value is a single conventionally formatted string with two required parts: a repo-relative artifact path, then a stable rule/check identifier, then an optional human note. Format: `<path>#<rule-id> -- <note>`. Per gate type:
  - lint: `pyproject.toml#tool.ruff.select:DTZ -- bans naive datetimes`
  - CI: `.github/workflows/ci.yml#jobs.lint.steps[name=ruff] -- runs the DTZ gate`
  - instruction file: `CLAUDE.md#timestamps-utc -- always stamp UTC ISO-8601`
  The `<rule-id>` must be something a grep can find in the named file. Permitted on both tracks.
- Demotion preserves the file: status flips to `hardened`, `hardened_into` + `last_audited` set, body untouched (provenance survives; the entry becomes a pointer). Never `git rm` on Harden.
- **Field invariants per status.** The invariant this spec enforces is **negative**: after any status flip, no field belonging to the PREVIOUS status survives. It is not a claim that each status populates a field.

  | status | `hardened_into` | `stale_reason` / `stale_date` |
  |---|---|---|
  | `active` | must be absent | must be absent |
  | `stale` | must be absent | optional -- schema-permitted, written by nothing |
  | `hardened` | must be present | must be absent |

  So `mark-hardened` sets `hardened_into` and clears the stale pair; `mark-stale` clears `hardened_into`; `mark-fresh` clears both families. The `mark-stale` clearing is a change to that EXISTING handler, not only new code.

  **Correction (plan-time error, caught at completion review 2026-07-25):** an earlier draft of this table read `stale` -> `stale_reason`/`stale_date` **present**, which asserted an invariant the codebase has never satisfied. `cmd_memory_mark_stale` has never written either field -- verified by `git log -S'fm["stale_reason"]'` returning no commit -- because the reason is recorded in `audit_notes`. The two fields are permitted by `MEMORY_OPTIONAL_FIELDS` and populated by nothing. Making `mark-stale` start writing them would be an unrelated behavior change to a pre-existing command, duplicating into `stale_reason` what already lives in `audit_notes`, and is out of this spec's scope. The requirement that actually protects against contradictory frontmatter -- `hardened_into` never surviving into `stale` -- is unchanged, implemented, and tested. This is a correction of a false assertion, not a relaxation of the gate.
- `last_audited` precision is a **UTC date** (`YYYY-MM-DD`), matching the existing `mark-stale` / `mark-fresh` handlers (`flowctl.py:11893`, `:11947`) and `_MEMORY_QUOTED_STRING_FIELDS` (`:9516`). Harden introduces no new timestamp precision. "Re-stamping" is therefore a no-op within the same UTC day, and idempotency must be asserted on `hardened_into` replacement, not on an observable timestamp change.
- Default `memory list` / `memory search` exclude `hardened` (same treatment as `stale`); `--status hardened` / `--status all` include it. memory-scout therefore stops re-injecting the entry -- the gate has replaced the context injection.

**Recurrence detection inputs (audit Phase 1, per entry):**

```bash
grep -c '^## Update ' <entry-file>          # reinforcement writes
# frontmatter: related_to length, last_updated
# substantive write history: git log --format='COMMIT %H' --patch --unified=0 -- <entry-file>
# piped through awk, counting only commits whose diff on the entry touches something other
# than the audit's own bookkeeping fields (last_audited, audit_notes, status, stale_reason,
# stale_date, hardened_into) -- exact command in workflow.md 0.75.1
```

Plus LLM judgment: entries in the same `related_to` cluster count toward one candidate (the cluster, not each member, is the Harden unit -- consolidate first if needed).

**Proposal thresholds (recalibrated at plan time 2026-07-24 per Decision 3's standing instruction; documented in phases.md, overridable by judgment in either direction with evidence stated).** An entry (or cluster) becomes a Harden CANDIDATE when ANY of the two primary signals fires:

- (i) >= 2 `## Update` headings on the entry;
- (iii) >= 4 **substantive** commits touching the entry file -- commits that changed only the audit's bookkeeping frontmatter (`last_audited`, `audit_notes`, `status`, `stale_reason`, `stale_date`, `hardened_into`) are excluded. Every `mark-fresh` / `mark-stale` / `mark-hardened` rewrites those fields, so counting them would make the signal grow with audit diligence rather than recurring pain: in a repo that commits its audits, the creation commit plus three routine sweeps would clear the threshold, permanently bypassing the 0.75 auto-Keep pre-filter and eroding the intended O(changed) behavior (review finding, PR #239).

`related_to` cluster size is **demoted from a standalone trigger to a corroborating signal**: a cluster of >= 3 entries raises a candidate ONLY when it co-occurs with at least one `## Update` heading somewhere in the cluster (or with signal (iii) on any member). On its own it proposes nothing.

Thresholds gate PROPOSING only; the human gates APPLYING. Mechanizability is a separate AND condition and is always LLM-judged.

**Calibration evidence (this repo's store, 71 entries, measured 2026-07-24):**

| Signal | Entries matching | Share |
|---|---|---|
| (i) >= 2 `## Update` headings | 3 | 4% |
| (iii) >= 4 substantive commits on the entry file | ~1 in 20 sampled | ~5% |
| `related_to` >= 3 (as a standalone trigger) | 20 | **28%** |

`related_to` is auto-populated by overlap scoring on every `memory add`, so a large cluster reflects tag/topic collision, not a re-taught lesson. Left standalone it would flag more than a quarter of the store on the first post-ship audit run — noise that would train the user to decline Harden reflexively. Signals (i) and (iii) are selective and match the "recurring pain" intuition, so they stay as-is. The structure Decision 3 fixed (any-of, propose-only, judgment-overridable) is preserved; only `related_to`'s standing changed.

### Worked example (normative for shape, illustrative values)

Assume a Python repo with ruff configured. Entry `.flow/memory/conventions/timestamps-utc.md`, lesson "always stamp timestamps UTC ISO-8601; naive `datetime.now()` broke receipt comparisons", carrying two `## Update` sections (re-learned in fn-97 and fn-104) and 4 commits.

1. Phase 1 evidence: `grep -c '^## Update '` -> 2; substantive commit count -> 4 (audit-stamp commits excluded); `related_to: []`. Candidate (threshold (i) met). Mechanizable: yes -- naive-datetime use is grep/lint-detectable.
2. Duplication guard: grep ruff config for `DTZ` -> absent. Proceed.
3. Ask step shows: gate type (a) lint rule; draft artifact = add `DTZ` to the ruff `select` list in `pyproject.toml`; evidence bullets from step 1; options accept / different gate type / decline.
4. On accept: edit `pyproject.toml`. **Then verify the gate actually fires before retiring the lesson** -- run `ruff check` and confirm the `DTZ` rule is active in the resolved config (not merely present as text in a file that ruff does not read, and not disabled by a later `ignore` entry). Verification failing means the entry stays `active` and the graduation is reported as failed; nothing is demoted.
5. Only after verification passes: `flowctl memory mark-hardened conventions/timestamps-utc --gate-ref "pyproject.toml#tool.ruff.select:DTZ -- bans naive datetimes" --audited-by "/flow-next:audit"`.
6. Entry frontmatter after (body untouched):

```yaml
status: hardened            # was: active
hardened_into: "pyproject.toml#tool.ruff.select:DTZ -- bans naive datetimes"
last_audited: '2026-07-22'
```

7. Report: `Hardened: 1` with detail line `conventions/timestamps-utc -> lint (pyproject.toml ruff DTZ)`. `memory list` no longer shows the entry; `memory list --status hardened` does; memory-scout stops injecting it.

## API Contracts
<!-- scope: technical -->

New thin plumbing, mirroring `mark-stale` / `mark-fresh`:

```bash
flowctl memory mark-hardened <id> --gate-ref "<path>#<rule-id> -- <note>" [--json]
flowctl memory mark-hardened <id> --gate-ref "..." --audited-by "/flow-next:audit"
```

- Sets `status: hardened`, `hardened_into: <gate-ref>`, **clears `stale_reason` / `stale_date`** (field invariants, see Architecture), stamps `last_audited` (UTC date, `YYYY-MM-DD`), records optional `audit_notes`. Body never modified. Idempotent -- re-marking replaces `hardened_into`; `last_audited` is a date, so a same-day re-mark is observably a no-op on that field and tests must assert on `hardened_into`, not on the stamp.
- `--gate-ref` is stored verbatim; flowctl does NOT parse or validate the `<path>#<rule-id>` convention. The format is a skill-side contract (the audit skill composes it; a later audit greps it) -- validating it in flowctl would be judgment leaking into plumbing. Only non-emptiness is enforced.
- Errors: unknown id (exit nonzero, message names the id); missing/empty `--gate-ref` (usage error). Legacy flat-file ids rejected with the migrate-first message (same as mark-stale).
- `flowctl memory mark-fresh <id>` clears BOTH families: `hardened` -> `active` dropping `hardened_into`, and the existing stale-field clearing (un-graduation escape hatch, e.g. gate later removed).
- `flowctl memory mark-stale <id>` (existing command, changed here) additionally drops `hardened_into`, so a hardened entry marked stale cannot keep a pointer to a gate it no longer claims.
- `memory list` / `search` / `read` JSON output includes `hardened_into` when present.
- No other flowctl surface changes. Artifact generation (lint rule text, CI step YAML, instruction-file line) is skill-side prose written via Edit/Write -- no `flowctl gate` subcommand (would violate the agentic-vs-deterministic rule: judging what the gate should say is intelligence).

## Edge Cases & Constraints
<!-- scope: technical -->

- **Autofix never applies Harden.** `mode:autofix` (and therefore any pilot/Ralph invocation) reports Harden candidates under Recommended only -- no artifact writes, no demotion. Rationale: graduation edits files outside `.flow/memory/` (lint config, CI, CLAUDE.md); silent edits there from an autonomous sweep are unacceptable. Audit proposes; a human accepts.
- **Duplication guard.** Before proposing, grep the candidate gate surfaces (linter config, CI workflows, CLAUDE.md/AGENTS.md) for an existing rule covering the class. Already enforced -> propose demote-to-pointer only (entry retires, no new artifact), citing the existing gate as `--gate-ref`.
- **Decision-track entries** (`knowledge/decisions/`): supersede-not-delete semantics are untouched. Harden on a decision entry demotes via `mark-hardened` (file stays on disk, consistent with "decision history stays on disk"); most decisions are judgment records, not mechanizable checks -- expect Harden to be rare here, and the calibrated judging question stays primary.
- **Repos without linter or CI** (or non-code repos like an Obsidian vault): targets (a)/(b) unavailable; (c) instruction-file rule is the universal floor. The skill must not scaffold a linter or CI pipeline to satisfy a Harden -- gate lands in what exists.
- **Legacy flat files**: skipped, as today (migrate first).
- **First post-ship audit run gets no special treatment.** Recurrence signals are derived retroactively, so the first ordinary audit after this lands may surface several Harden candidates at once. That is intended, not a bug, and there is no first-run suppression or rate limit — the recalibrated thresholds (Architecture) are what keeps the volume sane. This is distinct from the deliberately out-of-scope *retro-hardening sweep* (Boundaries): candidates surface through the normal audit ritual, not a one-off campaign.
- **Artifact staging, not blind writes**: generated lint/CI edits are shown as a draft in the Ask step (interactive) before Edit/Write executes; instruction-file edits stay minimal (1-2 lines) and never restructure the file. Existing "auto-committing without user awareness" rule covers the commit.
- **Cross-platform** (CLAUDE.md checklist): canonical prose uses `AskUserQuestion`/`Task`; run `./scripts/sync-codex.sh` twice and commit the mirror diff. Cursor/Droid get no rewrite pass -- new prose needs no Claude-only phrases beyond what the audit skill already carries.
- **Version discipline**: land code + docs + `## Unreleased` CHANGELOG entry; no version bump (batched releases).
- **Retroactivity constraint**: recurrence detection must work from existing artifacts (Update headings, related_to, git log) so pre-existing entries are eligible. Any new counter (if adopted, see Decision Context) only helps future entries.

## Quick commands

Focused suites for this feature's files. The FULL suite (`python3 scripts/run_tests_parallel.py`) runs ONCE at the final gate, not per task.

```bash
# Memory command + CLI-surface + bootstrap-pin suites (the blast radius of a flowctl.py edit)
cd plugins/flow-next/tests && python3 -m unittest \
  test_memory_mark_stale test_memory_mark_fresh test_memory_mark_hardened \
  test_flowctl_surface test_startup_bootstrap -q

# Smoke the new command end-to-end against the dogfood store
.flow/bin/flowctl memory list --json | jq '.entries | length'
.flow/bin/flowctl memory list --status hardened --json
.flow/bin/flowctl memory list --status all --json | jq '.entries | length'

# Codex mirror must be idempotent and its validation guards green
./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --porcelain plugins/flow-next/codex/
```

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `phases.md` documents Harden as a sixth outcome with explicit decision criteria: recurrence signal (named artifacts: `## Update` heading count, `related_to` cluster size, git-log write count) AND mechanizability; the quick-reference decision tree includes the Harden branch.
- **R2:** Audit Phase 1 gathers the recurrence artifacts per entry; the spec of thresholds states plainly that no read-side usage telemetry exists and detection is write-side + LLM judgment. **Recurrence signals are gathered BEFORE the Phase 0.75 auto-Keep decision, and a recurrence-qualified entry (or cluster) bypasses auto-Keep and enters Harden investigation even when its module is unchanged.** Today Phase 0.75 auto-Keeps unchanged-module entries and excludes them from Phase 1 entirely -- leaving that order intact would make the most-hardenable entries (old, stable, repeatedly re-taught, module long since settled) exactly the ones never considered, defeating retroactivity.
- **R3:** Interactive mode presents each Harden candidate individually with: proposed gate type ((a)/(b)/(c)), draft artifact content, evidence bullets, and accept / pick-different-gate-type / decline options via the blocking-question tool.
- **R4:** On acceptance, the graduation artifact is written to the chosen surface, **the gate is verified live (R16)**, and only then is the entry demoted via `flowctl memory mark-hardened <id> --gate-ref "..."`; the entry file remains on disk with body intact and `hardened_into` pointing at the gate in the `<path>#<rule-id>` form.
- **R5:** In `mode:autofix`, Harden candidates appear ONLY under Recommended in the report; no gate artifact is written and no entry is demoted.
- **R6:** `flowctl memory mark-hardened` exists with the contract in API Contracts (status flip, `hardened_into`, `last_audited`, idempotent, `--json`); `mark-fresh` reverts a hardened entry to active and drops `hardened_into`; unit tests cover round-trip, idempotency, unknown id, legacy rejection.
- **R7:** Default `memory list` / `memory search` exclude `hardened`; `--status hardened` and `--status all` include; memory-scout consequently no longer surfaces hardened entries (verified via the existing status-filter path, no scout change needed).
- **R8:** Duplication guard: when the class is already enforced by an existing gate, the audit proposes pointer-demotion citing that gate instead of generating a duplicate artifact. A textual match is not sufficient evidence -- the guard must confirm the matched rule is ACTIVE (not commented out, not in an `ignore` list, not in a config the tool does not actually read, not a disabled CI step) before treating it as enforcement. An inactive match is not a duplicate; it is a broken gate, and the entry stays active.
- **R9:** Audit report gains a `Hardened: N` count plus per-entry detail (gate type, artifact path, gate-ref); autofix report shows Harden under Recommended.
- **R10:** Decision-track entries are never `git rm`'d by Harden; supersession fields are preserved alongside `hardened` status.
- **R11:** Docs updated in the same workstream: `docs/memory-schema.md` (audit lifecycle + status values + `hardened_into`), `docs/flowctl.md` (mark-hardened), audit `SKILL.md`/`workflow.md`/`phases.md`; `scripts/sync-codex.sh` run twice with mirror diff committed; CHANGELOG entry under `## Unreleased`. The full doc sweep list is in References.
- **R12:** `phases.md` states an explicit outcome-precedence rule for an entry qualifying for several outcomes at once, and the decision tree encodes it: **correctness first** (Replace / Delete win — a wrong lesson is never graduated into a gate), **then Consolidate** (a `related_to` cluster is consolidated before the merged entry is considered for Harden, per the "the cluster, not each member, is the Harden unit" rule), **then Harden**. Keep/Update are unaffected.
- **R13:** Hardened entries have defined behavior on subsequent audit runs: Phase 0.75/Phase 1 do NOT drop them silently. Each hardened entry gets a lightweight gate-liveness check — does the surface named by `hardened_into` still exist and still carry the rule? Gate gone → the audit proposes `flowctl memory mark-fresh <id>` (un-graduation, entry returns to `active`) with the evidence; gate present → the entry is reported as still-hardened and NOT re-investigated in full. A gate upgrade (e.g. instruction-file rule promoted to a lint rule) is a re-`mark-hardened`, which is idempotent and replaces `hardened_into`.
- **R14:** The status-transition matrix is complete and every mutation enforces the per-status field invariants from Architecture -- not just its own field. The invariant is **negative**: no field belonging to the previous status survives the flip. `active -> hardened` and `stale -> hardened` both succeed and clear `stale_reason` / `stale_date`; `hardened -> stale` clears `hardened_into`; `hardened -> active` via `mark-fresh` clears `hardened_into` and the stale family. No transition is required to POPULATE `stale_reason` / `stale_date` -- `mark-stale` has never written them (the reason lives in `audit_notes`), and this spec does not change that. This modifies the EXISTING `mark-stale` and `mark-fresh` handlers, not only the new command. Unit tests cover every transition in the matrix and assert that no field from the prior status survives.
- **R15:** Cross-version behavior is documented **honestly**, matching what the code actually does. `validate_memory_frontmatter` runs only inside `write_memory_entry` (`flowctl.py:9607`), so an older flowctl does NOT fail loudly on read: it silently reads a `hardened` entry, and because its default filter excludes only `stale`, it will *surface* the entry in default `memory list` / `search` / memory-scout results. The loud failure happens on the next WRITE: any older-flowctl rewrite of that entry fails validation on the unknown status value and the unknown `hardened_into` field, so there is no silent corruption. `docs/memory-schema.md` states exactly this -- read-through, write-refusal -- alongside the existing lockstep dual-copy invariant (`plugins/flow-next/scripts/flowctl.py` and `.flow/bin/flowctl.py` must be updated together), and does not claim a read-side guarantee the enum extension cannot provide. No compatibility shim is added; lockstep upgrade is the mitigation.
- **R16:** A gate is verified live before the lesson is retired. On acceptance the audit runs a gate-type-appropriate check -- lint: run the linter and confirm the new rule is active in the RESOLVED config (not merely present as text, not overridden by a later ignore); CI: confirm the step parses and sits in a workflow/job that actually runs, not a disabled or unreferenced one; instruction file: confirm the rule landed in the substantive file the agents actually read, not an `@`-including stub. Verification failure means the entry stays `active`, `mark-hardened` is NOT called, and the report shows the graduation as failed with the reason. A gate that does not fire is worse than no gate: it retires the only working copy of the lesson while enforcing nothing.

## Early proof point

Task `fn-122-harden-verdict-graduate-recurring.1` (flowctl plumbing) validates the core architectural bet: Decision 4's claim that extending `MEMORY_STATUS` with `hardened` gives list/search/memory-scout exclusion **for free** through the existing status-filter path, with no scout change (R7). It also pays the known flowctl.py tax up front — dual copies, `SOURCE_SHA256`/`HELP_SHA256` re-pin, regenerated `flowctl-help.txt`, CLI-surface snapshot.

If it fails — if exclusion needs scout-side changes, or the status enum turns out to be load-bearing somewhere that makes `hardened` unsafe — stop and re-evaluate Decision 4 (status value vs a separate `hardened_into`-only field on an otherwise-active entry) **before** writing any audit-skill prose in `.2`, since every skill sentence names the shipped CLI surface.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | phases.md documents Harden as sixth outcome + decision tree branch | fn-122-harden-verdict-graduate-recurring.2 | — |
| R2  | Phase 1 gathers recurrence artifacts; honest "no read-side telemetry" statement | fn-122-harden-verdict-graduate-recurring.2 | — |
| R3  | Interactive per-candidate Ask with gate type, draft artifact, evidence, 3 options | fn-122-harden-verdict-graduate-recurring.2 | — |
| R4  | On accept: artifact written + entry demoted via mark-hardened, body intact | fn-122-harden-verdict-graduate-recurring.2 | — |
| R5  | autofix reports Harden under Recommended only; never writes or demotes | fn-122-harden-verdict-graduate-recurring.2 | — |
| R6  | `flowctl memory mark-hardened` contract + mark-fresh revert + unit tests | fn-122-harden-verdict-graduate-recurring.1 | — |
| R7  | Default list/search exclude hardened; `--status hardened`/`all` include | fn-122-harden-verdict-graduate-recurring.1 | — |
| R8  | Duplication guard proposes pointer-demotion citing the existing gate | fn-122-harden-verdict-graduate-recurring.2 | — |
| R9  | Report gains `Hardened: N` + per-entry detail; autofix Recommended bucket | fn-122-harden-verdict-graduate-recurring.2 | — |
| R10 | Decision-track entries never `git rm`'d; supersession fields preserved | fn-122-harden-verdict-graduate-recurring.2 | — |
| R11 | Docs sweep + sync-codex twice + CHANGELOG Unreleased | fn-122-harden-verdict-graduate-recurring.3 | — |
| R12 | Outcome-precedence rule (correctness > Consolidate > Harden) in the tree | fn-122-harden-verdict-graduate-recurring.2 | — |
| R13 | Hardened entries on later runs: gate-liveness check, un-harden proposal | fn-122-harden-verdict-graduate-recurring.2 | — |
| R14 | Complete transition matrix + per-status field invariants across all three mutations | fn-122-harden-verdict-graduate-recurring.1 | — |
| R15 | Honest cross-version contract: silent read-through, write refusal; documented | fn-122-harden-verdict-graduate-recurring.3 | documentation-only; `.1` adds no read-side mechanism because none is possible via the enum |
| R16 | Gate verified live before demotion; failure keeps the entry active | fn-122-harden-verdict-graduate-recurring.2 | — |

## Boundaries
<!-- scope: business -->

Out of scope:

- **Read-side usage telemetry.** No instrumentation of memory-scout or worker re-anchor reads, no hit counters, no analytics. If ever wanted, that is its own spec.
- **Auto-apply anywhere.** No autofix application, no pilot-stage auto-acceptance, no Ralph pathway that writes gates unattended. Harden is propose-and-confirm by design.
- **A gate-synthesis engine.** No deterministic generator for lint rules across arbitrary languages/linters; the draft artifact is host-agent-authored prose/config for THIS repo, user-reviewed. No `flowctl gate` subcommand.
- **Scaffolding missing infrastructure.** Never creates a linter setup or CI pipeline to have somewhere to put a gate.
- **Retro-hardening sweep of this repo's own store** as part of the feature work (running the new verdict over flow-next's ~40 entries is a follow-up, not acceptance).
- **Docs-site (flow-next.dev) changes** are the maintainer's downstream pass, tracked outside this spec.
- **A first-class review-checklist artifact** wired to `/flow-next:impl-review` (gate type (d)) -- follow-up spec material, see Architecture.

## Strategy Alignment

Active tracks served by this plan:

- **Self-improving through normal work** — the track states "Audit is the garbage collector, not the growth mechanism." Harden adds the missing *graduation* path: a lesson that keeps being re-learned stops riding the context window and becomes a gate. It lands inside the existing audit ritual, so it needs no new ceremony and no extra command to remember, which is the track's stated bar for improvement that actually happens.
- **Ralph autonomous mode** — reinforces "same gates interactive or autonomous" and the surface-don't-force reflex. A graduated gate fires in lint/CI regardless of which harness wrote the code, while Harden itself stays propose-and-confirm (R5: autofix reports, never applies), consistent with the track's rule that shared repo infrastructure is not mutated unattended.

Design-principle check — **"flowctl grows only under burden of proof"**: `memory mark-hardened` is pure persistence (status flip + one field + timestamp), a direct sibling of the existing `mark-stale`/`mark-fresh`, and carries zero judgment. All judgment (is this recurring? is it mechanizable? which gate surface? what should the rule say?) stays in the skill. The spec explicitly refuses a `flowctl gate` subcommand for exactly this reason. No drift.

## References

Anchors gathered at plan time (verified against the tree at plan time — re-verify line numbers before editing):

**flowctl (task .1)**
- `plugins/flow-next/scripts/flowctl.py:9252` — `MEMORY_STATUS: tuple[str, ...] = ("active", "stale")`
- `plugins/flow-next/scripts/flowctl.py:9210-9222` — `MEMORY_OPTIONAL_FIELDS` frozenset
- `plugins/flow-next/scripts/flowctl.py:9259-9280` — `MEMORY_FIELD_ORDER` (deterministic write order)
- `plugins/flow-next/scripts/flowctl.py:9601` — `write_memory_entry` (atomic writer; calls the frontmatter validator)
- `plugins/flow-next/scripts/flowctl.py:11826-11859` — `_memory_resolve_categorized_entry` (id resolution + legacy rejection; reuse, do not reimplement)
- `plugins/flow-next/scripts/flowctl.py:11862-11924` — `cmd_memory_mark_stale` (the clone template)
- `plugins/flow-next/scripts/flowctl.py:11926+` — `cmd_memory_mark_fresh` (gains the hardened revert)
- `plugins/flow-next/scripts/flowctl.py:11445` / `:11479-11485` — `cmd_memory_list` + its status filter
- `plugins/flow-next/scripts/flowctl.py:11638` / `:11700-11705` — `cmd_memory_search` + its status filter (must change in lockstep with list)
- `plugins/flow-next/scripts/flowctl.py:30171-30410` — argparse wiring; two `--status choices=["active","stale","all"]` sites; `:30338-30383` is the mark-stale subparser template
- `plugins/flow-next/scripts/flowctl_bootstrap.py:19-21` — `SOURCE_SHA256` / `HELP_SHA256` pins
- `plugins/flow-next/tests/test_startup_bootstrap.py:305-320` — the pin assertions + `test_dogfood_bootstrap_is_byte_identical`
- `plugins/flow-next/tests/test_flowctl_surface.py:98-106` — literal CLI surface snapshot listing every `memory <subcmd>`
- `plugins/flow-next/tests/test_memory_mark_stale.py`, `test_memory_mark_fresh.py` — the test shape to mirror

**Audit skill (task .2)**
- `plugins/flow-next/skills/flow-next-audit/phases.md:5-11` — outcome table; `:15` — the "5 outcomes" sentence; `:232-276` — decision-entry calibration; `:336-360` — decision tree
- `plugins/flow-next/skills/flow-next-audit/workflow.md:283-303` — Phase 0.75 change-detection pre-filter; `:307` — Phase 1 Investigate; `:445-455` — Phase 2 Classify outcome list; `:478` — Phase 3 Ask; `:534-607` — Phase 4 Execute per-outcome subsections; `:615` — Phase 5 Report + Commit
- `plugins/flow-next/skills/flow-next-audit/SKILL.md:1-12` — frontmatter description + outcome list; autofix-mode rules around `:60`

**Docs sweep (task .3)**
- `plugins/flow-next/docs/memory-schema.md` — status values, optional frontmatter fields, audit-lifecycle prose (~`:110-150`)
- `plugins/flow-next/docs/flowctl.md:860` (status enum), `:893-894` (`--status` choices on list/search), `:900` (default-excludes prose), `:913-918` (`mark-fresh`) — plus a new `#### memory mark-hardened` subsection
- `plugins/flow-next/docs/self-improving.md:11`, `:18` — five-outcome enumerations
- `README.md:368` — `/flow-next:audit` feature-table row enumerating the outcomes
- `plugins/flow-next/agents/memory-scout.md:45` — documents the `--status` filter behavior
- `CHANGELOG.md` — `## [Unreleased]` (stage the entry; no version bump, per CLAUDE.md batched-release rule)
- `scripts/sync-codex.sh:1510,1577,1627` — audit-skill references in the mirror generation

**Relevant memory entries** (read before starting the matching task):
- `flowctl-edit-sha-pin-checklist` — any flowctl.py edit needs dual copies + `SOURCE_SHA256`/`HELP_SHA256` re-pin + regenerated help snapshot + sync-codex
- `skill-prose-must-match-real-flowctl-2026-06-10` — skill prose must name the SHIPPED CLI surface, not a plan draft (this is why `.2` follows `.1`)
- `adding-a-review-backend-sweep-all-2026-06-29` — adding a status value / subcommand means sweeping EVERY enumeration site
- `adding-a-tracker-to-tracker-sync-sweep-2026-06-28` — named-file doc sweeps miss secondary surfaces; sweep by grep, not by memory
- `audit-sync-codexsh-during-planning-for-2026-04-30` and `sync-codexsh-tool-substitution-needs-2026-05-18` — audit `sync-codex.sh` transforms when adding tool-referencing prose
- `test-production-path-not-parallel-construction-2026-05-21` — test the real argparse routing, not a mock-patched parallel construction

**Downstream (out of this spec, maintainer's pass):** flow-next.dev docs site, AI x SDLC guide, Obsidian vault notes — tracked per the maintainer's private walk requirement, not an acceptance criterion here.

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

**Plan-time decisions (2026-07-24, `/flow-next:plan`; these execute Decision 3's standing instruction and close gaps the scope pass left open):**

5. **`related_to` demoted to a corroborating signal** (Architecture). The store measurement showed a standalone `>= 3` cluster trigger would flag 28% of entries; `related_to` is auto-populated by overlap scoring, so cluster size measures topic collision, not re-teaching. Signals (i) and (iii) keep their values. Structure (any-of, propose-only, judgment-overridable) unchanged, as Decision 3 required.
6. **Outcome precedence: correctness > Consolidate > Harden** (R12). A wrong lesson must never be graduated into a gate, so Replace/Delete win outright; a `related_to` cluster is consolidated before the merged entry is considered, which follows directly from the existing "the cluster, not each member, is the Harden unit" rule.
7. **Hardened entries stay visible to the audit, at low cost** (R13). Default `memory list`/`search` exclude them (R7 — that is what stops re-injection), but the audit's own walk keeps a cheap gate-liveness check so a removed gate can propose un-graduation via the existing `mark-fresh` escape hatch. Without this, a reverted lint rule would strand the lesson permanently outside the context window with no path back. Full re-investigation of hardened entries is NOT re-run — liveness only.
8. **`stale` -> `hardened` is a legal transition** (R14). A lesson can be stale as written and still name a real, mechanizable class; forcing a `mark-fresh` round trip first would be ceremony without value.
9. **Cross-version reads fail loudly** (R15). The repo already requires the two flowctl copies to move in lockstep, so an old-flowctl read of a `hardened` entry is a validation error, documented as such rather than defended against with a compatibility shim.

**Plan-review round 1 corrections (2026-07-24, codex/gpt-5.6-sol; all six findings accepted, three of them after verifying the claim against the code):**

10. **R15 was factually wrong and is rewritten.** It claimed an older flowctl would fail loudly when reading a `hardened` entry. `validate_memory_frontmatter` is called only from `write_memory_entry` (`flowctl.py:9607`) -- reads never validate. Worse, the default status filter excludes only `stale`, so an old flowctl would *surface* hardened entries rather than reject them. The honest contract is read-through / write-refusal, and lockstep upgrade is the mitigation. A compatibility shim was considered and rejected: an enum extension cannot retroactively teach old readers anything, and inventing a second signalling mechanism for a repo that already requires lockstep copies is cost without benefit.
11. **Gate verification before demotion is now first-class (R16).** The original flow wrote an artifact and immediately retired the memory entry, trusting that writing config equals enforcing a rule. A malformed lint config, a rule shadowed by a later `ignore`, a CI step in a job that never runs, or a duplication-guard grep matching a commented-out rule would all retire the lesson while enforcing nothing -- strictly worse than not hardening. Verification failure keeps the entry active and reports a failed graduation.
12. **`hardened_into` gains a format** (`<path>#<rule-id> -- <note>`). R13's gate-liveness check needs something to look at; free-text prose gives it nothing. flowctl still stores it verbatim and validates only non-emptiness -- parsing the convention in flowctl would be judgment leaking into plumbing.
13. **Ordering fix: recurrence signals are gathered before Phase 0.75's auto-Keep** (R2). Auto-Keep excludes unchanged-module entries from Phase 1 investigation; since recurrence evidence was to be gathered in Phase 1, the entries most likely to deserve hardening -- old, settled, repeatedly re-taught -- were exactly the ones that would never be seen.
14. **Field invariants are per status, enforced by every mutation** (R14). The original matrix only described the new command's own field, which would have let `mark-stale` strand a `hardened_into` and `stale -> hardened` strand a `stale_reason`. `mark-stale` and `mark-fresh` are therefore in scope for task `.1`.
15. **`last_audited` stays a UTC date** (`YYYY-MM-DD`), matching the existing handlers; the worked example's full timestamp was wrong. Idempotency is asserted on `hardened_into` replacement, since a same-day re-stamp is unobservable.

**Completion-review correction (2026-07-25, codex/gpt-5.6-sol):**

16. **R14's field-invariant table asserted a state the codebase never had.** The draft claimed a `stale` entry carries `stale_reason` / `stale_date`; `cmd_memory_mark_stale` has never written either (verified: `git log -S'fm["stale_reason"]'` finds no commit), storing the reason in `audit_notes` instead. Rather than make an unrelated pre-existing command start writing a duplicate of `audit_notes`, the table and R14 now state the invariant as it was always meant: negative -- no prior-status field survives a flip. `hardened_into` never surviving into `stale` is the part that prevents contradictory frontmatter, and it is implemented and tested. The shipped docs (task `.3`) already described the real behavior; this aligns the spec to them.

**Rejected alternatives:** a standalone `/flow-next:harden` skill (audit already walks every entry with evidence in hand; a second sweep duplicates Phase 0-2); deleting graduated entries (loses provenance -- the pointer answers "why does this lint rule exist" forever); auto-applying under pilot with a strike system (gate surfaces are shared repo infrastructure; wrong lint rules block every future run -- the failure mode is much worse than a wrong stale-mark).
