# Prospect — resume-artifact machinery (Phase 0 §0.2–0.5)

> **Loaded only when the Phase 0 gate in workflow.md prints its active sentinel** —
> `.flow/prospects/` already holds at least one `*.md` artifact, or the gate's
> probe/parse errored (fail open). A run against an empty prospects directory
> never reads this file: Phase 0 ends at §0.1 and control passes to Phase 1.

Contents:

- [0.2 — Parse + classify each candidate](#02--parse--classify-each-candidate)
- [0.3 — Decide whether to surface](#03--decide-whether-to-surface)
- [0.4 — Blocking question](#04--blocking-question)
- [0.5 — Routing](#05--routing)

`$PROSPECTS_DIR`, `$TODAY`, and `$PY` come from the workflow.md Preamble. **Bash vars do NOT survive across prompt turns** — the §0.2 block below must re-declare the Preamble's canonical Python picker block VERBATIM at its top before invoking `$PY`.

---

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
# Re-resolve $PY: re-declare the Preamble's canonical picker block verbatim
# here first (vars die across prompt turns).

$PY - "$PROSPECTS_DIR" "$TODAY" <<'PY'
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

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

Present the resumable list in a deterministic numbered format and ask the user to choose a path. Use `plain-text numbered prompt`.

Frozen option strings (R19 anchor — must match exactly across backends):

```
fresh         — start a new prospect artifact (Phase 1)
extend N      — append a new dated section to artifact #N (resumable list above)
open N        — print the path to artifact #N and exit Phase 0
```

`extend` and `open` indices reference the **resumable** list only — never the corrupt list. Validate the index; reject `extend 0`, out-of-range numbers, or selecting a non-resumable artifact.

### 0.5 — Routing

- `fresh` → continue to Phase 1 with no prior-session context.
- `extend N` → record `EXTEND_TARGET=<artifact path>` for use in Phase 5 (which appends a dated section to it); continue to Phase 1 noting the target in the snapshot.
- `open N` → print `Artifact: <absolute path>` to stdout and exit 0. Do not run Phase 1.

