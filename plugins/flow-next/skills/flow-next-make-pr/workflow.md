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

Decisions, Memory, Glossary/strategy, Open items, Where to look. Filled in fn-42.4.

## Phase 3: Mermaid generation (fn-42.5)

Trigger gating, hard caps, fallback prose. Filled in fn-42.5. The `mermaid-rules.md` ref file (R10-R14) is also written in fn-42.5.

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
