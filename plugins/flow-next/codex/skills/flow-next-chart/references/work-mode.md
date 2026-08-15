# Work mode - claim one decision, run its evidence route, redraw

Read this file only when Phase 0 routed to **work mode** (a chart id, a pinned D-ID, "work the next decision on ...", or an open decision reached through re-entry). Chart-mode and status-only invocations never need it.

- [Phase 2: Work mode (adaptive loop)](#phase-2-work-mode-adaptive-loop)
- [2.1 - Re-anchor](#21---re-anchor)
- [2.2 - Frontier is the sole selection input](#22---frontier-is-the-sole-selection-input)
- [2.3 - Claim before any work](#23---claim-before-any-work)
- [2.4 - Load full body only for the claimed decision](#24---load-full-body-only-for-the-claimed-decision)
- [2.5 - Attended hard gate](#25---attended-hard-gate)
- [2.6 - Evidence route by type](#26---evidence-route-by-type)
- [2.7 - Prototype lifecycle (attended)](#27---prototype-lifecycle-attended)
- [2.8 - Resolve / out-of-scope / release](#28---resolve--out-of-scope--release)
- [2.9 - Sharpen newly visible decisions](#29---sharpen-newly-visible-decisions)
- [2.10 - Recompute frontier and stop](#210---recompute-frontier-and-stop)
- [Phase 5: Supersession steering](#phase-5-supersession-steering)

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

---

## Phase 2: Work mode (adaptive loop)

**Goal:** one session-sized uncertainty from the live frontier, one claim, one evidence route, one transition, re-chart. Never execute a frozen up-front sequence.

### 2.1 - Re-anchor

```bash
"$FLOWCTL" chart show "$CHART_ID" --json
```

Load compact metadata + map body. Re-state **Outcome** and honor standing preferences / named skills in `## Notes`. Do **not** load every decision body/asset yet.

If chart status is `done` or `abandoned`, stop unless the user explicitly asks to reopen (`chart reopen --reason` after read-back). Suggest briefing/capture when done and briefable history exists.

### 2.2 - Frontier is the sole selection input

```bash
"$FLOWCTL" chart frontier "$CHART_ID" --json
```

Frontier = open, unblocked, unclaimed, dependency-ordered.

- Empty + not briefable (blocked/claimed/parked remain) -> report stuck reasons; `CHART_VERDICT=BLOCKED` or `NO_WORK` as appropriate.
- Empty + briefable -> go to the Phase 4 briefing path (workflow.md mode dispatch names the briefing reference); `CHART_VERDICT=COMPLETE` when briefing succeeds or when reporting briefable with no work left.
- Human pin (`--decision`) must appear on the frontier (or be the open locator-selected D-ID after claim eligibility check). If pinned decision is blocked/claimed/resolved, report and stop - do not silently pick another.

Choose the **smallest** uncertainty whose answer most reduces uncertainty or unlocks others. Prefer cheaper unattended evidence when it settles the same question.

**Oversized decisions:** if the selected question cannot fit one agent context (~100k tokens / one session), **split before claim** via `add-decision` + `wire-decision` (or sharpen on a parent resolve) - never dispatch a workstream-sized D-ID.

### 2.3 - Claim before any work

```bash
"$FLOWCTL" chart claim "<chart-id>.D<n>" --json
```

On conflict: print owner/age; do not work the decision. Offer `release-claim` for owner, or audited `--break-stale --reason` only after age gate. Terminal `BLOCKED` when claim fails and no alternate is selected in this invocation (one invocation never silently switches D-IDs after a failed claim).

### 2.4 - Load full body only for the claimed decision

Read the decision record + assets for the claimed D-ID only. Context discipline: navigation stays compact; selection loads depth.

### 2.5 - Attended hard gate

If stored `attendance` is `attended` **and** the driver is unattended:

1. Persist **no** answer.
2. Do not resolve, out-of-scope, or attach fabricated assets.
3. Prefer `chart release-claim` with note `awaiting human (attended)` when a clean release is available; if the loop crashed mid-claim, leave claim visible for recovery.
4. Terminal:

```text
CHART_VERDICT=NEEDS_HUMAN chart=<id> decision=<D> reason="attended decision requires human; no answer written"
```

### 2.6 - Evidence route by type

| Type | Route |
|---|---|
| `research` | Dispatch read-only scout (`Task` / Explore or portable read-only). Digest facts + citations. Write safe answer file. |
| `probe` | Measure/reproduce against the real system; store results as safe summary + evidence path/ref. |
| `eval` | Bake-off on real fixtures; winner + why. |
| `prototype` | Phase 2.7 (attended lifecycle). |
| `interview` | One question at a time via `plain-text numbered prompt` (numbered fallback). Never self-answer. |
| `task` | Perform only the enabling work; if attended, wait for human completion signal. |

Midway through an evidence route the answer often starts to look obvious and the pull is to just build the thing instead of resolving the decision. That pull is the signal you are standing at the edge of the map: the decision is unresolved precisely because the route past it was unknown. Resolve the D-ID with evidence and let capture and plan own the build.

Unsafe content (secrets, guard-triggering destructive commands): refuse to embed. Keep source at repository-relative path or approved HTTPS URL; store redacted summary + link. Describe dangerous operations in prose - never paste literal destructive shell command strings into answers or this skill.

### 2.7 - Prototype lifecycle (attended)

1. **Create or import ONE scoped throwaway artefact** (sketch, branch, HTML mock, fixture) sized to the question.
2. **Attach while open:**

```bash
# asset JSON: { "kind": "path"|"git_ref"|"branch"|"commit"|"url"|"https",
#               "reference": "<safe ref>", "display": "<summary>", "revision": "<optional>" }
"$FLOWCTL" chart attach-asset "<chart-id>.D<n>" --asset-file assets.json --json
```

Idempotent; decision stays `open`.

3. **Present** the exact safe reference/revision to the human (not a paraphrase of an unattached path).
4. **Record the reaction** (approve direction / reject / redirect).
5. **Resolve or supersede** with answer file capturing the reaction + asset refs. Use `--supersedes` when the reaction invalidates a prior assumption (Phase 5).
6. If the human does not react this session: release claim with `awaiting reaction` note **or** leave crash/claim state observable. **Resume later from the existing asset** - never rebuild, never infer approval.
7. Prototype code is **evidence**, never silent implementation under plan/work.

Missing or unsafe artefact -> cannot resolve a prototype decision.

### 2.8 - Resolve / out-of-scope / release

**Resolve:**

```bash
"$FLOWCTL" chart resolve "<chart-id>.D<n>" \
  --answer-file answer.md \
  [--sharpen-file sharpen.json] \
  [--supersedes D3,D5] \
  [--keep-dependents] \
  [--assets '[]'] \
  --json
```

**Out-of-scope** (closes without ledger answer; writes `## Boundaries`):

```bash
"$FLOWCTL" chart out-of-scope "<chart-id>.D<n>" --reason "<one line>" --json
```

**Release** without closing (stop / hand back):

```bash
"$FLOWCTL" chart release-claim "<chart-id>.D<n>" --json
```

### 2.9 - Sharpen newly visible decisions

After an answer exposes sharper questions, include them in the same resolve transaction:

```json
{
  "decisions": [
    {
      "title": "Pick retention window",
      "type": "interview",
      "question": "How long must tenant audit logs remain queryable?"
    }
  ],
  "remove_questions": ["<parked-key-that-sharpened>"]
}
```

`resolve --sharpen-file` allocates new D-IDs, wires graph if provided, removes parked keys, all-or-nothing. Do not hand-edit Open Questions. Accepted top-level keys are `decisions`, `remove_questions` (aliases `remove_parked` / `parked_removals`), and `notes_append`; any other key fails the whole resolve with `sharpen_file_unknown_key` before anything is allocated.

**Correcting a grounding note.** `## Notes` is otherwise write-once for the life of the chart. When the answer you are resolving directly disproves one of those starting facts, carry the correction in `notes_append` in the **same** resolve - not as a separate follow-up:

```json
{
  "notes_append": "- auth module DOES have tests (src/auth/tests/, 14 files)"
}
```

flowctl stamps the date (`- [corrected YYYY-MM-DD] ...`) and appends it to `## Notes`, creating the section if the chart has none; existing notes are never rewritten. The resolve result reports the appended bullet(s) under `notes_appended`. **Unattended discovery writes a correction only when the measured answer directly contradicts a specific existing note - never speculatively, and never as a guess at what the note-writer "probably meant."** A note that is merely incomplete, not contradicted, is left alone.

### 2.10 - Recompute frontier and stop

After every resolve / out-of-scope / supersession:

1. Call `chart frontier` again.
2. Propose the next smallest uncertainty from the **new** state (do not execute it in this invocation).
3. Emit exactly one terminal line, e.g.:

```text
CHART_VERDICT=RESOLVED chart=fn-140 decision=fn-140.D2 reason="storage approach settled via probe; frontier redrawn"
```

Independent unattended frontier members may be offered for **parallel separate invocations** - never batch-claimed here.

---

## Phase 5: Supersession steering

When the user says the direction changed (e.g. prototype reversed an earlier assumption):

1. Read back: which prior D-ID(s) are invalidated, what the new answer is, and cascade implications (`depends_on` open dependents lose claims; resolved dependents get replacement D-IDs unless `--keep-dependents`).
2. Resolve the new decision with `--supersedes <D,...>` after consent.
3. Report every affected D-ID. Ledger lines for superseded decisions stay struck-through - never deleted.

