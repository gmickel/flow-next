# /flow-next:make-pr workflow

Execute these phases in order. Each gates on the prior. Stop on user-blocking error — never plow through with bad state.

## Preamble

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODAY="$(date -u +%Y-%m-%d)"
```

`jq`, `python3` (or `python`), `gh`, and `git` must be on PATH. Mode + flags come from the SKILL.md mode-detection block (`DRAFT_FORCE`, `NO_MERMAID`, `WRITE_MEMORY`, `DRY_RUN`, `BASE_REF`, `EPIC_ID`).

If `.flow/` does not exist, print `No .flow/ directory — this command runs inside a flow-next-managed repo.` and exit 1.

---

## Phase 0: Pre-flight

**Goal:** every external dependency is resolved (gh installed + authed; epic id known; base ref valid; branch ahead of base; tasks done; no existing OPEN PR) before any rendering work starts. Phase 0 has the heaviest external-state dependencies; failing fast here keeps Phases 1-4 deterministic.

### 0.0 — Detect Ralph context

Detect once, route deterministically downstream. Per spec R24, the skill is **not** Ralph-blocked — autonomous loops opening draft PRs is the intended use.

```bash
RALPH=0
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
  RALPH=1
fi
```

When `RALPH=1`:

- Phase 0 questions hard-error with non-zero exit + a clear stderr message (no user to ask).
- Phase 4 skips the `AskUserQuestion` preview entirely.
- Phase 4 forces `--draft` regardless of `--ready` (Ralph never opens ready-to-merge PRs).
- Phase 5 emits the PR URL on stdout for the harness to capture.

There is no `FLOW_MAKE_PR_ALLOW_QUESTIONS_IN_RALPH` opt-in. Ralph is deterministic.

### 0.1 — gh pre-flight

`gh` is the only PR-creation primitive the skill supports — no manual `git push` fallback for missing `gh`.

```bash
if ! command -v gh >/dev/null 2>&1; then
  cat <<'EOF' >&2
Error: gh CLI not installed. /flow-next:make-pr requires gh for PR creation.

Install:
  macOS: brew install gh
  Linux: see https://github.com/cli/cli#installation
  Windows: winget install --id GitHub.cli

Then authenticate:
  gh auth login --hostname github.com
EOF
  exit 1
fi

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  cat <<'EOF' >&2
Error: gh CLI not authenticated for github.com. Run:

  gh auth login --hostname github.com

If you already authed and this still fails, check `gh auth status` for hostname mismatches.
EOF
  exit 1
fi
```

### 0.2 — Resolve epic id

Resolution order:

1. **Explicit `$EPIC_ID` argument** — if non-empty after flag parsing, use it directly.
2. **Branch-match** — derive current branch and match against `.flow/epics/*.json` `branch_name` field.
3. **Ask** — interactive only. Ralph hard-errors.

```bash
if [[ -z "$EPIC_ID" ]]; then
  CURRENT_BRANCH=$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || echo "")
  if [[ -n "$CURRENT_BRANCH" ]]; then
    # Match against .flow/epics/*.json `branch_name` field. flowctl's epic store
    # writes branch_name on epic create; jq across all epics finds the match.
    EPIC_ID=$(find "$REPO_ROOT/.flow/epics" -maxdepth 1 -name '*.json' 2>/dev/null \
      | xargs -I{} jq -r --arg b "$CURRENT_BRANCH" \
          'select(.branch_name == $b) | .id' {} 2>/dev/null \
      | head -1)
  fi
fi

if [[ -z "$EPIC_ID" ]]; then
  if [[ "$RALPH" == "1" ]]; then
    echo "Error: no epic id supplied and no .flow/epics/*.json branch_name matches '$CURRENT_BRANCH'. Ralph cannot prompt — pass an explicit epic id." >&2
    exit 2
  fi
  # Interactive: ask via AskUserQuestion.
  # Question: "No epic detected from current branch. Provide an epic id (fn-N-slug) or abort?"
  # Options: 1. Type epic id  2. Abort
  # On "Type epic id" — accept user input, validate via flowctl show.
  : "ask user for EPIC_ID (AskUserQuestion); abort exits 1"
fi
```

Validate the resolved epic exists:

```bash
if ! "$FLOWCTL" show "$EPIC_ID" --json >/dev/null 2>&1; then
  echo "Error: epic '$EPIC_ID' not found in .flow/epics/. Check id with: $FLOWCTL epics" >&2
  exit 1
fi
```

### 0.3 — Base-branch detection cascade

```bash
if [[ -z "$BASE_REF" ]]; then
  for candidate in origin/main main origin/master master; do
    if git -C "$REPO_ROOT" rev-parse --verify --quiet "$candidate" >/dev/null 2>&1; then
      BASE_REF="$candidate"
      break
    fi
  done
fi

if [[ -z "$BASE_REF" ]]; then
  if [[ "$RALPH" == "1" ]]; then
    echo "Error: no base ref detected (origin/main, main, origin/master, master all missing). Pass --base <ref> explicitly." >&2
    exit 2
  fi
  # Interactive: ask user for the base ref via AskUserQuestion. No frozen options —
  # accept a typed branch name; validate via git rev-parse --verify --quiet.
  : "ask user for BASE_REF; on abort exit 1"
fi

# Final validation — base must exist whether detected or supplied.
if ! git -C "$REPO_ROOT" rev-parse --verify --quiet "$BASE_REF" >/dev/null 2>&1; then
  echo "Error: base ref '$BASE_REF' is not a valid git ref. Check with: git rev-parse --verify $BASE_REF" >&2
  exit 1
fi
```

### 0.4 — Branch validity

HEAD must be a real commit, distinct from base, and ahead of base by at least one commit.

```bash
HEAD_SHA=$(git -C "$REPO_ROOT" rev-parse --verify HEAD 2>/dev/null) || {
  echo "Error: HEAD does not resolve to a commit. Repo state is broken; run from a normal branch." >&2; exit 1; }

BASE_SHA=$(git -C "$REPO_ROOT" rev-parse --verify "$BASE_REF" 2>/dev/null)

if [[ "$HEAD_SHA" == "$BASE_SHA" ]]; then
  echo "Error: HEAD and base ($BASE_REF) point at the same commit. Nothing to PR." >&2
  exit 1
fi

# Verify HEAD is ahead of base (base is an ancestor of HEAD).
if ! git -C "$REPO_ROOT" merge-base --is-ancestor "$BASE_REF" HEAD; then
  echo "Error: base ($BASE_REF) is not an ancestor of HEAD. Rebase or pick a different --base." >&2
  exit 1
fi

# Confirm at least one commit exists on the branch ahead of base.
COMMITS_AHEAD=$(git -C "$REPO_ROOT" rev-list --count "$BASE_REF..HEAD")
if [[ "$COMMITS_AHEAD" -lt 1 ]]; then
  echo "Error: HEAD is 0 commits ahead of $BASE_REF. Nothing to PR." >&2
  exit 1
fi
```

### 0.5 — Tasks-done validation

Every task under the epic should be `done` before opening a PR. The cognitive-aid R-ID coverage table assumes done-tasks; in-progress tasks produce gaps.

```bash
EPIC_JSON=$("$FLOWCTL" show "$EPIC_ID" --json)
OPEN_TASKS=$(printf '%s' "$EPIC_JSON" | jq -r '[.tasks[]? | select(.status != "done") | .id] | join(", ")')
OPEN_COUNT=$(printf '%s' "$EPIC_JSON" | jq '[.tasks[]? | select(.status != "done")] | length')
```

| Context | Behavior |
|---------|----------|
| `OPEN_COUNT == 0` | Proceed silently. |
| `OPEN_COUNT > 0` AND `DRY_RUN == 1` | Warn on stderr but proceed (`--dry-run` is for inspection — body should still render). |
| `OPEN_COUNT > 0` AND `RALPH == 1` | Hard-error with the open-task list. Ralph workers should not open PRs for incomplete epics. |
| `OPEN_COUNT > 0` AND interactive | Ask via `AskUserQuestion`: "Tasks not done: `<OPEN_TASKS>`. Proceed anyway / abort and run `/flow-next:work` first?" Lead with abort as the recommendation; user can override. |

```bash
if [[ "$OPEN_COUNT" -gt 0 ]]; then
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "Warning: $OPEN_COUNT task(s) not yet done ($OPEN_TASKS). Continuing because --dry-run." >&2
  elif [[ "$RALPH" == "1" ]]; then
    echo "Error: $OPEN_COUNT task(s) under $EPIC_ID still open ($OPEN_TASKS). Ralph cannot open PRs for incomplete epics." >&2
    exit 2
  else
    : "ask user via AskUserQuestion; on abort exit 1, on proceed continue"
  fi
fi
```

### 0.6 — Existing-PR refusal

**Critical: filter on `.state == "OPEN"`.** A bare `gh pr view --json url 2>/dev/null` returns rc=0 for both CLOSED and MERGED PRs — a "JSON returned = refuse" check would false-positive on reused branches (branch had a previous PR closed without merge, or merged + pushed-again-to). Filter via jq so closed/merged PRs don't trigger refusal.

```bash
EXISTING=$(gh pr view --json url,state,number 2>/dev/null \
  | jq -r 'select(.state == "OPEN") | .url' \
  || true)

if [[ -n "$EXISTING" ]]; then
  cat <<EOF >&2
Error: branch already has an OPEN pull request: $EXISTING

This skill creates new PRs only. To address review feedback on the existing PR,
use:

  /flow-next:resolve-pr

If you want a fresh PR (e.g. the open one is stale), close it manually first:

  gh pr close <number> --comment "Replaced by upcoming /flow-next:make-pr"
EOF
  exit 1
fi
```

`gh pr view` exit 1 with stderr "no pull requests found" = clean to proceed. CLOSED/MERGED PRs with rc=0 are filtered out by the `select(.state == "OPEN")` clause — `EXISTING` will be empty, refusal won't fire.

### 0.7 — Capture pre-flight context for downstream phases

```bash
PHASE0_CONTEXT=$(jq -n \
  --arg epic "$EPIC_ID" \
  --arg base "$BASE_REF" \
  --arg head "$HEAD_SHA" \
  --arg branch "${CURRENT_BRANCH:-$(git -C "$REPO_ROOT" branch --show-current)}" \
  --argjson commits_ahead "$COMMITS_AHEAD" \
  --argjson open_tasks "$OPEN_COUNT" \
  --argjson dry_run "$DRY_RUN" \
  --argjson ralph "$RALPH" \
  --argjson no_mermaid "$NO_MERMAID" \
  --argjson write_memory "$WRITE_MEMORY" \
  --arg draft_force "$DRAFT_FORCE" \
  '{epic:$epic, base:$base, head:$head, branch:$branch,
    commits_ahead:$commits_ahead, open_tasks:$open_tasks,
    dry_run:($dry_run==1), ralph:($ralph==1),
    no_mermaid:($no_mermaid==1), write_memory:($write_memory==1),
    draft_force:$draft_force}')
```

Phases 1-5 read `$PHASE0_CONTEXT` rather than re-deriving values.

### Done when

- `gh` is installed AND authenticated.
- `EPIC_ID` resolves to an epic in `.flow/epics/`.
- `BASE_REF` resolves to a real git ref AND is an ancestor of HEAD with `COMMITS_AHEAD >= 1`.
- Open-task validation passed (silently, with warning, or with explicit user override).
- No OPEN PR exists on the current branch.
- Ralph context captured. `PHASE0_CONTEXT` JSON is built and ready for Phase 1.

---

## Phase 1: Gather inputs (filled by fn-42.3 / fn-42.4)

**Goal:** call `flowctl epic export-cognitive-aid <EPIC_ID> --base <BASE_REF> --json` once and load the structured payload. The schema is documented in the epic spec under "Architecture & Data Models".

This phase is implemented in dependent tasks. Scaffold-task notes:

- Single subprocess call (latency + atomicity per the epic's Decision Context).
- Payload includes: `epic` (spec metadata + R-IDs), `tasks[]` (done summaries + evidence), `memory.{decisions,bugs,patterns}[]` (filtered to entries created or last-touched in the epic timeframe), `glossary.changes[]`, `strategy.tracks[]` + `## Strategy Alignment` block, `diff.{stat,name_status,log}`, `reviews.{deferred,suppressed_count,unaddressed}`.
- Use `--section <name>` if a downstream phase needs only one slice (debugging or partial render).

---

## Phase 2: Render body header sections (fn-42.3)

**Goal:** turn the structured payload from Phase 1 into the **header half** of the PR body — the sections a reviewer reads *first* to decide where to focus. Header half = Title + summary block + TL;DR + R-ID coverage table + Critical changes. The context half (Decisions / Memory / Glossary / Open items / Where to look) lands in fn-42.4 §Phase 2 (cont). The mermaid `## Structural changes` section lands in fn-42.5 §Phase 3.

The host agent's reasoning IS the renderer. **There is no Python renderer to call** — the agent reads the payload and emits markdown directly. flowctl provided the structured input; the skill turns it into prose. This is the "harness's own model is the QA layer" part of the spec.

### 2.0 — Section order (load-bearing)

The body sections appear in this exact order. Skip any section whose source content is empty (see §2.6 Section-omission rule). Never reorder — reviewers learn the shape and skim accordingly.

1. **Title** + summary block (epic id link, branch / base, task counts, R-ID coverage ratio).
2. **TL;DR** — 3-5 plain-language bullets covering the headline change.
3. **R-ID coverage** — table mapping every spec R-ID to satisfying task(s) + evidence commit(s).
4. **Critical changes** — ≤7 bullets, prioritized by churn / cross-module / public-interface / security-sensitive / behavior-visible.
5. **Structural changes** — mermaid codefences + prose summary (filled in fn-42.5 §Phase 3).
6. **Decisions made** — `knowledge/decisions/` entries written during the epic (fn-42.4).
7. **Memory left behind** — `bug/*` + `knowledge/architecture-patterns/*` entries (fn-42.4).
8. **Glossary / strategy notes** — added/renamed terms + tracks served (fn-42.4).
9. **Open items** — spec open questions + deferred review findings + epic-review flags (fn-42.4).
10. **Where to look** — methodology #4 reviewer-focus list (fn-42.4).
11. **Footer breadcrumb** — `Generated by /flow-next:make-pr from <epic-id> against <base-ref> on <YYYY-MM-DD>`.

This task (fn-42.3) is responsible for steps 1-4. Steps 5-11 are owned by other tasks in the epic; the skill scaffold here just commits to the order.

### 2.1 — Title + summary block

**Title** — computed in fn-42.6 from the epic title (truncate to 72 chars + ellipsis if longer; first sentence of `epic.spec_sections.goal_and_context` truncated to 70 + `…` as fallback when epic title is empty). The body itself uses the epic title as a `# <title>` H1.

**Summary block** — a single blockquote directly under the H1, four lines:

```markdown
> **Epic:** [<epic-id>](.flow/specs/<epic-id>.md)
> **Branch:** `<branch>` → `<base>`
> **Tasks:** <done> completed (<open> open if any — flagged in Open items)
> **R-ID coverage:** <covered>/<total> satisfied
```

All four values come from the payload directly:

- `<epic-id>` from `epic.id`
- `<branch>` from `PHASE0_CONTEXT.branch`, `<base>` from `PHASE0_CONTEXT.base`
- `<done>` / `<open>` from `tasks_summary.done` / `tasks_summary.open`
- `<covered>` = `len(acceptance_criteria) - len(tasks_summary.uncovered_r_ids)`; `<total>` = `len(acceptance_criteria)`

A 2-line natural-language summary appears between the H1 and the blockquote, drawn from `epic.spec_sections.goal_and_context` first paragraph, truncated to ~240 characters with sentence-boundary respect. Never invent — if `goal_and_context` is empty the summary is omitted.

### 2.2 — TL;DR composition

Render `## TL;DR` as 3-5 markdown bullets, each one a single-line plain-language statement. Source priority order:

1. **First sentence of `epic.spec_sections.goal_and_context`** — paraphrased into a single bullet; this is the headline change.
2. **Top 5 tasks by lines-changed** (`tasks[].evidence.commits` mapped to `git log` churn — host agent uses the diff's `high_churn_files` as a hint for which tasks shipped the most content). For each surviving task, take `tasks[].done_summary` first sentence, paraphrase to one line.
3. **Stop at 5 bullets total.** If the epic shipped fewer than 4 substantive changes, ship 3 bullets — never pad.

TL;DR rules:

- Bullets are plain English, not jargon; readers include reviewers who didn't write the spec.
- Never include R-IDs in TL;DR bullets — R-IDs go in the coverage table.
- Never quote raw diff content; talk ABOUT the change.
- If a `done_summary` is empty for a task, skip it — don't fabricate.

If `goal_and_context` is empty AND no tasks have `done_summary`, the body is unrenderable — abort with stderr `Empty epic content (no goal_and_context, no done_summary fields populated). Run /flow-next:work to populate task done_summaries first.` exit 1. See §2.7 Abort conditions.

### 2.3 — R-ID coverage table

Render `## R-ID coverage` as a markdown table. Exact column order, exact header text:

```markdown
| R-ID | Acceptance criterion | Task | Evidence |
|------|----------------------|------|----------|
| R1 | <criterion text, ≤120 chars + … if truncated> | [fn-N.M](.flow/tasks/fn-N.M.md) | [`<sha7>`](../../commit/<sha40>) |
| R2 | <…> | [fn-N.K](.flow/tasks/fn-N.K.md), [fn-N.L](.flow/tasks/fn-N.L.md) | [`<sha7>`](../../commit/<sha40>), [`<sha7>`](../../commit/<sha40>) |
| R7 | <…> | ⚠️ uncovered | — |
```

Field rules:

- **R-ID column** — every entry from `epic.spec_sections.acceptance_criteria[].id` in spec order. NEVER renumber; gaps in numbering (R1, R3, R5 — R2 deleted post-creation) are preserved verbatim per the R-ID renumber-forbidden rule.
- **Acceptance criterion column** — `epic.spec_sections.acceptance_criteria[].text` truncated to 120 characters. If truncated, append `…` (single ellipsis character, not three dots). Never edit content; truncation is mechanical at byte boundary respecting word boundaries when feasible.
- **Task column** — derived ONLY from `tasks[].satisfies[]`. For each R-ID, find every task whose `satisfies` array contains that R-ID. Render as a comma-separated list of links: `[fn-N.M](.flow/tasks/fn-N.M.md)`. **Never infer from task title.** Never infer from commit message text. If `tasks[].satisfies[]` is empty for every task → R-ID is uncovered → render `⚠️ uncovered`.
- **Evidence column** — for each linked task, emit `[\`<sha7>\`](../../commit/<sha40>)` for every entry in `tasks[].evidence.commits`. SHAs come from the payload only; never invent. If a task has multiple commits, list all of them comma-separated. If the task has no evidence commits but is `done`, emit `—` (em-dash) in that slot. For uncovered R-IDs, emit a single `—`.

After the table, if `tasks_summary.uncovered_r_ids` is non-empty, append a single italic sentence:

```markdown
⚠️ **<N> uncovered acceptance criterion(a):** R<i>, R<j>, R<k>. Reviewer should confirm these are intentional gaps before merge.
```

This makes the gap explicit — not silently buried in the table. The reviewer's eye lands on the `⚠️` marker and the explanatory line directly under the table reinforces it.

If `tasks_summary.uncovered_r_ids` length equals `len(acceptance_criteria)` (every R-ID uncovered) the body is unrenderable — abort with stderr `Empty R-ID coverage (no tasks satisfy any spec R-ID). Run /flow-next:work or check task satisfies frontmatter.` exit 1. See §2.7.

### 2.4 — Critical changes section (5-tier priority)

Render `## Critical changes` as a bulleted list, **capped at 7 bullets total**. The host agent identifies critical changes by walking `diff_summary` fields in **this exact priority order**, taking bullets in tier order until the cap is hit:

| Tier | Trigger condition | Source field | Bullet template |
|------|-------------------|--------------|-----------------|
| 1 | High-churn files | `diff_summary.high_churn_files[]` (top 5 by `additions+deletions`, already pre-sorted) | `**High-churn:** \`<path>\` (+<additions>/-<deletions> lines)` |
| 2 | Cross-module changes (new dependency edges) | `diff_summary.cross_module_changes[]` (array of strings already shaped as `module-A imports module-B (new)`) | `**Cross-module:** <verbatim entry from array>` |
| 3 | Public interface changes (potentially breaking) | `diff_summary.public_exports_changed[]` (array of `{file, added[], removed[]}`) | `**Public interface:** \`<file>\` adds \`<sym>\` / removes \`<sym>\`` — see weakening rule below |
| 4 | Security-sensitive paths | `diff_summary.security_sensitive_paths[]` (array of paths) | `**Security-sensitive:** changes to \`<path>\` (review carefully)` |
| 5 | Behavior-visible (user-facing surfaces) | `diff_summary.files[]` filtered to paths matching `commands/`, `routes/`, `pages/`, `app/`, `cli/`, `hooks/`, `bin/` | `**Behavior-visible:** \`<path>\` (+<additions>/-<deletions>) — affects <user-facing surface noun>` |

Allocation rule:

1. Walk tiers 1 → 5 in order.
2. Within each tier, take entries in their array order (already pre-sorted by flowctl: tier 1 sorted by churn descending; tier 2 in cross-module-detection order; tier 3 in file-discovery order; tier 4 alphabetical; tier 5 host agent picks the highest-churn matches first).
3. Stop when the bullet count hits 7 — even if higher-priority tiers are exhausted but lower tiers have unused entries. The cap is hard.
4. If `public_exports_changed[].removed[]` is non-empty for any file, that bullet emits FIRST within tier 3 (potentially-breaking changes get reviewer attention before additions).

**Empty-content fallback rule.** If every tier's source array is empty (heuristic: `<5` files in `diff_summary.files[]`, `<50` total LOC across `lines_added + lines_removed`, no module-boundary signal in `cross_module_changes`, no public-export signal in `public_exports_changed`), the section is **still included** with a single lead bullet:

```markdown
- Limited churn — review the R-ID coverage table for surface area and the linked task evidence commits for full context.
```

This is the one section that doesn't honor the §2.6 omission rule — even a tiny PR benefits from explicit "there's no critical-changes signal here" framing rather than a missing heading the reviewer thinks was forgotten.

**No-weakening rule (load-bearing).** Every entry in `public_exports_changed[].removed[]` is **potentially breaking**. The bullet says "potentially breaking" or `removes \`<sym>\`` exactly. Never paraphrase as "non-breaking", "internal-only", "minor", or "trivial". The agent does not have whole-codebase visibility; calling something non-breaking requires a global call-graph the agent doesn't have. The reviewer makes that call.

**File path rule.** Every path in a Critical changes bullet must appear in `diff_summary.files[]`. The agent never invents paths from the spec or from imagined structure. If a tier wants to surface a file that isn't in `diff_summary.files[]`, that bullet is dropped — not approximated.

### 2.5 — Hallucination guardrails (load-bearing for fn-42.3)

Phase 2 body rendering is the surface where hallucination risk peaks: the agent has rich structured input AND open-ended natural-language output, which is exactly the shape that produces fluent-sounding fabrication. These rules are load-bearing — every claim in the rendered body must trace back to a structured field in the export payload. **Honest "unclear" / "uncovered" beats plausible "wrong".**

The 10 rules below are not advisory. They define what the body MAY and MAY NOT contain. The skill prose, smoke tests, and review prompts all reference these rules by number.

1. **No hallucinated file references.** Every `<path>` in the body comes from `diff_summary.files[]`. Never fabricate paths from the spec text, from acceptance criteria, or from intent. If you want to mention a file that isn't in the diff, you can't — drop the claim.
2. **No hallucinated symbol names.** Every `<symbol>` named in Critical changes comes from `diff_summary.public_exports_changed[]`. Never derive from spec language ("the new validate function") if `validate` doesn't appear in the diff signal — that suggests it's an internal helper, not a public export.
3. **No hallucinated SHAs.** Every `<sha>` in the R-ID coverage table comes from `tasks[].evidence.commits[]`. Don't shorten differently than 7 chars; don't fabricate when an evidence array is empty.
4. **No "non-breaking" weakening.** Every `public_exports_changed[].removed` entry is potentially breaking. Never reclassify as "non-breaking", "internal", "minor", "trivial", or "harmless removal." The agent doesn't have global call-graph visibility. Reviewer judgment, not author judgment.
5. **No copy-pasted diff content.** The body talks ABOUT the diff (paths, churn, structure, modules). It NEVER quotes code. GitHub renders the diff below the body — duplication is wasted reviewer attention, AND privacy / secret-leakage risk: an LLM-generated body that quotes diff content could surface a secret the linter caught but the body grabbed.
6. **No inflated scope.** Every claim in the body must trace to either (a) the R-ID coverage table or (b) a task's `done_summary`. If you can't anchor a claim to one of those, drop it. "We also improved overall reliability" with no concrete trace = drop.
7. **No R-ID misattribution.** `tasks[].satisfies[]` is the source of truth. NEVER infer R-ID coverage from task titles ("This task is about validation, must be satisfying R3"). NEVER infer from commit messages alone. Empty `satisfies` → uncovered → ⚠️.
8. **No stale references.** Cross-check against `diff_summary.files[].status`. A file with `status == "D"` (deleted) cannot appear in the body as if it still exists. A file with `status == "R"` (renamed) appears under its new path; the old path is mentioned only if the rename itself is the load-bearing change.
9. **No invented "why".** The Decision Context section in fn-42.4 is a read-only mirror of `.flow/memory/knowledge/decisions/` + the spec's `## Decision Context`. NEVER paraphrase, never extend, never narrate a plausible-sounding rationale to fill a gap. If no decision exists for a structural change, the body says so honestly: `*No decision-track memory entry for this change. Decision context unclear — surface in PR comments if needed.*`
10. **Trace every claim.** The meta-rule: every sentence in the body must trace to a structured field in the export payload (epic / tasks / memory / glossary / strategy / diff / reviews) or to a verbatim spec quote. If you can't point to which field a claim came from, drop the claim.

When data is missing, surface that honestly:

- No `done_summary` for a task → row in TL;DR is dropped, not invented.
- No evidence commits for a task → `—` in the table, not a guess from `git log`.
- No decisions in `memory_during_epic.decisions` → Decisions section says "*No decision-track memory entries for this epic.*" (omission honored per §2.6 — section is dropped entirely if empty per the section-omission rule, BUT if the body still emits the section heading for any reason, an honest empty-state note replaces invented content).

### 2.6 — Section-omission rule

Empty content → omit the entire section heading. Never emit an empty placeholder.

| Section | Emitted when | Omitted when |
|---------|--------------|--------------|
| Title + summary block | Always | Never (if the skill reaches Phase 2 the title is renderable from `PHASE0_CONTEXT`) |
| TL;DR | ≥1 bullet derivable | Aborts via §2.7 if zero bullets derivable |
| R-ID coverage table | ≥1 R-ID in spec | Aborts via §2.7 if every R-ID uncovered |
| Critical changes | Always (with fallback bullet per §2.4) | Never |
| Structural changes (mermaid) | Trigger conditions fire (fn-42.5) | When `--no-mermaid` OR no triggers |
| Decisions made | `memory_during_epic.decisions[]` non-empty (fn-42.4) | Empty array |
| Memory left behind | `memory_during_epic.bugs[]` OR `architecture_patterns[]` non-empty (fn-42.4) | Both empty |
| Glossary / strategy notes | `glossary_changes` non-empty OR `strategy_alignment.tracks_served` non-empty (fn-42.4) | Both empty |
| Open items | spec `## Open Questions` non-empty OR `deferred_findings` non-empty (fn-42.4) | All empty |
| Where to look | ≥1 reviewer-focus pointer derivable (fn-42.4) | None derivable |
| Footer breadcrumb | Always | Never |

The omission rule preserves skim-readability — a heading with no content trains the reviewer to ignore future headings ("oh, /flow-next:make-pr always emits empty sections, I can skip them"). One real signal per heading.

### 2.7 — Abort conditions

The skill aborts before producing a body when the content would be unrenderable:

| Condition | Stderr message | Exit code |
|-----------|----------------|-----------|
| `goal_and_context` empty AND every task has empty `done_summary` | `Empty epic content (no goal_and_context, no done_summary fields populated). Run /flow-next:work to populate task done_summaries first.` | 1 |
| Every R-ID uncovered (`tasks_summary.uncovered_r_ids` length == `len(acceptance_criteria)`) AND `len(acceptance_criteria) > 0` | `Empty R-ID coverage (no tasks satisfy any spec R-ID). Run /flow-next:work or check task satisfies frontmatter.` | 1 |

These are guard conditions, not warnings — a body with empty TL;DR or empty R-ID coverage is the cognitive-aid equivalent of a blank PR description, and shipping it would defeat the skill's purpose.

`acceptance_criteria` legitimately empty (zero R-IDs because the spec is intentionally minimal) is **not** an abort — the R-ID coverage table is omitted via §2.6 and the body proceeds with a TL;DR + Critical changes pair only. This is the small-spec escape hatch.

### Done when

- `## TL;DR` renders 3-5 plain-English bullets sourced from `goal_and_context` + top tasks' `done_summary`, never from invented content.
- `## R-ID coverage` table renders every R-ID with task links + evidence-commit links, with ⚠️ for uncovered and a follow-up sentence reinforcing the gap count.
- `## Critical changes` renders ≤7 bullets in 5-tier priority order (high-churn → cross-module → public-interface → security-sensitive → behavior-visible), with the limited-churn fallback bullet for low-signal diffs.
- All 10 hallucination guardrails (§2.5) hold for the rendered output — every claim traces to a payload field.
- Section-omission rule (§2.6) honored — empty headings never emitted.
- Abort conditions (§2.7) checked before writing any body content; unrenderable bodies exit 1 with a clear stderr message rather than emitting fabricated content.

---

## Phase 2 (cont): Render body context sections (fn-42.4)

**Goal:** turn the structured payload from Phase 1 into the **context half** of the PR body — the sections a reviewer reads *after* deciding where to focus, to anchor judgment in the surrounding intent. Context half = Decisions made + Memory left behind + Glossary / strategy notes + Open items + Where to look. The header half (TL;DR / R-ID coverage / Critical changes) lands in fn-42.3 §Phase 2; the mermaid section lands in fn-42.5 §Phase 3.

These five sections are **read-only mirrors of structured fields**. The host agent never paraphrases, never extends, never narrates a plausible-sounding rationale to fill a gap. The §2.5 hallucination guardrails (esp. rule 9 "no invented why" and rule 10 "trace every claim") apply here with extra force: the context sections are the surface where fluent fabrication is most tempting, because the underlying data (decisions, memory entries, open questions) is already prose-shaped. Treat them as text to reformat, not text to embellish.

### 2.8 — Decisions made section (R15)

Render `## Decisions made` when `memory_during_epic.decisions[]` is non-empty. Each entry from the array becomes one bullet; bullet shape is fixed:

```markdown
- **<title>** ([<id>](.flow/memory/<id>.md)) — <first_sentence>. Alternatives considered: <alternatives_considered>.
```

Field rules:

- **`<title>`** — `decisions[].title` verbatim. No editing, no truncation.
- **`<id>`** — `decisions[].id` verbatim (e.g. `knowledge/decisions/use-deterministic-export-2026-05-07`). Memory IDs are file-path-shaped.
- **Link target** — `.flow/memory/<id>.md`. The `id` already contains the track/category prefix; concatenating with `.flow/memory/` gives a relative path the forge will resolve.
- **`<first_sentence>`** — `decisions[].first_sentence` verbatim. flowctl already extracted this via `_export_first_sentence`. Never re-extract, never paraphrase.
- **`<alternatives_considered>`** — `decisions[].alternatives_considered` from the export. **Caveat: this field arrives as a stringified Python list** (e.g. `"['option-a', 'option-b']"`) because flowctl wraps the frontmatter list with `str()` during export. The host agent renders it readably:
  - String matches `^\[.*\]$` and is non-empty → strip the brackets + quotes, emit as a comma-separated phrase: `option-a, option-b`.
  - String is empty (`""`) or literally `"[]"` → omit the trailing `Alternatives considered: …` clause entirely (don't emit the label with no content).
  - String is plain prose (legacy entries that wrote a sentence rather than a list) → emit verbatim.
- **No truncation.** Decision entries are by-design prose-heavy; reviewer needs the full alternatives list to weigh the choice.

If `memory_during_epic.decisions[]` is empty, the section heading is omitted entirely per §2.6. **No fallback "no decisions" line.** Section either has bullets or doesn't appear.

**What this section MUST NOT do:**

- MUST NOT paraphrase, extend, or rewrite `first_sentence`. Read-only mirror.
- MUST NOT invent decision context for changes that have no memory entry. If a change in the diff lacks a `knowledge/decisions/` entry, the body says nothing about its rationale — the reviewer surfaces it in PR comments if needed.
- MUST NOT add commentary like "this is a good decision" / "the team weighed alternatives carefully". The bullet is `title + id + first_sentence + alternatives` — nothing else.
- MUST NOT include `decision_status` (proposed / accepted / superseded) — v1 keeps the bullet shape narrow. Future enhancement if reviewer feedback wants it.

### 2.9 — Memory left behind section (R16)

Render `## Memory left behind` when `memory_during_epic.bugs[]` OR `memory_during_epic.architecture_patterns[]` is non-empty. Two sub-lists when both are populated; one sub-list when only one is. Heading omitted entirely if both are empty.

Sub-list structure:

```markdown
**Bugs captured during this epic:**

- `<id>` — <winning_hypothesis_first_sentence>
- `<id>` — <winning_hypothesis_first_sentence>

**Architecture patterns captured during this epic:**

- `<id>` — <first_sentence>
```

Field rules:

- **`<id>`** — `bugs[].id` or `architecture_patterns[].id` verbatim, formatted as inline code (so the path is visually distinct from the description and easy to copy for `flowctl memory read <id>`).
- **`<winning_hypothesis_first_sentence>`** — `bugs[].winning_hypothesis_first_sentence` verbatim.
- **`<first_sentence>`** — `architecture_patterns[].first_sentence` verbatim.
- **No file links** — unlike the Decisions section, memory entries here don't link to file paths. Reviewer who wants more reads via `flowctl memory read <id>` (the id is already copy-pasteable). This keeps the section visually scannable; the Decisions section uses links because alternatives-considered context is harder to find without one.
- **No truncation.** First-sentence shapes are already pre-bounded by the `_export_first_sentence` helper.

If only one sub-array is populated, emit only that sub-list with its bold preamble. The bold preambles are load-bearing — they tell the reviewer **why** these entries appear in the PR body (not "look at all the memory we wrote" but "future debuggers searching for these symptoms will find this PR").

**Section purpose framing** — this section answers the methodology's question "what did this epic teach?" Memory entries written during an epic are the most discoverable record of pitfalls, conventions, and patterns established by the work. Surfacing them in the PR body lets the reviewer (a) verify the captured insight is accurate and (b) find the entries later via `memory-scout` without reconstructing the epic from commit history.

**What this section MUST NOT do:**

- MUST NOT paraphrase or expand `winning_hypothesis_first_sentence` / `first_sentence`. Read-only mirror.
- MUST NOT invent memory entries that aren't in the export payload (rule 7 of §2.5 — no fictitious memory IDs).
- MUST NOT include legacy-track entries (`legacy/pitfalls#N`) — those surface in `memory list` but `_export_memory_during_epic` deliberately excludes them. v1 only renders bugs + architecture_patterns from the categorized tree.
- MUST NOT recommend memory-store cleanup ("consider deleting these entries"). That's the job of `/flow-next:audit`, not the PR body.

### 2.10 — Glossary / strategy notes section (R17)

Render `## Glossary / strategy notes` when `glossary_changes` has any non-empty array OR `strategy_alignment.tracks_served[]` is non-empty OR `strategy_alignment.drift_flagged[]` is non-empty. Heading omitted entirely if every contribution is empty.

The section combines two distinct signals (glossary mutation + strategy alignment) under one heading because (a) both are repo-doc plumbing the reviewer typically skims, (b) each is usually 1-3 lines, and (c) two separate empty-most-of-the-time headings train reviewers to stop looking. One combined heading keeps the signal density per heading high.

#### Glossary clauses

Each non-empty array becomes one bold-prefix line:

```markdown
**Glossary:** added `<term>`, `<term>`; renamed `<old>` → `<new>` (<N> files); removed `<term>`.
```

Field rules:

- **`added`** — `glossary_changes.added[]` is an array of `{term, definition_first_sentence}`. Surface only the term (the first-sentence is reserved for `flowctl glossary read <term>`); render as backticked terms, comma-separated.
- **`renamed`** — `glossary_changes.renamed[]` is reserved for v2 per the `_export_glossary_diff` docstring (`renamed detection (heuristic on definition similarity) is a 2026-Q2 stretch goal per the spec; v1 emits an empty list`). v1 will always have an empty rename array; the clause never emits in v1. **Keep the rename clause in skill prose** so v2 doesn't have to re-document the shape — when the export starts populating `renamed[]`, the skill renders without code changes. (Defer-by-prose, not defer-by-omission.)
- **`removed`** — `glossary_changes.removed[]` is an array of strings (term names). Render as backticked terms, comma-separated.
- **Clause omission** — each of the three clauses (added / renamed / removed) is dropped if its source array is empty. The line emits whatever non-empty clauses remain, joined by `;`. If the line would be empty, no glossary line emits.

#### Strategy clauses

Strategy gets one or two lines depending on populated arrays:

```markdown
**Strategy:** served tracks `<track-1>`, `<track-2>`, `<track-3>`.
**Strategy drift:** `<track>` — <reason>; `<track>` — <reason>.
```

Field rules:

- **`tracks_served`** — `strategy_alignment.tracks_served[]` array of strings. Render backticked, comma-separated. If empty array, the served-tracks line is omitted.
- **`drift_flagged`** — `strategy_alignment.drift_flagged[]` is an array of `{track, reason}`. Each entry → `\`<track>\` — <reason>`, joined by `;`. If empty array, the drift line is omitted.
- **Heading-level interaction** — if neither glossary nor strategy contributions emit any line, the entire `## Glossary / strategy notes` heading is omitted. If only one of glossary/strategy emits content, the heading still appears with whatever content there is.

**Section purpose framing** — the methodology's "shared vocabulary survives the team" principle: glossary changes are ratifications of (or departures from) the project's canonical wording, and strategy alignment is the explicit anchor between this epic's work and the repo-wide direction. Reviewer scans this section to catch (a) accidental glossary drift (a renamed term that downstream specs still use), (b) strategy misalignment (an active-track epic that surfaced `## Strategy drift flagged for review` during sync). Both are easy to fix at PR time, much harder to retrofit later.

**What this section MUST NOT do:**

- MUST NOT invent glossary terms not in `glossary_changes`.
- MUST NOT paraphrase `drift_flagged[].reason` — already prose-shaped by sync output / spec authoring.
- MUST NOT recommend strategy edits ("consider revising STRATEGY.md to add this track"). v1 surfaces drift as read-only. The reviewer / user runs `/flow-next:strategy` if they want to act.
- MUST NOT cite STRATEGY.md verbatim — `tracks_served` is the parsed signal; the full strategy doc is not part of the export payload by design (would inflate body for low signal).

### 2.11 — Open items section (R18)

Render `## Open items` when ANY of the three sources below produce content. Section omitted only when ALL are empty.

Three sources, in order — each surfaces in the same checkbox bullet list with provenance breadcrumbs distinguishing origin:

#### Source A — Spec open questions

`epic.spec_sections.open_questions[]` from the export payload (already parsed via `_export_parse_open_questions` in flowctl). Each entry → one bullet:

```markdown
- [ ] <question text> — open question from spec
```

Field rules:

- **`<question text>`** — array entry verbatim (the export already strips `- ` prefix and trailing whitespace).
- **Provenance breadcrumb** — exact phrase ` — open question from spec` appended after the question. The em-dash is significant; reviewer's eye learns the breadcrumb shape.

#### Source B — Deferred impl-review findings (branch-slug sink)

`deferred_findings[]` from the export payload. v1 schema has at most one element with shape `{path: ".flow/review-deferred/<branch-slug>.md", items: [{raw: "- [ ] ..."}]}`. The `items[]` carries no per-task attribution — flowctl wrote the sink keyed by branch slug, not task id. Each `items[].raw` is a verbatim deferred-finding bullet.

Each entry → one bullet:

```markdown
- [ ] <stripped item text> — deferred from impl-review (`<sink-relpath>`)
```

Field rules:

- **`<stripped item text>`** — `items[].raw` with the leading `- [ ] ` (or `- [x] `) marker stripped, so the renderer can re-emit a `- [ ]` checkbox at body level. If `raw` already starts with `- [` then strip that prefix; otherwise emit `raw` verbatim. (The export captures `raw` with its original prefix per the `_export_review_receipts` implementation.)
- **`<sink-relpath>`** — `deferred_findings[0].path` rendered as backticked relative path (e.g. `\`.flow/review-deferred/fn-42-foo.md\``).
- **Provenance breadcrumb** — exact phrase ` — deferred from impl-review (<sink-relpath>)`. Branch-slug sink is the provenance because v1 has no per-task attribution; surfacing the sink path lets the reviewer drill in.
- **Multiple sinks** — schema allows the array to grow if v2 splits per-task, but v1 only ever returns at most one element. Loop over `deferred_findings[]` regardless to be forward-compatible.

#### Source C — Epic-review-flagged items

NOT in the export-cognitive-aid payload (`review_receipts` is empty in v1 per the implementation comment). Read directly from the epic JSON via flowctl:

```bash
EPIC_REVIEW_STATUS=$("$FLOWCTL" show "$EPIC_ID" --json | jq -r '.completion_review_status // "unknown"')
EPIC_REVIEW_AT=$("$FLOWCTL" show "$EPIC_ID" --json | jq -r '.completion_reviewed_at // empty')
```

If `EPIC_REVIEW_STATUS == "needs_work"`, emit a single bullet:

```markdown
- [ ] Epic-review verdict was `needs_work` (last reviewed <EPIC_REVIEW_AT>) — flagged by epic-review
```

Field rules:

- **Provenance breadcrumb** — exact phrase ` — flagged by epic-review`.
- **Findings detail** — v1 surfaces only the verdict + timestamp. The granular findings live in the `/flow-next:epic-review` receipt; reviewer drills in via that surface. v2 may aggregate findings into the bullet once the receipt format is stable.
- **`unknown` / `passed` status** — no bullet emitted. This source contributes content only when the epic-review explicitly flagged needs-work.

#### Section ordering + omission

Bullets emit in source order: A (spec open questions) → B (deferred review findings) → C (epic-review flag). Within each source, preserve the array's natural order (no re-sorting). If all three sources are empty, the heading is omitted entirely per §2.6 — never an empty `## Open items` placeholder.

**Section purpose framing** — the methodology's "explicit deferral over silent omission" principle: things flagged but not yet resolved deserve checkbox visibility, not burial in the spec / sink / receipt. Reviewer scans this section to decide whether the PR is mergeable as-is or whether a follow-up epic / task captures the remaining work. Each provenance breadcrumb tells the reviewer where to dig if they want context.

**What this section MUST NOT do:**

- MUST NOT invent open items not present in the three sources. The body is read-only mirroring.
- MUST NOT collapse multiple deferred findings into a single bullet ("3 deferred findings — see sink"). Each finding gets its own checkbox so reviewers can track resolution per item.
- MUST NOT paraphrase question text. Open questions are already prose-shaped by the spec author; rephrasing introduces drift.
- MUST NOT include findings the reviewer already accepted via `/flow-next:impl-review --interactive` "Acknowledge" — the interactive walkthrough records those separately and they don't appear in the deferred sink.

### 2.12 — Where to look section (R19, refined per practice-scout)

Render `## Where to look` when ANY of the five categories below fire. Heading omitted entirely if no category fires.

This section IS the methodology #4 handover artefact: an explicit reviewer-focus list pointing at the high-leverage decisions the host agent **cannot self-verify**. Where the rest of the body says "here is what changed", Where to look says "here is what *you* should pay attention to, because we cannot judge it from inside".

**Format rule (load-bearing):** every focus prompt is a **question**, not a label. Practice-scout finding: questions activate reviewer cognition more than labels. "**Performance:** `app/server.ts` — Is the new code path on a hot path?" beats "**Performance:** `app/server.ts` — hot path candidate" by a clear margin in reader engagement studies. Skill prose enforces the question-shape across all five categories.

#### Category 1: Architecture

**Trigger:** `epic.spec_sections.decision_context[]` is non-empty (architectural decisions captured in the spec). **Source field:** `decision_context[].question` (the `**bold-prefix**` from the `## Decision Context` bullet) and `decision_context[].answer` (the rest of the bullet).

Bullet shape:

```markdown
- **Architecture:** `<file:line>` — <focus question>
```

Field rules:

- **`<file:line>`** — chosen by the host agent from `diff_summary.files[]` whose path the architectural decision plausibly applies to. If the decision is general (no clear file anchor), emit just the file name without `:line`. If the host can't anchor the decision to a file in the diff, **drop the bullet** rather than invent a path (rule 1 of §2.5).
- **`<focus question>`** — synthesized from the `decision_context[].question` (or the answer's first sentence if question is empty). Must be question-shaped (ends with `?`). Examples: "Does the abstract base class hierarchy hold up if a fourth implementation arrives?", "Is the chosen serialization format forward-compatible with the v2 schema?". Keep one-sentence; never quote the full decision body.
- **Cap** — at most 3 architecture bullets (top-3 most load-bearing decisions, host agent's call). More than 3 buries the signal.

#### Category 2: Security

**Trigger:** `diff_summary.security_sensitive_paths[]` is non-empty.

Bullet shape:

```markdown
- **Security:** `<path>` — Was the trust boundary preserved here?
```

Field rules:

- **`<path>`** — verbatim from `security_sensitive_paths[]`.
- **Question variants permitted** — the host agent picks from a small whitelist of security focus questions based on the path heuristic:
  - Path contains `auth/` / `crypto/` → "Was the trust boundary preserved here?"
  - Path contains `.github/workflows/` → "Does this CI step run with appropriate scope (secrets / permissions)?"
  - Path contains `scripts/hooks/` → "Could this hook be bypassed or made non-executable?"
  - Path contains `*.pem` / `secret` / `token` / `credential` filename patterns → "Is this file safe to commit, or did a real secret leak in?"
  - Default fallback → "Was the trust boundary preserved here?"
- **Cap** — at most 3 security bullets. If more than 3 paths fire, host agent picks the highest-stakes (auth > crypto > workflows > hooks > *.pem).

#### Category 3: Business correctness

**Trigger:** any `diff_summary.files[].path` matches one of the user-facing surface prefixes: `commands/`, `routes/`, `pages/`, `app/`, `cli/`, `hooks/`, `bin/`. (Same prefix list as the Critical changes tier 5 in §2.4, kept identical for consistency.)

Bullet shape:

```markdown
- **Business correctness:** `<path>` — Does this still match the intended user-facing behavior?
```

Field rules:

- **`<path>`** — verbatim from `diff_summary.files[]`.
- **Question variants permitted** — host agent may swap to "Does the user-facing wording / API contract still match the spec?" when the change is in `commands/` / `cli/` (more contract-shaped) vs the default phrasing for `routes/` / `pages/` (more behavior-shaped).
- **Cap** — at most 2 business-correctness bullets (top-2 highest-churn user-facing files). Reviewer doesn't need a list of every touched route; they need 1-2 anchors to start verification from.

#### Category 4: Performance

**Trigger:** any `diff_summary.files[].path` matches hot-path heuristics. Hot-path heuristics in v1:

- File extension matches `.py`/`.ts`/`.tsx`/`.js`/`.jsx`/`.go`/`.rs` AND
- Diff content (host agent's reading of the unified diff for that file) shows new/modified `for`/`while` loops, new SQL/DB-query call sites, new function calls inside React render bodies, new hot-path framework primitives (e.g. `useEffect`/`useMemo` in TSX, `tokio::spawn` in Rust, `goroutine` in Go).

Bullet shape:

```markdown
- **Performance:** `<path>` — Is the new code path on a hot path?
```

Field rules:

- **`<path>`** — verbatim from `diff_summary.files[]`.
- **Question variants permitted** — host agent may sharpen to "Is the new loop bound by a user-controllable input?" when the loop is unbounded; or "Does the new query path introduce an N+1 pattern?" when SQL/DB call sites change.
- **Heuristic scope** — host agent's call. If the diff is small (`< 50 LOC` per the §2.4 limited-churn bullet condition) the heuristic almost never fires; that's intentional. False-positive performance flags are noise.
- **Cap** — at most 2 performance bullets.

#### Category 5: Tests (refined per practice-scout)

**Trigger:** test coverage is thin in the diff. Specifically: `diff_summary.files[]` contains zero files matching `*.test.*` / `*_test.*` / `tests/` / `__tests__/` / `spec/`.

Bullet shape:

```markdown
- **Tests:** No new tests in this PR — what behavior assertion would catch a regression?
```

Field rules:

- **One bullet only** — the trigger is binary (any test files vs none); no per-file enumeration.
- **Question phrasing fixed** — the question is identical regardless of the diff specifics. Reviewer's job is to decide whether the missing-tests fact is acceptable for the change at hand; the skill flags it, the reviewer judges it.
- **Suppress when** — the diff is purely documentation-only (every file in `diff_summary.files[]` matches `*.md` / `docs/`). No tests are expected for docs-only PRs; emitting the bullet is noise.
- **Suppress when** — `diff_summary.files_changed < 3` AND `diff_summary.lines_added + diff_summary.lines_removed < 30`. Trivial-diff PRs (lockfile bump, typo, formatting) don't need test bullets.

#### Category ordering + omission

Bullets emit in category order: Architecture → Security → Business correctness → Performance → Tests. Within each category, preserve the source array's natural order. If no category fires, the heading is omitted entirely per §2.6.

Section-level cap: **at most 8 bullets total across all 5 categories** (3+3+2+2+1 = 11 worst case; 8 keeps the section skim-readable). When the cap would be exceeded, drop bullets in reverse-category order (Tests first if multiple Tests bullets exist — though v1 only emits 1; then Performance; then Business correctness; then Security; finally Architecture). Architecture is the highest-value reviewer-focus signal and never trimmed.

**Section purpose framing** — the methodology's "the agent cannot self-verify high-leverage decisions" principle. Architecture, security boundaries, business contracts, hot-path performance, and test-coverage adequacy are all judgments that require whole-codebase visibility, deployment context, runtime understanding, or organizational knowledge the agent does not have. Surfacing them as questions (not labels) primes the reviewer to actually engage rather than rubber-stamp.

**What this section MUST NOT do:**

- MUST NOT use labels instead of questions. Every focus prompt ends with `?`.
- MUST NOT invent file paths or line numbers (rule 1 of §2.5). Every `<path>` must appear in `diff_summary.files[]`.
- MUST NOT add categories beyond the 5 documented (Architecture / Security / Business correctness / Performance / Tests). v1 keeps the surface narrow; v2 may add Documentation, Migration, Observability if reviewer feedback wants them.
- MUST NOT pre-judge the answer to its own questions ("**Performance:** `app/server.ts` — Is the new code path on a hot path? **Probably not.**"). The agent doesn't have the visibility to judge; the reviewer does.
- MUST NOT cap bullets by guessing at importance — use the documented per-category caps + section-level cap. Determinism beats intuition for body-rendering.

### 2.13 — Section-omission rule (extended for context sections)

The §2.6 omission rule extends to all five context sections. Recap with the additions:

| Section | Emitted when | Omitted when |
|---------|--------------|--------------|
| Decisions made | `memory_during_epic.decisions[]` non-empty | Empty array |
| Memory left behind | `memory_during_epic.bugs[]` OR `architecture_patterns[]` non-empty | Both empty |
| Glossary / strategy notes | `glossary_changes` has any non-empty array OR `strategy_alignment.tracks_served` non-empty OR `strategy_alignment.drift_flagged` non-empty | All empty |
| Open items | spec `open_questions` non-empty OR `deferred_findings` non-empty OR `completion_review_status == "needs_work"` | All empty |
| Where to look | ≥1 of the 5 categories fires | None fire |

The rule preserves skim-readability: a heading with no content trains the reviewer to ignore future headings. One real signal per heading.

### 2.14 — Honest-empty-state escape hatch

The §2.5 rule 9 ("no invented why") means the agent never narrates rationale to fill empty Decisions / Open items / Where to look. But the user might still want to know why a section is missing. The skill handles this by **never emitting an honest-empty-state line in the body** — the body is silent on missing sections, and the reviewer who notices an absent section infers correctly: no decisions captured (run `/flow-next:audit` to verify), no open items flagged, no high-leverage focus signals fired.

This is the explicit choice the §2.5 hallucination guardrails force. Body content is structured-mirror only; the absence of a section is itself the signal. **Do not emit sentinel lines like "*No decisions for this epic*" or "*No open items*"** — those clutter the body without adding signal, and create the misleading impression that the skill ran some search and confirmed empty (when it just read empty arrays).

The one exception is the §2.4 Critical changes "Limited churn" fallback bullet — that one stays because Critical changes always renders (so there's no omission to infer from), and the bullet tells the reviewer where to look instead.

### Done when

- `## Decisions made` renders one bullet per `memory_during_epic.decisions[]` entry, with title + memory link + first sentence + alternatives-considered (parsed from stringified-list shape). Section omitted entirely when array empty.
- `## Memory left behind` renders bug + architecture-pattern sub-lists with bold preamble per sub-list. Section omitted when both arrays empty. One sub-list shown when only one populated.
- `## Glossary / strategy notes` renders glossary clauses (added / renamed-deferred-to-v2 / removed) and strategy clauses (tracks served / drift flagged). Each clause omits when its source array is empty; section heading omits when all contributions empty.
- `## Open items` aggregates spec open questions + branch-slug-sink deferred findings + epic-review needs-work flag, each as a checkbox bullet with provenance breadcrumb. Section omitted when all three sources empty.
- `## Where to look` renders questions (not labels) across 5 categories: Architecture / Security / Business correctness / Performance / Tests. Each category's trigger condition references concrete payload signals. Per-category cap (3/3/2/2/1) + section-level cap (8) enforced. Section omitted when no category fires.
- All five sections honor the §2.5 hallucination guardrails: no invented file paths, no fabricated decisions, no synthesized open items, no editorialized rationale.
- Each section has its "What this section MUST NOT do" callout in the rendered prose. Echo-chamber risk mitigated via explicit boundaries.
- §2.14 honest-empty-state rule honored: no sentinel "*No decisions*" / "*No open items*" lines emitted. Absence of section IS the signal.

---

## Phase 3: Mermaid generation (fn-42.5)

**Goal:** when the diff signals warrant it, emit a `## Structural changes` section with one to three mermaid codefences, each preceded by a one-paragraph prose summary in plain language. The diagrams are supplementary; the prose is load-bearing — forges that don't render mermaid still convey the change. When triggers don't fire OR `--no-mermaid` is set, the section is omitted entirely (never an empty placeholder).

The host agent reads `mermaid-rules.md` (sibling file in this skill) before emitting any codefence and validates each rendered diagram against the §6 checklist there. **No deterministic Python renderer.** flowctl's `epic export-cognitive-aid` payload provides the structured signals (`cross_module_changes`, `public_exports_changed`, `modules_touched`, `diff_summary.files`); the agent picks shape, picks nodes, emits codefence, validates.

### 3.0 — `--no-mermaid` short-circuit

Phase 3 is bypassed entirely when `$NO_MERMAID == 1`. **No diagrams emitted.** Prose summaries are also skipped — Phase 3's whole job is the diagram + prose pair, and emitting prose without diagrams under `--no-mermaid` produces a degenerate section that confuses the reader ("why is there structural-change prose with no structural diagram?").

```bash
if [[ "$NO_MERMAID" == "1" ]]; then
  : "skip Phase 3 entirely; the rendered body has no ## Structural changes heading"
  return 0  # or equivalent skip control in the host agent's render loop
fi
```

R14 invariant: `--no-mermaid` produces a body with NO `## Structural changes` section, regardless of how many trigger conditions would have fired.

### 3.1 — Trigger evaluation (5 conditions, ANY fires → emit section)

The host agent evaluates the five trigger conditions below against the export payload. If **any** fires, Phase 3 produces a `## Structural changes` section. If **none** fire, the section is omitted (no heading, no prose, no diagrams).

| # | Trigger | Source field | Default shape (if this is the only trigger) |
|---|---------|--------------|---------------------------------------------|
| 1 | `cross_module_changes[]` non-empty (new dependency edges between modules) | `diff_summary.cross_module_changes[]` | `flowchart LR` |
| 2 | `public_exports_changed[]` non-empty (added or removed public symbols) | `diff_summary.public_exports_changed[]` | `flowchart LR` if function-shaped; `classDiagram` if class-shaped; `sequenceDiagram` if route-handler-shaped |
| 3 | New top-level directory (file added in path that didn't exist on `base_ref`) | `diff_summary.modules_touched[]` cross-checked against `git ls-tree $BASE_REF --name-only` | `graph TB` |
| 4 | Removed top-level directory (all files of dir in `--diff-filter=D`) | `diff_summary.files[]` filtered to `status == "D"` and grouped by top-level dir | `graph TB` |
| 5 | High-fan-out epic — `>15 files in >3 distinct modules` | `len(diff_summary.files) > 15 AND len(diff_summary.modules_touched) > 3` | `graph TB` |

When **multiple triggers fire**, the host agent picks shape per the diagram (one diagram per logical concern) but stays under the §3.2 caps. Triggers 1+2 commonly co-occur (a refactor that adds a new module and exports new functions from it) — the agent emits one `flowchart LR` showing both the new module and its imports.

### 3.1a — Skip rules (within trigger evaluation)

Even when a trigger fires, Phase 3 is **skipped** (section omitted, no diagrams, no prose) when any of these apply:

- **Pure additive within one module + <50 LOC.** Tiny additions get a critical-changes bullet, not a diagram. Heuristic: `len(diff_summary.modules_touched) == 1 AND lines_added < 50 AND lines_removed == 0`.
- **Repo has no detectable module structure.** Flat-layout repos (no `src/`, `plugins/`, `app/`, `lib/`, `pkg/`, `cmd/`, `internal/`, `cli/`, `routes/`, `commands/`, `skills/`, `agents/`) — diagrams of "the whole repo" are noise. Heuristic: `diff_summary.modules_touched[]` contains only the empty-string root or only single-segment paths that aren't in the known-module-prefix list.
- **No-mermaid override.** The `--no-mermaid` flag short-circuited at §3.0 — covered there but recapped here for completeness.

When skip rules engage, the host agent emits a stderr breadcrumb: `Phase 3 skipped: <reason>`. Useful for the user to debug "why didn't I get a diagram?" without re-running.

### 3.2 — Hard caps (enforce on every diagram)

| Cap | Value | Enforced where |
|-----|-------|----------------|
| Diagrams per PR | 3 | When more than 3 triggers would emit, collapse to **one** `graph TB` overview |
| Nodes per diagram | 12 | When a diagram would exceed, group by module/abstraction (`scouts (5)` instead of five sibling nodes) |
| Edges per diagram | 25 | Same readability cliff as nodes; group when exceeded |
| Characters per codefence | 12,000 | Count chars between opening ` ```mermaid ` and closing ` ``` `; collapse / split when above |

**Allocation rule when triggers exceed 3 diagrams:**

```
Triggers 1+2 fire (cross-module + public exports) → emit 1 flowchart LR combining both
Triggers 3+4 fire (new dir + removed dir) → emit 1 graph TB showing both as additions/removals
Trigger 5 fires alone → emit 1 graph TB overview
Triggers 1+2+3 fire → 1 flowchart LR + 1 graph TB (still under cap)
Triggers 1+2+3+5 fire → 1 graph TB overview only (cap collapses 4 candidate diagrams to one)
```

The collapse-to-one rule prefers `graph TB` when the alternative is more than 3 separate diagrams — overview beats fragmented detail.

**Node-cap grouping rule:** when a flowchart or classDiagram would have >12 nodes, group siblings by abstraction. `flowchart LR` example:

````
Bad (15 nodes):
  skill --> agent_A
  skill --> agent_B
  skill --> agent_C
  skill --> agent_D
  skill --> agent_E
  ... (11 more)

Good (3 nodes):
  skill --> scouts["scouts (5)"]
  skill --> workers["workers (3)"]
  skill --> validators["validators (2)"]
````

The grouped label keeps the fan-out signal without burying it in 15 visually-similar nodes.

### 3.3 — Shape selection per diagram

The host agent picks shape from the four documented in `mermaid-rules.md` §3:

| Shape | When |
|-------|------|
| `flowchart LR` | Module-level dependency changes (default for trigger 1). Function-shape additions in `public_exports_changed[]`. |
| `classDiagram` | Type / class additions or removals (when `public_exports_changed[]` includes class symbols — e.g. `class Foo`, `class Bar(Base)`). |
| `sequenceDiagram` | New API endpoint or protocol flow (route handlers added — paths in `diff_summary.files[]` matching `routes/`, `handlers/`, `api/`, route-definition keywords in changed-file content). |
| `graph TB` | High-level "epic touches these N areas" overview (default for trigger 5; default when collapsing 4+ diagrams to one). |

**Rule of thumb:** if you can't decide between `flowchart LR` and `graph TB`, pick `flowchart LR` for "A depends on B" stories and `graph TB` for "epic touched these areas" stories. The reader's mental model is different — left-to-right reads as flow, top-to-bottom reads as decomposition.

### 3.4 — Prose-summary-precedes-diagram rule (R13, load-bearing)

**Every** mermaid codefence is preceded by a one-paragraph prose summary in plain language, three to five sentences, anchored to file paths from `diff_summary.files[]`. The diagram is supplementary; the prose is load-bearing.

This serves two readers:

1. **Forges that don't render mermaid** (older self-hosted Gitea / Bitbucket / GitHub Enterprise). The prose preserves the structural-change signal even when the codefence renders as a code block.
2. **Reviewers who skim diagrams.** A diagram is a glance, not a read. The prose tells the reviewer what they're looking at and why.

**Pattern:**

```markdown
## Structural changes

[Paragraph 1: 3-5 sentences in plain language describing what changed structurally
and why it matters. Anchored to file paths from `diff_summary.files[]`. No jargon.]

​```mermaid
[diagram 1]
​```

[Paragraph 2 (only if more than one diagram): same shape — plain-language structural
description, anchored to paths.]

​```mermaid
[diagram 2]
​```
```

**Prose rules:**

- **Three to five sentences.** Shorter = doesn't justify a diagram; longer = the diagram itself becomes redundant.
- **Plain language.** No jargon ("the IoC container ratifies the dependency injection contract" — no). The reader includes reviewers who didn't write the spec.
- **Anchored.** Every file path mentioned in the prose appears in `diff_summary.files[]`. Same hallucination guardrail as Critical changes (rule 1 of §2.5).
- **Self-contained.** If you removed the diagram, the prose alone should still convey the structural change.
- **Not a caption.** Don't write "Figure 1: Module dependencies." Write the explanation directly.
- **Never quote diff content.** Same rule as the rest of the body — paths, churn, modules; no code.

When `--no-mermaid` is set the section is omitted entirely (R14, §3.0); prose summaries are NOT emitted standalone — they exist to frame the diagrams, not replace them. (See §3.0 for the rationale.)

### 3.5 — Pre-emission validation (each codefence)

Before committing a codefence to the body, the host agent runs the `mermaid-rules.md` §6 validation checklist on the rendered output. **If any check fails, re-render with the issue corrected.** Do NOT emit a known-broken diagram and hope the reviewer catches it — mermaid breaks silently (the codefence renders as code, not as a diagram), so the reviewer's "the diagram looks weird" feedback is the only signal.

The `mermaid-rules.md` §6 checklist (full text in the ref file — recapped here):

1. Quotes balanced.
2. No bare reserved word (`end`, `default`, `subgraph`, `class`, `state`, `direction`, `click`, `style`, `o`, `x`) as a node id.
3. No emoji in labels.
4. No MathJax / LaTeX syntax.
5. No relative or internal-anchor links in `click` directives.
6. classDiagram: no inheritance cycles.
7. flowchart: arrow-character preference (`-->` / `-.->` / `==>` over `--o` / `--x`).
8. Total chars ≤12K per codefence.

**Re-render loop:** if validation fails, the agent identifies which rule failed, applies the fix from the ref file (e.g. rule 1 says "quote labels containing parens" — agent re-renders with `A["Label with (parens)"]` instead of `A(Label with parens)`), then re-runs the checklist. Loop until all 8 rules pass. **Do not emit a partial fix and proceed.**

### 3.6 — Section omission

When zero triggers fire (§3.1) OR a skip rule engages (§3.1a) OR `--no-mermaid` is set (§3.0), the entire `## Structural changes` heading is omitted. **Never an empty heading.** This is the same §2.6 omission rule the rest of the body honors — empty headings train reviewers to skip future headings.

Phase 3 has no fallback bullet equivalent to Critical changes' "Limited churn" line. Critical changes always renders because the section is mandatory; Structural changes is optional. The signal of "no diagram" is the absence of the heading; reviewers who notice the absence infer correctly: no module-boundary, no public-interface, no fan-out — the diff is structurally local.

### 3.7 — Hallucination guardrails (Phase 3 specifics)

The §2.5 hallucination guardrails apply to Phase 3 with these specific reinforcements:

- **No invented modules.** Every node in a diagram representing a module must correspond to a path in `diff_summary.modules_touched[]` or to a path in `diff_summary.files[]`. **Never** invent a "Helper module" that doesn't appear in the diff.
- **No invented edges.** Every edge in `flowchart`/`classDiagram` must correspond to a real signal: an entry in `cross_module_changes[]` (for "A imports B"), or a real composition relationship visible in `public_exports_changed[]` content, or a route → handler relationship visible in the diff. **Never** infer a `A --> B` edge from "it would make sense if A used B."
- **No invented symbol names.** Class members in `classDiagram` come from `public_exports_changed[].added[]` only. Never derive from spec language.
- **No "for clarity" embellishment.** If a diagram has 6 real nodes and the agent thinks "adding 2 more would explain it better" — don't. The 6 are what changed. Adding context nodes that didn't change in this diff dilutes the signal.

When in doubt: **fewer nodes, fewer edges, more honest.** A diagram with 4 nodes and 3 edges that all trace to the diff is a better cognitive aid than one with 12 nodes where 6 of them are inferred context.

### Done when

- `--no-mermaid` short-circuits before any trigger evaluation; the body has no `## Structural changes` heading.
- Trigger evaluation walks the 5 conditions and the 3 skip rules; emits Phase 3 only when ≥1 trigger fires AND no skip rule applies.
- Hard caps enforced (max 3 diagrams, max 12 nodes, max 25 edges, max 12K chars per codefence). Excess collapses to a `graph TB` overview; node excess groups by module/abstraction.
- Shape selection picks from the 4 documented shapes (`flowchart LR` / `classDiagram` / `sequenceDiagram` / `graph TB`) per the §3.3 rules.
- Every codefence is preceded by a 3-5 sentence plain-language prose summary anchored to `diff_summary.files[]` paths. The diagram is supplementary; prose is load-bearing.
- Each codefence passes the `mermaid-rules.md` §6 validation checklist (8 rules) before being emitted. Re-render loop on any failure.
- Section omission honored: zero triggers OR skip rule OR `--no-mermaid` → no `## Structural changes` heading at all.
- Hallucination guardrails honored: no invented modules / edges / symbols; "fewer nodes, more honest" over "context nodes for clarity."

---

## Phase 4: Push + create PR (fn-42.6)

`git push -u origin HEAD`, `gh pr create`, draft/ready logic, `--dry-run` short-circuit, Ralph behavior, `--memory` side effect. Filled in fn-42.6.

## Phase 5: Output + footer (fn-42.6)

Emit PR URL, print breadcrumb, optional memory write. Filled in fn-42.6.

---

## Manual smoke (Task 2 acceptance)

The skill itself is markdown — no unit-test surface. Phase 0 validation is exercised via the smoke test (fn-42.7) and by manual invocation in a real session. Expected behavior:

- `command -v gh` missing → exit 1 with install instructions.
- `gh auth status` failing → exit 1 with login instructions.
- `--base <bad-ref>` → exit 1 with `git rev-parse --verify` failure message.
- Branch with no `branch_name` match in any `.flow/epics/*.json` AND no positional epic id → interactive `AskUserQuestion`; Ralph hard-errors with exit 2.
- Tasks not all done + interactive → `AskUserQuestion` proceed/abort; Ralph exits 2; `--dry-run` warns and continues.
- Branch with an OPEN PR → exit 1 with `/flow-next:resolve-pr` hint.
- Branch with a CLOSED or MERGED PR (no OPEN) → continues cleanly. **This is the load-bearing check** — fn-42 spike validated empirically that bare `gh pr view --json url` rc=0 for closed/merged PRs would false-positive without the `select(.state == "OPEN")` filter.
- Branch with no PR history at all (`gh pr view` exits 1) → continues cleanly.
- Ralph mode (`FLOW_RALPH=1`) → no `AskUserQuestion` calls in Phase 0; deterministic exit codes on missing context.
