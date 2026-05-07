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

TL;DR, R-ID coverage table, Critical changes. Filled in fn-42.3.

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
