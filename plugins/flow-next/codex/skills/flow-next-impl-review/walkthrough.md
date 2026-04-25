# Interactive walkthrough (fn-32.3 --interactive)

Per-finding walkthrough flow that lets a **human user** decide what happens to
each review finding on a NEEDS_WORK verdict. Active only when:

- `--interactive` flag set at invocation time
- Primary review verdict is NEEDS_WORK (or still NEEDS_WORK after validator)
- **Not in Ralph mode** (`REVIEW_RECEIPT_PATH` and `FLOW_RALPH` both unset)

**No env var form.** `--interactive` is per-invocation only — this is a
hard-coded rule in SKILL.md to prevent Ralph from accidentally engaging a flow
that requires user input. If `REVIEW_RECEIPT_PATH` is set OR `FLOW_RALPH=1`,
the skill exits 2 with a clear error before running anything. See SKILL.md
"Interactive flag + Ralph-block" for the guard.

## Finding source

The walkthrough consumes the **merged finding set** from the primary review,
with validator drops applied if `--validate` also ran, and deep-pass findings
fingerprint-deduped / cross-pass promoted if `--deep` also ran. It doesn't
care which pass produced each finding — it reads the merged output.

Extract findings into `/tmp/walkthrough-findings.jsonl` using the same JSON
Lines format as the validator pass (see workflow.md "Validator Pass"):

```jsonl
{"id":"f1","severity":"P1","confidence":75,"classification":"introduced","file":"src/auth.ts","line":42,"title":"null deref in middleware","suggested_fix":"Add current_user guard before line 42"}
{"id":"f2","severity":"P2","confidence":50,"classification":"introduced","file":"src/cart.ts","line":88,"title":"off-by-one on empty cart","suggested_fix":"Use >= 1 instead of > 0"}
```

If `--deep` was used, findings from deep passes retain their `pass` field
(e.g., `"pass": "adversarial"`). If `--validate` was used, only kept findings
appear. If neither, all primary findings appear.

## Pre-flight: load blocking question tool

Before the walkthrough loop, the skill must have access to a **blocking
question tool** (a tool that pauses the agent until the user answers):

Use `request_user_input`. It's a deferred tool — call first to load its schema if it isn't already in scope.

If the tool is unreachable, fall through to a chat-prompt fallback (print
the question, wait for the user's next message). The fallback is less
reliable — prefer the blocking tool wherever available.

## Per-finding flow

For each finding in the merged set:

1. Render the finding block:

 ```
 Finding N/M:
 [P1, confidence 75, introduced] src/auth.ts:42 — null deref in middleware

 Detail: Accessing user.role without a guard leads to undefined when the
 session cookie is missing. The middleware runs before any authentication
 resolver, so undefined propagates into permission checks.

 Suggested fix: Add a current_user guard before line 42.

 What should the agent do?
 1. Apply — implement the suggested fix
 2. Defer — leave unresolved; record in .flow/review-deferred/<branch>.md
 3. Skip — ignore this finding entirely
 4. Acknowledge — note it but take no action (not a bug, or intentional)
 5. LFG the rest — apply recommended action for this + all remaining findings
 ```

2. Present via the platform blocking question tool with five labelled choices:
 `Apply`, `Defer`, `Skip`, `Acknowledge`, `LFG the rest`.

3. Record the user's decision. Accumulate into four lists:
 - **Apply list** — findings to fix via fixer dispatch
 - **Defer list** — findings to record in the defer sink
 - **Skip list** — findings to log only
 - **Acknowledge list** — findings noted but not actioned

4. If the user picked **LFG the rest**, exit the loop and auto-classify every
 remaining finding:

 | Finding shape | Auto-action |
 |---------------|-------------|
 | P0 or P1 @ confidence ≥ 75 | Apply |
 | Everything else | Defer |

 (The simple P0/P1@75 rule mirrors the suppression gate used in the primary
 review: anything worth surviving the gate is worth applying; lower-signal
 survivors default to Defer so the user can revisit them later.)

## Branch slug + defer sink

The defer sink is a markdown file under `.flow/review-deferred/`, one per
branch. Branch slug derivation:

```bash
BRANCH=$(git branch --show-current)
# tr '/' '-' handles feature/foo-style branches; strip anything non-slug-safe
BRANCH_SLUG=$(printf '%s' "$BRANCH" | tr '/' '-' | tr -cd 'a-zA-Z0-9-_.')
DEFER_FILE=".flow/review-deferred/${BRANCH_SLUG}.md"
```

Create `.flow/review-deferred/` if absent. The file is **append-only**: each
review session creates a new `## <timestamp> — review session <receipt-id>`
section. The user revisits this file manually; the walkthrough never deletes
existing content.

Use the helper subcommand (handles the append atomically):

```bash
$FLOWCTL review-walkthrough-defer \
 --findings-file /tmp/walkthrough-defer.jsonl \
 --receipt "$RECEIPT_PATH" \
 --json
```

The subcommand:
- Derives `BRANCH_SLUG` from the current branch (or `--branch` override)
- Creates `.flow/review-deferred/` if absent
- Appends a timestamped section with one bullet per deferred finding
- Reads receipt `id` / `session_id` to stamp the section header
- Prints the absolute path of the updated file (JSON or text)

Sink format:

```markdown
# Deferred review findings — <branch-slug>

## 2026-04-24 18:42 — review session fn-32.3 (sess-abc)

- [P1, confidence 75, introduced] src/auth.ts:42 — null deref in middleware
 - Suggested: Add current_user guard before line 42
 - Deferred reason: deferred by user

- [P2, confidence 50, introduced] src/cart.ts:88 — off-by-one on empty cart
 - Suggested: Use >= 1 instead of > 0
 - Deferred reason: deferred by user
```

(Users may add prose between sessions; the helper always appends after the
last `## ` header, never rewrites.)

## After walkthrough

### Apply list → fixer dispatch

If the Apply list is non-empty, dispatch the fixer (worker agent) for those
findings only. Do not re-run the primary review inside this session — commit
the fixes and exit. Re-review is a separate user action.

```bash
# Write a targeted fix prompt for the worker agent
cat > /tmp/walkthrough-apply.md <<EOF
The user reviewed the findings below and chose Apply. Implement fixes for
these findings only. Do not address Defer / Skip / Acknowledge items.

$(cat /tmp/walkthrough-apply.jsonl | jq -r '"- [\(.severity), confidence \(.confidence)] \(.file):\(.line) — \(.title)\n Fix: \(.suggested_fix)"')
EOF
```

### Defer list → sink

Append via the `flowctl review-walkthrough-defer` helper (see above). The
sink is the **only** durable record of deferred findings — it is not in the
receipt (receipt only carries the count).

### Skip / Acknowledge lists → receipt only

No filesystem write beyond the receipt. The counts appear in
`receipt.walkthrough`.

### Update receipt with walkthrough counts

The record subcommand stamps the receipt atomically:

```bash
$FLOWCTL review-walkthrough-record \
 --receipt "$RECEIPT_PATH" \
 --applied "${#APPLY_LIST[@]}" \
 --deferred "${#DEFER_LIST[@]}" \
 --skipped "${#SKIP_LIST[@]}" \
 --acknowledged "${#ACK_LIST[@]}" \
 --lfg-rest "${LFG_USED:-false}" \
 --json
```

Receipt extension:

```json
{
 "type": "impl_review",
 "id": "fn-32.3",
 "mode": "codex",
 "verdict": "NEEDS_WORK",
 "session_id": "sess-abc",
 "walkthrough": {
 "applied": 3,
 "deferred": 2,
 "skipped": 1,
 "acknowledged": 0,
 "lfg_rest": false
 },
 "walkthrough_timestamp": "2026-04-24T18:42:00Z"
}
```

All fields are **additive** — existing Ralph scripts and receipt consumers
read `verdict` as before and ignore the new `walkthrough` key. (Note: Ralph
never sees this block because `--interactive` hard-errors in Ralph mode.)

## Verdict after walkthrough

- **Apply list empty** → verdict stays NEEDS_WORK (no fixer dispatch). The
 user explicitly chose not to fix anything this session. Exit.
- **Apply list non-empty** → fixer runs, commits fixes, exits. Re-review is
 a separate `/flow-next:impl-review --interactive` invocation (or without
 `--interactive` — receipt carries session_id so the primary review
 continues its chat).

Walkthrough never flips the verdict itself. The verdict was set by the
primary review (or validator); walkthrough only sorts findings into buckets
and records decisions.

## Acceptance criteria coverage (R-IDs from fn-32 epic)

- **R8:** Per-finding blocking question with five options ✓ (§ "Per-finding flow")
- **R9:** Ralph env detection hard-errors with clear message ✓ (SKILL.md "Interactive flag + Ralph-block")
- **R10:** `.flow/review-deferred/<branch-slug>.md` as a durable record ✓ (§ "Branch slug + defer sink")
- **R11:** Apply list dispatches fixer; Skip/Acknowledge logged no-op ✓ (§ "After walkthrough")
- **R12:** Receipt extensions additive / Ralph-ignoring ✓ (§ "Update receipt")

## Anti-patterns

- **Running walkthrough in Ralph mode** — hard error at skill entry; never
 silently downgrade to non-interactive.
- **Rewriting the defer file** — append-only. Users may have added manual
 context between sessions.
- **Committing before the user chooses "Apply"** — the fixer runs only for
 Apply-list findings. Do not auto-commit from a Defer/Skip/Acknowledge
 decision.
- **Running the loop on a SHIP verdict** — walkthrough only makes sense on
 NEEDS_WORK (or still-NEEDS_WORK after validator). On SHIP, the skill
 exits cleanly without asking anything.
- **Re-entering the walkthrough within the same session** — after fixer
 dispatch + commit, exit. Re-review is a fresh invocation by the user.
