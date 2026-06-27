---
satisfies: [R14, R15, R16]
---

## Description
Make tracker-sync **autonomous-safe** + supply the **enumeration method**, the **named skill ops**, and the **concrete question-valve contract** backlog mode needs.
1. **R14 — Phase-0 autonomy parity:** extend the gate at `steps.md:19` (today `FLOW_RALPH`/`REVIEW_RECEIPT_PATH` only) to also recognize `FLOW_AUTONOMOUS=1` / `mode:autonomous`, matching `work`/`make-pr`/`resolve-pr`/`capture`. Ceremony never prompts under the marker; conflicts `sync defer`, never `AskUserQuestion`.
2. **Enumeration method (finding #1):** add `listOpenIssues(filter) → issue[]` to `adapter-interface.md` (the 8 existing methods are per-issue). Implement for **Linear + GitHub** (v1). **Exact-match filter (round-2 #4):** lists issues at the **exact `tracker.readyState` state/label** — `readyState` matching is exact, no state ordering exists, so no "beyond". Returns normalized `issue` structs.
3. **Named skill-level tracker-sync ops (round-2 #2):** the adapter method is low-level; pilot invokes tracker-sync via named **operations** like the existing `comment <spec-id>`. Add **`list-open`** (enumerate promoted issues via `listOpenIssues`) and **`question <spec-id|tracker-id>`** (post a question-valve comment with the anchor). Skill-level + transport-blind — NOT flowctl transport. **`list-open` no-ops with a note when `tracker.readyState` is unset** (no promoted-lane filter — round-3 #4). A **tracker-only `question`** (no spec) is **exempt from the spec-id-based sync receipt** (no spec id to key on — its audit is the pilot-log row + the tracker comment anchor; round-3 #3), and its **parked state lives in the tracker** — detected by scanning comments for `flow-next:question id=… status=open` + a matching `flow-next:answer id=…`, with no spec import/flip until capture/interview later creates a spec (round-3 #1).
4. **R15 question-valve contract (findings #5/#6 + round-2 #3/#8):** stable anchor `<!-- flow-next:question id=<hash> status=open|answered -->` where **`id` hashes stable fields only** (`subjectId` + blocked-stage + `reasonCode` + `questionSlug`, where **`subjectId` = the spec id when spec-backed, else the opaque tracker id** — tracker-only items have no spec id; free-prose reason OUTSIDE the hash so rephrasing never duplicates), **no bare tracker issue key rendered in the anchor**. The tracker comment carries the same `id`. **Answer matching:** the normalized `comment` struct gains **optional reply/parent metadata** where the tracker threads (Linear); for **flat trackers (GitHub)** the human's answer comment carries `<!-- flow-next:answer id=<hash> -->`, matched by `id`. A matched answer imports **under the matching `## Open Questions` entry by `id`** (not just `## Sync Log`) and flips the anchor to `answered`.
5. **R16:** reuse status-sync's `tracker.readyState` → `ready` projection as-is (`status-sync.md:365-416`); the pull-before-scan ordering lives in .3/.4.

**Size:** M · independent of .1 (parallel-safe).
**Files:** `flow-next-tracker-sync/steps.md`, `references/adapter-interface.md`, `references/comments-sync.md`, `references/linear-ladder.md` (+ `references/linear-graphql.md`), `references/github.md` (the concrete Linear + GitHub adapter docs that implement `listOpenIssues` + the named ops), `docs/tracker-sync.md`, tests.

## Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-tracker-sync/steps.md:17-23` — Phase-0 gate (fix L19) + where named ops (`comment`) are defined
- `plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md:11-26` — the 8 methods (+ `listOpenIssues`) + the normalized `comment` struct (+ reply/parent metadata)
- `plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md:68-190` — dedup + marker + answer-import path
- `plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md:365-416` — readyState→ready (R16)
- `plugins/flow-next/skills/flow-next-tracker-sync/references/github.md` + `references/linear-ladder.md` — the concrete GitHub/Linear adapters that must implement `listOpenIssues` + the named ops

## Key context
Tracker-sync is projection, not coordination. `listOpenIssues` + the `comment` reply metadata are the only net-new adapter surface — keep transport-blind. GitHub comments are flat (no threads) — the `<!-- flow-next:answer id= -->` marker is the load-bearing fallback. Codex-mirror impact handled in .5.

## Acceptance
- [ ] Phase-0 gate recognizes `FLOW_AUTONOMOUS=1`/`mode:autonomous`; ceremony never prompts; conflicts `sync defer`.
- [ ] `listOpenIssues(filter) → issue[]` added + implemented for Linear+GitHub, filtered to the **exact** `tracker.readyState`, normalized structs; named ops `list-open` + `question <spec-id|tracker-id>` exposed (skill-level, transport-blind).
- [ ] question-anchor `id` hashes stable fields only (no prose, no bare issue key); the normalized `comment` carries optional reply/parent metadata, and a flat-tracker answer (`<!-- flow-next:answer id= -->`) is matched by `id` and imported under the matching Open Question, flipping it to `answered`.
- [ ] `list-open` no-ops (with a note) when `tracker.readyState` is unset; a tracker-only `question` is exempt from the spec-id sync receipt, and its parked/answered state is detected by scanning tracker comments (no spec anchor required).
- [ ] R16 reuses the existing status-sync projection; `docs/tracker-sync.md` documents the parity fix + `listOpenIssues` + the named ops; tests cover the gate, the anchor/answer round-trip (threaded + flat), exact-match enumeration, and the readyState-null no-op.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
