# /flow-next:make-pr workflow

Execute these phases in order. Each gates on the prior. Stop on user-blocking error — never plow through with bad state.

## Preamble

```bash
set -e
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODAY="$(date -u +%Y-%m-%d)"
```

`jq`, `python3` (or `python`), `gh`, and `git` must be on PATH. Mode + flags come from the SKILL.md mode-detection block (`DRAFT_FORCE`, `NO_MERMAID`, `WRITE_MEMORY`, `DRY_RUN`, `BASE_REF`, `SPEC_ID`, `AUTONOMOUS`).

If `.flow/` does not exist, print `No .flow/ directory — this command runs inside a flow-next-managed repo.` and exit 1.

---

## Phase 0: Pre-flight

**Goal:** every external dependency is resolved (gh installed + authed; spec id known; base ref valid; branch ahead of base; tasks done; no existing OPEN PR) before any rendering work starts. Phase 0 has the heaviest external-state dependencies; failing fast here keeps Phases 1-4 deterministic.

**Fence discipline (fn-110):** on the happy path Phase 0 runs as exactly THREE bash fences — §0.0–0.1 (context + gh), §0.2–0.4 (spec id, base ref, branch validity), §0.5–0.7 (single `flowctl show` capture + tasks-done + existing-PR + context). The subsection headers below describe the parts of each fence; do not split them back into per-subsection calls. **Interactive-ask exemption:** a Bash fence cannot pause for `plain-text numbered prompt`. When the §0.2–0.4 fence prints a `NEED_INPUT:` line and exits, ask the user OUTSIDE the fence, then RE-RUN that same fence with the supplied `SPEC_ID` / `BASE_REF` preset — the re-run does not count against the three-fence happy path (Ralph/autonomous never reaches it; those contexts hard-error inside the fence instead).

### 0.0 — Detect Ralph / autonomous context

Detect once, route deterministically downstream. Per spec R24, the skill is **not** Ralph-blocked — autonomous loops opening draft PRs is the intended use.

`AUTONOMOUS` comes from SKILL.md mode detection (`mode:autonomous` token or `FLOW_AUTONOMOUS=1`). It is a separate flag — autonomous drivers (e.g. /flow-next:pilot) are NOT Ralph; neither signal here may ever set `RALPH`, and `FLOW_AUTONOMOUS` activates no ralph-guard hooks.

When `RALPH=1` or `AUTONOMOUS=1`:

- Phase 0 questions hard-error with non-zero exit + a clear stderr message (no user to ask in an autonomous context). (Interactive mode resolves the same gaps with its usual Phase 0 info prompts — not a confirm gate.)
- Phase 4 forces `--draft` regardless of `--ready` (autonomous loops never open ready-to-merge PRs) — the one autonomous-vs-interactive difference now that the confirm gate is gone for both.
- **Ralph only** (`RALPH=1`): Phase 5 emits the `PR_URL=` line on stdout for the harness to capture.
 This and every receipt/harness semantic stay keyed on `RALPH` alone — `AUTONOMOUS` never triggers them.

There is no `FLOW_MAKE_PR_ALLOW_QUESTIONS_IN_RALPH` opt-in. Ralph is deterministic.

### 0.1 — gh pre-flight

`gh` is the only PR-creation primitive the skill supports — no manual `git push` fallback for missing `gh`.

Skip both checks under `--dry-run`. Rationale: dry-run renders the PR body to stdout and exits before any `git push` / `gh pr create` (Phase 4.0), so requiring `gh` to be installed + authed there blocks the documented inspection path on machines / CI jobs that only want to preview the body. The same checks fire on the real path because Phase 4.6 invokes `gh pr create` unconditionally.

```bash
# --- §0.0: Ralph / autonomous context ---
RALPH=0
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
 RALPH=1
fi

# --- §0.1: gh pre-flight (skipped under --dry-run) ---
if [[ "$DRY_RUN" != "1" ]]; then
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
fi
```

### 0.2 — Resolve spec id

Resolution order:

1. **Explicit `$SPEC_ID` argument** — if non-empty after flag parsing, use it directly.
2. **Branch-match** — derive current branch and match against `.flow/specs/*.json` `branch_name` field. Markdown sidecars live at `.flow/specs/<id>.md`. (Pre-1.0 `.flow/epics/` repos: port first per `.flow/usage.md` "Pre-1.0 layout porting".)
3. **Ask** — interactive only. Ralph hard-errors.

### 0.3 — Base-branch detection cascade

Cascade: `--base` → `origin/main` → `main` → `origin/master` → `master` → ask (interactive) / exit 2 (Ralph/autonomous); the detected-or-supplied ref is then validated via `git rev-parse --verify --quiet`.

### 0.4 — Branch validity

HEAD must be a real commit, distinct from base, share a merge-base with base, and have at least one commit since that merge-base. **The base is NOT required to be an ancestor of HEAD** — feature branches commonly fork from older `main` while `origin/main` advances; `gh pr create` happily handles this case (GitHub computes the diff against the merge-base, not against `BASE_REF` head). The strict-ancestor check would falsely reject the everyday "branch is behind base on linear history but has its own commits" scenario.

The combined §0.2–0.4 fence:

```bash
# --- §0.2: resolve spec id ---
if [[ -z "$SPEC_ID" ]]; then
 CURRENT_BRANCH=$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || echo "")
 if [[ -n "$CURRENT_BRANCH" ]]; then
 # Match against `.flow/specs/*.json` `branch_name` field. flowctl's spec
 # store writes branch_name on spec create; jq across specs/ finds the match.
 SPEC_ID=$(
 find "$REPO_ROOT/.flow/specs" -maxdepth 1 -name '*.json' 2>/dev/null \
 | xargs -I{} jq -r --arg b "$CURRENT_BRANCH" \
 'select(.branch_name == $b) | .id' {} 2>/dev/null \
 | head -1)
 fi
fi

if [[ -z "$SPEC_ID" ]]; then
 if [[ "$RALPH" == "1" || "$AUTONOMOUS" == "1" ]]; then
 echo "Error: no spec id supplied and no .flow/specs/*.json branch_name matches '$CURRENT_BRANCH'. Autonomous context cannot prompt — pass an explicit spec id." >&2
 exit 2
 fi
 # Interactive: STOP this fence — a Bash call cannot pause for plain-text numbered prompt.
 # Ask outside the fence ("No spec detected from current branch. Provide a spec id
 # (fn-N-slug) or abort?" — options: 1. Type spec id 2. Abort; abort exits 1),
 # then RE-RUN this fence with SPEC_ID preset (interactive-ask exemption above).
 # §0.5's single `flowctl show` capture validates the typed id.
 echo "NEED_INPUT: SPEC_ID (no branch_name match for '$CURRENT_BRANCH')"
 exit 3
fi

# Spec existence is validated by §0.5's single `flowctl show` capture (fn-110) —
# no separate validation-only `show >/dev/null` call here.

# --- §0.3: base-branch detection cascade ---
if [[ -z "$BASE_REF" ]]; then
 for candidate in origin/main main origin/master master; do
 if git -C "$REPO_ROOT" rev-parse --verify --quiet "$candidate" >/dev/null 2>&1; then
 BASE_REF="$candidate"
 break
 fi
 done
fi

if [[ -z "$BASE_REF" ]]; then
 if [[ "$RALPH" == "1" || "$AUTONOMOUS" == "1" ]]; then
 echo "Error: no base ref detected (origin/main, main, origin/master, master all missing). Pass --base <ref> explicitly." >&2
 exit 2
 fi
 # Interactive: STOP this fence — ask for the base ref outside it (plain-text numbered prompt,
 # no frozen options — accept a typed branch name; on abort exit 1), then RE-RUN
 # this fence with BASE_REF preset (interactive-ask exemption above). The re-run's
 # final validation below rejects an invalid typed ref.
 echo "NEED_INPUT: BASE_REF (origin/main, main, origin/master, master all missing)"
 exit 3
fi

# Final validation — base must exist whether detected or supplied.
if ! git -C "$REPO_ROOT" rev-parse --verify --quiet "$BASE_REF" >/dev/null 2>&1; then
 echo "Error: base ref '$BASE_REF' is not a valid git ref. Check with: git rev-parse --verify $BASE_REF" >&2
 exit 1
fi

# --- §0.4: branch validity (same fence continues) ---
HEAD_SHA=$(git -C "$REPO_ROOT" rev-parse --verify HEAD 2>/dev/null) || {
 echo "Error: HEAD does not resolve to a commit. Repo state is broken; run from a normal branch." >&2; exit 1; }

BASE_SHA=$(git -C "$REPO_ROOT" rev-parse --verify "$BASE_REF" 2>/dev/null)

if [[ "$HEAD_SHA" == "$BASE_SHA" ]]; then
 echo "Error: HEAD and base ($BASE_REF) point at the same commit. Nothing to PR." >&2
 exit 1
fi

# Resolve the merge-base. Required for a valid PR — without one the branches
# are unrelated histories and gh pr create will fail.
MERGE_BASE=$(git -C "$REPO_ROOT" merge-base "$BASE_REF" HEAD 2>/dev/null) || {
 echo "Error: HEAD and base ($BASE_REF) share no merge-base — unrelated histories. Pick a different --base." >&2
 exit 1; }

# Confirm at least one commit exists on the branch since the merge-base.
# Use <merge-base>..HEAD (NOT <BASE_REF>..HEAD) so a branch that's behind base
# on linear history is still accepted as long as it has its own commits.
COMMITS_AHEAD=$(git -C "$REPO_ROOT" rev-list --count "$MERGE_BASE..HEAD")
if [[ "$COMMITS_AHEAD" -lt 1 ]]; then
 echo "Error: HEAD has 0 commits since merge-base with $BASE_REF. Nothing to PR." >&2
 exit 1
fi
```

### 0.5 — Tasks-done validation

Every task under the spec should be `done` before opening a PR. The cognitive-aid R-ID coverage table assumes done-tasks; in-progress tasks produce gaps. The single `flowctl show` capture in the combined fence below is ALSO the spec-existence validation (fn-110 — the old §0.2 validation-only `show >/dev/null` folded into it): a failed capture errors out with the spec-not-found message.

| Context | Behavior |
|---------|----------|
| `OPEN_COUNT == 0` | Proceed silently. |
| `OPEN_COUNT > 0` AND `DRY_RUN == 1` | Warn on stderr but proceed (`--dry-run` is for inspection — body should still render). |
| `OPEN_COUNT > 0` AND (`RALPH == 1` OR `AUTONOMOUS == 1`) | Hard-error with the open-task list. Autonomous loops should not open PRs for incomplete specs. |
| `OPEN_COUNT > 0` AND interactive | **Warn on stderr and proceed** (no prompt — autonomous create). The open items make the PR a **draft** via the §4.2 heuristic, which is exactly the "open a draft early" workflow; the warning names the open tasks + suggests `/flow-next:work` so the user can finish + flip to `--ready`. |

### 0.6 — Existing-PR refusal

**Critical: filter on `.state == "OPEN"`.** A bare `gh pr view --json url 2>/dev/null` returns rc=0 for both CLOSED and MERGED PRs — a "JSON returned = refuse" check would false-positive on reused branches (branch had a previous PR closed without merge, or merged + pushed-again-to). Filter via jq so closed/merged PRs don't trigger refusal.

**`--update` mode inverts this check.** After resolve-pr / land fix rounds, the created PR body goes stale — the R-ID coverage SHAs, Review-plan buckets, churn numbers, and SHA-pinned blob links all describe a diff that no longer exists (worst on the most-reviewed PRs). `--update` (parsed from `$ARGUMENTS` alongside `--dry-run`/`--ready` → `UPDATE_MODE=1`) re-renders Phases 1-3 against the CURRENT payload and `gh pr edit`s the EXISTING open PR's body (§4.6). So under `--update` an existing OPEN PR is REQUIRED — its number is the edit target — and its absence is the error. resolve-pr / land may invoke `/flow-next:make-pr <spec-id> --update` after committing fixes to refresh the cognitive aid.

`gh pr view` exit 1 with stderr "no pull requests found" = clean to proceed. CLOSED/MERGED PRs with rc=0 are filtered out by the `select(.state == "OPEN")` clause — `EXISTING` will be empty, refusal won't fire.

### 0.7 — Capture pre-flight context for downstream phases

The combined §0.5–0.7 fence:

```bash
# --- §0.5: tasks-done validation (single show capture = spec-existence validation) ---
if ! SPEC_JSON=$("$FLOWCTL" show "$SPEC_ID" --json 2>/dev/null); then
 echo "Error: spec '$SPEC_ID' not found in .flow/specs/. Check id with: $FLOWCTL specs" >&2
 exit 1
fi
OPEN_TASKS=$(printf '%s' "$SPEC_JSON" | jq -r '[.tasks[]? | select(.status != "done") | .id] | join(", ")')
OPEN_COUNT=$(printf '%s' "$SPEC_JSON" | jq '[.tasks[]? | select(.status != "done")] | length')

if [[ "$OPEN_COUNT" -gt 0 ]]; then
 if [[ "$RALPH" == "1" || "$AUTONOMOUS" == "1" ]]; then
 echo "Error: $OPEN_COUNT task(s) under $SPEC_ID still open ($OPEN_TASKS). Autonomous context cannot open PRs for incomplete specs." >&2
 exit 2
 else
 # Interactive + --dry-run alike: warn, don't block. Open items → draft (§4.2).
 echo "Note: $OPEN_COUNT task(s) not yet done ($OPEN_TASKS) — opening as a DRAFT. Run /flow-next:work to finish, then mark the PR ready." >&2
 fi
fi

# --- §0.6: existing-PR refusal (or --update target resolution) ---
EXISTING_JSON=$(gh pr view --json url,state,number 2>/dev/null | jq -c 'select(.state == "OPEN")' || true)
EXISTING=$(printf '%s' "$EXISTING_JSON" | jq -r '.url // empty' 2>/dev/null || true)
UPDATE_PR_NUMBER=$(printf '%s' "$EXISTING_JSON" | jq -r '.number // empty' 2>/dev/null || true)

if [[ "${UPDATE_MODE:-0}" == "1" ]]; then
 # --update REFRESHES the existing open PR's body — an OPEN PR is required as the target.
 if [[ -z "$EXISTING" ]]; then
 echo "Error: --update needs an existing OPEN pull request on this branch; none found. Run /flow-next:make-pr (without --update) to create one first." >&2
 exit 1
 fi
 echo "Update mode: refreshing PR #$UPDATE_PR_NUMBER body against the current diff." >&2
elif [[ -n "$EXISTING" ]]; then
 cat <<EOF >&2
Error: branch already has an OPEN pull request: $EXISTING

This skill creates new PRs only. To refresh the existing PR's body after fix rounds,
re-run with --update:

 /flow-next:make-pr <spec-id> --update

To address review feedback, use /flow-next:resolve-pr. For a fresh PR, close the open
one first: gh pr close <number> --comment "Replaced by upcoming /flow-next:make-pr"
EOF
 exit 1
fi

# --- §0.7: capture pre-flight context (same fence continues) ---
PHASE0_CONTEXT=$(jq -n \
 --arg spec "$SPEC_ID" \
 --arg base "$BASE_REF" \
 --arg head "$HEAD_SHA" \
 --arg branch "${CURRENT_BRANCH:-$(git -C "$REPO_ROOT" branch --show-current)}" \
 --argjson commits_ahead "$COMMITS_AHEAD" \
 --argjson open_tasks "$OPEN_COUNT" \
 --argjson dry_run "$DRY_RUN" \
 --argjson ralph "$RALPH" \
 --argjson autonomous "$AUTONOMOUS" \
 --argjson no_mermaid "$NO_MERMAID" \
 --argjson write_memory "$WRITE_MEMORY" \
 --arg draft_force "$DRAFT_FORCE" \
 '{spec:$spec, base:$base, head:$head, branch:$branch,
 commits_ahead:$commits_ahead, open_tasks:$open_tasks,
 dry_run:($dry_run==1), ralph:($ralph==1), autonomous:($autonomous==1),
 no_mermaid:($no_mermaid==1), write_memory:($write_memory==1),
 draft_force:$draft_force}')
```

Phases 1-5 read `$PHASE0_CONTEXT` rather than re-deriving values.

### Done when

- Ralph context detected (`RALPH=1` if `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` set). Autonomous context detected (`AUTONOMOUS=1` if the `mode:autonomous` token was parsed or `FLOW_AUTONOMOUS=1`) — never sets `RALPH`; prompt sites hard-error under `RALPH || AUTONOMOUS`.
- When `DRY_RUN != 1`: `gh` installed AND `gh auth status --hostname github.com` succeeds. Skipped under `--dry-run` (Phase 4.0 short-circuits before any `gh pr create`, so requiring `gh` there blocks the documented inspection path on machines / CI jobs that only render the body).
- `SPEC_ID` resolved (positional arg → branch-match against `.flow/specs/*.json` `branch_name` → interactive prompt / Ralph-or-autonomous exit 2) and validated via `flowctl show <spec-id> --json` (spec exists).
- `BASE_REF` resolved through the cascade (`--base` → `origin/main` → `main` → `origin/master` → `master` → ask / Ralph-or-autonomous exit 2) and validated via `git rev-parse --verify --quiet`.
- HEAD resolves; HEAD ≠ BASE; `git merge-base BASE HEAD` succeeds (shared history); `COMMITS_AHEAD >= 1` since that merge-base. (Base is NOT required to be an ancestor of HEAD — see §0.4 / §0.5.)
- Open-task validation: silent when all done; otherwise a stderr warning + **proceed as draft** (no prompt) — interactively and under `--dry-run` alike. Ralph/autonomous hard-errors (exit 2).
- Existing-PR refusal check: `gh pr view --json url,state,number | jq -r 'select(.state == "OPEN") | .url'` returns empty — no OPEN PR on the current branch (CLOSED/MERGED PRs never trigger refusal).
- `PHASE0_CONTEXT` JSON built (spec / base / head / branch / commits_ahead / open_tasks / flags / draft_force) and ready for Phase 1.

**Failure modes:** gh missing / unauthenticated → exit 1 + install / `gh auth login` instructions (both skipped under `--dry-run`); spec or base unresolved under Ralph/autonomous → exit 2; base ref invalid, HEAD == BASE, unrelated histories (no merge-base), or 0 commits since merge-base → exit 1; open tasks under Ralph/autonomous → exit 2; OPEN PR exists → exit 1 + `/flow-next:resolve-pr` hint.

---

## Phase 1: Gather inputs

**Goal:** call `flowctl spec export-cognitive-aid <SPEC_ID> --base <BASE_REF> --json` once and load the structured payload. The schema is documented in the spec under "Architecture & Data Models".

This phase is implemented in dependent tasks. Scaffold-task notes:

- Single subprocess call (latency + atomicity per the spec's Decision Context).
- Payload includes the nine current top-level fields: `spec`, `tasks[]`, `tasks_summary`, `memory_during_epic`, `glossary_changes[]`, `strategy_alignment`, `diff_summary`, `removed_export_refs[]`, and `deferred_findings[]`. The historical name `memory_during_epic` remains part of the payload schema; there is no legacy top-level `epic` alias.
- The export is one atomic full-payload read. It has no section filter; downstream phases reuse the in-memory payload.

### Done when

- `flowctl spec export-cognitive-aid <SPEC_ID> --base <BASE_REF> --json` returned successfully; payload parsed into an in-memory dict matching the spec's "Architecture & Data Models" schema.
- All nine top-level payload fields above are present and accounted for before rendering.

---

## Phase 1.5: HTML render lens (opt-in) — PR artifact

**Gated on `artifacts.html.enabled` — this check is the ONLY addition when the mode is off.** Runs directly after Phase 1 (the export payload is the lens's input) and BEFORE Phase 2, so the artifact commit (step 5 below) lands before §2.4b captures `HEAD_SHA` — the SHA-pinned blob link then points at a commit that actually contains `pr.html`.

```bash
HTML_LENS=$("$FLOWCTL" config get artifacts.html.enabled --json | jq -r 'if .value == true then "true" else "false" end')
# --dry-run promises NO state change (§4.0) — no artifact, no commit, no body line.
[[ "$DRY_RUN" == "1" ]] && HTML_LENS=false
```

When `HTML_LENS != true` (off, unset, or `--dry-run`): **skip this entire phase.** Load no reference file, write no artifact, add no body line, print no artifact-related output — the gate read above is the only cost.

When `HTML_LENS = true`:

1. **Load the disclosure reference** [`plugins/flow-next/references/html-artifacts.md`](../../references/html-artifacts.md) (relative cross-link — resolves from this skill dir in every install layout). It owns ALL design and generation rules; §5 is the PR-lens contract (read-only review instrument: masthead + dials, sticky review-progress bar, 90-second read, churn map by review intent, R-ID → evidence table, where-to-look checklist, risk register). Never duplicate its rules here; follow it top to bottom.
2. **Generate the artifact** at the fixed path (reference §1.3):

 ```bash
 mkdir -p ".flow/artifacts/${SPEC_ID}"
 # Host agent generates .flow/artifacts/${SPEC_ID}/pr.html per reference §5.
 ```

 Inputs are `EXPORT_PAYLOAD` (R-IDs from `spec.spec_sections.acceptance_criteria`, `tasks[].satisfies[]` + `tasks[].evidence.commits[]`, `diff_summary` files/churn/modules) plus `git diff --stat "$MERGE_BASE"..HEAD` for any stat the payload lacks. **Diff-derived, never commit messages** — commit subjects/bodies are not lens input. The staleness stamp (reference §1.5, PR variant) uses HEAD **at payload-export time** — the code under review; the artifact commit below deliberately excludes itself from its own churn map.
3. **R-ID verification (warn-in-artifact, never block).** Cross-check the payload before publishing: an R-ID whose owning tasks claim evidence commits absent from the diff range, an R-ID with no owning task (`tasks_summary.uncovered_r_ids`), or evidence commits touching no files in `diff_summary.files[]` — each renders as a **visibly flagged row** in the R-ID → evidence table (red R-ID cell + `mismatch` chip + one-line reason, reference §5.5). Never block make-pr on a mismatch, never silently drop the row.
4. **Run the reference's pre-publish checklist (§8)**, including the self-containment self-check grep (§2) — it must print `OK: self-contained` before the body may link the artifact.
5. **Link mode + narrow commit.** Link strategy follows the ignore status of the EXACT artifact file (a repo can ignore `.flow/artifacts/**`, `*.html`, or the exact path without the directory itself matching — the dir-level probe misclassifies those); committed artifacts land BEFORE Phase 2 so the blob link resolves once §4.6 pushes. Every git step is failure-guarded — the skill runs under `set -e`, so an unguarded `git add`/`git commit` (hook rejection, index lock, nothing-to-commit) would abort the whole run instead of degrading:

 ```bash
 ARTIFACT_PATH=".flow/artifacts/${SPEC_ID}/pr.html"
 LENS_OK=true # any failure below flips this — never aborts the skill
 if git check-ignore --no-index -q "$ARTIFACT_PATH"; then
 LINK_MODE=local # file ignored (dir, glob, or exact-path rule) → local-open guidance, never a blob link that 404s
 # --no-index honors the ignore rule even when an earlier run already committed
 # the artifact (plain check-ignore skips tracked files → would re-commit forever)
 else
 LINK_MODE=repo
 # Stage ONLY the artifact file — NEVER `git add -A` / `git add .` (the
 # working tree may carry unrelated changes that are not make-pr's concern).
 if ! git add -- "$ARTIFACT_PATH" 2>/dev/null; then
 LENS_OK=false
 elif git diff --cached --quiet -- "$ARTIFACT_PATH" 2>/dev/null; then
 : # regeneration produced byte-identical content already in HEAD — blob link already resolves; no empty commit
 elif ! git commit -m "chore(flow): pr artifact ${SPEC_ID}" -- "$ARTIFACT_PATH"; then
 LENS_OK=false
 fi
 fi
 if [[ "$LENS_OK" != "true" ]]; then
 LINK_MODE="" # no body line — a blob link is only emitted for content that landed in a commit
 echo "HTML render lens skipped: artifact stage/commit failed — PR proceeds without the body link" >&2
 fi
 ```

 The fixed-message pathspec commit (`-- "$ARTIFACT_PATH"`) rides §4.6's `git push -u origin HEAD` — by creation time the blob URL resolves on the remote branch. Dirty-tree discipline: the pathspec confines the commit to the artifact even if unrelated changes happen to be staged.
6. **Record the body line for Phase 2 (§2.1).** `LINK_MODE=repo` → absolute SHA-pinned blob URL per the §2.4b artifact row (`https://github.com/<owner>/<repo>/blob/<head-sha>/.flow/artifacts/<spec-id>/pr.html`, where `<head-sha>` is captured AFTER the artifact commit) plus the note "GitHub renders committed HTML as source — open locally in a browser". `LINK_MODE=local` → local-open guidance only (`.flow/artifacts/<spec-id>/pr.html` as bare inline code, "gitignored — open locally"). `LINK_MODE` empty (`LENS_OK=false`) → no body line at all. Never emit a blob link that 404s.
7. **No Lavish — ever.** The PR lens is a read-only review instrument (reference §5): make-pr never opens a `lavish-axi` session and never polls, **interactive AND autonomous alike** — review conversation belongs to the code host. There is no Lavish snippet in this skill by design; do not import one from capture §5.10 / plan Step 8.5.
8. **Failure is non-fatal — mechanically.** The stage/commit path is already guarded by step 5's `LENS_OK` flag. Generation or checklist failure (steps 2-4, host-agent actions) takes the same route: do NOT run step 5's stage/commit at all — set `LENS_OK=false`, `LINK_MODE=""`, print ONE stderr note (`HTML render lens skipped: <reason>`), and proceed to Phase 2 — the PR is the product, the lens is an extra. Exactly one stderr note total per skipped lens. Under Ralph ALL artifact messaging routes to stderr — the `PR_URL=<url>` single-line stdout contract (§5.4) and every receipt are untouched.

### Done when

- Mode off/unset or `--dry-run`: nothing happened beyond the single config read — no reference load, no artifact, no commit, no body line, no output change.
- Mode on: `.flow/artifacts/<spec-id>/pr.html` exists at the fixed path, derived from the export payload + real diff (**never commit messages**), pre-publish checklist (reference §8) passed incl. the self-containment grep → `OK: self-contained`, staleness stamp present.
- R-ID verification ran: payload-vs-diff mismatches (claimed evidence outside the diff range, uncovered R-IDs, evidence touching no diff files) render as visibly flagged rows (red R-ID cell + `mismatch` chip + reason) — warn-in-artifact, never blocks make-pr.
- Ignore probe ran against the EXACT artifact file (`git check-ignore --no-index -q "$ARTIFACT_PATH"` — `--no-index` so an already-tracked artifact still honors a later ignore rule), not the directory.
- `LINK_MODE=repo`: exactly one narrow pathspec commit (`chore(flow): pr artifact <spec-id>` `--` artifact file only), landing before §2.4b's `HEAD_SHA` capture; byte-identical regeneration makes no empty commit (blob link already resolves).
- Every git step failure-guarded via `LENS_OK` — no unguarded `git add`/`git commit` that could abort the skill under `set -e`.
- Render-lens body line recorded for §2.1 (or skipped — `LINK_MODE=""` — with one stderr note on failure).
- NO `lavish-axi` session opened and NO poll — interactive AND autonomous alike (read-only review instrument; no Lavish snippet exists in this skill).
- Failure path: generation / checklist / stage / commit failure ⇒ `LENS_OK=false`, body line skipped, exactly ONE stderr note (`HTML render lens skipped: <reason>`), phase exits cleanly into Phase 2 — PR creation proceeds. Ralph `PR_URL=<url>` stdout contract + receipts untouched.

---

## Phase 2: Render body header sections

**Goal:** turn the structured payload from Phase 1 into the **header half** of the PR body — the sections a reviewer reads *first* to decide where to focus. Header half = Title + summary block + TL;DR + R-ID coverage table + Critical changes + How to review this PR + Review plan. The context half (Decisions / Memory / Glossary / Open items) lands in §Phase 2 (cont). The mermaid `## Structural changes` section lands in §Phase 3.

The host agent's reasoning IS the renderer. **There is no Python renderer to call** — the agent reads the payload and emits markdown directly. flowctl provided the structured input; the skill turns it into prose. This is the "harness's own model is the QA layer" part of the spec.

### 2.0 — Section order (load-bearing)

The body sections appear in this exact order. Skip any section whose source content is empty (see §2.6 Section-omission rule). Never reorder — reviewers learn the shape and skim accordingly.

1. **Title** + summary block (spec id link, branch / base, task counts, R-ID coverage ratio).
2. **TL;DR** — 3-5 plain-language bullets covering the headline change.
3. **Not in this PR (by design)** — the spec's scope boundaries (§2.2b), so scope objections don't become review threads. Only when `spec.spec_sections.boundaries[]` is non-empty.
4. **R-ID coverage** — table mapping every spec R-ID to satisfying task(s) + evidence commit(s).
5. **Verification** — per-task test evidence + the honest "no test changed alongside X" gap fact (§2.3b), so the reviewer sees what was actually checked. Only when any `tasks[].evidence.tests[]` is non-empty.
6. **Critical changes** — ≤7 bullets, prioritized by churn / cross-module / public-interface / security-sensitive / behavior-visible.
7. **How to review this PR** — the trust-calibration coaching block (§2.4c): what the pipeline verified mechanically (tests / gates / R-ID coverage / cross-model review) vs what the human must judge, so the reviewer trusts the buckets below. Always rendered (like Critical changes).
8. **Review plan** — the risk-ranked, budgeted read-order (§2.4d): Must review (~X%) / Spot-check / Safe to skim, so the reviewer spends the next 30 minutes on the ~20-30% that carries real judgment risk and skips the rest with confidence. Only when `diff_summary.files[]` has ≥2 files.
9. **Structural changes** — mermaid codefences + prose summary (see §Phase 3).
10. **Decisions made** — `knowledge/decisions/` entries written during the spec.
11. **Memory left behind** — `bug/*` + `knowledge/architecture-patterns/*` entries.
12. **Glossary / strategy notes** — added/renamed terms + tracks served.
13. **Open items** — spec open questions + deferred review findings + spec-completion-review flags.
14. **Live QA** — the `qa_verdict` receipt summary (outcome + open P0/P1 + BLOCKED/NA reason + R-ID coverage), only when the receipt is present (§2.11b).
15. **Footer breadcrumb** — `Generated by /flow-next:make-pr from <spec-id> against <base-ref> on <YYYY-MM-DD>`.

(The footer is always section "last"; the numbering shifts when optional sections — Not-in-this-PR, Verification, Review plan, Live QA — are omitted, but section *order* is fixed. The three review-surfacing constructs are complementary, not redundant: **Critical changes** = the ≤7 highest-risk highlights; **How to review this PR** = the trust frame (what the pipeline already verified vs the human's job); **Review plan** = every changed area risk-bucketed into Must review / Spot-check / Safe to skim with a hard focus budget. Together they get the reviewer to the ~20-30% that carries judgment risk — the older per-category "Where to look" list is folded into the Review plan's per-item what-to-check questions.)

### 2.1 — Title + summary block

**Title** — computed from the spec title (truncate to 72 chars + ellipsis if longer; first sentence of `spec.spec_sections.goal_and_context` truncated to 70 + `…` as fallback when spec title is empty). The body itself uses the spec title as a `# <title>` H1.

**Summary block** — a single blockquote directly under the H1, four lines:

```markdown
> **Spec:** [<spec-id>](https://github.com/<owner>/<repo>/blob/<head-sha>/.flow/specs/<spec-id>.md)
> **Branch:** `<branch>` → `<base>`
> **Tasks:** <done> completed (<open> open if any — flagged in Open items)
> **R-ID coverage:** <covered>/<total> satisfied
```

(The spec link is a `.flow/*` artifact → blob, SHA-pinned per §2.4b. Same for every `.flow/tasks/*` / `.flow/memory/*` link below.)

**Render-lens line (only when Phase 1.5 recorded one).** Append it as a fifth blockquote line — committed artifact (`LINK_MODE=repo`):

```markdown
> **Render lens:** [`.flow/artifacts/<spec-id>/pr.html`](https://github.com/<owner>/<repo>/blob/<head-sha>/.flow/artifacts/<spec-id>/pr.html) — GitHub renders committed HTML as source; open locally in a browser. Regenerable; markdown is the record.
```

Gitignored artifacts (`LINK_MODE=local`) get local-open guidance only — `` > **Render lens:** `.flow/artifacts/<spec-id>/pr.html` (gitignored — open locally in a browser; regenerable) `` — never a blob link that 404s. With the mode off/unset (or `--dry-run`, or Phase 1.5 failed) this line is absent entirely.

All four values come from the payload directly:

- `<spec-id>` from `spec.id`
- `<branch>` from `PHASE0_CONTEXT.branch`, `<base>` from `PHASE0_CONTEXT.base`
- `<done>` / `<open>` from `tasks_summary.done` / `tasks_summary.open`
- `<covered>` = `len(acceptance_criteria) - len(tasks_summary.uncovered_r_ids)`; `<total>` = `len(acceptance_criteria)`

A 2-line natural-language summary appears between the H1 and the blockquote, drawn from `spec.spec_sections.goal_and_context` first paragraph, truncated to ~240 characters with sentence-boundary respect. Never invent — if `goal_and_context` is empty the summary is omitted.

### 2.2 — TL;DR composition

Render `## TL;DR` as 3-5 markdown bullets, each one a single-line plain-language statement. Source priority order:

1. **First sentence of `spec.spec_sections.goal_and_context`** — paraphrased into a single bullet; this is the headline change.
2. **Top 5 tasks by lines-changed** (`tasks[].evidence.commits` mapped to `git log` churn — host agent uses the diff's `high_churn_files` as a hint for which tasks shipped the most content). For each surviving task, take `tasks[].done_summary` first sentence, paraphrase to one line.
3. **Stop at 5 bullets total.** If the spec shipped fewer than 4 substantive changes, ship 3 bullets — never pad.

TL;DR rules:

- Bullets are plain English, not jargon; readers include reviewers who didn't write the spec.
- Never include R-IDs in TL;DR bullets — R-IDs go in the coverage table.
- Never quote raw diff content; talk ABOUT the change.
- If a `done_summary` is empty for a task, skip it — don't fabricate.

If `goal_and_context` is empty AND no tasks have `done_summary`, the body is unrenderable — abort with stderr `Empty spec content (no goal_and_context, no done_summary fields populated). Run /flow-next:work to populate task done_summaries first.` exit 1. See §2.7 Abort conditions.

### 2.2b — Not in this PR (by design) section

Render `## Not in this PR (by design)` when `spec.spec_sections.boundaries[]` is non-empty — the spec's own scope statements, surfaced so a reviewer's scope objection ("why didn't you also do X?") is answered before it becomes a review thread. Placed directly after TL;DR because scope objections form on the first skim, not at the bottom.

- Up to **5 bullets**, each a `boundaries[]` entry **verbatim**, first-sentence-truncated to ~140 chars + `…` (mechanical, the same truncation op as the acceptance-criterion 120-char rule). If more than 5, render the first 5 + a final `…and <N> more (see spec)` line linking the spec blob (§2.4b).
- **Verbatim read-only mirror — never invent a boundary, never soften or editorialize one.** Each bullet is a plain statement of what is intentionally out of scope: `- <boundary text>`. This section is a projection of `spec_sections.boundaries[]` and nothing else; empty array → section omitted entirely (§2.6).

### 2.3 — R-ID coverage table

Render `## R-ID coverage` as a markdown table. Exact column order, exact header text:

```markdown
| R-ID | Acceptance criterion | Task | Evidence |
|------|----------------------|------|----------|
| R1 | <criterion text, ≤120 chars + … if truncated> | [fn-N.M](https://github.com/<owner>/<repo>/blob/<head-sha>/.flow/tasks/fn-N.M.md) | [`<sha7>`](https://github.com/<owner>/<repo>/commit/<sha40>) |
| R2 | <…> | [fn-N.K](https://github.com/<owner>/<repo>/blob/<head-sha>/.flow/tasks/fn-N.K.md), [fn-N.L](…) | [`<sha7>`](https://github.com/<owner>/<repo>/commit/<sha40>), [`<sha7>`](…) |
| R7 | <…> | ⚠️ uncovered | — |
```

Field rules:

- **R-ID column** — every entry from `spec.spec_sections.acceptance_criteria[].id` in spec order. NEVER renumber; gaps in numbering (R1, R3, R5 — R2 deleted post-creation) are preserved verbatim per the R-ID renumber-forbidden rule. **Provenance chip:** when `acceptance_criteria[].tag` is `inferred` (weak provenance — the criterion was inferred by planning, not stated verbatim or paraphrased from the user's spec), append ` · inferred` in that row's R-ID cell (e.g. `R15 · inferred`) so the reviewer knows which criteria deserve a second look. `verbatim` / `paraphrase` / absent tags render no chip.
- **Acceptance criterion column** — `spec.spec_sections.acceptance_criteria[].text` truncated to 120 characters. If truncated, append `…` (single ellipsis character, not three dots). Never edit content; truncation is mechanical at byte boundary respecting word boundaries when feasible.
- **Task column** — derived ONLY from `tasks[].satisfies[]`. For each R-ID, find every task whose `satisfies` array contains that R-ID. Render as a comma-separated list of **blob** links (task spec is an artifact to read): `[fn-N.M](https://github.com/<owner>/<repo>/blob/<head-sha>/.flow/tasks/fn-N.M.md)` (per §2.4b). **Never infer from task title.** Never infer from commit message text. If `tasks[].satisfies[]` is empty for every task → R-ID is uncovered → render `⚠️ uncovered`.
- **Evidence column** — for each linked task, emit an absolute whole-commit-diff link `[\`<sha7>\`](https://github.com/<owner>/<repo>/commit/<sha40>)` for every entry in `tasks[].evidence.commits` (per §2.4b — NOT the bare `../../commit/` relative form). SHAs come from the payload only; never invent. If a task has multiple commits, list all of them comma-separated. If the task has no evidence commits but is `done`, emit `—` (em-dash) in that slot. For uncovered R-IDs, emit a single `—`.

After the table, if `tasks_summary.uncovered_r_ids` is non-empty, append a single italic sentence:

```markdown
⚠️ **<N> uncovered acceptance criterion(a):** R<i>, R<j>, R<k>. Reviewer should confirm these are intentional gaps before merge.
```

This makes the gap explicit — not silently buried in the table. The reviewer's eye lands on the `⚠️` marker and the explanatory line directly under the table reinforces it.

If `tasks_summary.uncovered_r_ids` length equals `len(acceptance_criteria)` (every R-ID uncovered) the body is unrenderable — abort with stderr `Empty R-ID coverage (no tasks satisfy any spec R-ID). Run /flow-next:work or check task satisfies frontmatter.` exit 1. See §2.7.

### 2.3b — Verification section

Render `## Verification` when any `tasks[].evidence.tests[]` is non-empty — the reviewer's dominant question is "do I trust this?", and this is the only place the body says what was actually run. Placed directly after R-ID coverage (verification evidence belongs beside the coverage claim).

- **One line per task** whose `evidence.tests[]` is non-empty: `**<task-id>** — <entry> · <entry> · …`. Each item is a `tasks[].evidence.tests[]` entry rendered **verbatim** (worker-authored free text — a read-only mirror exactly like `done_summary`; never paraphrase, and never summarize a `NEEDS_WORK`→`SHIP` review history down to "passed"). A task with empty `tests[]` is omitted from the list — never fabricate a test claim for it.
- **Honest test-gap fact (a fact, never an inference).** After the per-task lines, if a high-churn or public-interface **source** file has NO accompanying test-file change in the diff, add ONE line: `Test files in this diff: \`<test paths>\`. No test-file change accompanies: \`<path>\` (+<a>/-<d>).` Derive strictly from `diff_summary.files[]` path patterns (a path containing `test`, `spec`, `__tests__`, `_test.`, or `.test.` is a test file) + per-file churn. **Say "no test file changed alongside" (fact); NEVER "untested" (an inference the agent cannot make — the change may be covered by an existing, unmodified test).** If every changed source file has a companion test change, omit the gap line.
- Omitted entirely (§2.6) when every task's `tests[]` is empty.

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

### 2.4b — Linkable file references (load-bearing — applies to Critical changes, Review plan, R-ID coverage, Decisions, anywhere a path appears)

**Relative links DO NOT work in PR/issue bodies.** GitHub resolves a relative link in a PR *description* against the current **page URL** (`…/pull/<N>/…`) — producing a broken `…/pull/<N>/<relpath>` link, NOT the repo file. (This is the opposite of markdown *files inside the repo*, where relative links resolve against the file's location — which is where the wrong assumption came from. Validated wrong on PR #153.) Bare-code-span paths (`` `path` ``) are also not auto-linked — they render as inline code only.

**Every file/path reference in the body MUST be an absolute `https://github.com/<owner>/<repo>/…` URL.** Pick the URL **by purpose — diff for code, blob for artifacts:**

| Reference | Render as | Why |
|-----------|-----------|-----|
| **Code under review** (Critical changes, Review plan must-review items) | `` [`<path>`](https://github.com/<owner>/<repo>/commit/<sha>#<anchor>) `` — per-commit **diff** + file anchor | reviewer wants the *change*; `<sha>` = the commit that changed the file (from `tasks[].evidence.commits[]`); `<anchor>` lands on that file's diff |
| **Artifact to read** (`.flow/specs/*`, `.flow/tasks/*`, `.flow/memory/*`, a doc cited for context) | `` [`<path>`](https://github.com/<owner>/<repo>/blob/<head-sha>/<path>) `` — **blob**, SHA-pinned | read in full, not as a diff; SHA-pin so links survive branch deletion after merge |
| **Evidence column** (R-ID table) | `` [`<sha7>`](https://github.com/<owner>/<repo>/commit/<sha>) `` — whole-commit diff | "this commit satisfied the R-ID" |
| **Line ref** (rare) | `` [`<path>:L<n>`](https://github.com/<owner>/<repo>/blob/<head-sha>/<path>#L<n>) `` — blob + line, SHA-pinned | precise line; deep-links work on fresh load |

**Lookup + the code-diff `<anchor>` (the host agent runs this once per PR).** The anchor is GitHub's per-file diff id: `diff-` + the lowercase SHA-256 hex of the file-path string.

```bash
GH_NWO=$(gh repo view --json nameWithOwner --jq .nameWithOwner) # "owner/repo"
HEAD_SHA=$(git rev-parse HEAD) # SHA-pin blob links (survive branch delete)
BLOB_BASE="https://github.com/${GH_NWO}/blob/${HEAD_SHA}"
COMMIT_BASE="https://github.com/${GH_NWO}/commit"
file_anchor() { printf 'diff-%s' "$(printf '%s' "$1" | shasum -a 256 | cut -d' ' -f1)"; }
# code ref → ${COMMIT_BASE}/${sha}#$(file_anchor "$path")
# artifact → ${BLOB_BASE}/${path}
# evidence → ${COMMIT_BASE}/${sha}
```

**Anchor caveat (do NOT try to "fix" it).** The `#diff-<hash>` anchor lands on the file's diff on a **fresh page load / new tab (Cmd-click)**; on a plain *same-tab* click GitHub lazy-renders large commit diffs and won't auto-scroll — it still opens the correct commit diff, just without the jump. This is a GitHub limitation. **You cannot force new-tab** — GitHub strips `target="_blank"`/`rel` from PR-body markdown (verified). Reviewers Cmd-click focus links, so keep the anchor; it degrades gracefully to the whole-commit diff.

If `gh repo view` / `git rev-parse` fails (no remote, missing auth), **render paths as bare inline code** (`` `path` ``) rather than emit a broken relative link — an unlinked path beats a 404.

**Where this applies:**

- **§2.3 R-ID coverage table** — Task column → blob (artifact); Evidence column → whole-commit diff.
- **§2.4 Critical changes** — every code path → code-diff link (commit + anchor). Bare `` `<path>` `` or a relative link is forbidden here.
- **§2.4d Review plan** — every must-review code path → code-diff link (commit + anchor); the symbol anchor rides the `#diff-<hash>` file anchor.
- **§2.8 Decisions made** — the memory-entry id → blob (`.flow/memory/<id>.md`), SHA-pinned. If a decision cites a code path, that path → code-diff link.
- **Mermaid prose summary** (§3) — paths in the prose follow this rule (absolute). Mermaid node labels CANNOT carry markdown links (plain-text), so paths inside diagrams stay bare.

**One bare exception:** plain `path` strings that are JSON *field references* in the prose (`` `diff_summary.files[]` ``, `` `tasks[].satisfies[]` ``) are not user-facing file paths — leave them as inline code, unlinked.

**Anti-patterns:**

```markdown
- [`plugins/flow-next/scripts/flowctl.py`](plugins/flow-next/scripts/flowctl.py) ← BROKEN: relative → resolves to /pull/<N>/plugins/... (404)
- `plugins/flow-next/scripts/flowctl.py` (~line 12001) ← inline code, no link at all
```

Correct:

```markdown
- **Must review:** [`plugins/flow-next/scripts/flowctl.py`](https://github.com/owner/repo/commit/<sha>#diff-<sha256(path)>) — Does the schema cover...
- **Read:** [`.flow/specs/fn-1-foo.md`](https://github.com/owner/repo/blob/<head-sha>/.flow/specs/fn-1-foo.md)
```

### 2.4c — How to review this PR (trust calibration)

Render `## How to review this PR` directly after Critical changes and directly BEFORE the Review plan — a short (**≤ ~8 lines**) coaching block that calibrates the reviewer's trust: what the pipeline already verified mechanically, and therefore what the human's job actually is. This is the single highest-impact section the eval measured (trust-calibration 5→9 on a real shipped PR): the risk buckets below only pay off when the reviewer knows which machine checks already ran. Always rendered — the trust frame is valuable even on a one-file PR where the Review plan itself is omitted.

Render shape (these are rendered *lines*, not sub-headings):

```markdown
## How to review this PR

The pipeline already verified this — you don't re-check it from scratch:
- **Tests / gates:** <verbatim evidence from the `## Verification` section, e.g. `fn-93.1 — unit + smoke green`; or `no test evidence recorded on this PR`>
- **R-ID coverage:** <covered>/<total> acceptance criteria satisfied<; N uncovered — see the table above>
- **Cross-model review:** <e.g. `N findings deferred, M suppressed by the review gate`; or `no cross-model review recorded on this PR`>

Your job — the calls the pipeline can't make:
- Line-review the **Must review** bucket below — the ~20-30% that carries real judgment risk.
- Spot-check the verified claims above; sample, don't re-run everything.
- Own what machines can't judge: product intent, API taste, risk appetite.
```

**Single-file PRs (Review plan omitted per §2.4d's ≥2-files gate):** the first "your job" line must NOT reference a bucket that isn't rendered — replace it with a direct pointer to the one file: `- Line-review [\`<path>\`](<commit-diff link per §2.4b>) — it is the whole review surface.` The other lines stay. Never point at a section the omission rules removed (§2.6).

Field rules:

- **Mechanically-verified summary** draws from two export signals only: `tasks[].evidence.tests[]` (the same evidence §2.3b Verification renders) and R-ID coverage (acceptance-criteria count minus `tasks_summary.uncovered_r_ids`). `deferred_findings[]` is an open-items signal, not proof that a cross-model review ran. The export carries no review-verdict or suppression field, so the cross-model line says `no cross-model review recorded on this PR` rather than inferring one.
- **No-overclaim rule (load-bearing).** Cite ONLY verification present in the payload. Absent verification is stated honestly, never implied: no test evidence → "no test evidence recorded on this PR"; no review-verdict field → "no cross-model review recorded on this PR". NEVER write "reviewed by a second model" / "fully tested" without an authoritative signal — the reviewer must be able to trust every line of this block literally. (This is §2.5 rule 11 — the same no-invented-claims discipline the Review plan rests on.)
- **≤ ~8 rendered lines** (priorities, not a hard cap): a coaching frame, not a report. It sets up the buckets; it does NOT restate the Review plan's per-file detail (no repetition between this block and the buckets — the eval flagged length only when the two duplicated each other).
- **No-evidence payloads (specless / manual PRs)** — all three signals may be absent; the block then honestly states each absence and still frames "your job". The eval verified this degrades cleanly (honesty stayed high with zero evidence).

**What this section MUST NOT do:**

- MUST NOT claim any verification the payload doesn't carry (no-overclaim rule — §2.5 rule 11).
- MUST NOT repeat the Review plan's per-file buckets — it frames them, it doesn't restate them.
- MUST NOT editorialize the pipeline's confidence ("thoroughly reviewed", "high-quality change"). State what ran; let the reviewer judge.

### 2.4d — Review plan (risk-ranked, budgeted)

Render `## Review plan` when `diff_summary.files[]` has ≥2 files — the bucketed read-order that tells the reviewer which slice of the diff carries the real judgment risk (the ~20-30% worth careful reading) and, just as important, which 70-80% is safe to skim and WHY. This section replaces the older per-category "Where to look" reviewer-focus list, folding its what-to-check questions into the must-review items: where **Critical changes** flags the ≤7 highest-risk highlights, Review plan places EVERY changed area into exactly one of three **risk** buckets, and the **How to review this PR** block above frames the trust the buckets rest on. Buckets without that coaching frame + budget regress — the eval measured must-review ballooning to ~55% of the diff, defeating the whole point; the coaching block, focus budget, and per-item what-to-check below are load-bearing, not decoration.

Three buckets, rendered in this order, each an H3 with a churn-estimated percentage:

- `### Must review (~X%)` — the judgment-risk slice: line-review this.
- `### Spot-check` — real code, low risk: read the shape, sample the details.
- `### Safe to skim (~Y%)` — mechanical / generated / derived: confirm the generator ran, don't line-review.

**Bucket percentages** — estimate `~X%` / `~Y%` from `diff_summary` churn (each bucket's summed `additions+deletions` over total changed lines), rounded to the nearest ~5%. The number is a budget signal, not an audit — never present it as exact.

**Must-review items — one checkbox line each, four parts (WHY + WHAT + symbol anchor):**

```markdown
- [ ] 🔴 [`<path/area>`](https://github.com/<owner>/<repo>/commit/<sha>#<anchor>) — <WHY risky, one clause> — <WHAT to check: one concrete reviewer-answerable question?> — open `<function/symbol>`
```

- **`<path/area>`** — a code path from `diff_summary.files[]`, rendered as a commit-diff link per §2.4b (code under review → `commit/<sha>#<anchor>`). Never invented (§2.5 rule 1).
- **WHY risky** — one clause tracing to a payload signal: high churn (`high_churn_files[]`), a public-interface change (`public_exports_changed[]`), a security-sensitive path (`security_sensitive_paths[]`), a new cross-module edge (`cross_module_changes[]`), or a user-facing surface (`commands/ routes/ pages/ app/ cli/ hooks/ bin/`). **No invented risk** — every WHY names the signal it came from (§2.5 rule 11).
- **WHAT to check** — one concrete question the reviewer can answer *by reading that file* (e.g. "Does the new export stay backward-compatible with existing callers?", "Is the trust boundary preserved on this path?"). A question, not a label; ends with `?`. This is the old Where-to-look focus question, now anchored to the specific must-review file.
- **symbol anchor** — the specific function/symbol to open so the reviewer lands on the exact code: from `public_exports_changed[].added` / `.removed`, or fn-86's `changed_symbols` field when present. When no symbol signal exists, name the file's most-churned area in words rather than invent a symbol — degrade gracefully (§2.5 rule 2 forbids fabricated symbol names).

**Focus budget (load-bearing).** Must-review targets **≤ ~30%** of changed lines. When the risk signals would push it past that, carve the mechanical subset OUT explicitly into Safe to skim and name what you moved and why (e.g. "the +400-line generated fixture is mechanical — moved to skim"). The budget is the discipline that keeps Must review meaning "worth your judgment", not "everything that changed" — a must-review bucket over ~30% with no explicit carve-out is the failure the eval caught.

**Derived-file rule (load-bearing).** Generated mirrors, byte-identical dual copies, and task-state files ALWAYS land in Safe to skim with the derivation named — never counted as review risk, even when they carry high churn:

- generated mirror (e.g. a `codex/` sync path) → "regenerated by `sync-codex.sh`, guard-verified — skim"
- byte-identical dual copy (e.g. `.flow/bin/flowctl.py` beside `plugins/flow-next/scripts/flowctl.py`) → "byte-identical copy, parity-tested — skim"
- task-state / receipt files under `.flow/` → "task-state, not hand-written code — skim"

fn-86 will classify these deterministically (`derived_files` / `derived` fields on `diff_summary.files[]`); consume those when present, and until then name the derivation from repo knowledge (CLAUDE.md / docs). A derived file with real churn is STILL Safe to skim — the derivation, not the line count, decides the bucket.

**Spot-check + Safe-to-skim rendering** — GitHub task-list checkboxes (`- [ ]`) so the reviewer's progress persists. Prefix each bucket's list with its emoji + label once as the H3. On large diffs do NOT enumerate every safe-to-skim file — group with a count and the reason: `- [ ] ⚪ 12 docs/changelog files — mechanical`.

- **Every `diff_summary.files[]` path appears in exactly one bucket; a path is never invented** (§2.5 rule 1).
- **Tiny-PR collapse.** When the whole diff is `< ~100` changed lines, the three-bucket split is dishonest overhead: emit a single `### Must review` bucket listing everything, no forced percentages, no carve-outs. A small PR is read in full — say so honestly rather than manufacture a spot-check / skim split.
- Omitted (§2.6) when `diff_summary.files[]` has fewer than 2 files (a one-file PR needs no plan).

**What this section MUST NOT do:**

- MUST NOT invent a risk claim. Every WHY traces to a `diff_summary` signal (§2.5 rule 11). "This looks fragile" with no payload anchor → drop it, or move the file to Spot-check.
- MUST NOT count a derived file as review risk — the derived-file rule is absolute, churn notwithstanding.
- MUST NOT let Must review exceed ~30% without an explicit carve-out naming what moved to Safe to skim.
- MUST NOT use a label where a question belongs in the WHAT-to-check clause (questions activate reviewer cognition; labels don't).
- MUST NOT pre-judge the answer to its own what-to-check question (§2.5 rule 4 no-weakening applies — never "probably fine").

### 2.5 — Hallucination guardrails (load-bearing)

Phase 2 body rendering is the surface where hallucination risk peaks: the agent has rich structured input AND open-ended natural-language output, which is exactly the shape that produces fluent-sounding fabrication. These rules are load-bearing — every claim in the rendered body must trace back to a structured field in the export payload. **Honest "unclear" / "uncovered" beats plausible "wrong".**

The 11 rules below are not advisory. They define what the body MAY and MAY NOT contain. The skill prose, smoke tests, and review prompts all reference these rules by number.

1. **No hallucinated file references.** Every `<path>` in the body comes from `diff_summary.files[]`. Never fabricate paths from the spec text, from acceptance criteria, or from intent. If you want to mention a file that isn't in the diff, you can't — drop the claim.
2. **No hallucinated symbol names.** Every `<symbol>` named in Critical changes comes from `diff_summary.public_exports_changed[]`. Never derive from spec language ("the new validate function") if `validate` doesn't appear in the diff signal — that suggests it's an internal helper, not a public export.
3. **No hallucinated SHAs.** Every `<sha>` in the R-ID coverage table comes from `tasks[].evidence.commits[]`. Don't shorten differently than 7 chars; don't fabricate when an evidence array is empty.
4. **No "non-breaking" weakening.** Every `public_exports_changed[].removed` entry is potentially breaking. Never reclassify as "non-breaking", "internal", "minor", "trivial", or "harmless removal." The agent doesn't have global call-graph visibility. Reviewer judgment, not author judgment.
5. **No copy-pasted diff content.** The body talks ABOUT the diff (paths, churn, structure, modules). It NEVER quotes code. GitHub renders the diff below the body — duplication is wasted reviewer attention, AND privacy / secret-leakage risk: an LLM-generated body that quotes diff content could surface a secret the linter caught but the body grabbed.
6. **No inflated scope.** Every claim in the body must trace to either (a) the R-ID coverage table or (b) a task's `done_summary`. If you can't anchor a claim to one of those, drop it. "We also improved overall reliability" with no concrete trace = drop.
7. **No R-ID misattribution.** `tasks[].satisfies[]` is the source of truth. NEVER infer R-ID coverage from task titles ("This task is about validation, must be satisfying R3"). NEVER infer from commit messages alone. Empty `satisfies` → uncovered → ⚠️.
8. **No stale references.** Cross-check against `diff_summary.files[].status`. A file with `status == "D"` (deleted) cannot appear in the body as if it still exists. A file with `status == "R"` (renamed) appears under its new path; the old path is mentioned only if the rename itself is the load-bearing change.
9. **No invented "why".** The Decision Context section is a read-only mirror of `.flow/memory/knowledge/decisions/` + the spec's `## Decision Context`. NEVER paraphrase, never extend, never narrate a plausible-sounding rationale to fill a gap. If no decision exists for a structural change, the body says so honestly: `*No decision-track memory entry for this change. Decision context unclear — surface in PR comments if needed.*`
10. **Trace every claim.** The meta-rule: every sentence in the body must trace to a structured field in the export payload (spec / tasks / memory / glossary / strategy / diff / reviews) or to a verbatim spec quote. If you can't point to which field a claim came from, drop the claim.
11. **No invented risk claims.** Every WHY-risky clause in the Review plan (§2.4d) and every "verified" claim in the How-to-review block (§2.4c) traces to a payload signal — a `diff_summary` risk signal (`high_churn_files` / `public_exports_changed` / `security_sensitive_paths` / `cross_module_changes` / a user-facing surface prefix) for risk, or `tasks[].evidence` / `tasks_summary` for verification. NEVER narrate risk the payload doesn't support ("this looks fragile", "probably a hot path") and NEVER claim verification the payload doesn't carry (no-overclaim rule). If no signal anchors the risk, the file is not must-review; if no signal anchors the verification, say it is absent. Same discipline as rule 1 (paths) and rule 9 (why), applied to the risk-surfacing sections.

When data is missing, surface that honestly:

- No `done_summary` for a task → row in TL;DR is dropped, not invented.
- No evidence commits for a task → `—` in the table, not a guess from `git log`.
- No decisions in `memory_during_spec.decisions` → Decisions section says "*No decision-track memory entries for this spec.*" (omission honored per §2.6 — section is dropped entirely if empty per the section-omission rule, BUT if the body still emits the section heading for any reason, an honest empty-state note replaces invented content).

### 2.6 — Section-omission rule

Empty content → omit the entire section heading. Never emit an empty placeholder.

| Section | Emitted when | Omitted when |
|---------|--------------|--------------|
| Title + summary block | Always | Never (if the skill reaches Phase 2 the title is renderable from `PHASE0_CONTEXT`) |
| TL;DR | ≥1 bullet derivable | Aborts via §2.7 if zero bullets derivable |
| Not in this PR (by design) | `spec_sections.boundaries[]` non-empty | Empty array |
| R-ID coverage table | ≥1 R-ID in spec | Aborts via §2.7 if every R-ID uncovered |
| Verification | any `tasks[].evidence.tests[]` non-empty | Every task's `tests[]` empty |
| Critical changes | Always (with fallback bullet per §2.4) | Never |
| How to review this PR | Always (trust frame — even a one-file PR) | Never |
| Review plan | `diff_summary.files[]` has ≥2 files | Fewer than 2 changed files |
| Structural changes (mermaid) | Trigger conditions fire | When `--no-mermaid` OR no triggers |
| Decisions made | `memory_during_spec.decisions[]` non-empty | Empty array |
| Memory left behind | `memory_during_spec.bugs[]` OR `architecture_patterns[]` non-empty | Both empty |
| Glossary / strategy notes | `glossary_changes` non-empty OR `strategy_alignment.tracks_served` non-empty | Both empty |
| Open items | spec `## Open Questions` non-empty OR `deferred_findings` non-empty | All empty |
| Footer breadcrumb | Always | Never |

The omission rule preserves skim-readability — a heading with no content trains the reviewer to ignore future headings ("oh, /flow-next:make-pr always emits empty sections, I can skip them"). One real signal per heading.

### 2.7 — Abort conditions

The skill aborts before producing a body when the content would be unrenderable:

| Condition | Stderr message | Exit code |
|-----------|----------------|-----------|
| `goal_and_context` empty AND every task has empty `done_summary` | `Empty spec content (no goal_and_context, no done_summary fields populated). Run /flow-next:work to populate task done_summaries first.` | 1 |
| Every R-ID uncovered (`tasks_summary.uncovered_r_ids` length == `len(acceptance_criteria)`) AND `len(acceptance_criteria) > 0` | `Empty R-ID coverage (no tasks satisfy any spec R-ID). Run /flow-next:work or check task satisfies frontmatter.` | 1 |

These are guard conditions, not warnings — a body with empty TL;DR or empty R-ID coverage is the cognitive-aid equivalent of a blank PR description, and shipping it would defeat the skill's purpose.

`acceptance_criteria` legitimately empty (zero R-IDs because the spec is intentionally minimal) is **not** an abort — the R-ID coverage table is omitted via §2.6 and the body proceeds with a TL;DR + Critical changes pair only. This is the small-spec escape hatch.

### Done when

- Body section order locked (§2.0): H1 title + summary block → TL;DR → R-ID coverage → Critical changes → How to review this PR → Review plan → (Structural changes, §Phase 3) → context sections (§Phase 2 cont) → footer breadcrumb. Sections never reorder.
- Title + summary block renders spec id link, branch / base, task counts, R-ID coverage ratio — plus the optional ≈240-char `goal_and_context` summary and the Phase 1.5 render-lens blockquote line when one was recorded (absent entirely when the mode is off, under `--dry-run`, or when Phase 1.5 failed).
- `## TL;DR` renders 3-5 plain-English bullets sourced from `goal_and_context` + top tasks' `done_summary`, never from invented content. Never includes R-IDs, never quotes raw diff content, never pads when fewer than 4 substantive changes shipped.
- `## R-ID coverage` table renders every R-ID from `acceptance_criteria` in spec order (gaps preserved verbatim — never renumber), columns exactly `R-ID | Acceptance criterion | Task | Evidence`; Task column derives ONLY from `tasks[].satisfies[]` — never inferred from titles or commit messages; ⚠️ for uncovered + the italic follow-up sentence reinforcing the gap count.
- `## Critical changes` renders ≤7 bullets in 5-tier priority order (high-churn → cross-module → public-interface with `removed[]` items FIRST within tier 3 → security-sensitive → behavior-visible), with the limited-churn fallback bullet for low-signal diffs (the one section never omitted entirely).
- `## How to review this PR` (§2.4c) renders the trust-calibration block: mechanically-verified summary (tests / R-ID coverage / cross-model review, each drawn from the payload) + honest "no … recorded on this PR" for any absent signal + the "your job" framing. ≤ ~8 lines, no-overclaim rule honored, always rendered.
- `## Review plan` (§2.4d) renders the three risk buckets (`### Must review (~X%)` / `### Spot-check` / `### Safe to skim (~Y%)`) covering every `diff_summary.files[]` path exactly once; must-review items carry WHY (payload-traced) + WHAT-to-check (a question) + a symbol anchor; must-review ≤ ~30% with explicit carve-outs; derived files always safe-to-skim with the derivation named; tiny-PR (<~100 lines) collapses to a single honest Must-review bucket. Only when ≥2 changed files.
- No-weakening rule honored: every `public_exports_changed[].removed` entry surfaced as "potentially breaking" / `removes \`<sym>\`` — NEVER paraphrased as "non-breaking", "internal-only", "minor", or "trivial".
- All 11 hallucination guardrails (§2.5) hold for the rendered output — no fabricated paths (every `<path>` ∈ `diff_summary.files[]`), symbols, SHAs (every `<sha>` ∈ `tasks[].evidence.commits[]`), or risk/verification claims (every WHY + every "verified" traces to a payload signal — rule 11); every claim traces to a payload field.
- Section-omission rule (§2.6) honored — empty headings never emitted.
- Abort conditions (§2.7) checked before writing any body content; unrenderable bodies exit 1 with a clear stderr message rather than emitting fabricated content. (Zero R-IDs in the spec is NOT an abort — the coverage table is omitted and the body proceeds with the TL;DR + Critical changes pair.)

---

## Phase 2 (cont): Render body context sections

**Goal:** turn the structured payload from Phase 1 into the **context half** of the PR body — the sections a reviewer reads *after* deciding where to focus, to anchor judgment in the surrounding intent. Context half = Decisions made + Memory left behind + Glossary / strategy notes + Open items. The header half (TL;DR / R-ID coverage / Critical changes / How to review this PR / Review plan) lands in §Phase 2; the mermaid section lands in §Phase 3.

These four sections are **read-only mirrors of structured fields**. The host agent never paraphrases, never extends, never narrates a plausible-sounding rationale to fill a gap. The §2.5 hallucination guardrails (esp. rule 9 "no invented why" and rule 10 "trace every claim") apply here with extra force — the context sections are where fluent fabrication is most tempting. Treat them as text to reformat, not text to embellish.

### 2.8 — Decisions made section (R15)

Render `## Decisions made` when `memory_during_spec.decisions[]` is non-empty. Each entry from the array becomes one bullet; bullet shape is fixed:

```markdown
- **<title>** ([<id>](https://github.com/<owner>/<repo>/blob/<head-sha>/.flow/memory/<id>.md)) — <first_sentence>. Alternatives considered: <alternatives_considered>.
```

Field rules:

- **`<title>`** — `decisions[].title` verbatim. No editing, no truncation.
- **`<id>`** — `decisions[].id` verbatim (e.g. `knowledge/decisions/use-deterministic-export-2026-05-07`). Memory IDs are file-path-shaped.
- **Link target** — blob, SHA-pinned (per §2.4b — `.flow/memory/<id>.md` is an artifact to read): `https://github.com/<owner>/<repo>/blob/<head-sha>/.flow/memory/<id>.md`. The `id` already contains the track/category prefix; concatenate it after `.flow/memory/`. (A bare relative `.flow/memory/<id>.md` is BROKEN in a PR body — see §2.4b.)
- **`<first_sentence>`** — `decisions[].first_sentence` verbatim. flowctl already extracted this via `_export_first_sentence`. Never re-extract, never paraphrase.
- **`<alternatives_considered>`** — `decisions[].alternatives_considered` from the export. **Caveat: this field arrives as a stringified Python list** (e.g. `"['option-a', 'option-b']"`) because flowctl wraps the frontmatter list with `str()` during export. The host agent renders it readably:
 - String matches `^\[.*\]$` and is non-empty → strip the brackets + quotes, emit as a comma-separated phrase: `option-a, option-b`.
 - String is empty (`""`) or literally `"[]"` → omit the trailing `Alternatives considered: …` clause entirely (don't emit the label with no content).
 - String is plain prose (legacy entries that wrote a sentence rather than a list) → emit verbatim.
- **No truncation.** Decision entries are by-design prose-heavy; reviewer needs the full alternatives list to weigh the choice.

If `memory_during_spec.decisions[]` is empty, the section heading is omitted entirely per §2.6. **No fallback "no decisions" line.** Section either has bullets or doesn't appear.

**What this section MUST NOT do:**

- MUST NOT paraphrase, extend, or rewrite `first_sentence`. Read-only mirror.
- MUST NOT invent decision context for changes that have no memory entry. If a change in the diff lacks a `knowledge/decisions/` entry, the body says nothing about its rationale — the reviewer surfaces it in PR comments if needed.
- MUST NOT add commentary like "this is a good decision" / "the team weighed alternatives carefully". The bullet is `title + id + first_sentence + alternatives` — nothing else.
- MUST NOT include `decision_status` (proposed / accepted / superseded) — v1 keeps the bullet shape narrow. Future enhancement if reviewer feedback wants it.

### 2.9 — Memory left behind section (R16)

Render `## Memory left behind` when `memory_during_spec.bugs[]` OR `memory_during_spec.architecture_patterns[]` is non-empty. Two sub-lists when both are populated; one sub-list when only one is. (Omission per the §2.13 table.)

Sub-list structure:

```markdown
**Bugs captured during this spec:**

- `<id>` — <winning_hypothesis_first_sentence>
- `<id>` — <winning_hypothesis_first_sentence>

**Architecture patterns captured during this spec:**

- `<id>` — <first_sentence>
```

Field rules:

- **`<id>`** — `bugs[].id` or `architecture_patterns[].id` verbatim, formatted as inline code (so the path is visually distinct from the description and easy to copy for `flowctl memory read <id>`).
- **`<winning_hypothesis_first_sentence>`** — `bugs[].winning_hypothesis_first_sentence` verbatim.
- **`<first_sentence>`** — `architecture_patterns[].first_sentence` verbatim.
- **No file links** — unlike the Decisions section, memory entries here don't link to file paths. Reviewer who wants more reads via `flowctl memory read <id>` (the id is already copy-pasteable). This keeps the section visually scannable; the Decisions section uses links because alternatives-considered context is harder to find without one.
- **No truncation.** First-sentence shapes are already pre-bounded by the `_export_first_sentence` helper.

If only one sub-array is populated, emit only that sub-list with its bold preamble. The bold preambles are load-bearing — they tell the reviewer **why** these entries appear in the PR body (not "look at all the memory we wrote" but "future debuggers searching for these symptoms will find this PR").

**Section purpose framing** — this section answers the methodology's question "what did this spec teach?" Memory entries written during a spec are the most discoverable record of pitfalls, conventions, and patterns established by the work. Surfacing them in the PR body lets the reviewer (a) verify the captured insight is accurate and (b) find the entries later via `memory-scout` without reconstructing the spec from commit history.

**What this section MUST NOT do:**

- MUST NOT paraphrase or expand `winning_hypothesis_first_sentence` / `first_sentence`. Read-only mirror.
- MUST NOT invent memory entries that aren't in the export payload (rule 7 of §2.5 — no fictitious memory IDs).
- MUST NOT include legacy-track entries (`legacy/pitfalls#N`) — those surface in `memory list` but `_export_memory_during_spec` deliberately excludes them. v1 only renders bugs + architecture_patterns from the categorized tree.
- MUST NOT recommend memory-store cleanup ("consider deleting these entries"). That's the job of `/flow-next:audit`, not the PR body.

### 2.10 — Glossary / strategy notes section (R17)

Render `## Glossary / strategy notes` when `glossary_changes` has any non-empty array OR `strategy_alignment.tracks_served[]` is non-empty OR `strategy_alignment.drift_flagged[]` is non-empty. (Omission per the §2.13 table.)

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

**Section purpose framing** — the methodology's "shared vocabulary survives the team" principle: glossary changes are ratifications of (or departures from) the project's canonical wording, and strategy alignment is the explicit anchor between this spec's work and the repo-wide direction. Reviewer scans this section to catch (a) accidental glossary drift (a renamed term that downstream specs still use), (b) strategy misalignment (an active-track spec that surfaced `## Strategy drift flagged for review` during sync). Both are easy to fix at PR time, much harder to retrofit later.

**What this section MUST NOT do:**

- MUST NOT invent glossary terms not in `glossary_changes`.
- MUST NOT paraphrase `drift_flagged[].reason` — already prose-shaped by sync output / spec authoring.
- MUST NOT recommend strategy edits ("consider revising STRATEGY.md to add this track"). v1 surfaces drift as read-only. The reviewer / user runs `/flow-next:strategy` if they want to act.
- MUST NOT cite STRATEGY.md verbatim — `tracks_served` is the parsed signal; the full strategy doc is not part of the export payload by design (would inflate body for low signal).

### 2.11 — Open items section (R18)

Render `## Open items` when ANY of the three sources below produce content. Section omitted only when ALL are empty.

Three sources, in order — each surfaces in the same checkbox bullet list with provenance breadcrumbs distinguishing origin:

#### Source A — Spec open questions

`spec.spec_sections.open_questions[]` from the export payload (already parsed via `_export_parse_open_questions` in flowctl). Each entry → one bullet:

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

- **`<stripped item text>`** — `items[].raw` with the leading `- [ ] ` (or `- [x] `) marker stripped, so the renderer can re-emit a `- [ ]` checkbox at body level. If `raw` already starts with `- [` then strip that prefix; otherwise emit `raw` verbatim. (The export captures `raw` with its original prefix in `deferred_findings[]`.)
- **`<sink-relpath>`** — `deferred_findings[0].path` rendered as backticked relative path (e.g. `\`.flow/review-deferred/fn-42-foo.md\``).
- **Provenance breadcrumb** — exact phrase ` — deferred from impl-review (<sink-relpath>)`. Branch-slug sink is the provenance because v1 has no per-task attribution; surfacing the sink path lets the reviewer drill in.
- **Multiple sinks** — schema allows the array to grow if v2 splits per-task, but v1 only ever returns at most one element. Loop over `deferred_findings[]` regardless to be forward-compatible.

#### Source C — Spec-completion-review-flagged items

Completion-review state is not in the export-cognitive-aid payload. Read it directly from the spec JSON via flowctl:

```bash
SPEC_REVIEW_STATUS=$("$FLOWCTL" show "$SPEC_ID" --json | jq -r '.completion_review_status // "unknown"')
SPEC_REVIEW_AT=$("$FLOWCTL" show "$SPEC_ID" --json | jq -r '.completion_reviewed_at // empty')
```

If `SPEC_REVIEW_STATUS == "needs_work"`, emit a single bullet:

```markdown
- [ ] Spec-completion-review verdict was `needs_work` (last reviewed <SPEC_REVIEW_AT>) — flagged by spec-completion-review
```

Field rules:

- **Provenance breadcrumb** — exact phrase ` — flagged by spec-completion-review`.
- **Findings detail** — v1 surfaces only the verdict + timestamp. The granular findings live in the `/flow-next:spec-completion-review` receipt; reviewer drills in via that surface. v2 may aggregate findings into the bullet once the receipt format is stable.
- **`unknown` / `passed` status** — no bullet emitted. This source contributes content only when the spec-completion-review explicitly flagged needs-work.

#### Section ordering + omission

Bullets emit in source order: A (spec open questions) → B (deferred review findings) → C (spec-completion-review flag). Within each source, preserve the array's natural order (no re-sorting). If all three sources are empty, the heading is omitted entirely per §2.6 — never an empty `## Open items` placeholder.

**Section purpose framing** — the methodology's "explicit deferral over silent omission" principle: things flagged but not yet resolved deserve checkbox visibility, not burial in the spec / sink / receipt. Reviewer scans this section to decide whether the PR is mergeable as-is or whether a follow-up spec / task captures the remaining work. Each provenance breadcrumb tells the reviewer where to dig if they want context.

**What this section MUST NOT do:**

- MUST NOT invent open items not present in the three sources. The body is read-only mirroring.
- MUST NOT collapse multiple deferred findings into a single bullet ("3 deferred findings — see sink"). Each finding gets its own checkbox so reviewers can track resolution per item.
- MUST NOT paraphrase question text. Open questions are already prose-shaped by the spec author; rephrasing introduces drift.
- MUST NOT include findings the reviewer already accepted via `/flow-next:impl-review --interactive` "Acknowledge" — the interactive walkthrough records those separately and they don't appear in the deferred sink.

### 2.11b — Live QA section (fn-72 — only when a `qa_verdict` receipt is present)

Render `## Live QA` **only when** the QA receipt exists at `.flow/review-receipts/qa-<spec-id>.json` (the `/flow-next:qa` skill's default committed path; written when QA ran — via the opt-in pilot stage or a manual `/flow-next:qa` pass). With no receipt the section is omitted entirely (the §2.6 rule — most specs have no QA pass, so this is the common case and the body is byte-identical to today). This is the **R7 surfacing owner**: the QA stage advances even on `NEEDS_WORK`, so the findings reach a human only if make-pr renders them here.

**Read the receipt (guarded — a malformed/absent file omits the section, never aborts the body):**

```bash
QA_RECEIPT="$REPO_ROOT/.flow/review-receipts/qa-$SPEC_ID.json"
QA_PRESENT=0
if [ -f "$QA_RECEIPT" ] && jq -e . "$QA_RECEIPT" >/dev/null 2>&1; then
 QA_PRESENT=1
 QA_OUTCOME="$(jq -r '.qa_outcome // "unknown"' "$QA_RECEIPT")"
 QA_HEAD_SHA="$(jq -r '.head_sha // ""' "$QA_RECEIPT")"
 QA_BLOCKED_REASON="$(jq -r '.blocked_reason // ""' "$QA_RECEIPT")"
 QA_NA_REASON="$(jq -r '.na_reason // ""' "$QA_RECEIPT")"
 QA_COV_COVERED="$(jq -r '.rid_coverage.covered // "?"' "$QA_RECEIPT")"
 QA_COV_TOTAL="$(jq -r '.rid_coverage.total // "?"' "$QA_RECEIPT")"
fi

# Freshness — the receipt carries head_sha for exactly this reason. The QA receipt is
# keyed to the CODE head; Phase 1.5 may have already committed the pr.html artifact,
# which advanced HEAD — so compare against the PRE-ARTIFACT head (HEAD^ when HEAD is the
# artifact commit), never the post-artifact HEAD, or a fresh pass reads as stale.
# The receipt's head_sha is the head AT QA TIME. Bookkeeping commits land ABOVE the code
# head AFTER QA — pilot's `chore(flow): qa verdict <spec>` receipt commit, then Phase 1.5's
# `chore(flow): pr artifact <spec>`. So the branch tip is NOT the code head. Accept the
# receipt if its head_sha matches the tip OR any commit reached by peeling those leading
# bookkeeping commits (the code head and everything above it). Fail CLOSED on empty.
QA_FRESH_OK=0
if [ "$QA_PRESENT" = "1" ] && [ -n "$QA_HEAD_SHA" ]; then
 _s="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "")"
 while [ -n "$_s" ]; do
 [ "$_s" = "$QA_HEAD_SHA" ] && { QA_FRESH_OK=1; break; }
 git -C "$REPO_ROOT" log -1 --format='%s' "$_s" 2>/dev/null \
 | grep -qE '^chore\(flow\): (qa verdict|pr artifact) ' || break
 _s="$(git -C "$REPO_ROOT" rev-parse "$_s^" 2>/dev/null || echo "")"
 done
fi
[ "$QA_FRESH_OK" = 1 ] || QA_PRESENT=0 # stale or empty head_sha → omit the section
```

Read directly with `jq` (do NOT compose any free-form receipt field into shell-built JSON — surface the values as rendered markdown only). The receipt fields are exactly those task .1 added (`qa_outcome`, `head_sha`, `branch`, `rid_coverage`, `open_p0p1` as **objects**, plus the scoped `blocked_reason` / `na_reason`).

**Section body (when `QA_PRESENT=1`):**

```markdown
## Live QA

> **Outcome:** <qa_outcome> · **Ran against:** `<head_sha short>` · **R-ID coverage:** <covered>/<total>

<conditional outcome line — see field rules>

<open P0/P1 list — one checkbox bullet per open_p0p1[] object, only when the array is non-empty>
```

Field rules:

- **`<qa_outcome>`** — verbatim from `qa_outcome` (one of `SHIP` / `NEEDS_WORK` / `NA` / `BLOCKED`). Render the four-outcome value, **NOT** the Ralph-guard `verdict` projection (a `BLOCKED` receipt projects `verdict=NEEDS_WORK`; surfacing `verdict` here would mislabel "couldn't verify" as "found problems"). Read `qa_outcome`, never `verdict`.
- **`<head_sha short>`** — first 8 chars of `head_sha`; omit the "Ran against" clause if empty.
- **R-ID coverage** — `rid_coverage.covered`/`rid_coverage.total`; omit the clause if either is `?`.
- **Conditional outcome line:**
 - `SHIP` → `> Live QA passed: all derived scenarios passed on the running app with captured evidence; zero open P0/P1.`
 - `NA` → `> Live QA not applicable: <na_reason>` (no driveable user-visible AC — the common backend/CLI case).
 - `BLOCKED` → `> Live QA could not run: <blocked_reason>` (no local app reachable / no driver — **not** a failure; the augmenting pass was skipped).
 - `NEEDS_WORK` → `> Live QA found issues — see the open P0/P1 list below. (Advisory: this does not block merge; the human reviewer + land gate decide.)`
- **Open P0/P1 list** — only when `open_p0p1[]` is non-empty (typically the `NEEDS_WORK` outcome). One checkbox bullet per object, using its structured fields (`severity` ∈ `{P0,P1}`, `reason` one-line symptom, `file` surface/route, `id` finding id):

 ```markdown
 - [ ] **<severity>** — <reason> (`<file>`) — QA finding `<id>`
 ```

 Render the objects' fields verbatim as markdown text; never invent or paraphrase. If `open_p0p1` is empty, emit no list (a `SHIP`/`NA`/`BLOCKED` receipt has none).

**What this section MUST NOT do:**

- MUST NOT mark the PR blocked or change its draft/ready state on a `NEEDS_WORK` outcome — QA is advisory (fn-72 R7). It surfaces findings; merge stays the human's + land's decision.
- MUST NOT read `verdict` in place of `qa_outcome` — the projection collapses `BLOCKED` into `NEEDS_WORK`.
- MUST NOT inline free-form receipt text into any shell-composed JSON — render it as markdown only (the receipt was written safely by the QA skill; make-pr only *reads* it).
- MUST NOT fabricate a Live QA section when no receipt is present — absence of the receipt means QA never ran; the section is omitted (no sentinel line).

**Section purpose framing** — this is the live-app verification signal a static-review PR never carries: "does the running product actually work?" The QA stage advances the build loop on every outcome (including `NEEDS_WORK`), so this section is the only place a `NEEDS_WORK` live-QA result reaches the human reviewer before merge. It complements (never replaces) CI/staging/manual QA.

### 2.13 — Section-omission rule (extended for context sections)

The §2.6 omission rule extends to all four context sections. Recap with the additions:

| Section | Emitted when | Omitted when |
|---------|--------------|--------------|
| Decisions made | `memory_during_spec.decisions[]` non-empty | Empty array |
| Memory left behind | `memory_during_spec.bugs[]` OR `architecture_patterns[]` non-empty | Both empty |
| Glossary / strategy notes | `glossary_changes` has any non-empty array OR `strategy_alignment.tracks_served` non-empty OR `strategy_alignment.drift_flagged` non-empty | All empty |
| Open items | spec `open_questions` non-empty OR `deferred_findings` non-empty OR `completion_review_status == "needs_work"` | All empty |
| Live QA | `.flow/review-receipts/qa-<spec-id>.json` exists and parses (§2.11b) | No receipt / unparseable receipt (the common case — QA didn't run) |

### 2.13b — Footer breadcrumb (section 11 of body order)

The body's final line is a single italicized provenance breadcrumb. **Always emitted** — the breadcrumb is an honest disclosure that the body was generated by a skill, anchored to its inputs (spec id + base ref + date). Reviewers learn to look for the breadcrumb when deciding whether to grep the rendered body or re-run the skill.

```markdown
---

*Generated by `/flow-next:make-pr` from [<spec-id>](https://github.com/<owner>/<repo>/blob/<head-sha>/.flow/specs/<spec-id>.md) against `<base-ref>` on <YYYY-MM-DD>.*
```

Field rules:

- **`<spec-id>`** — `spec.id`.
- **`<base-ref>`** — `PHASE0_CONTEXT.base` (e.g. `origin/main`, `main`, `develop`). Backticked.
- **`<YYYY-MM-DD>`** — UTC date at body-render time, from `date -u +%Y-%m-%d`.
- **Em-dash separator (`---`)** — separates the breadcrumb visually from the last content section.
- **No truncation, no abbreviation.** The breadcrumb is one line. If the values would exceed 80 chars combined, that's still acceptable — visibility beats brevity.
- **No `Phase 4 dry-run: ...` qualifier under `--dry-run`** — the breadcrumb is identical regardless of whether `gh pr create` ran. The body content IS the artefact; whether it lands on stdout or in a PR doesn't change its provenance.

The breadcrumb is rendered during Phase 2 so it survives all downstream phases (mermaid generation, push, PR create) without a re-render. It also survives `--dry-run` (covered in §4.0) — the dry-run output emits the in-memory body string, which already contains the breadcrumb because Phase 2 rendered it before Phase 4 ran.

### 2.14 — Honest-empty-state escape hatch

The §2.5 rule 9 ("no invented why") means the agent never narrates rationale to fill empty Decisions / Open items. But the user might still want to know why a section is missing. The skill handles this by **never emitting an honest-empty-state line in the body** — the body is silent on missing sections, and the reviewer who notices an absent section infers correctly: no decisions captured (run `/flow-next:audit` to verify), no open items flagged.

This is the explicit choice the §2.5 hallucination guardrails force. Body content is structured-mirror only; the absence of a section is itself the signal. **Do not emit sentinel lines like "*No decisions for this spec*" or "*No open items*"** — those clutter the body without adding signal, and create the misleading impression that the skill ran some search and confirmed empty (when it just read empty arrays).

The one exception is the §2.4 Critical changes "Limited churn" fallback bullet — that one stays because Critical changes always renders (so there's no omission to infer from), and the bullet tells the reviewer where to look instead.

### Done when

- `## Decisions made` renders one bullet per `memory_during_spec.decisions[]` entry, with title + memory link + first sentence + alternatives-considered (parsed from stringified-list shape). Section omitted entirely when array empty.
- `## Memory left behind` renders bug + architecture-pattern sub-lists with bold preamble per sub-list. Section omitted when both arrays empty. One sub-list shown when only one populated.
- `## Glossary / strategy notes` renders glossary clauses (added / renamed-deferred-to-v2 / removed) and strategy clauses (tracks served / drift flagged). Each clause omits when its source array is empty; section heading omits when all contributions empty.
- `## Open items` aggregates spec open questions + branch-slug-sink deferred findings + spec-completion-review needs-work flag, each as a checkbox bullet with provenance breadcrumb. Source order A → B → C. Section omitted when all three sources empty.
- `## Live QA` (§2.11b) renders the `qa_verdict` receipt summary — `qa_outcome` (NOT the `verdict` projection) + the persisted `open_p0p1` objects + BLOCKED/NA reason + `rid_coverage` — only when `.flow/review-receipts/qa-<spec-id>.json` is present and parses. Advisory (never changes draft/ready state). Section omitted when no receipt exists (the common case).
- (The reviewer-focus questions the old Where-to-look section carried now live inside the Review plan's must-review items as the per-item WHAT-to-check clause — §2.4d. There is no standalone Where-to-look section.)
- All four context sections honor the §2.5 hallucination guardrails: no invented file paths, no fabricated decisions, no synthesized open items, no editorialized rationale.
- Each section has its "What this section MUST NOT do" callout in the rendered prose. Echo-chamber risk mitigated via explicit boundaries.
- §2.14 honest-empty-state rule honored: no sentinel "*No decisions*" / "*No open items*" lines emitted. Absence of section IS the signal.

---

## Phase 3: Mermaid generation

**Goal:** when the diff signals warrant it, emit a `## Structural changes` section with one to three mermaid codefences, each preceded by a one-paragraph prose summary in plain language. The diagrams are supplementary; the prose is load-bearing — forges that don't render mermaid still convey the change. When triggers don't fire OR `--no-mermaid` is set, the section is omitted entirely (never an empty placeholder).

The host agent reads `mermaid-rules.md` (sibling file in this skill) before emitting any codefence and validates each rendered diagram against the §6 checklist there. **No deterministic Python renderer.** flowctl's `spec export-cognitive-aid` payload provides the structured signals (`cross_module_changes`, `public_exports_changed`, `modules_touched`, `diff_summary.files`); the agent picks shape, picks nodes, emits codefence, validates.

### 3.0 — `--no-mermaid` short-circuit

Phase 3 is bypassed entirely when `$NO_MERMAID == 1`. **No diagrams emitted.** Prose summaries are also skipped — Phase 3's whole job is the diagram + prose pair, and emitting prose without diagrams under `--no-mermaid` produces a degenerate section that confuses the reader ("why is there structural-change prose with no structural diagram?").

```bash
if [[ "$NO_MERMAID" == "1" ]]; then
 : "skip Phase 3 entirely; the rendered body has no ## Structural changes heading"
 return 0 # or equivalent skip control in the host agent's render loop
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
| 5 | High-fan-out spec — `>15 files in >3 distinct modules` | `len(diff_summary.files) > 15 AND len(diff_summary.modules_touched) > 3` | `graph TB` |

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
| `graph TB` | High-level "spec touches these N areas" overview (default for trigger 5; default when collapsing 4+ diagrams to one). |

**Rule of thumb:** if you can't decide between `flowchart LR` and `graph TB`, pick `flowchart LR` for "A depends on B" stories and `graph TB` for "spec touched these areas" stories. The reader's mental model is different — left-to-right reads as flow, top-to-bottom reads as decomposition.

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
- Trigger evaluation walks the 5 conditions ((1) `cross_module_changes[]` non-empty, (2) `public_exports_changed[]` non-empty, (3) new top-level dir, (4) removed top-level dir, (5) >15 files in >3 modules) and the skip rules; emits Phase 3 only when ≥1 trigger fires AND no skip rule applies. When a skip rule engages, the stderr breadcrumb `Phase 3 skipped: <reason>` is emitted.
- Hard caps enforced (max 3 diagrams, max 12 nodes, max 25 edges, max 12K chars per codefence). Excess collapses to a `graph TB` overview; node excess groups by module/abstraction.
- Shape selection picks from the 4 documented shapes (`flowchart LR` / `classDiagram` / `sequenceDiagram` / `graph TB`) per the §3.3 rules.
- Every codefence is preceded by a 3-5 sentence plain-language prose summary anchored to `diff_summary.files[]` paths. The diagram is supplementary; prose is load-bearing.
- Each codefence passes the `mermaid-rules.md` §6 validation checklist (8 rules: quotes balanced, no reserved-word bare ids, no emoji, no MathJax, no relative click links, no inheritance cycles, arrow-char preference, ≤12K chars) before being emitted. Re-render loop on any failure — never emit a known-broken codefence.
- `mermaid-rules.md` ref file present with: §1 reserved words, §2 special-character escapes + HTML-entity fallback (decimal codes only), §3 shape decision matrix, §4 hard-caps recap, §5 prose-summary rule, §6 validation checklist.
- Section omission honored: zero triggers OR skip rule OR `--no-mermaid` → no `## Structural changes` heading at all.
- Hallucination guardrails honored: no invented modules / edges / symbols; "fewer nodes, more honest" over "context nodes for clarity."

---

## Phase 4: Push + create PR

**Goal:** turn the rendered body into an open PR. Compute title + draft flag, persist the body to disk, then push the branch and run `gh pr create` directly — **no confirm prompt** — with the body delivered via `--body-file` (NOT a heredoc). `--dry-run` is the preview path and short-circuits before any state change. `--memory` is deferred to Phase 5.

The host agent owns the body string at this point — Phases 2/3 produced it. Phase 4 takes that string, writes it to a tempfile, decides title + draft, then hands the file to `gh` — **no confirm prompt** (see §4.5). **No code in this phase rewrites body content.** If the body is too long for `gh pr create`, the truncation policy in §4.4 fires before invocation.

**Sub-section ordering.** `--dry-run` (§4.0) short-circuits before any state change; otherwise the phase flows straight through to push + `gh pr create` (§4.6) with no interactive gate. Phase 4 layout:

1. **§4.0** — `--dry-run` short-circuit (R22) — earliest exit; no state change at all (the inspection path).
2. **§4.1** — PR title format (R21) — compute `PR_TITLE` from spec.
3. **§4.2** — Draft-vs-ready matrix (R24) — compute `DRAFT_FLAG` from Ralph context + open items + force flags.
4. **§4.3** — Body delivery via `--body-file` (R20) — persist rendered body to tempfile.
5. **§4.4** — Body length cap + truncation policy — enforce 65K cap before invoking `gh`.
6. **§4.5** — No confirm gate (autonomous create) — flows straight into §4.6; flags, not a prompt, are the escape hatches.
7. **§4.6** — Push branch + `gh pr create` retry loop — runs directly after §4.4 (§4.6a links the PR to the tracker issue first).
8. **§4.7** — Failure recovery hints — stderr text per error class on `gh pr create` failure.

### 4.0 — `--dry-run` short-circuit (R22)

When `$DRY_RUN == 1`, Phase 4 emits the rendered body to stdout and exits 0. **No `git push`, no `gh pr create`, no `--memory` side effect.** This makes the skill safe to compose with `pbcopy` / inspection / smoke tests.

The body string is owned by the host agent at this point — Phases 2/3 produced it. The dry-run path emits the in-memory body directly without persisting to disk; subsequent sub-sections (§4.3 onwards) are skipped.

```bash
if [[ "$DRY_RUN" == "1" ]]; then
 printf '%s\n' "$BODY_CONTENT"
 echo "" >&2
 echo "Dry-run: body written to stdout. No push, no PR created, no memory entry written." >&2
 exit 0
fi
```

`--dry-run` is the exclusive output for Phase 4 — `--memory` does NOT fire under `--dry-run` (writing memory for a PR that wasn't opened produces orphan entries that pollute future `memory-scout` results). The footer breadcrumb still appears in the dry-run output because it's part of the body Phase 2 already rendered.

**Create + finalize (§4.1 → Phase 5) — loaded on demand.** If §4.0 did NOT short-circuit (this is a real create/update, not `--dry-run`), **read [create-and-finalize.md](create-and-finalize.md)** and execute it end-to-end: PR title (§4.1), body persist + truncation (§4.2-4.4), tracker linkage + `gh pr create` / `--update` `gh pr edit` + retry (§4.6), failure hints (§4.7), then Phase 5 (receipt, footer, `PR_URL=` emission). Under `--dry-run` the run already exited at §4.0 — never read that file for a preview.

## Anti-patterns (cross-phase)

This skill is the autonomous-loop terminus, which means it's also the most-tempting surface for "improvements" that defeat its purpose. The patterns below are explicitly forbidden — both in current implementation AND in any future v2 enhancement that lands on this skill.

1. **Letting the agent open the PR without making the PR reviewable.** The skill exists to produce a cognitive-aid body; opening a PR with an empty body or a body that doesn't trace to flow-next state would be the first failure mode. Every section in the body must trace to a structured field; abort conditions (§2.7) prevent unrenderable bodies from reaching `gh pr create`.

2. **Auto-merging the PR.** Out of scope per methodology #9 — merge is a human decision. The skill creates and exits. **Never invoke `gh pr merge`**, never suggest the user run it as a next step, never offer an `--auto-merge` flag.

3. **Including raw diff content in the body.** Privacy + duplication. The body talks ABOUT the diff (paths, churn, modules); GitHub renders the diff below the body. Any body that quotes code is one secret-leak away from a security incident. Hallucination guardrail rule 5 (§2.5) — non-negotiable.

4. **Generating `gh pr merge` invocations.** Recapped from #2 because it's the most-likely v2 footgun: "wouldn't it be nice if the skill could --auto-merge after CI passes?" No. The skill is a one-shot artefact producer.

5. **Inflating scope claims beyond what the diff supports.** Hallucination guardrail rule 6 (§2.5). Every TL;DR / Critical-changes / Where-to-look claim must trace to a payload field. "We also improved overall reliability" with no concrete trace = drop.

6. **Heredoc body delivery.** §4.3 — `--body-file` is the only reliable form when LLM-generated content contains backticks, `$`, or escaped quotes. v2 alternative ("just escape the bad characters") is a strict downgrade; don't reintroduce the heredoc form even with quoting.

7. **Silent fallback to `git push` + manual `curl` to GitHub API.** When `gh` is missing, the skill exits with install instructions (§0.1). Don't try to be clever — half-baked PR creation produces broken PRs that the user has to clean up manually.

8. **Ralph-blocking the skill.** Per spec R24, the skill is **not** Ralph-blocked. Don't add a `FLOW_RALPH=1` exit-2 guard. Ralph's autonomous-loop opens draft PRs for human review; that's the entire point.

9. **Writing memory entries without `--memory`.** Default off. The user opts in for structurally-significant specs. Auto-writing on every PR floods `memory-scout` with low-signal entries.

10. **Renumbering R-IDs in the coverage table.** The R-ID renumber-forbidden invariant is repo-wide; the body mirrors it. R1, R3, R5 (R2 deleted post-creation) renders verbatim — never as R1, R2, R3.

These anti-patterns are documented in skill prose (not just in the spec) so v2 enhancements have to consciously violate them. If a future enhancement seems to require any of the above, stop and reconsider the design — chances are the value is achievable without crossing these lines.

---

## Manual smoke

The skill itself is markdown — no unit-test surface. Phase 0 validation is exercised via the smoke test and by manual invocation in a real session. Expected behavior:

- `command -v gh` missing → exit 1 with install instructions.
- `gh auth status` failing → exit 1 with login instructions.
- `--base <bad-ref>` → exit 1 with `git rev-parse --verify` failure message.
- Branch with no `branch_name` match in any `.flow/specs/*.json` AND no positional spec id → interactive `plain-text numbered prompt`; Ralph hard-errors with exit 2.
- Tasks not all done + interactive → warn on stderr + proceed (open items force a draft via §4.2); Ralph exits 2; `--dry-run` warns and continues. No `plain-text numbered prompt` for open tasks.
- Branch with an OPEN PR → exit 1 with `/flow-next:resolve-pr` hint.
- Branch with a CLOSED or MERGED PR (no OPEN) → continues cleanly. **This is the load-bearing check** — fn-42 spike validated empirically that bare `gh pr view --json url` rc=0 for closed/merged PRs would false-positive without the `select(.state == "OPEN")` filter.
- Branch with no PR history at all (`gh pr view` exits 1) → continues cleanly.
- Ralph mode (`FLOW_RALPH=1`) → no `plain-text numbered prompt` calls in Phase 0; deterministic exit codes on missing context.
- `artifacts.html.enabled` unset/false → Phase 1.5 is a single config read; no reference load, no `.flow/artifacts/` write, no commit, no render-lens body line, byte-identical body vs pre-feature.
- `artifacts.html.enabled` true → `.flow/artifacts/<spec-id>/pr.html` written, self-check grep prints `OK: self-contained`, exactly one `chore(flow): pr artifact <spec-id>` commit (artifact file only — `git show --stat` lists one path) before `gh pr create`, blob link in the body resolves on the remote branch.
- `artifacts.html.enabled` true + `--dry-run` → no artifact written, no commit, no render-lens line in the stdout body.
- `artifacts.html.enabled` true + the artifact file ignored by ANY rule (`.flow/artifacts/`, `.flow/artifacts/**`, `*.html`, or the exact path) → no commit, body carries local-open guidance, no blob link.
- `artifacts.html.enabled` true + artifact commit fails (e.g. rejecting pre-commit hook) → PR still created, no render-lens body line, exactly one stderr note.
- `artifacts.html.enabled` true + Ralph → artifact may generate, but stdout is still exactly `PR_URL=<url>`; all artifact messaging on stderr; no `lavish-axi` invocation in the transcript (interactive or autonomous — the PR lens never opens a session).
