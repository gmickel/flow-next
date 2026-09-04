# Spec Template & Acceptance-Criteria Discipline

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


The canonical spec scaffold lives at [`../templates/spec.md`](../../templates/spec.md). This doc covers the **rules** that surround it - R-ID semantics, confidence anchors, introduced-vs-pre-existing, protected artifacts, trivial-diff skip, and the 3-tier template discovery cascade - not the section list itself (R17: cross-link, never re-embed).

## Contents

- [Canonical scaffold](#canonical-scaffold)
- [3-tier discovery cascade](#3-tier-discovery-cascade)
- [Customizing the scaffold for your project](#customizing-the-scaffold-for-your-project)
- [Durability: contracts, not coordinates](#durability-contracts-not-coordinates)
- [Parked unknowns: the optional fog slot](#parked-unknowns-the-optional-fog-slot)
- [Acceptance criteria: R-ID rules](#acceptance-criteria-r-id-rules)
- [Confidence anchors (0 / 25 / 50 / 75 / 100)](#confidence-anchors-0-25-50-75-100)
- [Introduced vs pre-existing](#introduced-vs-pre-existing)
- [Protected artifacts](#protected-artifacts)
- [Trivial-diff skip](#trivial-diff-skip)
- [Receipt schema (additive only)](#receipt-schema-additive-only)
- [See also](#see-also)

## Canonical scaffold

[`../templates/spec.md`](../../templates/spec.md) is the single source of truth for the spec structure. The template's frontmatter enumerates the seven canonical sections + auxiliary sections; do not duplicate that list here. Read the template directly before authoring.

The template is consumed by:

| Consumer | Role |
|----------|------|
| `flow-next-capture` | synthesizes a spec from conversation context |
| `flow-next-interview` | refines a spec via Q&A (`--scope=business|technical|both`) |
| `flow-next-plan` | breaks a spec into tasks |
| `CLAUDE.md` | "Creating a spec" guide cross-links the template rather than embedding |

## 3-tier discovery cascade

When a skill needs the spec template, it walks three locations in order (first match wins):

1. `<repo_root>/SPEC.md` - your customized scaffold (uppercase preferred)
2. `<repo_root>/spec.md` - lowercase honored when uppercase absent
3. `${PLUGIN_ROOT}/templates/spec.md` - bundled (canonical source of truth)

Since fn-220 flowctl itself applies this cascade for `spec create` and `spec skeleton`, so a repo `SPEC.md` shapes CLI-created specs as well as skill-authored ones.

Case-insensitive FS handling (macOS APFS, Windows NTFS) and the bash walker that implements it live in [`../references/spec-template-discovery.md`](../../references/spec-template-discovery.md).

## Customizing the scaffold for your project

**The bundled section list is a default, not a requirement.** Tier 1 exists so a project can impose its own spec shape without forking the plugin or waiting for upstream to agree. If your team wants user stories in every spec, a risk register, a rollout/runbook section, a compliance block, or a data-retention statement - add it and it is there on every spec that project authors from then on.

### How

```bash
# from your repo root
cp "$CLAUDE_PLUGIN_ROOT/templates/spec.md" SPEC.md   # bundled scaffold — the plugin install is the only source
$EDITOR SPEC.md                                       # add / reorder / reword
git add SPEC.md && git commit -m "docs: project spec scaffold"
```

Commit it. The scaffold is a team artifact - an uncommitted `SPEC.md` gives you a spec shape your teammates and your CI agents do not have.

Frontmatter and the `<!-- scope: ... -->` markers are authoring guidance, not spec content; keep them if you want the interview passes to keep routing correctly, and know that they may be stripped from the finished spec body.

### What is safe to change

- **Adding sections.** Free, and the main reason to customize. Nothing parses for an unknown heading, so an extra section is carried as prose.
- **Reordering** sections, including moving an added section between canonical ones.
- **Rewriting the guidance prose** under any heading. It is instruction to the authoring agent - make it say what your project actually needs. This is the highest-leverage edit and the most commonly missed one.

  A worked example - **house style for acceptance criteria**. Want BDD-flavored (Given/When/Then) criteria on every spec? Rewrite the guidance under `## Acceptance Criteria` in your copied `SPEC.md`:

  ```markdown
  ## Acceptance Criteria

  <!-- House style: write each criterion as a BDD scenario - Given <context>,
       when <action>, then <observable outcome>. Keep the **R<n>:** marker;
       use sibling ids (R4a, R4b) for scenario variants of one requirement. -->

  - **R1:** Given a signed-in user with an expired session, when they submit the form, then the draft is preserved and they are returned to it after re-auth.
  ```

  Every spec the project authors from then on arrives with that instruction, and every interview/capture pass writes criteria in that shape. The only load-bearing parts are the heading name and the `**R<n>:**` bullet marker - the criterion *text* is yours (the parser reads wrapped multi-line bullets, and anything it cannot read is surfaced as `acceptance_criteria_residue` rather than silently dropped). The same move works for any house convention.

  More house styles, same mechanism - each is one instruction comment (or one rewritten guidance line) in your copied `SPEC.md`, and every spec the project authors from then on obeys it:

  | Team wants | Instruction to add under the relevant heading |
  |---|---|
  | **User-story criteria** (product orgs) | Under `## Acceptance Criteria`: *"Phrase each criterion as: As a <role>, I can <capability>, so that <outcome> - observable outcome mandatory, keep the `**R<n>:**` marker."* |
  | **Observability mandate** (SRE-minded) | Under `## Acceptance Criteria`: *"Every criterion names the signal that proves it in production - a metric, log line, or alert. A criterion with no signal is not accepted."* |
  | **Compliance traceability** (regulated) | Under `## Acceptance Criteria`: *"Tag each criterion with the control it satisfies (e.g. `[SOC2-CC6.1]`, `[GDPR-Art17]`)."* Plus an added `## Data & Compliance` section: classification of data touched, retention, audit-trail impact. |
  | **Non-functional budgets** | An added `## Budgets` section: *"State the numeric budgets this change must hold: p95 latency, bundle-size delta, WCAG level. 'Fast' is not a budget; '<200ms p95' is."* |
  | **Rollout & revert** (ops) | An added `## Rollout` section: *"Feature flag or migration? Name the flag, the rollout stages, and the tested revert path. A migration with no revert statement is incomplete."* |
  | **Test-evidence rule** | Under `## Acceptance Criteria` or `## Boundaries`: *"Every criterion names the command or test file that will prove it - the worker baselines and re-runs exactly those."* |
  | **Specs in your language** | Rewrite the guidance prose in German/French/Japanese/... - the authoring passes follow the instruction language, and the four parsed headings plus `**R<n>:**` markers stay English so the tooling keeps reading them. |

  Composable with [role passes](teams.md#roles-and-ownership): a platform or quality role's standing section is just another row of this table.
- **Adding project vocabulary**, links to your ADRs / design docs / glossary, or a house rule ("every spec names the observability signal that proves it worked").

### What breaks if you rename or remove a canonical heading

These four headings are parsed by `flowctl`. Renaming or deleting one does not error - the corresponding feature silently degrades, which is worse. Verified against the current implementation:

| Heading | What reads it | Consequence if renamed or removed |
|---|---|---|
| `## Acceptance Criteria` | R-ID extraction (`_export_parse_acceptance_criteria`) | R-IDs stop being found. Coverage tables in `make-pr` and the review skills come out empty, task `satisfies:` mapping breaks, and unaddressed-R-ID verdict gating stops firing. Legacy `## Acceptance criteria` and bare `## Acceptance` are tolerated; anything else is not. |
| `## Boundaries` | exact-match regex on the heading | The "Not in this PR" section of a generated PR body loses its source. |
| `## Goal & Context` | interview business-scope routing | `--scope=business` loses a write target; the business pass has nowhere canonical to put framing. |
| `## Decision Context` | flat-vs-substructured detection | The `### Motivation` / `### Implementation Tradeoffs` promotion logic cannot tell which shape the spec is in. |

Keep R-ID bullets in the canonical form - `- **R1:** <criterion>` - with optional single-letter sibling suffixes (`R4a`, `R4b`). The parser matches `R<digits><optional letter>`; prose numbering like "Requirement 1" is not recognized.

The other three canonical sections (`Architecture & Data Models`, `API Contracts`, `Edge Cases & Constraints`) are technical-scope write targets. Removing them is survivable, but the technical interview pass will have fewer places to put what it learns.

### Custom sections and the interview passes: use the scope marker

`flowctl scope write-policy` enumerates the seven canonical sections only, so a section you added appears in neither its `writable` nor its `preserved` list. Ownership of a project-added section therefore comes from **the section's own scope-owner marker in the spec body**, and the interview passes apply a three-way rule:

| Marker on your section | What an interview pass does |
|---|---|
| names the pass's own scope (`<!-- scope: business -->` under `--scope=business`) | **writes it** - fills and refines it like a canonical section of that scope |
| names the other scope | preserves it byte-for-byte |
| `<!-- scope: both -->` | writable under any pass |
| absent or unparseable | preserves it byte-for-byte, and says so in the read-back |

So the marker is the difference between a section that gets filled and a section that stays frozen. Add one if you want the interview to do the work; leave it off if the section is yours to hand-write.

Two consequences worth knowing:

- A marked section is **rewritable**. If you hand-write user stories and mark them `scope: business`, the next business pass will refine them. That is the point, but it means hand-authored content under a marker you own is not sacred - drop the marker to freeze it.
- Scope-owner markers are ordinarily authoring guidance and may be stripped from a finished spec body. For project-added sections they must be **kept**, because they are the only ownership signal a later pass has. See [`../references/spec-template-discovery.md`](../../references/spec-template-discovery.md).

`capture` and `plan` seed from the template directly and have no such caveat.

### Worked example: adding user stories

```markdown
## Goal & Context
<!-- scope: business -->
...

## User Stories
<!-- scope: business -->

Numbered, one actor per story: "As a <actor>, I want <capability>, so that <benefit>."
Cover the unhappy paths too, not only the demo path.

## Architecture & Data Models
<!-- scope: technical -->
...
```

Canonical headings untouched, one section added, scope marker set so the business pass owns it.

### Why the default stays lean

We benchmarked adding user-story and test-seam sections to the bundled scaffold. A first pass looked positive; a pre-registered replication did not hold up, and the larger scaffold cost roughly a third more spec length - paid on every downstream read by every worker and reviewer. So the default stays lean and the override stays available. Section preferences are project-specific and the cascade is the right place to express them.

## Durability: state the contract

**A spec states contracts: types, signatures, behaviors, invariants.** It does not state file paths or line numbers. Coordinates rot on the first refactor, and a spec full of rotted coordinates is what turns plan-sync into churn - every downstream task spec gets rewritten because a file moved, not because anything was decided differently.

One carved exception: **a decision-rich snippet whose exact location is the decision** - the case where "here, not there" is the content, and a reader who lands anywhere else has misread the spec. Name the location then, and only then.

**Tasks are exempt and unchanged.** `**Files:**` / `**Touches:**` are a task's job under the task-shape doctrine: a task is a work order pointed at a place, and pointing at the place is the point. The boundary is the artifact, not the topic - the same repo, the same feature, one rule for specs and another for the tasks under them.

## Parked unknowns: the optional fog slot

`## Parked unknowns` is an optional auxiliary section. It holds what the spec genuinely does not know yet, one bullet per item, so fog is visible instead of dressed up as a decision.

Each bullet must pass the **fog-or-ticket test**:

- **Decidable now** → decide it. It belongs in the canonical section that owns it, not here.
- **Resolvable by scheduled work** → make it a task or a ticket. A known unknown with a known way to find out is work, not fog.
- **Genuinely unknown** - needs a decision nobody has made, an experiment nobody has run, or an answer from outside the repo - → park it here in one line, naming what would resolve it.

**Graduate-on-resolution.** When an interview or plan resolves a parked item, the answer moves into the section that owns it and the bullet is deleted from `## Parked unknowns`. A bullet that outlives its own answer reads as an open question on a spec that has in fact closed it - the failure this section exists to prevent. An empty section is omitted, never left as a heading.

## Acceptance criteria: R-ID rules

R-IDs are numbered acceptance criteria written as `**R1:** ...`, `**R2:** ...` in plain markdown prose under the `## Acceptance Criteria` section (the canonical section name; the scaffold heading is the authoritative source).

```markdown
## Acceptance Criteria
- **R1:** OAuth login works for Google provider
- **R2:** Session persists across page reloads
- **R3:** Logout clears session tokens
```

Task specs reference them via frontmatter when relevant:

```yaml
---
satisfies: [R1, R3]
---
```

Rules:

- Plain markdown prose, not YAML - keeps specs human-editable.
- **Renumber-forbidden** after the first review cycle. Deletions leave gaps (`R1, R3, R5` stays that way); new criteria take the next unused number.
- **Append-only across passes.** A `--scope=technical` pass cannot rewrite or renumber R-IDs added by an earlier `--scope=business` pass; it appends new criteria with the next unused number.
- Plan skill writes R-IDs on creation; plan-sync preserves them through drift updates.
- Impl-review and spec-completion review emit a per-R-ID coverage table (met / partial / not-addressed / deferred).
- Any unaddressed R-ID flips verdict to `NEEDS_WORK`; receipt carries an `unaddressed: ["R2", "R5"]` array so the fix loop has targeted work.

### Error-case enumeration (negative-cases discipline)

Every behavioral R-ID must make its failure surface visible - either by naming the error / invalid-input / boundary cases *inside that bullet*, or by an explicit one-liner that there is none beyond a named parent. Silence is incomplete; a declared "none" is complete.

**What counts as an enumeration.** Per criterion, name the cases the implementation must handle (or deliberately refuse): malformed input, missing files/resources, conflicting state, limits (size, rate, concurrency), and any other boundary the criterion creates. Write them as sub-clauses or sub-bullets under the parent R-ID - **not** as new sub-R-IDs and **not** as a new coverage-table column. Letter-suffix siblings (`R4a`, `R4b`) remain for genuinely separable criteria, unchanged.

```markdown
- **R1:** Parse config file into typed settings. Errors: malformed JSON → clear
  message + non-zero exit; missing file → same; over size limit → reject.
- **R2:** Settings object is frozen after load (no error surface beyond R1).
```

**Why ("considered" vs "forgot").** A persisted regression suite entrenches blind spots as faithfully as knowledge - "all tests pass" every session actively signals nothing-to-fix for cases nobody enumerated. Plan-time enumeration is the cheap fix: plan-review's fresh eyes can see an R-ID with neither error clauses nor a no-error-surface line as incomplete, without new review-stage machinery. The discipline exists so a reader can tell *considered and ruled out* from *forgot*.

**G-ID interplay.** Standing error-handling criteria in `.flow/criteria.md` (e.g. "every CLI exits non-zero on user error") are **referenced by G-ID, never restated** as R-ID prose. The error discipline applies only to what the spec *adds* - its own R-IDs - the same non-restatement rule as the rest of the G-ID system. Mid-flight specs written before this discipline exist with no enumerated error cases: the work-stage test-tie scopes to "error cases enumerated in the ACs", so an empty set triggers nothing (not retroactive).

### Global criteria (G-IDs): the same grammar at project scope

Some acceptance criteria are not about one spec - "every route change regenerates the API contract", "no new dependency without a health check". Those live in an optional, user-owned `.flow/criteria.md` as **G-IDs**: the R-ID grammar with a `G` prefix, one line-anchored bullet per criterion:

```markdown
- **G1:** Every route change regenerates the API contract.
- **G2:** No new dependency without a health check (scope: package.json).
```

The rules mirror R-IDs where they apply:

- Plain markdown prose; optional scope hints (paths/globs) live in the prose itself.
- Ids must be unique; gaps are allowed (deleting G2 leaves G1, G3). **Never renumber** - G-IDs are stable identity across specs and receipts, exactly like R-ID numbers within a spec.
- `flowctl criteria list --json` parses and validates the file; invalid content is a loud error, an absent file is a silent no-op everywhere.
- The **spec is the unit of compliance**: spec completion review (not per-task impl review) judges each G-ID against the whole implementation and records `met` / `violated` / `n/a` per criterion in the review receipt's additive `criteria` array. Violations also surface as normal findings.
- **G-IDs are never restated as R-IDs.** The spec-authoring skills (`plan`, `capture`, `interview`) do not copy standing criteria into a spec's `## Acceptance Criteria` - a copy drifts as `criteria.md` evolves and gets judged twice. A spec references a relevant G-ID in prose; an R-ID covers only what the spec adds beyond the standing rule.

`/flow-next:setup` offers to scaffold the file (opt-in; declining leaves no trace). See [`review-findings.md`](review-findings.md) § Global-criteria compliance for the receipt field, and [`flowctl.md`](flowctl.md) § criteria for the CLI.

### Source tags: what you said vs what the agent inferred

`/flow-next:capture` **and** `/flow-next:interview` tag every acceptance criterion they write at source: `[user]` (the human's words - the PO under a business pass, the tech lead under a technical one), `[paraphrase]` (that meaning, tightened), `[inferred]` (the agent's own inference), plus `[strategy:<track>]` when a criterion traces to a STRATEGY.md track. The tag is a trailing token on the bullet:

```markdown
- **R1:** Root marketplace manifest exists and imports cleanly. [user]
- **R3:** Host detection switches to a positive signal. [inferred]
```

Three rules matter when reading a tagged spec:

- **A pass tags only the criteria it authors**, and never retags an existing bullet - provenance is frozen exactly like the R-ID number. So on a spec that went through a business pass then a technical pass, each criterion's tag reflects the pass that wrote it.
- **Untagged means unknown provenance, never `[user]`.** Criteria written before this shipped, or by hand, carry no tag. Defaulting them to "a human said this" is wrong in the dangerous direction.
- **The tags are load-bearing, not decoration**: the read-back refuses to recommend `approve` while unverified `[inferred]` items remain (the no-self-blessing rule). In interview that is narrowed to `[inferred]` criteria no question covered, since an answered question has already done the verifying.

They are also the cheapest review filter available, because reading them is a grep rather than a model judgment. Tally which criteria are grounded and which are guesswork:

```bash
flowctl cat fn-14 \
  | grep -oE '\*\*R[0-9]+[a-z]?:.*\[[^]]+\]$' \
  | sed -E 's/^\*\*(R[0-9]+[a-z]?):.*\[([^]]+)\]$/\2\t\1/' \
  | sort | awk -F'\t' '{c[$1]=c[$1]" "$2; n[$1]++} END {for (t in c) printf "%-26s %2d %s\n", t, n[t], c[t]}'

user                        6  R1 R13 R5 R6 R7 R8
paraphrase                  3  R10 R12 R2
inferred                    4  R11 R3 R4 R9
strategy:Cross-platform parity  1  R14
```

Two details in that pipeline are load-bearing, and both exist because a track name is **not** a lowercase slug - it keeps its literal casing and may contain spaces or hyphens (`[strategy:Cross-platform parity]`):

- the character class is `[^]]+`, not `[a-z:]+` - a lowercase-only class silently drops every `[strategy:*]` criterion from the tally;
- `sed` emits a **tab** and `awk` reads `-F'\t'` - with the default whitespace split, a track name containing a space lands in `$2` and the tally reports a phantom tag.

Then interview only the uncertainty instead of re-litigating settled requirements:

```text
/flow-next:interview fn-14 - focus only on the [inferred] acceptance criteria
(R3, R4, R9, R11); the [user] and [paraphrase] ones are settled, leave them alone
```

Append-only R-ID numbering is what makes that targeting safe - a later pass cannot renumber or rewrite the criteria you already blessed, and it will not retag them either.

Scope: tags apply to a spec's `## Acceptance Criteria` bullets. Task acceptance is plain `- [ ]` checklist items and carries no tags, and an interview over a loose markdown file leaves that file's structure alone - tags start when `/flow-next:plan` promotes it to a spec.

Note: `flowctl spec export-cognitive-aid --json` does not surface parsed criteria with their tags as a top-level array today (the parse feeds the PR-body coverage table internally), so the grep above is the supported route.

## Confidence anchors (0 / 25 / 50 / 75 / 100)

Reviewers score every finding on exactly five discrete values:

| Anchor | Meaning |
|--------|---------|
| 100 | Verifiable from code alone, zero interpretation. |
| 75 | Full execution path traced - input → branch → wrong output. |
| 50 | Depends on conditions visible but not fully confirmable. |
| 25 | Requires runtime conditions with no direct evidence. |
| 0 | Speculative. |

**Suppression gate:** after dedup, findings below 75 are dropped. Exception: P0 findings at 50+ survive. Reviews report `suppressed_count` by anchor; receipt optionally carries it as `{"50": 3, "25": 7, "0": 2}`.

## Introduced vs pre-existing

Each finding is classified:

- `introduced: true` - caused by this branch's diff.
- `pre_existing: true` - broken on the base branch.

Verdict gate considers only `introduced` findings. Pre-existing issues surface in a separate non-blocking "Pre-existing issues" section. Receipt carries `introduced_count` + `pre_existing_count` so Ralph stops fighting bugs it didn't introduce.

## Protected artifacts

Review prompts carry a hardcoded never-flag list - findings recommending deletion or gitignore of these paths are discarded during synthesis:

- `.flow/*` (specs, tasks, memory, state)
- `.flow/bin/*` (legacy flowctl copies - reviewers never advise deleting a user's committed files; removal is the user's own call at the setup / plan touchpoints)
- `.flow/memory/*` (learnings store)
- `docs/plans/*`, `docs/solutions/*` (when the project uses them)
- `scripts/ralph/*` (Ralph harness)

Prevents cross-model reviewers unfamiliar with flow-next conventions from proposing destructive cleanups.

## Trivial-diff skip

`flowctl triage-skip --base <ref>` runs a deterministic whitelist (lockfile-only / docs-only / release-chore / generated-file-only) and returns `VERDICT=SHIP` without invoking the configured backend. Receipt is written with `mode: triage_skip`, `source: deterministic`, and a one-line reason.

```bash
flowctl triage-skip --base main
# VERDICT=SHIP
# reason=lockfile-only (bun.lock)
# source=deterministic
```

An optional LLM layer for ambiguous diffs is gated behind `FLOW_TRIAGE_LLM=1`. On by default in Ralph mode; opt-out via `--no-triage` or `FLOW_RALPH_NO_TRIAGE=1`.

## Receipt schema (additive only)

All review receipts may carry these optional fields; existing consumers that read by key ignore unknowns:

```json
{
  "mode": "codex",
  "verdict": "NEEDS_WORK",
  "unaddressed": ["R2", "R5"],
  "suppressed_count": {"50": 3, "25": 7, "0": 2},
  "introduced_count": 2,
  "pre_existing_count": 4
}
```

## See also

- [`../templates/spec.md`](../../templates/spec.md) - the canonical scaffold (section list, scope-owner annotations, flat-vs-substructured Decision Context).
- [`../../../GLOSSARY.md`](https://github.com/gmickel/flow-next/blob/main/GLOSSARY.md) - definitions for *Spec*, *Task*, *R-ID*, *Frozen-at-handover*.
- [`../skills/flow-next-interview/SKILL.md`](../../skills/flow-next-interview/SKILL.md) - 3-tier discovery cascade walker.
- [`flowctl.md`](flowctl.md) - `flowctl spec create / set-plan / export-cognitive-aid` reference.
