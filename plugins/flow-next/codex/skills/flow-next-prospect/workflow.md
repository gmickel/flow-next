# /flow-next:prospect workflow

Execute these phases in order. Each gates on the prior. Stop on user-blocking error — never plow through with bad state.

## Preamble

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
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

## Phase 2: Generate (R2, R18) — divergent-convergent + persona seeding

**Goal:** produce a flat candidate list with **wide spread** by running one divergent generation pass anchored by ≥2 distinct persona voices. Phase 2 does **not** self-judge or pre-rank — that is Phase 3's job, on a separate prompt without this prompt's framing.

### 2.1 — Resolve volume from focus hint

Volume comes from `FOCUS_HINT` (Phase 1 §1.1). Default if no hint:

```bash
VOLUME_TARGET_MIN=15
VOLUME_TARGET_MAX=25
REJECTION_FLOOR=0.40   # Phase 3 default
```

Hint patterns (case-insensitive, leading/trailing whitespace tolerated):

| Hint | Generation target | Phase 3 rejection floor |
|---|---|---|
| _(none)_ or `concept` / `path` / `constraint` | 15-25 candidates | 0.40 |
| `top N` (with N integer) | `ceil(N * 1.8)` candidates | 0.40 (must leave ≥N survivors) |
| `N ideas` (with N integer) | `≥N` candidates (LLM may exceed) | 0.40 |
| `raise the bar` | 25-30 candidates | 0.60-0.70 |

`top N` math: with a 0.40 rejection floor, `ceil(N * 1.8)` keeps ≥N alive in expectation (`1.8 * 0.6 ≈ 1.08`, so the count survives even when the LLM rejects slightly more than the floor). When `top N` and `raise the bar` both appear, take the stricter floor (0.60) and bump generation to `ceil(N * 3.0)` to keep ≥N survivors.

Stash the resolved settings in shell:

```bash
GENERATION_TARGET="${VOLUME_TARGET_MIN}-${VOLUME_TARGET_MAX}"   # display-only string
SURVIVOR_TARGET=""                                              # set only when "top N" hint
```

### 2.2 — Pick personas

Apply the selection rule from `personas.md` based on `FOCUS_KIND` plus hint flavor:

- `open-ended` / `path` / `constraint` / generic `concept` / `top N` / `N ideas` → **senior-maintainer + first-time-user**
- `concept` matching `/audit|harden|secur|review|polish|risk|qual/i` → **senior-maintainer + adversarial-reviewer**
- `raise the bar` → **all three** (senior-maintainer + first-time-user + adversarial-reviewer)

The selected persona texts are read from `personas.md` and concatenated under `## Personas` in the Phase 2 prompt. Order: senior-maintainer first, then the others in the order listed by the rule.

### 2.3 — Run the divergent generation pass

Issue **one** prompt. Inputs: the Phase 1 grounding snapshot, the focus hint, the persona texts, the generation target. **Do not** include any critique-pass scaffolding — the generator must not self-judge. The critique runs as a separate prompt in Phase 3 without these instructions.

Prompt template (fill in the bracketed slots):

```
You are generating candidate ideas for a `/flow-next:prospect` artifact. This is the divergent generation pass — produce a wide net. Critique runs separately afterwards; do not self-judge here.

## Focus

focus_hint: [FOCUS_HINT or "(open-ended)"]
focus_kind: [FOCUS_KIND]
[focus_path: <FOCUS_PATH> if path]

## Grounding snapshot

[Phase 1 snapshot verbatim — git log, open epics, CHANGELOG, memory, audit]

## Personas

[Concatenated persona texts from personas.md, in selection-rule order]

Generate as if alternating between these voices. Let each voice claim ideas the others would miss. Do **not** flatten them into a single neutral perspective.

## Generation target

Produce [GENERATION_TARGET_DESCRIPTION] candidates. Wide net — encourage contrarian, unobvious takes. Repeating the obvious 3-5 ideas everyone would suggest is failure.

## Output format

Emit a flat YAML list. **One item per candidate.** No nesting, no preamble, no commentary outside YAML. The list is consumed verbatim by the next prompt — extra prose breaks the parser.

```yaml
candidates:
  - title: <short title, ≤80 chars>
    summary: <one-line summary, ≤120 chars>
    affected_areas:
      - <path or subsystem>
      - <path or subsystem>
    size: <S | M | L | XL>
    risk_notes: <one-line risk / unknown / caveat — ≤120 chars>
    persona: <senior-maintainer | first-time-user | adversarial-reviewer>
  - title: ...
```

Constraints:

- Each candidate must list at least one `affected_areas` entry.
- `size` is one of S (≤200 LOC), M (200-800 LOC), L (800-2000 LOC), XL (>2000 LOC).
- `persona` records which voice's lens the idea came from (used by Phase 3 only as metadata; do not let it bias the generation).
- `risk_notes` is the one-line caveat — *what could make this a bad call* — not a sales pitch.
- Do not add scores, rankings, or "priority" fields. Phase 4 ranks; you generate.
```

The `GENERATION_TARGET_DESCRIPTION` slot:

| Hint | Slot text |
|---|---|
| _(default)_ | `15-25` |
| `top N` | `ceil(N*1.8) — generate at least <K> so that ≥N survive critique` (substitute K) |
| `N ideas` | `at least N (you may exceed N if the wide net produces more)` |
| `raise the bar` | `25-30 — broader net, the critique pass will be stricter` |

### 2.4 — Validate the YAML

Parse the model output. The skill must accept output the model wraps in ```yaml fences as well as bare YAML. A defensive parser:

```bash
python3 - <<'PY'
import sys, re, yaml  # PyYAML may not be installed — fall back to a stdlib loader if needed.
text = sys.stdin.read()
m = re.search(r"```yaml\s*\n(.*?)\n```", text, re.DOTALL)
body = m.group(1) if m else text
data = yaml.safe_load(body) if 'yaml' in dir() else None
PY
```

If PyYAML is unavailable on the host, fall back to the stdlib parser pattern from Phase 0 §0.2 — it covers the limited subset (block list, scalar fields, no anchors / no nesting beyond `affected_areas`). Any candidate missing `title`, `summary`, or `affected_areas` is dropped before Phase 3 with a stderr warning (`Phase 2: dropped malformed candidate at index <i>: <reason>`).

Hand the validated list to Phase 3 as `CANDIDATES_YAML` (canonical form: re-serialize from the parsed object so downstream prompts get a clean shape).

If fewer than `floor(GENERATION_TARGET_MIN * 0.7)` valid candidates survive validation, surface a blocking question:

```
Phase 2 produced only K valid candidates (target was M-N). Options:
  retry      — re-run Phase 2 with the same prompt
  loosen     — proceed with K candidates anyway (Phase 3 floor still applies)
  abort      — exit; no artifact written
```

The `loosen` path keeps the run going but flags the under-volume in the eventual artifact frontmatter (`generation_under_volume: true`) so downstream readers know the spread was narrow.

---

## Phase 3: Critique (R3, R12) — separate prompt, rejection floor enforced

**Goal:** evaluate every candidate from Phase 2 with explicit `keep|drop` verdicts plus a fixed taxonomy reason. The critique pass runs in a **separate prompt** that does **not** see Phase 2's system prompt, the personas, or the focus hint — this prevents sycophancy ("the generator wanted X, the critic finds reasons to keep X"). The critique sees only the grounding snapshot and the candidate list.

### 3.1 — Build the critique prompt

Inputs: `CANDIDATES_YAML` (Phase 2 §2.4) + the Phase 1 grounding snapshot. **Excluded:** `FOCUS_HINT`, persona texts, Phase 2 prompt.

Rejection taxonomy (R3 anchor — frozen string list):

```
duplicates-open-epic   — material overlap with an open epic in the grounding snapshot
out-of-scope           — outside what this codebase / the focus area should tackle
insufficient-signal    — speculative without evidence in grounding snapshot
too-large              — XL or undermined by size; should be split or deferred
backward-incompat      — would break public contracts / users without strong justification
other                  — explain in `reason` field; use sparingly
```

Prompt template:

```
You are critiquing candidate ideas for a `/flow-next:prospect` artifact. You are the second pass — you did **not** generate these. Your job is to reject what does not belong.

## Grounding snapshot

[Phase 1 snapshot verbatim]

## Candidates

[CANDIDATES_YAML — one entry per candidate]

## Critique instructions

Evaluate each candidate against the grounding snapshot. Reject aggressively. "Could be useful someday" is not a reason to keep — that is exactly what `insufficient-signal` is for.

For each candidate, emit a verdict: `keep` or `drop`. If `drop`, the `taxonomy` field must be one of:

- `duplicates-open-epic` — same direction as a listed open epic
- `out-of-scope` — not aligned with this codebase or the focus area
- `insufficient-signal` — no grounding evidence supports this being worth doing now
- `too-large` — XL size or scope creep without commensurate payoff
- `backward-incompat` — breaks contracts / users without strong justification
- `other` — explain specifically in `reason`

If `keep`, leave `taxonomy: null`. The `reason` field is required for both verdicts and should be one specific sentence — no hedging, no "could be a good idea but" language.

Target rejection rate: **[REJECTION_FLOOR_PCT]%**. Below that floor, the run will surface a violation and ask the user to regenerate, loosen, or ship anyway. Aim above the floor. If you cannot in good conscience reject the floor's worth of these candidates, that is a signal the generation pass was already too narrow.

## Output format

```yaml
critiques:
  - index: 0       # zero-indexed position in the input list
    verdict: keep | drop
    taxonomy: null | duplicates-open-epic | out-of-scope | insufficient-signal | too-large | backward-incompat | other
    reason: <one specific sentence>
  - index: 1
    ...
```

Emit one entry per candidate, in order. No preamble, no commentary outside YAML.
```

`REJECTION_FLOOR_PCT` is `40` (default), `60` (under `raise the bar`).

### 3.2 — Parse + apply the floor

Pair each critique entry with its candidate by `index`. Compute:

```
rejection_rate = drops / total
```

If `rejection_rate < REJECTION_FLOOR`, surface a **blocking question** with the frozen options:

```
Critique rejected only X% (below the ≥Y% floor). Options:
  regenerate    — re-run Phase 2 + Phase 3 from scratch (new candidates)
  loosen-floor  — accept this critique result; ship survivors as-is
  ship-anyway   — same as loosen-floor; preserved for clarity in transcripts
```

Frozen string format (R12 anchor — must match across backends): `regenerate | loosen-floor | ship-anyway`. Use the platform's blocking question tool (`AskUserQuestion` / `request_user_input` / `ask_user`); fall back to numbered-options when no blocking tool is available. Validate the choice; reject anything outside the three options.

- `regenerate` → loop back to Phase 2 §2.3 with a fresh prompt invocation. Cap at **1 regeneration**; a second floor violation auto-routes to `loosen-floor` with a printed warning (avoids infinite loops on a model that genuinely can't reject).
- `loosen-floor` / `ship-anyway` → continue to Phase 4. Record `floor_violation: true` in the eventual artifact frontmatter.

### 3.3 — Hand off survivors + drops to Phase 4

Materialize:

- `SURVIVORS` — list of `{candidate, critique}` pairs where `critique.verdict == "keep"`. Order preserved from Phase 2.
- `DROPS` — list of `{candidate, critique}` pairs where `critique.verdict == "drop"`. Used by Phase 5 (task 3) to populate the `## Rejected` section.

If `len(SURVIVORS) == 0`, surface a blocking question:

```
Critique rejected every candidate. Options:
  regenerate    — re-run Phase 2 + Phase 3 with a fresh prompt
  abort         — exit; no artifact written
```

No third option here — shipping zero survivors produces a useless artifact.

---

## Phase 4: Rank survivors (R2) — bucketed, prose-only

**Goal:** assign each survivor to one of three labeled buckets and stamp it with a forced-format leverage sentence. **No numeric scores.** Past position 5, ranking is near-random across reruns; bucketing stabilizes the top-3 while keeping the rest legible.

### 4.1 — Build the rank prompt

Inputs: `SURVIVORS` (Phase 3 §3.3) + the Phase 1 grounding snapshot. Personas and focus hint are **not** re-introduced — Phase 4 ranks on grounding-evidence, not on the generator's framing.

Buckets (R2 / R4 anchor — frozen labels):

```
High leverage (1-3)            — small-diff, large-impact wins; top-3 cap
Worth considering (4-7)        — solid mid-leverage; positions 4-7
If you have the time (8+)      — lower priority; positions 8 and beyond
```

Prompt template:

```
You are ranking survivors of a critique pass for a `/flow-next:prospect` artifact. You did not generate or critique these — your job is to bucket and order.

## Grounding snapshot

[Phase 1 snapshot verbatim]

## Survivors

[SURVIVORS — yaml list with original candidate fields + the critique reason that kept each one]

## Ranking instructions

Assign each survivor to exactly one bucket and a position within that bucket. Cap the top bucket at 3 entries — High leverage is a scarce label, not a default. Most survivors land in Worth considering; only the genuinely lower-priority ones land in If you have the time.

Each survivor gets a **leverage sentence** in this exact forced format:

`Small-diff lever because <X>; impact lands on <Y>.`

- `<X>` names the structural reason this is a small change (one or two existing files, well-isolated boundary, additive, etc.).
- `<Y>` names what the impact reaches (which call sites, which user flows, which subsystems benefit).
- One sentence. No hedging. No "could potentially" / "might enable" / "would be nice" — those are signals to drop the candidate, not to rank it.

Do **not** emit numeric scores, percentage estimates, "leverage values", or rank weights. Prose only.

## Output format

```yaml
ranking:
  high_leverage:           # 0-3 entries
    - position: 1
      original_index: <int>   # the index from the Phase 3 SURVIVORS list
      leverage: "Small-diff lever because ...; impact lands on ..."
    - position: 2
      ...
  worth_considering:       # 0-N entries
    - position: 4
      original_index: <int>
      leverage: "..."
    ...
  if_you_have_the_time:    # 0-N entries
    - position: 8
      original_index: <int>
      leverage: "..."
    ...
```

Position numbers run 1-indexed, sequential, and stable across the buckets (positions 1-3 in High leverage, 4-7 in Worth considering, 8+ in If you have the time). Skip positions if a bucket is shorter than its slot — e.g., if High leverage has only 2 entries, Worth considering still starts at position 4. Buckets may be empty.
```

### 4.2 — Validate the ranking

Parse the model output. Reject and re-prompt **once** if any of:

- `high_leverage` has more than 3 entries.
- A `position` number is reused or non-sequential within its bucket.
- An `original_index` is out of range or duplicated across buckets.
- A `leverage` sentence does not match the regex `^Small-diff lever because .+; impact lands on .+\.$` — the format is the forced function, not a suggestion.
- Any numeric scoring leaks in (regex-check for `score:`, `priority:`, `weight:`, `\d+/10`, `\d+%`).

On re-prompt, send a single corrective message: `Output rejected — <specific reason>. Re-emit the ranking in the exact format above.` After one retry, fall through with whatever validates and surface a stderr warning.

### 4.3 — Hand off to Phase 5

Materialize `RANKED` — the parsed ranking with each survivor's full candidate record (title, summary, affected_areas, size, risk_notes, persona) joined in by `original_index`. Order:

1. High leverage entries by position
2. Worth considering entries by position
3. If you have the time entries by position

`RANKED` plus `DROPS` (Phase 3 §3.3) is the input to Phase 5 (task 3) — the artifact writer.

---

## Phase 5: Write artifact (R4, R13)

**Goal:** atomically write a single markdown artifact to `.flow/prospects/<slug>-<date>.md` so it survives Ctrl-C, concurrent runs, and resume on the next session. **Artifact lands on disk before Phase 6 fires.** Never gate the write on the handoff prompt.

### 5.1 — Inputs assembled

- `FOCUS_TEXT` — Phase 1's focus expansion (the literal text that goes under `## Focus`). When the user gave no hint, set this to `"_(open-ended)_"`.
- `GROUNDING_SNAPSHOT` — Phase 1's structured 30-50 line snapshot, verbatim.
- `RANKED` — Phase 4 §4.3 output. Three buckets: `high_leverage`, `worth_considering`, `if_you_have_the_time`. Each survivor entry carries `position, title, summary, leverage, size`, plus optional `affected_areas, risk_notes, persona` (Phase 2 candidate fields surface unchanged when present; the writer renders only what's there — never invents defaults).
- `DROPS` — Phase 3 §3.3 rejected list. Each carries `title, taxonomy, reason`.
- `VOLUME` — count of candidates fed into Phase 3 (pre-critique).
- `REJECTION_RATE` — `len(DROPS) / VOLUME` rounded to two decimals.
- Optional flags from upstream phases — written **only when set**:
  - `floor_violation: true` — Phase 3 set this when the user picked `loosen-floor` / `ship-anyway` on a rejection-floor miss.
  - `generation_under_volume: true` — Phase 2 set this when validated candidates fell below `floor(GENERATION_TARGET_MIN * 0.7)`.

### 5.2 — Slug + artifact id allocation (R13)

Use the bundled helpers — both are stdlib-only and concurrency-safe:

```bash
python3 - "$PROSPECTS_DIR" "$FOCUS_HINT" "$TODAY" <<'PY'
import importlib.util, os, sys
from pathlib import Path

# Load flowctl module without invoking the CLI.
flowctl_py = os.environ.get("FLOWCTL_PY") or (
    Path(os.environ.get("DROID_PLUGIN_ROOT") or os.environ["CLAUDE_PLUGIN_ROOT"])
    / "scripts" / "flowctl.py"
)
spec = importlib.util.spec_from_file_location("fc", str(flowctl_py))
fc = importlib.util.module_from_spec(spec); spec.loader.exec_module(fc)

prospects_dir, focus_hint, today = sys.argv[1], sys.argv[2], sys.argv[3]
base_slug = fc._prospect_slug(focus_hint or None)
artifact_id = fc._prospect_next_id(Path(prospects_dir), base_slug, today)
print(artifact_id)
PY
```

- First slot is `<base_slug>-<TODAY>` (e.g. `dx-improvements-2026-04-25`).
- Same-day collisions append `-2`, `-3`, ... — the base slug stays stable so `flowctl prospect promote` lookup remains keyable on the artifact id.
- Path-style hints (e.g. `plugins/flow-next/skills/`) collapse `/`, `\`, `.` to separators inside `_prospect_slug` so they slugify cleanly.
- Empty / non-ASCII-only / pure-punctuation hints fall back to `open-ended`.

### 5.3 — Build frontmatter + body, then atomic write

Body rendering and frontmatter validation are bundled — do **not** hand-roll YAML or template strings in the skill. Use `flowctl.render_prospect_body` and `flowctl.write_prospect_artifact`:

```python
ranked = {                                  # from Phase 4 §4.3
    "high_leverage":         [{...}, {...}],
    "worth_considering":     [{...}, ...],
    "if_you_have_the_time":  [{...}, ...],
}
drops = [{"title": ..., "taxonomy": ..., "reason": ...}, ...]
body = fc.render_prospect_body(focus_text, grounding_snapshot, ranked, drops)

frontmatter = {
    "title": <focus or "Open-ended prospect">,
    "date": today_iso,                       # quoted as a string by the writer
    "focus_hint": focus_hint or "",
    "volume": volume,                        # int
    "survivor_count": survivor_count,        # int
    "rejected_count": rejected_count,        # int
    "rejection_rate": rejection_rate,        # float, two decimals
    "artifact_id": artifact_id,
    "promoted_ideas": [],                    # task 5 (promote) appends here
    "status": "active",
}
# Optional flags — set ONLY when upstream phases provided them.
if phase3_floor_violation:
    frontmatter["floor_violation"] = True
if phase2_generation_under_volume:
    frontmatter["generation_under_volume"] = True

target = Path(prospects_dir) / f"{artifact_id}.md"
fc.write_prospect_artifact(target, frontmatter, body)
```

Atomic semantics (R4 anchor):

- Writer renders the whole document in memory before touching disk.
- A per-pid temp file (`.tmp.<pid>.<artifact-id>.md`) is created alongside the target, then `os.link()`'d onto the final path. `link()` is atomic on POSIX and **fails on existing target** (`FileExistsError`) — guarantees a Ctrl-C mid-write never leaves a half-written artifact and that two concurrent runners can't silently clobber one another.
- On filesystems without hard-link support, the writer falls back to `os.replace()` after re-checking existence.
- The temp file is unlinked in `finally` — no `.tmp.*` files leak on success or failure.

### 5.4 — Validation safety net

`write_prospect_artifact` validates the frontmatter before writing. If a required field is missing, status is invalid, or `promoted_ideas` is not a list, it raises `ValueError` and the artifact is **not** written. Surface the error to the user as a normal failure; do not retry blindly.

### 5.5 — Body section ordering (frozen)

The writer emits body sections in this exact order:

```
## Focus
## Grounding snapshot
## Survivors
  ### High leverage (1-3)
  ### Worth considering (4-7)
  ### If you have the time (8+)
## Rejected
```

Each survivor block:

```
#### <position>. <title>
**Summary:** <one line>
**Leverage:** Small-diff lever because <X>; impact lands on <Y>.
**Size:** <S|M|L|XL>
**Affected areas:** <comma-joined list>      # only when present
**Risk notes:** <one line>                   # only when present
**Persona:** <senior-maintainer | first-time-user | adversarial-reviewer>   # only when present
**Next step:** /flow-next:interview
```

`**Next step:**` is a hard-coded template line — not a candidate field. It always points at `/flow-next:interview` because the user's first move on a survivor is almost always to refine it before promoting.

Empty buckets render `_(none)_`. Empty `## Rejected` renders `_(none)_`.

---

## Phase 6: Handoff prompt (R9, R19)

**Goal:** offer the user a one-keystroke path from "artifact saved" to either an epic (via `flowctl prospect promote`), an interview (via `/flow-next:interview`), or a clean exit. The artifact already exists on disk by the time this phase fires — Ctrl-C here loses nothing.

### 6.1 — Pick the blocking-question tool

| Platform     | Tool                | Notes                                           |
|--------------|---------------------|-------------------------------------------------|
| Claude Code  | `AskUserQuestion`   | Deferred — load via `ToolSearch select:AskUserQuestion` if not already in scope |
| Codex        | `request_user_input`| Native                                          |
| Gemini       | `ask_user`          | Native                                          |
| Pi           | `ask_user`          | Requires `pi-ask-user` extension                |
| Fallback     | _frozen string_     | Print the exact format below; read user reply from chat |

If the platform tool is available, use it with these labelled choices (one per survivor + skip + interview):

- `Promote #1: <title>`
- `Promote #2: <title>`
- ... (one per survivor across all buckets)
- `Skip`
- `Interview instead`

The tool's free-text `description` field gets the artifact path so the user has it visible while choosing.

### 6.2 — Frozen numbered-options fallback (R19)

When no blocking tool is reachable (or the platform tool errors), print this **exact** string format. Do not paraphrase, re-order, or add commentary — the smoke test in task 6 grep-checks this format:

```
Saved: .flow/prospects/<artifact-id>.md

Promote a survivor to an epic?
  1) Promote #1: <title>
  2) Promote #2: <title>
  ...
  N) Skip
  i) Interview (ask /flow-next:interview what to refine)

Enter choice [1-N|i|skip]:
```

Number the survivors 1-N in the same order they appear in the artifact (high_leverage first, then worth_considering, then if_you_have_the_time). `Skip` is the last numeric option (`N`); `i` is the alphabetic interview shortcut.

### 6.3 — Reply parsing

Normalize the reply (strip whitespace, lowercase). Route by exact match:

| Reply | Action |
|-------|--------|
| `1`, `2`, ..., `N-1` (where `N` is the Skip slot) | Run `flowctl prospect promote <artifact-id> --idea <reply>`. Echo the new epic id and exit. |
| `N`, `skip`, empty string | Print `Skipped. Artifact saved at .flow/prospects/<artifact-id>.md` and exit. |
| `i`, `interview` | Print suggestion: `Run /flow-next:interview <epic-or-task-id> to refine. Artifact saved at .flow/prospects/<artifact-id>.md`. **Do not auto-invoke** — the user picks the target id. |
| anything else | Reprint the menu once with `Unrecognized choice: <reply>`. On second invalid reply, print `Skipped (no valid choice). Artifact saved at .flow/prospects/<artifact-id>.md` and exit cleanly. |

### 6.4 — Exit cleanly regardless

The artifact is on disk. Phase 6 does not retry, does not extend, does not delete. If `flowctl prospect promote` errors (task 5 lands the command), surface its stderr verbatim and exit non-zero — the user can re-run promote manually with the artifact id printed in the saved-to line.
