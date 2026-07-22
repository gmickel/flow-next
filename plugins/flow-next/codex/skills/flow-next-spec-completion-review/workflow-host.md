# Host Backend Workflow (spec-completion-review)

Use when `BACKEND="host"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and `SPEC_ID`.

**fn-123 R5:** `host` is a NON-EXECUTABLE selection sentinel. Review runs as a host-native fresh-context subagent (skill-owned judgment). No `flowctl host` subcommand, no subprocess path, no model/effort on the backend string — pins live in the AGENTS.md model-routing section.

## Critical rules

1. **DO NOT REVIEW COMPLETION YOURSELF** — you coordinate; a fresh-context host-native subagent reviews
2. Pin the subagent to a **cross-family** model slug (family that did **not** write the implementation)
3. Every re-review is a **fresh subagent** — no context reuse, no fabricated resume ids
4. Receipt records actual reviewer model + `"mode": "host"`
5. Fail closed when no cross-family pin is available (never silent same-family self-review)

## Step 1: Resolve cross-family pin

1. Read the AGENTS.md model-routing section (caller routing instructions) for the review role / cross-family pairing.
2. Identify the family that wrote the implementation.
3. Pick a reviewer slug from a **different** family.

**If no cross-family pin is available:**
- **Interactive:** ask the user explicitly (plain-text numbered prompt) which reviewer model/family to use — do not silently self-review
- **Autonomous** (`mode:autonomous` / `FLOW_AUTONOMOUS=1` / Ralph / `REVIEW_RECEIPT_PATH` set): stop with `NEEDS_HUMAN: host review needs a cross-family model pin in AGENTS.md model-routing` — never same-family self-review

## Step 2: Dispatch read-only reviewer subagent

Dispatch a **fresh** read-only reviewer subagent with the resolved pin:

| Host | How to pin |
|------|------------|
| Claude Code | Native subagent `model` param; `disallowedTools: Edit, Write, Task` (or host read-only equivalent) |
| Cursor | In-prompt slug pin on the subagent (Cursor honors in-prompt model pins) |
| Other | Generic fresh-context reviewer; note in the receipt that pin enforcement is host-dependent |

Give the subagent:
- Spec requirements / R-IDs / acceptance criteria
- Task list + evidence that work claims done
- Diff / implementation surfaces to check compliance (not code-quality taste — that is impl-review)
- Prior findings for convergence (on re-review)
- Required verdict tags: `SHIP` / `NEEDS_WORK`

Wait for the subagent result (blocking — do not background).

## Step 3: Receipt

Receipt path (same contract as the subprocess backends — spec-scoped default; explicit `REVIEW_RECEIPT_PATH` always wins):

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/completion-review-receipt${SPEC_ID:+-${SPEC_ID}}.json}"
```

Write:

```json
{
 "type": "completion_review",
 "id": "<spec-id>",
 "mode": "host",
 "verdict": "<SHIP|NEEDS_WORK>",
 "model": "<actual-reviewer-slug>",
 "spec": "host",
 "session_id": null,
 "timestamp": "<ISO-8601>"
}
```

`session_id` is literal `null` — host re-reviews are always fresh subagents; `null` distinguishes by-design non-resumability from an incomplete receipt. Shape stays compatible with existing consumers.

## Step 4: Status write

Host has no handler-owned status write. After the terminal verdict (or when SKILL.md's fix loop exits), ensure completion status is recorded per SKILL.md Step 3 (`flowctl spec set-completion-review-status`) when the caller expects it — or write status here if this skill is the sole owner of the terminal path for host:

```bash
# On SHIP / capped NEEDS_WORK as applicable (caller may also write — do not double-conflicting writes)
$FLOWCTL spec set-completion-review-status "$SPEC_ID" --status ship --json # on SHIP
$FLOWCTL spec set-completion-review-status "$SPEC_ID" --status needs_work --json # on NEEDS_WORK at cap
```

Prefer a single write: if SKILL.md Step 3 always runs after return, skip duplicate writes here and only return the verdict.

## Step 5: Return verdict

Return the verdict to SKILL.md's shared Fix Loop. On NEEDS_WORK re-review: **new** subagent every cycle (same pin rules; include prior findings).

## Anti-patterns (Host backend)

- **Self-reviewing** — coordinator never grades its own completion claim
- **Silent same-family self-review** when no cross-family pin is available
- **Reusing a prior subagent context** for re-review (always fresh)
- **Putting a model on the backend string** (`host:opus`) — rejected by flowctl; pins live in AGENTS.md
- **Calling a non-existent `flowctl host` command**
- **Fabricating resume/session ids** for host receipts
