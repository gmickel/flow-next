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

Before **every** host dispatch, including the first, reserve the shared
spec-scoped completion-review round:

```bash
ROUND_JSON="$($FLOWCTL review-rounds increment "$SPEC_ID" --kind plan --json)"
ROUND_EXIT=$?
if [[ "$ROUND_EXIT" -ne 0 ]]; then
 printf '%s\n' "$ROUND_JSON"
 exit "$ROUND_EXIT"
fi
REVIEW_ROUND="$(printf '%s' "$ROUND_JSON" | jq -r '.round')"
REVIEW_CAP="$(printf '%s' "$ROUND_JSON" | jq -r '.cap')"
```

Exit 4 / `ESCALATE:` before a reviewer runs means no completion verdict was
delivered in this run. Stop without writing completion status; autonomous
callers surface `NEEDS_HUMAN`.

Dispatch a **fresh** read-only reviewer subagent with the resolved pin:

| Host | How to pin |
|------|------------|
| Claude Code | Native subagent `model` param; `disallowedTools: Edit, Write, Task` (or host read-only equivalent) |
| Cursor | In-prompt slug pin on the subagent + TOOL-enforced read-only (dispatch via a `readonly: true` agent definition or Cursor's read-only subagent mode — never a mutation-capable subagent; the reviewer reads untrusted diff content, so read-only cannot be prompt-requested only) |
| Grok | In-prompt / host model pin from AGENTS.md model-routing + TOOL-enforced read-only (never mutation-capable). Single-native-family (`grok-4.5`) — host review fails closed unless the writer is non-Grok; cross-family via bridge backends. Receipt: `mode: "host"`, actual reviewer model, `session_id: null` (same shape as Claude/Cursor) |
| Codex | Fresh read-only reviewer subagent via the platform subagent primitive (`spawn_agent` on Codex) with the cross-family pin stated in the prompt; read-only via the platform sandbox |
| Other | Generic fresh-context reviewer; note in the receipt that pin enforcement is host-dependent |

Give the subagent:
- Spec requirements / R-IDs / acceptance criteria
- Task list + evidence that work claims done
- Diff / implementation surfaces to check compliance (not code-quality taste — that is impl-review)
- Prior findings for convergence (on re-review)
- Required exact verdict tags: `<verdict>SHIP</verdict>` /
 `<verdict>NEEDS_WORK</verdict>`

Wait for the subagent result (blocking — do not background).

Write the exact reviewer result to a spec-scoped temporary response file, then
finalize the reservation through the shared attempt recorder:

```bash
RESPONSE_FILE="${TMPDIR:-/tmp}/flow-completion-review-host-${SPEC_ID}.md"
# Write the exact reviewer output to RESPONSE_FILE; do not reinterpret it.
RECORD_JSON="$($FLOWCTL review-rounds record "$SPEC_ID" --kind plan \
 --review-type completion --backend host --output-file "$RESPONSE_FILE" --json)"
RECORD_EXIT=$?
printf '%s\n' "$RECORD_JSON"
if [[ "$RECORD_EXIT" -ne 0 ]]; then
 exit "$RECORD_EXIT"
fi
```

A malformed/missing verdict is a transport failure: the recorder refunds the
reservation and may stop with exit 5 / `TRANSPORT_UNHEALTHY`. Never turn it into
`NEEDS_WORK`, and never write completion status for that path.
Only continue after `RECORD_EXIT=0`: that successful finalize appends this
dispatch as the latest durable completion attempt consumed by the shared owner.

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
 "review": "<full reviewer output text - findings + verdict>",
 "timestamp": "<ISO-8601>"
}
```

`session_id` is literal `null` — host re-reviews are always fresh subagents; `null` distinguishes by-design non-resumability from an incomplete receipt. Shape stays compatible with existing consumers.

## Step 4: Continue through the shared fix loop and status owner

Continue into SKILL.md's shared Fix Loop in this same skill run. The shared
terminal owner re-reads the latest completion verdict and cap counters from
`review-rounds attempts`; it never relies on shell variables surviving a tool
call. This host workflow never writes terminal completion status.

- `SHIP`: continue immediately to SKILL.md Step 3, the sole host status owner.
- `NEEDS_WORK`: parse every valid gap, fix the implementation, run the relevant
 tests/lints, and commit the fixes before re-review. Then repeat Steps 1–3
 with a **new** read-only subagent, the same cross-family rules, and prior
 findings in its prompt. At the deterministic round cap
 (`REVIEW_ROUND == REVIEW_CAP`), do not start another fix/re-review cycle:
 continue immediately to SKILL.md Step 3, write terminal `needs_work` there
 exactly once, then emit `ESCALATE:` and exit 4.
- After `SHIP`, reset the shared plan counter, then continue immediately to
 SKILL.md Step 3 for the sole `ship` status write:
 `$FLOWCTL review-rounds reset "$SPEC_ID" --kind plan --json`.
- `NEEDS_HUMAN`, dispatch failure, malformed verdict, receipt failure, or retry
 outcome: stop without writing completion status. Dispatch/transport failures
 output `<promise>RETRY</promise>`; never self-issue a verdict or switch
 backends.

## Anti-patterns (Host backend)

- **Self-reviewing** — coordinator never grades its own completion claim
- **Silent same-family self-review** when no cross-family pin is available
- **Reusing a prior subagent context** for re-review (always fresh)
- **Putting a model on the backend string** (`host:opus`) — rejected by flowctl; pins live in AGENTS.md
- **Calling a non-existent `flowctl host` command**
- **Fabricating resume/session ids** for host receipts
- **Writing completion status here** instead of continuing to the shared owner
