---
satisfies: [R1, R2, R3, R4, R5, R8, R9, R10, R12, R13, R16]
---
# fn-122-harden-verdict-graduate-recurring.2 Audit skill: Harden outcome (phases, workflow, SKILL)

## Description
Add **Harden** as the sixth outcome of `/flow-next:audit`, across the skill's three prose files. All judgment lives here: recurrence detection, mechanizability, gate-type selection, the duplication guard, the draft artifact, and the precedence rules between competing outcomes.

Depends on task `.1` because every sentence naming a flowctl surface (`memory mark-hardened`, `--gate-ref`, `--status hardened`) must match the SHIPPED CLI, not a plan draft. Write the prose against what `.1` actually landed.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-audit/phases.md`
- `plugins/flow-next/skills/flow-next-audit/workflow.md`
- `plugins/flow-next/skills/flow-next-audit/SKILL.md`

### Approach

**phases.md** — add the outcome row to the table (:5-11), change "The 5 outcomes" to six (:15), add a `## Harden` section matching the existing per-outcome shape exactly (Meaning / When to use / When NOT to use / Action steps / Edge cases), and add the Harden branch plus the precedence rule to the decision tree (:336-360). Note in the decision-entry calibration section (:232-276) that Harden is expected to be rare on `knowledge/decisions/` entries — most decisions are judgment records, not mechanizable checks.

Document the recalibrated thresholds verbatim from the spec's Architecture section: primary signals are `>= 2` `## Update` headings OR `>= 4` commits on the entry file; a `related_to` cluster of `>= 3` is a **corroborating** signal only and proposes nothing on its own. State the calibration evidence briefly (a standalone cluster trigger flagged 28% of a 71-entry store; `related_to` is auto-populated by overlap scoring, so it measures topic collision, not re-teaching). Thresholds gate PROPOSING; the human gates APPLYING; mechanizability is a separate AND condition, always LLM-judged.

Document precedence explicitly (R12): correctness verdicts (Replace / Delete) win outright — a wrong lesson is never graduated into a gate; then Consolidate — a cluster is merged before the merged entry is considered, since the cluster is the Harden unit; then Harden.

**workflow.md** — thread the outcome through the phases:
- Phase 0.75 change-detection (:283-303) and Phase 1 Investigate (:307). **Ordering matters and the current order breaks the feature (R2).** Phase 0.75 today auto-Keeps entries whose module has not changed and excludes them from Phase 1 entirely. Recurrence evidence is cheap (three greps and a `git log`), so gather it BEFORE the auto-Keep decision and let a recurrence-qualified entry or cluster bypass auto-Keep into Harden investigation even when its module is unchanged. Left as-is, the entries most deserving of a gate — old, settled module, re-taught repeatedly — are exactly the ones never seen. Also give hardened entries the cheap gate-liveness check from R13 here, rather than a full re-investigation or a silent skip.
- Phase 2 Classify (:445-455): add Harden to the outcome list.
- Phase 3 Ask (:478): present each Harden candidate individually — the way Replace/Delete are presented today — with proposed gate type, draft artifact content, evidence bullets, and accept / pick-a-different-gate-type / decline options via the blocking-question tool.
- Phase 4 Execute (:534-607): a new `4.x` subsection — write the accepted artifact to the chosen surface, **verify the gate actually fires (R16)**, and only then demote via `flowctl memory mark-hardened`. Never `git rm`. Decision-track supersession fields are preserved alongside the new status.
- Phase 5 Report (:615): a `Hardened: N` count with per-entry detail lines (gate type, artifact path, gate-ref); in autofix, a Recommended bucket instead.

**SKILL.md** — update the frontmatter `description` and the body outcome list to six; add `memory mark-hardened` to the thin-plumbing sentence; add the autofix rule to Forbidden: Harden never auto-applies.

**Gate targets, cheapest-fitting first**, discovered from repo files (never assumed, never scaffolded): (a) an existing linter's config, (b) a step in existing CI, (c) a rule in the substantive CLAUDE.md / AGENTS.md — the universal floor, and the degradation target for review-shaped lessons since gate type (d) is out of v1.

**Gate verification before demotion (R16) — the load-bearing step.** Writing config is not the same as enforcing a rule. Before `mark-hardened` is called, confirm the gate actually fires, by gate type:
- lint: run the linter and confirm the new rule is active in the RESOLVED config — not merely present as text in a file the tool does not read, and not neutralized by a later ignore/disable entry.
- CI: confirm the step parses and sits in a workflow and job that actually run on the relevant trigger, not a disabled, unreferenced, or manual-only one.
- instruction file: confirm the rule landed in the SUBSTANTIVE file the agents read (the same "which file is real" discovery Phase 6 already does), not an `@`-including stub.

Verification failure means the entry stays `active`, `mark-hardened` is NOT called, and the report shows a failed graduation with the reason. A gate that does not fire is strictly worse than no gate: it retires the only working copy of the lesson while enforcing nothing.

**Duplication guard**: before proposing, grep the candidate gate surfaces for a rule already covering the class. A textual hit is not enough — apply the same activeness check as above. Already enforced AND active → propose pointer-demotion only, citing the existing gate as `--gate-ref`, with no new artifact. Matched but inactive (commented out, ignored, in a dead workflow) → that is a broken gate, not a duplicate: the entry stays active and the finding is reported.

**`--gate-ref` composition.** The audit skill owns the format `<path>#<rule-id> -- <note>` (flowctl stores it verbatim and validates nothing). `<path>` is repo-relative; `<rule-id>` must be a token a later `grep` can find in that file. This is what makes R13's gate-liveness check possible — a prose description would give the next audit nothing to look at. Examples: `pyproject.toml#DTZ -- ruff select entry, bans naive datetimes`, `.github/workflows/ci.yml#ruff check -- lint job runs the DTZ gate`, `CLAUDE.md#stamp timestamps in UTC ISO-8601 -- instruction-file floor gate`.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-audit/phases.md:5-15` — outcome table and the "5 outcomes" sentence
- `plugins/flow-next/skills/flow-next-audit/phases.md:336-360` — the decision tree to extend
- `plugins/flow-next/skills/flow-next-audit/workflow.md:445-455` — Phase 2 classify outcome list
- `plugins/flow-next/skills/flow-next-audit/workflow.md:534-607` — Phase 4 per-outcome execute subsections (4.1-4.6), the shape to match
- `plugins/flow-next/skills/flow-next-audit/SKILL.md:1-12` and the autofix-rules block around `:60`

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-audit/workflow.md:283-303` — Phase 0.75 change-detection pre-filter
- `plugins/flow-next/skills/flow-next-audit/phases.md:232-276` — decision-entry calibration

### Key context

- Canonical prose uses Claude-native tool names (`AskUserQuestion`, `Task`). Do NOT hand-edit the Codex mirror — `scripts/sync-codex.sh` regenerates it (task `.3` runs it). But DO keep new prose within transforms the sync script already handles; if a genuinely new Claude-only phrase is introduced, that is a sync-script concern to flag, not to work around.
- Cursor and Droid consume canonical files with no rewrite pass, so any Claude-builtin reference needs a portable fallback clause or graceful degradation stated inline.
- Skill prose must name the CLI surface that task `.1` actually shipped. Re-read the shipped `--help` rather than trusting this task file's flag names.
- No implementation code in prose: describe what the Ask step shows and what Execute writes, not a generator.

## Acceptance

- [ ] phases.md: Harden appears in the outcome table, the count line reads six, and a `## Harden` section exists matching the existing per-outcome structure (R1).
- [ ] phases.md decision tree includes the Harden branch AND the precedence rule: Replace/Delete > Consolidate > Harden, with the reason stated for each edge (R12).
- [ ] Thresholds documented as recalibrated: `>= 2` Update headings OR `>= 4` commits as primary triggers; `related_to >= 3` as corroborating-only; propose-only, judgment-overridable, mechanizability as a separate AND condition (R1).
- [ ] workflow.md Phase 1 gathers the recurrence artifacts per entry and states plainly that no read-side usage telemetry exists — detection is write-side artifacts plus LLM judgment (R2).
- [ ] workflow.md Phase 3 presents each Harden candidate individually with gate type, draft artifact, evidence bullets, and accept / different-gate-type / decline options via the blocking-question tool (R3).
- [ ] workflow.md Phase 4 writes the accepted artifact, verifies it, THEN calls `flowctl memory mark-hardened <id> --gate-ref "..."`; the entry file stays on disk with body intact; decision-track supersession fields preserved; never `git rm` (R4, R10).
- [ ] Gate verification documented per gate type (lint / CI / instruction file) as a hard precondition of demotion; verification failure keeps the entry `active`, skips `mark-hardened`, and reports a failed graduation with the reason (R16).
- [ ] `--gate-ref` composition documented as `<path>#<rule-id> -- <note>` with a worked example per gate type, and the `<rule-id>` stated to be grep-findable in `<path>` so the R13 liveness check has a target.
- [ ] workflow.md Phase 1 gathers recurrence signals BEFORE the Phase 0.75 auto-Keep decision; a recurrence-qualified entry/cluster bypasses auto-Keep even when its module is unchanged, with the reason stated in prose (R2).
- [ ] Duplication guard documented: an existing gate counts only when confirmed ACTIVE by the same check as R16; active match → pointer-demotion citing it, no duplicate artifact; inactive match → broken gate, entry stays active, finding reported (R8).
- [ ] Hardened entries on later runs: gate-liveness check documented — gate gone → propose `mark-fresh` un-graduation with evidence; gate present → reported as still-hardened, not fully re-investigated; a gate upgrade is a re-`mark-hardened` (R13).
- [ ] workflow.md Phase 5 reports `Hardened: N` plus per-entry detail (gate type, artifact path, gate-ref); autofix reports Harden under Recommended only (R9).
- [ ] SKILL.md lists six outcomes in both the frontmatter description and the body, names `memory mark-hardened` in the plumbing sentence, and states in Forbidden that Harden never auto-applies in autofix — no artifact write, no demotion (R5).
- [ ] Repos with no linter and no CI degrade to the instruction-file rule; the skill never scaffolds a linter or CI pipeline to host a gate.
- [ ] Every flowctl invocation named in the prose matches the shipped CLI from task `.1` (verified against `flowctl memory mark-hardened --help`, not this task file).


## Done summary
Added Harden as the sixth `/flow-next:audit` outcome across the skill's three prose files: phases.md gains the outcome row, a full `## Harden` section (recalibrated recurrence thresholds with calibration evidence, mechanizability as a separate AND condition, gate targets a/b/c with no scaffolding, duplication guard, gate verification before demotion, `--gate-ref` format, gate-liveness check on later runs), the precedence rule (correctness > Consolidate > Harden) and the extended decision tree; workflow.md gathers recurrence artifacts BEFORE the Phase 0.75 auto-Keep so recurrence-qualified entries and clusters bypass it, adds the hardened-entry liveness path, Phase 2 classification, per-candidate Phase 3 asks, Phase 4.7 execute (write -> verify -> `flowctl memory mark-hardened`, never `git rm`) and the Phase 5 Hardened bucket; SKILL.md lists six outcomes, names the shipped `memory mark-hardened` plumbing, and forbids autofix application, unverified demotion, `git rm`, and scaffolding.

Codex mirror regenerated via sync-codex.sh (twice, idempotent, guards green), including a widened flow-next-audit catalog description so Codex discovery surfaces the graduation trigger.
## Evidence
- Commits: da2911c15955d022d935a0e320de1043e27b451d, a8b413a8cb8235f4d9f4bec874994eef574db1ee, 6b8b90a3cd061978403f46ea930ee5cc95b9e710
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_memory_mark_stale test_memory_mark_fresh test_memory_mark_hardened test_flowctl_surface test_startup_bootstrap -q (67 tests, OK; baseline green pre-edit), ./scripts/sync-codex.sh (run twice, idempotent, all validation guards green), codex impl-review SHIP after 1 fix round (receipt /tmp/impl-review-receipt-fn-122-harden-verdict-graduate-recurring.2.json, gpt-5.6-sol, 0 unaddressed R-IDs)
- PRs: