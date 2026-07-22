# Host Backend Workflow (impl-review)

Use when `BACKEND="host"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and (optionally) `TASK_ID` / `BASE_COMMIT`.

**fn-123 R5:** `host` is a NON-EXECUTABLE selection sentinel. Review runs as a host-native fresh-context subagent (skill-owned judgment). No `flowctl host` subcommand, no subprocess path, no model/effort on the backend string — pins live in the AGENTS.md model-routing section.

## Critical rules

1. **DO NOT REVIEW CODE YOURSELF** — you coordinate; a fresh-context host-native subagent reviews
2. Pin the subagent to a **cross-family** model slug (family that did **not** write the diff)
3. Every re-review is a **fresh subagent** — no context reuse, no fabricated resume ids
4. Receipt records actual reviewer model + `"mode": "host"`
5. Fail closed when no cross-family pin is available (never silent same-family self-review)

## Step 1: Resolve cross-family pin

1. Read the AGENTS.md model-routing section (caller routing instructions) for the review role / cross-family pairing.
2. Identify the family that wrote the diff (session model / implementer family).
3. Pick a reviewer slug from a **different** family (uncorrelated blind spots).

**If no cross-family pin is available:**
- **Interactive:** ask the user explicitly (blocking question) which reviewer model/family to use — do not silently self-review
- **Autonomous** (`mode:autonomous` / `FLOW_AUTONOMOUS=1` / Ralph / `REVIEW_RECEIPT_PATH` set): stop with `NEEDS_HUMAN: host review needs a cross-family model pin in AGENTS.md model-routing` — never same-family self-review

## Step 2: Dispatch read-only reviewer subagent

Dispatch a **fresh** read-only reviewer subagent with the resolved pin:

| Host | How to pin |
|------|------------|
| Claude Code | Native subagent `model` param (existing reviewer-subagent arrangement); `disallowedTools: Edit, Write, Task` (or host read-only equivalent) |
| Cursor | In-prompt slug pin on the subagent + TOOL-enforced read-only (dispatch via a `readonly: true` agent definition or Cursor's read-only subagent mode — never a mutation-capable subagent; the reviewer reads untrusted diff content, so read-only cannot be prompt-requested only) |
| Codex | Fresh read-only reviewer subagent via the platform subagent primitive (`spawn_agent` on Codex) with the cross-family pin stated in the prompt; read-only via the platform sandbox |
| Other | Generic fresh-context reviewer; note in the receipt that pin enforcement is host-dependent |

Give the subagent:
- The impl-review rubric ([references/impl-review-prompt.md](references/impl-review-prompt.md))
- Diff scope (`--base` / branch vs main as resolved in Phase 0)
- Task id / focus areas if any
- Prior findings for convergence (on re-review)
- Required verdict tags: `SHIP` / `NEEDS_WORK` / `MAJOR_RETHINK`

Wait for the subagent result (blocking — do not background).

## Step 3: Receipt

Receipt path (same contract as the subprocess backends — fn-90 task-scoped default; explicit `REVIEW_RECEIPT_PATH` always wins):

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt${TASK_ID:+-${TASK_ID}}.json}"
```

Write a receipt compatible with existing consumers:

```json
{
  "type": "impl_review",
  "id": "<task-id or branch scope>",
  "mode": "host",
  "verdict": "<SHIP|NEEDS_WORK|MAJOR_RETHINK>",
  "model": "<actual-reviewer-slug>",
  "spec": "host",
  "session_id": null,
  "review": "<full reviewer output text - findings + verdict>",
  "timestamp": "<ISO-8601>"
}
```

`session_id` is literal `null` — deliberate: host re-reviews are always fresh subagents, and `null` distinguishes "no resumable session by design" from an accidentally incomplete receipt. `review` carries the reviewer's full output — the re-review ratchet reads it to inject prior findings into the next fresh subagent (convergence), so it is REQUIRED, not optional.

Do **not** invent a `session_id` for resume — host re-reviews always spawn a new subagent. Shape stays compatible with convergence/cap/pilot/land consumers (`mode`, `verdict`, `model`, `timestamp`).

## Step 4: Optional phases

When `--deep` / `--validate` / `--interactive` flags are set, run the gated phases from [workflow-common.md](workflow-common.md) / [optional-phases.md](optional-phases.md) where they apply. Host has no `flowctl host deep-pass` / `validate` — if those paths require a subprocess backend, either:
- run the pass as another host-native read-only subagent with the same cross-family pin, or
- skip with an explicit note in the receipt when the pass cannot run without a CLI backend

Never silently drop a required gate without a note.

## Step 5: Return verdict

Return the verdict to SKILL.md's shared Fix Loop. On NEEDS_WORK re-review: **new** subagent every cycle (same pin rules; include prior findings in the new prompt).

## Anti-patterns (Host backend)

- **Self-reviewing** — coordinator never grades its own diff
- **Silent same-family self-review** when no cross-family pin is available
- **Reusing a prior subagent context** for re-review (always fresh)
- **Putting a model on the backend string** (`host:opus`) — rejected by flowctl; pins live in AGENTS.md
- **Calling a non-existent `flowctl host` command**
- **Fabricating resume/session ids** for host receipts
