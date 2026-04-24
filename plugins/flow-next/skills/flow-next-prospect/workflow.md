# /flow-next:prospect workflow

Execute these phases in order. Each gates on the prior. Stop on user-blocking error — never plow through with bad state.

## Preamble

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PROSPECTS_DIR="$REPO_ROOT/.flow/prospects"
TODAY="$(date -u +%Y-%m-%d)"
```

`jq` and `python3` (or `python`) must be on PATH. The skill prefers stdlib-only Python for any frontmatter parsing — see Phase 0.

---

## Ralph-block (R8) — runs first, before everything else

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
  echo "Error: /flow-next:prospect requires a user at the terminal; not compatible with Ralph mode (REVIEW_RECEIPT_PATH or FLOW_RALPH detected)." >&2
  exit 2
fi
```

**No env-var opt-in.** Ralph cannot decide what a repo should build next — that's a human judgement call. Pattern matches fn-32 `--interactive`. The block runs before `mkdir`, before any user prompt, before any scan; the artifact directory is not created and no question is surfaced.

---

## Phase 0: Resume check (R5, R16)

**Goal:** if the user already has an active prospect artifact <30 days old, surface it and ask whether to extend it, start fresh, or open it. Corrupt artifacts must be detected and listed with `status: corrupt` so the user knows they exist, but never offered for extension or promote.

### 0.1 — Discover candidates

```bash
mkdir -p "$PROSPECTS_DIR"
shopt -s nullglob
CANDIDATE_FILES=( "$PROSPECTS_DIR"/*.md )
shopt -u nullglob
```

Skip the rest of Phase 0 if `CANDIDATE_FILES` is empty — go straight to Phase 1.

### 0.2 — Parse + classify each candidate

For each `*.md` directly under `.flow/prospects/` (no recursion into `_archive/`), use stdlib Python to parse frontmatter and validate required sections. Required for `status: active`:

- Frontmatter parses as YAML (block delimited by `---` lines at top of file).
- `date` field is present and parseable as ISO `YYYY-MM-DD`.
- `## Grounding snapshot` heading exists.
- `## Survivors` heading exists.
- Frontmatter `status` is `active` (or absent — default to `active`).

Mark `status: corrupt` if any of those checks fail. Mark `status: stale` if the date parses but is >30 days old. Mark `status: archived` if frontmatter explicitly says so.

A single Python helper keeps this cheap and dependency-free. Inline it directly in the skill rather than shelling out per file:

```bash
python3 - "$PROSPECTS_DIR" "$TODAY" <<'PY'
import os, sys, json, re
from datetime import date, datetime

prospects_dir, today_s = sys.argv[1], sys.argv[2]
today = date.fromisoformat(today_s)
out = []

FRONT_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

def parse_frontmatter(text):
    m = FRONT_RE.match(text)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm

for name in sorted(os.listdir(prospects_dir)):
    if not name.endswith(".md") or name.startswith("_"):
        continue
    path = os.path.join(prospects_dir, name)
    if not os.path.isfile(path):
        continue
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        out.append({"file": name, "status": "corrupt", "reason": "unreadable"})
        continue
    fm = parse_frontmatter(text)
    status = "active"
    reason = ""
    age_days = None
    artifact_id = None
    if fm is None:
        status, reason = "corrupt", "no frontmatter block"
    else:
        artifact_id = fm.get("artifact_id") or name[:-3]
        try:
            d = date.fromisoformat(fm.get("date", ""))
            age_days = (today - d).days
        except ValueError:
            status, reason = "corrupt", "unparseable date"
        if status == "active":
            if "## Grounding snapshot" not in text:
                status, reason = "corrupt", "missing Grounding snapshot section"
            elif "## Survivors" not in text:
                status, reason = "corrupt", "missing Survivors section"
        if status == "active":
            fm_status = (fm.get("status") or "active").lower()
            if fm_status == "archived":
                status = "archived"
            elif age_days is not None and age_days > 30:
                status = "stale"
    out.append({
        "file": name,
        "artifact_id": artifact_id,
        "status": status,
        "reason": reason,
        "age_days": age_days,
        "title": fm.get("title") if fm else None,
        "focus_hint": fm.get("focus_hint") if fm else None,
    })

print(json.dumps(out))
PY
```

Capture into `CANDIDATES_JSON`. Treat the JSON as authoritative — do not re-parse files.

### 0.3 — Decide whether to surface

Define **resumable** = `status == "active"` (≤30 days old, valid sections). Filter via `jq`:

```bash
RESUMABLE=$(jq '[.[] | select(.status == "active")]' <<< "$CANDIDATES_JSON")
RESUMABLE_COUNT=$(jq 'length' <<< "$RESUMABLE")
CORRUPT_COUNT=$(jq '[.[] | select(.status == "corrupt")] | length' <<< "$CANDIDATES_JSON")
```

If `RESUMABLE_COUNT == 0` and `CORRUPT_COUNT == 0`, skip to Phase 1 silently.

If `CORRUPT_COUNT > 0`, print a single warning line per corrupt artifact (`<file>: corrupt — <reason>`). They are visible but not offered.

If `RESUMABLE_COUNT == 0` (only corrupt artifacts), skip to Phase 1 — nothing to extend.

### 0.4 — Blocking question

Present the resumable list in a deterministic numbered format and ask the user to choose a path. Use the platform's blocking question tool (`AskUserQuestion` on Claude Code, `request_user_input` on Codex, `ask_user` on Gemini/Pi); fall back to printing the numbered list and reading a typed reply when no blocking tool is available.

Frozen option strings (R19 anchor — must match exactly across backends):

```
fresh         — start a new prospect artifact (Phase 1)
extend N      — append a new dated section to artifact #N (resumable list above)
open N        — print the path to artifact #N and exit Phase 0
```

`extend` and `open` indices reference the **resumable** list only — never the corrupt list. Validate the index; reject `extend 0`, out-of-range numbers, or selecting a non-resumable artifact.

### 0.5 — Routing

- `fresh` → continue to Phase 1 with no prior-session context.
- `extend N` → record `EXTEND_TARGET=<artifact path>` for use in Phase 5 (task 3 will append a dated section); for now, continue to Phase 1 noting the target in the snapshot.
- `open N` → print `Artifact: <absolute path>` to stdout and exit 0. Do not run Phase 1.

The `extend` / `open` paths are the same across this task and downstream tasks; only `extend`'s artifact-write side-effect lands in task 3.

---

## Phase 1: Ground (R1, R17)

**Goal:** produce a structured 30-50 line snapshot of repo state relevant to the focus hint. Each data source has a graceful-degradation fallback that records `scanned: none (reason)` rather than erroring. Titles + tags only; **never raw file bodies** — bloated context measurably degrades downstream generation quality.

### 1.1 — Focus-hint resolution

```bash
FOCUS_HINT="${ARGUMENTS:-}"
FOCUS_KIND="open-ended"   # one of: open-ended | concept | path | constraint | volume
FOCUS_PATH=""
```

Classify the hint by surface:

- Empty → `FOCUS_KIND=open-ended`. No further checks.
- Looks like a path (contains `/`, no spaces, `realpath -m "$REPO_ROOT/$FOCUS_HINT"` resolves under `$REPO_ROOT`) → `FOCUS_KIND=path`, set `FOCUS_PATH="$FOCUS_HINT"`.
- Matches one of `top N`, `N ideas`, `raise the bar` → `FOCUS_KIND=volume`. Volume semantics are interpreted in Phase 2 (task 2); record verbatim here.
- Anything else → `FOCUS_KIND=concept`. Hint flows to Phase 2 prompts as-is.

If `FOCUS_KIND == path` and `[[ ! -e "$REPO_ROOT/$FOCUS_PATH" ]]`, the hint resolves to nothing on disk. Ask via blocking question whether to (a) continue open-ended, (b) re-enter a different hint, or (c) abort. Do not assume open-ended silently — the user typed a path for a reason.

### 1.2 — Collect signals (graceful degradation per source)

Each subsection writes a small structured block into a single snapshot buffer. Empty / missing sources record `scanned: none (<reason>)` and contribute zero noise.

#### git log (last 30 days)

```bash
if [[ -d "$REPO_ROOT/.git" ]] && command -v git >/dev/null 2>&1; then
  GIT_FILES=$(git -C "$REPO_ROOT" log --since="30 days ago" --name-only --pretty=format: 2>/dev/null \
    | grep -v '^$' | sort -u)
  GIT_COUNT=$(printf "%s\n" "$GIT_FILES" | grep -c .)
  GIT_TOP=$(printf "%s\n" "$GIT_FILES" | head -10)
  GIT_BLOCK="git_log_30d: ${GIT_COUNT} files modified
top:
$(printf "%s\n" "$GIT_TOP" | sed 's/^/  - /')"
else
  GIT_BLOCK="git_log_30d: scanned: none (no git repo)"
fi
```

#### Open epics

```bash
EPICS_JSON=$("$FLOWCTL" epics --json 2>/dev/null || echo '{"epics":[]}')
OPEN_EPICS=$(jq '[.epics[] | select(.status == "open")]' <<< "$EPICS_JSON" 2>/dev/null || echo '[]')
EPICS_COUNT=$(jq 'length' <<< "$OPEN_EPICS" 2>/dev/null || echo 0)
if [[ "$EPICS_COUNT" -gt 0 ]]; then
  EPICS_BLOCK="open_epics: ${EPICS_COUNT}
$(jq -r '.[] | "  - \(.id): \(.title)"' <<< "$OPEN_EPICS")"
else
  EPICS_BLOCK="open_epics: scanned: none (no open epics)"
fi
```

`flowctl epics --json` returns all epics; filter by `status == "open"` via jq. Status values used by flowctl are `open` and `done` (sometimes `closed`); the filter can be widened to `status != "done"` if `closed` shows up.

The Phase 2 prompt uses this list as anti-duplication grounding — candidates that overlap an open epic must surface in Phase 3 critique under `duplicates-open-epic`.

#### CHANGELOG (top 50 lines)

```bash
if [[ -f "$REPO_ROOT/CHANGELOG.md" ]]; then
  CHANGELOG_HEAD=$(head -50 "$REPO_ROOT/CHANGELOG.md")
  # distill: keep only entry headers (lines starting with ##) + first bullet under each
  CHANGELOG_BLOCK="changelog_recent:
$(printf "%s\n" "$CHANGELOG_HEAD" | awk '
  /^## / { print "  " $0; getline; while ($0 == "" && (getline) > 0); if ($0 ~ /^[-*]/) print "    " $0; next
  }')"
else
  CHANGELOG_BLOCK="changelog_recent: scanned: none (no CHANGELOG.md)"
fi
```

Distillation keeps version headers + first bullet per entry — recent-shipped signal without bloating context.

#### Memory matches (gated on `memory.enabled` + initialised)

```bash
MEMORY_ENABLED=$("$FLOWCTL" config get memory.enabled --json 2>/dev/null \
  | jq -r '.value // false')

if [[ "$MEMORY_ENABLED" == "true" && "$FOCUS_KIND" == "concept" && -n "$FOCUS_HINT" ]]; then
  # memory search writes its error JSON to stdout AND exits non-zero when memory
  # isn't initialised — so the response is the source of truth, not the exit code.
  MEMORY_RESP=$("$FLOWCTL" memory search "$FOCUS_HINT" --limit 5 --json 2>/dev/null \
    || true)
  # `memory search --json` returns {"success": false, "error": "..."} on
  # uninitialised memory. Bare `.success // true` returns true for false (jq's
  # `//` only substitutes null/false), so probe `has("error")` instead.
  MEMORY_BAD=$(jq -r 'has("error")' <<< "$MEMORY_RESP" 2>/dev/null || echo true)
  if [[ "$MEMORY_BAD" == "true" ]]; then
    MEMORY_BLOCK="memory_matches: scanned: none (memory not initialised)"
  else
    HITS_COUNT=$(jq '(.matches // []) | length' <<< "$MEMORY_RESP" 2>/dev/null \
      || echo 0)
    if [[ "$HITS_COUNT" -gt 0 ]]; then
      MEMORY_BLOCK="memory_matches: ${HITS_COUNT}
$(jq -r '.matches[] | "  - [\(.track)/\(.category)] \(.title) — tags: \((.tags // []) | join(","))"' <<< "$MEMORY_RESP")"
    else
      MEMORY_BLOCK="memory_matches: scanned: none (no hits for \"$FOCUS_HINT\")"
    fi
  fi
elif [[ "$MEMORY_ENABLED" == "true" ]]; then
  MEMORY_BLOCK="memory_matches: scanned: skipped (no concept focus)"
else
  MEMORY_BLOCK="memory_matches: scanned: none (memory disabled)"
fi
```

Title + tags only. Never paste memory bodies — that's exactly the kind of grounding bloat to avoid. The response-shape check (`.success`) handles the "enabled but not yet initialised" case where `memory search --json` returns an error JSON and a non-zero exit; treating both signals as authoritative keeps the snapshot clean.

#### Memory audit stale entries (optional, present iff fn-34 has run)

```bash
AUDIT_DIR="$REPO_ROOT/.flow/memory/_audit"
if [[ -d "$AUDIT_DIR" ]]; then
  LATEST_AUDIT=$(ls -1t "$AUDIT_DIR"/*.md 2>/dev/null | head -1)
  if [[ -n "$LATEST_AUDIT" ]]; then
    # Read only the stale-flagged section if present; cap at 20 lines.
    AUDIT_EXCERPT=$(awk '/^## Stale/,/^## /' "$LATEST_AUDIT" | head -20)
    if [[ -n "$AUDIT_EXCERPT" ]]; then
      AUDIT_BLOCK="memory_audit_stale:
$(printf "%s\n" "$AUDIT_EXCERPT" | sed 's/^/  /')"
    else
      AUDIT_BLOCK="memory_audit_stale: scanned: none (no stale entries flagged)"
    fi
  else
    AUDIT_BLOCK="memory_audit_stale: scanned: none (no audit reports)"
  fi
else
  AUDIT_BLOCK="memory_audit_stale: scanned: none (audit not run)"
fi
```

### 1.3 — Emit snapshot

Concatenate the blocks under a single `## Grounding snapshot` heading. Order is fixed (git log → open epics → changelog → memory → memory audit) so the snapshot is comparable across runs. Cap each block by line-count so total output stays in the 30-50 line target window.

The snapshot is the input to Phase 2's generation prompt (task 2). For this task, the snapshot is printed to stdout for manual inspection — Phase 2's prompt scaffolding lands later.

```bash
cat <<EOF
## Grounding snapshot

focus_hint: ${FOCUS_HINT:-(none — open-ended)}
focus_kind: $FOCUS_KIND
$( [[ -n "$FOCUS_PATH" ]] && echo "focus_path: $FOCUS_PATH" )

$GIT_BLOCK

$EPICS_BLOCK

$CHANGELOG_BLOCK

$MEMORY_BLOCK

$AUDIT_BLOCK
EOF
```

### 1.4 — Manual smoke (acceptance R1, R17)

In the flow-next plugin repo: `prospect DX` should produce a readable snapshot listing recently-modified files, open epics (e.g. fn-33 itself), CHANGELOG entries from the last few releases, memory hits if memory is initialised, and `scanned: none (...)` lines for any absent source. The snapshot must fit in roughly 30-50 lines of output and must not contain raw file bodies.

If grounding can't produce a useful snapshot from a real repo (too noisy / too sparse / too slow), this is the early-proof-point gate — re-evaluate scanning strategy before building Phases 2-5.

---

## Phases 2-6 — deferred

Phase 2 (persona-seeded generate), Phase 3 (two-pass critique with rejection floor), Phase 4 (bucketed rank), Phase 5 (atomic artifact write), and Phase 6 (handoff prompt) are implemented in subsequent tasks of fn-33. Their prompt scaffolding consumes the snapshot from Phase 1 verbatim, so the snapshot format is the cross-task contract.
