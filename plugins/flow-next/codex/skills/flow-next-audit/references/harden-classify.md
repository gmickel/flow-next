# Harden classification (gated reference)

> Read from workflow.md §0.75 / Phase 2 and phases.md §Harden only for an entry or cluster
> §0.75.1 marked recurrence-qualified.

## Harden

**Meaning:** the entry is correct, keeps getting re-learned, and states a rule a machine can check. Graduate it into an enforced gate (a lint rule or a CI step) and demote the entry to a pointer at that gate — the file stays on disk, body intact. The lesson stops riding the context window on every run and starts firing automatically — for every agent and every human, in every harness.

An entry that is re-injected each run and re-taught each time is the anti-pattern: the agent re-fixes the same class instead of the class being impossible. Harden closes that loop.

**Two conditions, both required (AND):**

**(1) Recurrence signal.** Inferred from **write-side artifacts plus LLM judgment, never a usage count** — flow-next has no read-side telemetry: `memory-scout` retrieval and worker re-anchor reads leave zero trace, and nothing records "this entry fired during a run." Cite the artifacts in evidence bullets, never a count of uses. An entry (or cluster) becomes a **candidate** when ANY primary signal fires:

- **`>= 2` `## Update` headings** on the entry — the lesson was explicitly re-taught at least twice.
- **`>= 4` substantive commits** touching the entry file — sustained write churn on one lesson. Audit-bookkeeping commits and pure renames are not re-teachings and do not count.

`related_to` cluster size is a **corroborating signal only**: a cluster of `>= 3` raises a candidate ONLY when it co-occurs with at least one `## Update` heading somewhere in the cluster, or with the commit signal on any member. **On its own it proposes nothing.**

The scan that produces these numbers — the rename-following `git log`, the bookkeeping filter and why it exists, the cluster aggregates — lives in [workflow.md](../workflow.md) §0.75.1 and runs before the auto-Keep decision.

> **Why these thresholds.** On a real store, the `## Update` signal matches about 4% of entries and the commit signal about 5%; the bookkeeping filter holds the commit rate steady as audits accumulate. A standalone `related_to >= 3` trigger would match about **28%**. `related_to` is auto-populated by overlap scoring on every `memory add`, so cluster size measures topic collision, not re-teaching — left standalone it would flag more than a quarter of the store on the first run and train the user to decline Harden reflexively. The two primary signals are selective and match the recurring-pain intuition, so they keep their values.

Thresholds gate **proposing** only; the human gates **applying**. They are overridable by judgment in either direction — state the evidence when you override (e.g. a single-`## Update` entry that names a rule the linter already almost covers is worth proposing; four commits that were all typo fixes are not recurrence).

**(2) Mechanizability.** The lesson must be expressible as a deterministic check a gate can run — always LLM-judged, never inferred from the counts. "Never use naive `datetime.now()`" is mechanizable. "Prefer composition over inheritance when the hierarchy gets awkward" is not.

**When to use:**

- Both conditions hold: a recurrence signal fires AND the lesson is a deterministic, checkable rule.
- The rule can land in a gate surface that **already exists** in this repo (see Gate targets below).
- No existing, active gate already enforces the class (see Duplication guard).

**When NOT to use:**

- The lesson is wrong, misleading, or its code is gone → Replace / Delete win outright (precedence). Never graduate a wrong lesson.
- The entry is one of several overlapping entries → Consolidate first; the merged entry is the Harden unit.
- One-off lesson, no recurrence signal → Keep.
- Judgment-only lesson ("prefer X style when ambiguous", "escalate when the review disagrees") → not Harden. A gate that cannot decide mechanically becomes a false-positive generator. With a recurrence signal **and a nameable retrieval defect** the entry is an Update (retrieval-fix variant); with recurrence but no nameable defect — as without recurrence at all — it falls through to the ordinary reference-drift check, so Keep absent drift of its own. Recurrence alone never licenses a metadata edit: §0.75.1's counters never decrease, so an ungated branch re-fires on the same entry every run.
- The repo has no lint or CI surface to host the gate → not a gate audit can write; report it under Recommended naming flow's repeated-mistake route, which can add a check or test as code, and the entry stays `active`.
- **Autofix mode.** Harden never auto-applies. Candidates are reported under Recommended only — no artifact write, no demotion. Gate surfaces are shared repo infrastructure; an autonomous sweep must not edit lint config, CI, or CLAUDE.md unattended.

**Gate targets — walk the [hardening ladder](../../../references/hardening-ladder.md) from the top, discovered from repo files, never assumed and never scaffolded.** Its first, second and fourth levels (remove the opening, make the state unwritable, a behaviour test) change product code, which audit never writes: when one of them is the highest level that works, report it as a Recommended item naming flow's repeated-mistake route (`/flow-next:flow` with "agents keep doing <class>"; that route captures the spec instead of returning the lesson here), and the entry stays `active`. Audit writes only the ladder's lint or CI level, into surfaces that already exist. Instruction text is the ladder's level for lessons that need judgment, which are never Harden candidates (above), so audit writes no new instruction-file gate; instruction-file gates hardened earlier keep their liveness check (§0.75.2):

- **(a) Lint rule** — extend the repo's existing linter config (ruff, biome, eslint, … — discovered by reading the repo, not assumed from the language). No linter configured → unavailable, fall through.
- **(b) CI step** — a check in the repo's existing CI workflow (e.g. under `.github/workflows/`). No CI → unavailable; with neither surface, the entry goes to Recommended as above.

**Never scaffold infrastructure to host a gate.** Do not create a linter setup, a CI pipeline, or a config file that does not already exist. The gate lands in what the repo already has, or the entry goes to Recommended as above.

**Duplication guard (run BEFORE proposing):** grep the candidate gate surfaces (linter config, CI workflows, instruction files) for a rule already covering the class.

- **Matched AND active** (confirmed by the same activeness check as gate verification — [workflow.md](../workflow.md) §4.7 step 2) → the class is already enforced. Propose **pointer-demotion only**: no new artifact, `mark-hardened` citing the *existing* gate as `--gate-ref`.
- **Matched but inactive** (commented out, sitting in an `ignore` list, in a config the tool does not read, in a disabled or unreferenced CI job) → this is **not** a duplicate, it is a broken gate. The entry **stays `active`**, nothing is demoted, and the finding is reported so a human can fix the gate.
- **No match** → proceed with a new artifact.

A textual hit is never sufficient evidence of enforcement.

**Execution.** The procedure is [workflow.md](../workflow.md) §4.7 (interactive only): write the accepted draft, **verify the gate actually fires**, then demote via `flowctl memory mark-hardened` with a `<path>#<rule-id> -- <note>` gate-ref. Three rules from it are decision-shaping, so know them before you propose:

- **Verification is a hard precondition of demotion.** Writing config is not enforcing a rule, and a gate that does not fire is strictly worse than no gate: it retires the only working copy of the lesson while enforcing nothing. Verification failure → the entry stays `active`, `mark-hardened` is NOT called, and the run reports a failed graduation.
- **`<rule-id>` must be a literal substring of the artifact**, not a locator expression — the next run's gate-liveness check greps for it verbatim.
- **Never `git rm` on Harden**, on any track. The entry becomes a pointer so "why does this rule exist?" stays answerable forever.

**Already-hardened entries on later runs** are never dropped silently and never re-investigated: they get the cheap gate-liveness check in [workflow.md](../workflow.md) §0.75.2 (gate live → still-hardened; gate gone or inactive → propose un-graduation via `mark-fresh`; gate upgraded → re-`mark-hardened` with the new ref).

**Edge cases:**

- **Cluster candidates** — the cluster, not each member, is the Harden unit. Consolidate first (precedence), then evaluate the merged entry once. Never write one gate per member.
- **Decision-track entries** (`knowledge/decisions/`) — legal and **rare**; most decisions are judgment records, not mechanizable checks. See [decision-entries.md](decision-entries.md).
- **Stale entries** — `stale → hardened` is legal. A lesson can be stale as written and still name a real, mechanizable class; `mark-hardened` clears `stale_reason` / `stale_date` as part of the flip. Do not force a `mark-fresh` round trip first.
- **Non-code repos** (docs sites, an Obsidian vault) — targets (a)/(b) are simply unavailable; (c) is the floor.
- **First post-ship run** — recurrence signals are derived retroactively, so the first ordinary audit after this ships may surface several candidates at once. That is intended: the thresholds above are what keeps the volume sane, and there is no first-run suppression or rate limit.
- **Legacy flat files** — skipped as always; migrate first.

## Phase 2 Harden gate

**A Harden classification rests on two independent conditions.** A Harden proposed on one of them alone has broken this: it needs both a recurrence signal from §0.75.1 (`>= 2` `## Update` headings or `>= 4` entry-file commits; `related_to >= 3` corroborates only) and an LLM judgment that the lesson is mechanizable. Missing recurrence → Keep. **Recurrence present but not mechanizable → Update (retrieval fix), when the retrieval surface is actually deficient:** the lesson was re-learned while a correct entry sat in the store, so the defect is in how the entry is found, not what it says. Name the defect first — the field or fields (`title`, `tags`, `module`, `applies_when`, placement) that would miss the query this lesson's topic gets searched by. **No nameable defect → no retrieval fix**, recurrence notwithstanding (the entry falls through to the ordinary reference-drift check, so Keep unless it has drift of its own): the recurrence counters are all-history and never decrease, and a retrieval repair is itself a substantive commit in the §0.75.1 scan, so a branch that fired on recurrence alone would re-fire on every later audit forever and churn a repaired entry's metadata once per run in autofix. Evidence bullets cite the write-side artifacts (the `## Update` headings, the entry-file commits), never a usage count; the fix is scoped by [phases.md](../phases.md) §Update, retrieval-fix variant. The duplication guard runs before the candidate reaches Phase 3: an already-enforced-and-active class becomes a pointer-demotion proposal with no new artifact; a matched-but-inactive rule is a broken gate, so the entry stays `active` and the finding is reported. **In autofix mode, Harden candidates are never applied** — they are classified and reported under Recommended only.
