# /flow-next:make-pr — PR-as-cognitive-aid skill

## Conversation Evidence

> user: "this should be in Flow-Next surely, we have every other step, but not that"
> user: "make-pr, do mermaid, review opt-in, capture the epic - go into great detail in the spec so we have a great skill that creates the best PRs ever"
> user (clarifying): "for mermaid, this isn't rendering per se right, we're just adding mermaid codefences?" (yes — markdown codefence emitted as text; GitHub / GitLab / Gitea render natively, no rendering pipeline)
> user (revised): "we don't need cross model review for this i think, each harness is smart enough to determine the critical stuff, so drop that and the optional flag, makes it easier"

flow-next has 17 commands covering every SDLC step except PR creation. After `/flow-next:work` + `/flow-next:epic-review` + `/flow-next:sync` complete, the user is on their own with raw `gh pr create` — and `/flow-next:resolve-pr` only kicks in *after* the PR exists. This skill closes that gap by turning the rich flow-next state (epic spec, R-IDs, task done_summaries, evidence commits, decisions memory, bug-track memory, glossary changes, strategy alignment, deferred review findings, the diff itself) into a reviewable PR body — what the methodology calls a *cognitive-aid handover artefact*: reviewable on its own, verifiable against the spec, not a denial-of-attention attack on the reviewer. The host agent identifies critical changes directly from the structured input — no second-model review pass needed.

## Goal & Context

<!-- Source-tag breakdown: ~15% [user] / ~55% [paraphrase] / ~30% [inferred] -->

flow-next currently has zero PR-creation surface. The natural workflow ends with `flowctl done` on the last task and an epic in `done` status — at which point the user types `gh pr create` and either (a) writes the body manually, (b) lets the host agent generate a generic body from the diff, or (c) ships with `gh pr create --fill` which uses the last commit message. None of these are cognitive aids. A 10K-line diff with a 3-line auto-filled description is what the methodology calls "a denial-of-attention attack on the reviewer": the reviewer is forced to skim the whole diff, cross-reference the spec from memory, and reconstruct what changed and why.

flow-next is unusually well-positioned to fix this. Most repos have only the diff + commit messages to draw on. flow-next has nine additional structured input streams already in `.flow/`:

1. **Epic spec** with R-IDs, acceptance criteria, decision context, boundaries (`.flow/specs/<epic-id>.md`)
2. **Per-task `done_summary`** with evidence commits (`flowctl show <task> --json`)
3. **Decision-record memory** written during the epic (`.flow/memory/knowledge/decisions/`)
4. **Bug-track memory** auto-captured by Ralph on `NEEDS_WORK → SHIP` (`.flow/memory/bug/`)
5. **Architecture-patterns memory** (`.flow/memory/knowledge/architecture-patterns/`, populated post-fn-40)
6. **Glossary changes** (added terms, renames flagged by plan-sync)
7. **Strategy alignment** (which active tracks this epic served)
8. **Impl-review receipts** (verdict, deferred findings, walkthrough state)
9. **The diff itself** (`git diff $(git merge-base origin/main HEAD)..HEAD`)

`/flow-next:make-pr` walks all nine, structures them into a payload via `flowctl epic export-cognitive-aid <id> --json`, and renders a markdown PR body that:

- Surfaces critical changes (high-churn / cross-module / security-touching / breaking)
- Maps every R-ID in the spec to the task + commit(s) that satisfy it
- Lists decisions made (with alternatives considered) and memory entries left behind
- Notes glossary updates and strategy alignment
- Aggregates open items (spec `## Open Questions` + deferred review findings)
- Calls out where the human should focus (the high-leverage decisions the agent can't self-verify per methodology #4: architecture, intent, security, business correctness)
- Optionally includes mermaid diagrams when the diff crosses module boundaries or changes public interfaces

The skill IS a synthesis step — flowctl provides the structured input via the `epic export-cognitive-aid` plumbing; the skill renders the body and calls `gh pr create`. The host agent's reasoning identifies critical changes directly from the structured payload — no separate cross-model review pass; the harness's own model is the QA layer.

This epic is a **minor bump** — one new skill, one new slash command, one new flowctl subcommand (`epic export-cognitive-aid`), no schema changes.

## Architecture & Data Models

<!-- Source-tag breakdown: ~30% [paraphrase] / ~70% [inferred] -->

```
User invokes /flow-next:make-pr [<epic-id>] [--draft] [--no-mermaid] [--base <ref>] [--memory] [--dry-run]
         │
         ▼
    Skill workflow runs in host agent (no subprocess dispatch except gh)
         │
         ├─ Phase 0: Pre-flight
         │     - Resolve EPIC_ID (explicit arg, else infer from current branch matching .flow/epics/*.json branch_name)
         │     - Resolve BASE (--base flag, else origin/main, else main, else first branch in repo)
         │     - Validate: epic exists, branch ≠ base, ≥1 commit ahead of base, all tasks under epic in `done` status
         │       (warn-and-prompt if some tasks still open; user can proceed or abort)
         │     - Detect existing PR for this branch (`gh pr view --json url` returns OK) — refuse with hint to use
         │       /flow-next:resolve-pr or pass --update flag (deferred to v2; v1 hard-errors)
         │
         ├─ Phase 1: Gather inputs (flowctl epic export-cognitive-aid)
         │     Single flowctl subcommand returns the structured payload (schema below).
         │     Skill orchestrates parallel reads of memory + glossary + strategy + diff stats
         │     into one JSON blob the host agent renders.
         │
         ├─ Phase 2: Build PR body sections
         │     Title + TL;DR + R-ID coverage + Critical changes + Structural changes (mermaid?) +
         │     Decisions + Memory left behind + Glossary/strategy notes + Open items + Where to look.
         │     Host agent's reasoning identifies critical changes directly from the structured payload —
         │     this is where the harness's own model does the heavy lifting.
         │
         ├─ Phase 3: Mermaid generation (skipped if --no-mermaid or no module-boundary signal)
         │     Triggered when diff crosses module boundaries OR adds/removes public exports.
         │     Emits 0-3 codefences (NEVER more — clutter). Hard cap of 12 nodes per diagram.
         │
         ├─ Phase 4: Push branch + create PR
         │     - `git push -u origin HEAD` (skipped if already pushed)
         │     - `gh pr create --title "..." --body - --draft <if open items> < <body>`
         │     - Capture PR URL from output
         │
         └─ Phase 5: Output
               PR URL, footer, next-step hints (/flow-next:resolve-pr <PR#> after feedback).
               Optional: write a knowledge/architecture-patterns memory entry summarizing
               what shipped (gated by --memory flag, default off; user can opt-in for big PRs).
```

### Cognitive-aid input payload (flowctl epic export-cognitive-aid)

The skill calls `flowctl epic export-cognitive-aid <epic-id> --base <ref> --json` once and gets back this shape:

```json
{
  "epic": {
    "id": "fn-N-slug",
    "title": "...",
    "status": "open|done",
    "branch_name": "...",
    "spec_path": ".flow/specs/...",
    "spec_sections": {
      "goal_and_context": "<verbatim section text>",
      "architecture_overview": "<verbatim or first 500 chars>",
      "acceptance_criteria": [
        {"id": "R1", "text": "<criterion text>", "tag": "user|paraphrase|inferred|strategy:track"}
      ],
      "boundaries": ["<bullet 1>", "<bullet 2>"],
      "decision_context": [{"question": "...", "answer": "...", "tag": "..."}],
      "open_questions": ["<question>"]
    }
  },
  "tasks": [
    {
      "id": "fn-N.M",
      "status": "done|open",
      "title": "...",
      "satisfies": ["R1", "R3"],
      "done_summary": "...",
      "evidence": {"commits": ["sha1", "sha2"], "files_touched": ["..."]}
    }
  ],
  "tasks_summary": {
    "total": 0,
    "done": 0,
    "open": 0,
    "uncovered_r_ids": ["R7"]
  },
  "memory_during_epic": {
    "decisions": [{"id": "knowledge/decisions/...", "title": "...", "first_sentence": "...", "alternatives_considered": "..."}],
    "bugs": [{"id": "bug/...", "title": "...", "module": "...", "winning_hypothesis_first_sentence": "..."}],
    "architecture_patterns": [{"id": "knowledge/architecture-patterns/...", "title": "...", "first_sentence": "..."}]
  },
  "glossary_changes": {
    "added": [{"term": "...", "definition_first_sentence": "..."}],
    "renamed": [{"old": "...", "new": "...", "files_updated_count": 0}],
    "removed": ["term-name"]
  },
  "strategy_alignment": {
    "tracks_served": ["track-name"],
    "drift_flagged": [{"track": "...", "reason": "..."}]
  },
  "diff_summary": {
    "base_ref": "origin/main",
    "head_ref": "HEAD",
    "merge_base_sha": "...",
    "files_changed": 0,
    "lines_added": 0,
    "lines_removed": 0,
    "files": [
      {"path": "...", "status": "A|M|D|R", "additions": 0, "deletions": 0, "module": "plugins/flow-next/skills"}
    ],
    "modules_touched": ["plugins/flow-next/skills", "scripts"],
    "cross_module_changes": ["plugins/flow-next/skills/X imports plugins/flow-next/scripts/Y (new)"],
    "public_exports_changed": [{"file": "plugins/flow-next/scripts/flowctl.py", "added": ["cmd_pr_export"], "removed": []}],
    "high_churn_files": [{"path": "...", "additions": 0, "deletions": 0}],
    "security_sensitive_paths": ["scripts/hooks/", ".github/workflows/", "auth/"]
  },
  "review_receipts": [
    {"task_id": "fn-N.M", "verdict": "ship|needs_work", "findings_count": 0, "deferred_findings": []}
  ],
  "deferred_findings": [
    {"path": ".flow/review-deferred/<branch-slug>.md", "task_id": "fn-N.M", "items": []}
  ]
}
```

The host agent reads this payload and renders the PR body. flowctl's job is structured aggregation; the skill's job is markdown synthesis.

### PR body template

```markdown
# <epic title>

<2-line summary derived from Goal & Context first paragraph>

> **Epic:** [<epic-id>](.flow/specs/<epic-id>.md)
> **Branch:** `<branch>` → `<base>`
> **Tasks:** N completed (M open if any — flagged below)
> **R-ID coverage:** N/N satisfied

## TL;DR

- <bullet 1: core change in plain language>
- <bullet 2: secondary change>
- <bullet 3-5 as needed>

## R-ID coverage

| R-ID | Acceptance criterion | Task | Evidence |
|------|----------------------|------|----------|
| R1 | <text, max 120 chars, ellipsis> | [fn-N.1](.flow/tasks/fn-N.1.md) | [`<sha7>`](../../commit/<sha>) |

<If any R-ID has no satisfying task: ⚠️ flagged here>

## Critical changes

<3-7 bullets — derived from diff_summary by host agent reasoning:>

- **High-churn:** `<path>` (+<N>/-<M> lines)
- **Cross-module:** `<from>` now imports `<to>` (new dependency)
- **Public interface:** `<file>` adds `<symbol>` / removes `<symbol>` (potentially breaking)
- **Security-sensitive:** changes to `<path>` (review carefully)
- **Behavior-visible:** changes to `<path>` affect <user-facing surface>

## Structural changes

```mermaid
flowchart LR
  ...
```

<Optional second / third diagram if needed; max 3>

## Decisions made

<From .flow/memory/knowledge/decisions/ entries written during this epic:>

- **<title>** ([<id>](.flow/memory/knowledge/decisions/<file>)) — <first sentence>. Alternatives considered: <one-sentence>.

## Memory left behind

<Future debuggers will find these via `flowctl memory search`:>

- `bug/<category>/<slug>` — <one-line>
- `knowledge/architecture-patterns/<slug>` — <one-line>

## Glossary / strategy notes

<Only emitted when there's content:>

**Glossary:** added `<term>`, renamed `<old>` → `<new>` (<N> files).
**Strategy:** served tracks `<track-1>`, `<track-2>`. <Drift note if applicable>

## Open items

<Spec ## Open Questions + deferred impl-review findings:>

- [ ] <item> — deferred from impl-review of fn-N.M
- [ ] <item> — open question from spec
- [ ] <item> — flagged by epic-review

<If empty: omit section entirely.>

## Where to look

<Methodology #4 — explicit reviewer-focus list. Drawn from spec decision context + diff signals:>

- **Architecture:** `<file:line>` — <load-bearing decision recap>
- **Security:** `<file:line>` — <if security-sensitive paths touched>
- **Business correctness:** `<file:line>` — <if user-facing behavior changed>
- **Performance:** `<file:line>` — <if hot-path touched>

---

<sub>Generated by `/flow-next:make-pr` against epic `<epic-id>` at `<ISO timestamp>`.</sub>
```

### Mermaid generation logic

Diagrams are emitted **only** when the diff signals warrant them. Pure single-file edits get no diagram (clutter > value). The skill's mermaid logic:

**Triggers (any of these → produce a diagram):**

1. **Module-boundary crossings** — `cross_module_changes` non-empty.
2. **Public interface changes** — `public_exports_changed` non-empty.
3. **New top-level directory** — `modules_touched` includes a path that didn't exist on `base_ref`.
4. **Removed top-level directory** — `git diff --diff-filter=D --name-only base..HEAD` includes all files of an entire directory.
5. **>15 files in >3 distinct modules** — high-fan-out epic; an overview helps.

If ZERO triggers fire, skip the entire `## Structural changes` section. Don't emit an empty placeholder.

**Diagram shapes (host agent picks one per trigger):**

| Shape | When |
|-------|------|
| `flowchart LR` | Module-level dependency changes (A → B added/removed). Default for trigger 1. |
| `classDiagram` | Type / class additions / removals (when public_exports_changed includes class symbols). |
| `sequenceDiagram` | New API endpoint or protocol flow (route handlers added). |
| `graph TB` | High-level "epic touches these N areas" overview. Default for trigger 5. |

**Hard caps:**

- **Max 3 diagrams per PR.** More is clutter; reviewer tunes out.
- **Max 12 nodes per diagram.** GitHub's mermaid renderer handles more, but readability collapses past ~12.
- **Max 25 edges per diagram.** Same readability cliff.
- If trigger conditions would produce >3 diagrams, collapse to ONE high-level overview.
- If a diagram would exceed 12 nodes, group by module / abstraction (e.g. "5 scout agents" → one node labeled `scouts (5)`).

**Skip rules:**

- `--no-mermaid` flag → skip Phase 3 entirely.
- Diff is purely additive within one module + <50 LOC → skip.
- Repo has no detectable module structure (no `src/`, `plugins/`, `app/`, etc. — flat layout) → skip.

**Validation:**

The skill emits valid mermaid syntax. Common pitfalls to avoid (the skill prose explicitly warns against these):

- Reserved words as node IDs (`end`, `subgraph`) — must be quoted or renamed.
- Special characters in labels (`(`, `)`, `:` outside link syntax) — must be quoted with `"..."`.
- Cycles in `classDiagram` inheritance — mermaid silently breaks rendering.
- Diagrams over 12K characters — GitHub truncates.

### flowctl epic export-cognitive-aid

New flowctl subcommand at `plugins/flow-next/scripts/flowctl.py`. Signature:

```bash
flowctl epic export-cognitive-aid <epic-id> --base <ref> [--json]
flowctl epic export-cognitive-aid <epic-id> --base <ref> --section <name>  # filter to one section
```

Implementation walks `.flow/`, runs `git diff --stat`, `git diff --name-status`, `git log --oneline base..HEAD`, parses memory entries via existing helpers, and emits the JSON shape above. Heavy-lifting is mechanical (read files, run git, aggregate); this is appropriate flowctl Python territory per the architecture rule (no LLM judgment in the export step itself).

The subcommand is reusable — future skills (post-merge retro, weekly digest) can consume the same export.

### gh pr create invocation

```bash
# Push branch if needed (skip if already up-to-date with origin)
git push -u origin HEAD 2>/dev/null || true

# Determine draft vs ready: draft if open items > 0 OR running under Ralph
DRAFT_FLAG=""
if [[ "$OPEN_ITEMS_COUNT" -gt 0 ]] || [[ -n "${FLOW_RALPH:-}" ]]; then
  DRAFT_FLAG="--draft"
fi

# Create PR with body via heredoc (preserves all formatting including mermaid)
gh pr create --title "$PR_TITLE" $DRAFT_FLAG --body "$(cat <<'PRBODY'
<rendered body from Phase 2-3>
PRBODY
)"
```

**PR title format:** `<epic-title>` if ≤72 chars, else first sentence of Goal & Context truncated to 70 chars + ellipsis. No conventional-commit prefix unless the epic spec opens with one.

## API Contracts

<!-- Source-tag breakdown: ~10% [paraphrase] / ~90% [inferred] -->

### Slash command surface

```bash
/flow-next:make-pr                                    # auto-detect epic from branch
/flow-next:make-pr fn-42-flow-nextmake-pr-pr-as       # explicit epic id
/flow-next:make-pr --draft                            # force draft (overrides auto-detect)
/flow-next:make-pr --ready                            # force non-draft (overrides auto-detect)
/flow-next:make-pr --no-mermaid                       # skip diagrams
/flow-next:make-pr --base origin/develop              # non-default base branch
/flow-next:make-pr --memory                           # also write knowledge/architecture-patterns memory entry summarizing the epic
/flow-next:make-pr --dry-run                          # render body to stdout, do NOT push or create PR
```

### Mode detection

| Mode | When | Behavior |
|------|------|----------|
| Default (interactive) | User at terminal | Preview body via `AskUserQuestion`; user picks `create` / `dry-run` / `edit-body` / `abort`. Edit-body opens body in `$EDITOR` (or shows numbered sections to refine). |
| `--dry-run` | Any | Skip Phase 4 entirely. Print body to stdout. Useful for piping to clipboard or inspection. |
| Ralph mode (`FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` set) | Autonomous | Skill is **NOT Ralph-blocked**. Ralph runs through Phases 0-4 without the AskUserQuestion preview; opens the PR as `--draft` by default (Ralph PRs always draft until human approves). Use case: autonomous loop completes an epic and surfaces the PR for human review. |

### flowctl plumbing

Existing plumbing (no schema changes):
- `flowctl show <epic-id> --json` — returns epic JSON
- `flowctl show <task-id> --json` — returns task JSON with done_summary + evidence
- `flowctl memory list --track <track> --category <cat> --json` — memory entries
- `flowctl memory read <id> --json` — entry body
- `flowctl glossary list --json` — glossary state (for diff vs base)
- `flowctl strategy read --json` — strategy alignment

New plumbing (this epic):
- `flowctl epic export-cognitive-aid <epic-id> --base <ref> [--section <name>] [--json]` — aggregates everything into the schema above

No schema changes. No new memory categories. No new agent definitions.

## Edge Cases & Constraints

<!-- Source-tag breakdown: ~25% [paraphrase] / ~75% [inferred] -->

- **No epic detected.** If neither `$EPIC_ID` arg nor branch-match resolves an epic, exit with a hint: `No epic detected. Pass an epic id (fn-N-slug) or check out a branch matching an epic's branch_name field.`
- **Epic with no tasks.** Empty tasks array. Skill warns + asks user to confirm. Use case: a tiny single-commit epic that didn't go through `/flow-next:plan`. Body still renders (no R-ID coverage table — replaced with a note).
- **Tasks not all done.** Surface count + open task ids; ask user to (a) `--force` proceed, (b) abort and run `/flow-next:work` first.
- **R-ID coverage gaps.** If acceptance criterion has no satisfying task (no task lists it in `satisfies` and no commit-message reference matches), flag with ⚠️ in the coverage table. Don't silently drop.
- **Branch already has an open PR.** v1: hard-error with hint to use `/flow-next:resolve-pr` for review feedback. v2 may add `--update` flag.
- **Branch ahead of base by 0 commits.** Hard-error: `Branch <name> has no commits ahead of <base>. Nothing to PR.`
- **Branch base detection.** Default `origin/main`. If `origin/main` doesn't exist, try `main`, then `origin/master`, then `master`. If none exist, ask user via `--base` flag (Ralph: hard-error).
- **`gh` CLI not installed / not authenticated.** Detect via `gh auth status`; surface install/auth instructions if missing. Don't try to fall back to a manual `git push` workflow.
- **Diff too large to summarize cleanly.** If `files_changed > 100` OR `lines_added + lines_removed > 5000`, the body emits ONE high-level overview diagram + a note: `Large diff (<N> files, <M> lines). Reviewer focus list below highlights load-bearing changes.` The full file list is omitted from the Critical Changes section (only top-10 by churn shown); full list is in `git diff --stat`.
- **Multi-commit branches.** Each task's evidence commits link separately in the R-ID coverage table. The branch may have additional commits not tied to a task (rebases, merge commits, formatting); these are listed under "Other commits" only if non-trivial (>1 line of meaningful change).
- **Squash-merged base.** If the user squashes during merge, the cognitive aid is still useful pre-merge. Post-merge the artefact lives in PR history regardless.
- **Mermaid renderer not available** (forge other than GitHub/GitLab/Gitea). Codefence still shows source. The body has a fallback prose paragraph above each diagram describing the structural change in plain language — diagram is supplementary, not load-bearing.
- **`--memory` flag side effect.** When user passes `--memory`, skill writes a `knowledge/architecture-patterns/` entry summarizing what shipped. Idempotent: rerun adds no second entry (skips if entry already exists for this epic id). Default off because memory entries should be deliberate, not every-PR.
- **Privacy / secret leakage.** Skill must NOT include actual diff content in the body — only file paths, churn counts, and module-level summaries. Diff content goes in the actual PR (GitHub renders it). The body's Critical Changes section never includes raw code snippets.
- **PR body length.** GitHub allows 65536 characters. The skill targets ≤8000 characters for the cognitive aid; longer bodies hurt skim-readability. If aggregation produces >8000, truncate sections in priority order: drop full file list first, then trim TL;DR to 3 bullets, then collapse mermaid to overview-only.

## Acceptance Criteria

- **R1:** Skill at `plugins/flow-next/skills/flow-next-make-pr/SKILL.md` (with `workflow.md`, `phases.md`, `mermaid-rules.md` as needed) implements the five-phase methodology — Phase 0 (pre-flight) → Phase 1 (gather inputs) → Phase 2 (build PR body sections) → Phase 3 (mermaid generation) → Phase 4 (push + create PR) → Phase 5 (output + footer). [paraphrase]
- **R2:** Phase 0 resolves `$EPIC_ID` from explicit arg OR by matching current branch name against `.flow/epics/*.json` `branch_name` field. Validates: epic exists, branch ≠ base, ≥1 commit ahead of base, all tasks `done` (warn-and-prompt if not, hard-error in `--dry-run` is OK; non-dry-run interactive asks the user). Detects existing PR on the branch via `gh pr view --json url` and hard-errors with a hint to use `/flow-next:resolve-pr`. [paraphrase]
- **R3:** Phase 0 base-branch detection cascade: `--base` flag → `origin/main` → `main` → `origin/master` → `master` → ask user (interactive) / hard-error (Ralph). [paraphrase]
- **R4:** Phase 1 calls a single `flowctl epic export-cognitive-aid <epic-id> --base <ref> --json` subcommand (NEW — implemented in this epic) that aggregates the nine input streams (epic spec, tasks, decisions memory, bug memory, architecture-patterns memory, glossary diff, strategy alignment, diff stats, review receipts) into a structured JSON payload matching the schema in Architecture & Data Models. [paraphrase]
- **R5:** `flowctl epic export-cognitive-aid` is implemented as deterministic Python plumbing (no LLM judgment in the export step itself) per the architecture rule. Walks `.flow/`, runs `git diff --stat / --name-status / --diff-filter=`, parses memory frontmatter via existing helpers, runs `git log --oneline base..HEAD` to attribute commits to tasks via the evidence array. Heavy-lifting is mechanical aggregation; the LLM step is in the skill's body-rendering. [paraphrase]
- **R6:** `flowctl epic export-cognitive-aid` accepts `--section <name>` to filter the output to one of: `epic`, `tasks`, `memory`, `glossary`, `strategy`, `diff`, `reviews`. Useful for debugging and for skill prose that wants only one slice. Without `--section`, returns the full payload. [paraphrase]
- **R7:** Phase 2 renders the PR body using the template documented in Architecture & Data Models. Sections in order: Title + summary block + TL;DR + R-ID coverage table + Critical changes + Structural changes (mermaid, conditional) + Decisions made + Memory left behind + Glossary/strategy notes + Open items + Where to look + footer breadcrumb. Sections with no content are omitted entirely (never empty placeholder headings). [paraphrase]
- **R8:** R-ID coverage table maps every R-ID in spec `acceptance_criteria` to the satisfying task(s) (via task `satisfies` frontmatter when present, else by commit-message reference matching), and shows the linked evidence commit. Uncovered R-IDs are flagged with ⚠️ — the skill never silently drops uncovered criteria. Body must explicitly note the gap so the reviewer knows. [paraphrase]
- **R9:** Critical changes section surfaces (in this priority order, identified by host agent reasoning over the structured payload — no second-model review pass) high-churn files (top 5 by `additions+deletions`), cross-module changes (file in module A imports module B for the first time), public interface changes (added/removed exports in index/lib/__init__ files), security-sensitive paths (paths matching `auth/`, `crypto/`, `.github/workflows/`, `scripts/hooks/`, `*.pem`, `secret`/`token`/`credential` filename patterns), behavior-visible changes (paths matching `commands/`, `routes/`, `pages/`, `app/`). Caps at 7 bullets total; collapses if more. [paraphrase]
- **R10:** Phase 3 mermaid generation is gated by the trigger conditions in Architecture & Data Models §Mermaid generation logic (module-boundary crossings, public interface changes, new/removed top-level directory, high-fan-out epic). If zero triggers fire, the entire `## Structural changes` section is omitted — never an empty placeholder. [paraphrase]
- **R11:** Mermaid hard caps enforced: max 3 diagrams per PR, max 12 nodes per diagram, max 25 edges per diagram, max 12K characters per codefence. Logic to collapse / group when caps would be exceeded (e.g. 5 scout agents → one labeled node). [paraphrase]
- **R12:** Mermaid diagram shape selection: `flowchart LR` (default for module-dep changes), `classDiagram` (for class/type changes), `sequenceDiagram` (for new API/protocol flows), `graph TB` (for high-level overviews). Skill prose lists when each shape applies. [paraphrase]
- **R13:** Each mermaid diagram is preceded by a one-paragraph prose summary in plain language describing the structural change. The diagram is supplementary; the prose is the load-bearing description. Forges that don't render mermaid still convey the change via the prose. [paraphrase]
- **R14:** `--no-mermaid` flag skips Phase 3 entirely — no diagrams emitted, prose summaries still produced when triggers would have fired. [paraphrase]
- **R15:** Decisions section enumerates `.flow/memory/knowledge/decisions/` entries written between epic creation timestamp and HEAD. Each entry: title (linked to memory file path) + first sentence of the body + alternatives-considered (if `alternatives_considered` field present in frontmatter). Section omitted if no decisions. [paraphrase]
- **R16:** Memory left behind section enumerates `bug/*` and `knowledge/architecture-patterns/*` entries written during the epic. One line per entry: id + first-sentence summary. Helps future debuggers find what's been captured. Section omitted if empty. [paraphrase]
- **R17:** Glossary / strategy notes section emits only when there's content. Glossary: added terms (term + first-sentence definition), renames (old → new + count of files updated), removals. Strategy: tracks served (from active-tracks parse) + drift notes (when `## Strategy drift flagged for review` is present in spec or sync output). Section omitted entirely if empty. [paraphrase]
- **R18:** Open items section aggregates: spec `## Open Questions` block contents + deferred impl-review findings from `.flow/review-deferred/<branch-slug>.md` + epic-review-flagged items (when `epic-review-status` is `needs_work`). Each item formatted as a markdown checkbox with provenance breadcrumb. Section omitted if all empty. [paraphrase]
- **R19:** Where to look section is the methodology #4 reviewer-focus list — explicit pointers to the high-leverage decisions the agent can't self-verify. Categories: Architecture (load-bearing decisions from spec Decision Context), Security (surfaced when security-sensitive paths touched), Business correctness (when user-facing surfaces — `commands/`, `routes/`, `pages/` — changed), Performance (when hot-path heuristics fire). Each entry: category bold + file:line pointer + one-sentence focus prompt. [paraphrase]
- **R20:** Phase 4 pushes branch to origin (skipped if already up-to-date) and creates PR via `gh pr create --title --body "$(cat <<'PRBODY' ... PRBODY)"` heredoc. Default `--draft` if open items > 0 OR running under Ralph. `--ready` flag forces non-draft; `--draft` flag forces draft regardless. [paraphrase]
- **R21:** PR title format: epic title if ≤72 chars, else first sentence of Goal & Context truncated to 70 chars + ellipsis. No automatic conventional-commit prefix injection — repos with that convention should set it in the epic title or in their templates. [paraphrase]
- **R22:** `--dry-run` flag skips Phase 4 entirely; renders body to stdout. Useful for inspection, for piping to clipboard (`flow-next:make-pr --dry-run | pbcopy`), and for skill smoke tests. [paraphrase]
- **R23:** `--memory` flag (default off) writes a `knowledge/architecture-patterns/` memory entry summarizing what shipped. Idempotent — rerun for same epic does not add a second entry. Off-by-default because memory entries should be deliberate (epics with structural significance), not every-PR. [paraphrase]
- **R24:** Skill is **NOT Ralph-blocked**. Ralph workers can complete an epic, run `/flow-next:make-pr` autonomously, and surface the resulting draft PR for human review. Implementation: detect Ralph (`FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH`) and skip the interactive `AskUserQuestion` preview; force `--draft`; emit PR URL to stdout for the harness. The cognitive aid is for the human reviewer, not the autonomous loop. [paraphrase]
- **R25:** Skill prose includes explicit warnings against the methodology anti-pattern ("Letting the agent open the PR without making the PR reviewable"). Every section's prose explains *why* the section exists and what reviewers do with it — not just how to render it. [paraphrase]
- **R26:** Skill ships fully cross-platform per the canonical-Claude-native + sync-codex.sh rewrite pattern: canonical files use `AskUserQuestion`, `Task`; `scripts/sync-codex.sh` adds the `generate_openai_yaml` call in the workflow section; `REQUIRED_OPENAI_YAML_SKILLS` includes `flow-next-make-pr`. [paraphrase]
- **R27:** Slash command at `plugins/flow-next/commands/flow-next/make-pr.md` mirrors the existing `audit.md` / `prospect.md` shape; supports flags listed in API Contracts. [paraphrase]
- **R28:** Documentation updates: `CHANGELOG.md` entry; `plugins/flow-next/README.md` skills/commands table + count incremented + new section explaining the cognitive-aid concept and how to invoke; `CLAUDE.md` commands list updated; `.flow/usage.md` mentions the new command if it lists commands. [paraphrase]
- **R29:** Smoke test at `plugins/flow-next/scripts/make-pr_smoke_test.sh` exercises `flowctl epic export-cognitive-aid --json` against a fixture epic with: ≥1 task with done_summary + evidence, ≥1 decision memory entry, ≥1 bug memory entry, ≥1 glossary term, populated STRATEGY.md, ≥1 deferred impl-review finding, a multi-file diff with cross-module imports. Asserts the JSON shape matches the Architecture schema, the rendered body contains all expected sections, mermaid codefences are valid syntax, and `--dry-run` produces stdout-only output without creating PRs. [paraphrase]

## Boundaries

- **Out of scope:** Cross-model review of the PR body. The host agent (whichever harness — Claude Code, Codex, Droid) does the critical-stuff identification directly from the structured payload during Phase 2. Adding a second-model pass on top would be over-engineering for this skill: the harness's own model is competent at "what looks important in this diff" given the rich structured input, and forcing every PR through an extra LLM call (~50 PRs/week × N developers) costs more than it pays. If a team wants extra-rigorous review, that's what `/flow-next:impl-review` already provides on the *code itself*; doing it again on the PR description doubles the surface for marginal added safety.
- **Out of scope:** A `--update` flag for updating an existing PR's body. v1 hard-errors if a PR already exists for the branch and points the user at `/flow-next:resolve-pr` for feedback work. v2 may add `--update` once we have a clear use case (e.g. body got stale after pushing more commits to the branch).
- **Out of scope:** Auto-merging the PR. The methodology explicitly reserves merge for human review (step 9). Skill creates the PR and exits — never invokes `gh pr merge`.
- **Out of scope:** Generating mermaid SVGs / images. Codefences are emitted as text; the forge renders. No imagemagick, no plantuml, no mermaid-cli, no Puppeteer. If the forge doesn't render mermaid, the source is still readable in the codefence.
- **Out of scope:** Multi-epic PRs. v1 is one-epic-per-PR. If a branch contains commits across multiple epics, the skill prompts the user to pick which epic to anchor the cognitive aid on. v2 may support multi-epic aggregation.
- **Out of scope:** Conventional Commits prefix injection. Some repos prefer `feat:` / `fix:` / `chore:` prefixes; the skill does NOT auto-add these. Users who want them set them in the epic title or via their team's PR template.
- **Out of scope:** Squash-merge body generation. Some users squash on merge and want a different (shorter) body for the merge commit message. The cognitive aid is the PR body; the squash message is a separate concern (and `gh` handles it).
- **Out of scope:** Generating release-notes / changelog entries. Different audience (users vs. reviewers), different shape. A future skill (`/flow-next:release-notes`) may consume similar inputs but is not bundled.
- **Out of scope:** GitHub Projects / Linear / Jira integration. The skill talks to git + `gh` only. Linking to issue trackers is the user's responsibility (or a future extension).
- **Out of scope:** PR templates. Some repos enforce `.github/pull_request_template.md`. The skill IGNORES the template — its body is the cognitive aid, not the template form. Users who want to combine templates with the cognitive aid can do so manually post-creation, or this becomes a v2 enhancement.
- **Out of scope:** Diff content (raw code) in the PR body. The skill never copies code snippets into the body — file paths, churn counts, and module summaries only. The actual diff is what GitHub renders below the body.

## Decision Context

- **Why standalone, not folded into `/flow-next:work` or `/flow-next:epic-review`?** Three reasons: (1) PR creation is its own SDLC step per the methodology — handover artefact #6 — and deserves its own surface so users invoke it explicitly. (2) Not every epic ends in a PR (some epics are local-only experiments, dev-loop iteration); auto-firing PR creation from work / epic-review would be intrusive. (3) The skill needs the full epic context (all tasks done) — `/flow-next:work` operates per-task. [paraphrase]
- **Why not auto-fire after `/flow-next:epic-review` SHIP?** Same intrusion concern. Some users want to do a manual cleanup pass before opening the PR (commit reorder, message tweaks, branch rename). Auto-firing would force them to dismiss / abort. Standalone slash-command preserves user agency. A future config flag (`config.json` `make-pr.auto-fire-after-epic-review-ship: true`) could opt-in. [paraphrase]
- **Why no cross-model review of the PR body?** Each harness's own model is smart enough to identify critical changes from the structured input payload — running a second model over the body adds latency and cost (one LLM call per PR × N PRs/week × M developers) without proportional safety benefit. The structured input does the heavy lifting: a payload that already enumerates high-churn files, cross-module imports, public-export changes, security-sensitive paths, and deferred review findings makes "what's critical here?" a much easier question for any single competent model. If a team wants extra-rigorous review, `/flow-next:impl-review` already covers the *code* — running it again on the PR body is double-counting. [user]
- **Why is `--memory` opt-in rather than default-on?** Memory-entry inflation concern. If every PR auto-wrote a `knowledge/architecture-patterns/` entry, the memory store would inflate fast — most PRs aren't structurally significant. Off-by-default keeps memory deliberate; user opts-in for epics they want future readers to find via `memory-scout`. [paraphrase]
- **Why is the skill NOT Ralph-blocked when capture / prospect / strategy / diagnose are?** Capture / prospect / strategy decide *what to build*; diagnose's Phase 3 needs a user-checkpoint. PR creation is the *terminus* of an autonomous loop, not a decision point. Ralph workers that complete an epic should be able to surface a draft PR for human review without human intervention — that's the whole point of "Ralph runs autonomously, human reviews PR". Forcing Ralph-block here would break the autonomous-loop terminus. [paraphrase]
- **Why default to `--draft` under Ralph?** Trust calibration. Ralph workers shouldn't open ready-to-merge PRs without human review. Draft PRs surface to the team without auto-notifying for merge-readiness. The user manually marks `Ready` after reviewing. [paraphrase]
- **Why mermaid as text codefences rather than rendered images?** (a) Zero infrastructure cost — no rendering pipeline to install / version / fail. (b) Native rendering on every major forge (GitHub since 2022, GitLab, Gitea, Forgejo). (c) The source IS the documentation — diff-friendly, copy-paste-friendly, future-LLM-readable. (d) Forges that don't render still show readable source. (e) The prose summary above each diagram is the load-bearing description; the diagram is supplementary. No diagram = no rendering = degraded but still functional output. [paraphrase]
- **Why is the export logic (`flowctl epic export-cognitive-aid`) deterministic Python rather than agentic?** Pure aggregation: read files, run git, parse frontmatter, build JSON. No engineering judgment in the export step — that all happens in the skill's body-rendering. Per the architecture rule, mechanical aggregation is flowctl territory; LLM judgment lives in skills. Keeping the export deterministic also makes it reusable from other skills (post-merge retro, weekly digest) and from CI / scripts that don't have an agent in the loop. [paraphrase]
- **Why a single `export-cognitive-aid` subcommand rather than the skill calling many small flowctl commands?** Latency + atomicity. One subprocess call vs. ~15 (memory list + per-entry read × N + glossary + strategy + git diff + git diff --stat + git diff --name-status + epic show + per-task show × N). Single-call also gives a consistent point-in-time snapshot — concurrent file changes during the skill's execution can't corrupt half the payload. [paraphrase]
- **Why is the body capped at ~8000 characters when GitHub allows 65536?** Skim-readability. The whole point of the cognitive aid is that a human can decide where to focus *before* skimming the diff. A 60K-char body defeats the purpose — reviewer scrolls, gives up, opens the diff cold anyway. The 8K cap forces hierarchy: TL;DR + R-ID coverage table + critical changes + (optional mermaid) + decisions + memory + open items + reviewer focus list. Anything that doesn't fit at 8K is collapsed in priority order documented in Edge Cases. [paraphrase]
- **Why no diff content (raw code) in the body?** Two reasons: (1) GitHub already renders the diff below the body — duplication is wasted reviewer attention. (2) Privacy / secret leakage risk: an LLM-generated body that quotes diff content could accidentally surface a secret that the linter caught but the body grabbed. The body talks ABOUT the diff (paths, churn, structure) but never quotes it. [paraphrase]
- **Why ignore PR templates (`.github/pull_request_template.md`)?** v1 simplicity. Templates impose form-filling shape (specific headings, checkboxes, etc.) that competes with the cognitive-aid shape. Reconciling the two well is a separate UX problem. v1 ignores templates and produces the cognitive-aid body; v2 may merge or templatize. Users who need template compliance can post-edit the PR or delegate to v2. [paraphrase]

## Requirement coverage

| R-ID | Task |
|------|------|
| R1  | fn-42.M (TBD — populate via /flow-next:plan) |
| R2  | fn-42.M (TBD) |
| R3  | fn-42.M (TBD) |
| R4  | fn-42.M (TBD) |
| R5  | fn-42.M (TBD) |
| R6  | fn-42.M (TBD) |
| R7  | fn-42.M (TBD) |
| R8  | fn-42.M (TBD) |
| R9  | fn-42.M (TBD) |
| R10 | fn-42.M (TBD) |
| R11 | fn-42.M (TBD) |
| R12 | fn-42.M (TBD) |
| R13 | fn-42.M (TBD) |
| R14 | fn-42.M (TBD) |
| R15 | fn-42.M (TBD) |
| R16 | fn-42.M (TBD) |
| R17 | fn-42.M (TBD) |
| R18 | fn-42.M (TBD) |
| R19 | fn-42.M (TBD) |
| R20 | fn-42.M (TBD) |
| R21 | fn-42.M (TBD) |
| R22 | fn-42.M (TBD) |
| R23 | fn-42.M (TBD) |
| R24 | fn-42.M (TBD) |
| R25 | fn-42.M (TBD) |
| R26 | fn-42.M (TBD) |
| R27 | fn-42.M (TBD) |
| R28 | fn-42.M (TBD) |
| R29 | fn-42.M (TBD) |
