# fn-32-opt-in-review-flags.1 --validate flag: validator pass + flowctl validate subcommands + receipt fields

## Description

Implement `--validate` flag on `/flow-next:impl-review`. After NEEDS_WORK verdict, dispatch a validator pass (same backend session) that independently re-checks each finding. Drops false-positives; if all drop, verdict upgrades to SHIP. Receipt carries validator metadata.

**Size:** M

**Files:**
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md` — flag parsing
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md` — validator-pass flow
- `plugins/flow-next/skills/flow-next-impl-review/validate-pass.md` (new) — validator prompt template
- `plugins/flow-next/scripts/flowctl.py` — `codex validate`, `copilot validate` subcommands
- `.flow/bin/flowctl.py` (mirror)

## Validator prompt template (validate-pass.md)

```markdown
# Validator prompt

You are validating review findings for false positives. For each finding below, independently re-check it against the current code and decide whether the finding is actually valid.

Conservative bias: **only drop findings that are clearly wrong.** When uncertain, keep the finding. A kept false-positive is cheap (one extra check by the fixer); a dropped real bug is expensive (escapes to production).

For each finding:
1. Open the cited file and read around the cited line (±20 lines)
2. Check whether the claimed issue is actually present in the current code
3. Look for guards, handlers, or assumptions that address the concern elsewhere in the call chain
4. Consider whether the finding is factually correct about the language/framework

Return one line per finding in this exact format:

  <finding-id>: <validated: true | false> -- <one-sentence reason>

Examples:
  f1: validated: true -- null deref confirmed; no upstream guard
  f2: validated: false -- null check already present at src/auth.ts:40
  f3: validated: true -- race condition reproducible with concurrent requests
  f4: validated: false -- suggested fix misunderstands TypeScript narrowing behavior

Do not re-score confidence, re-classify severity, or invent new findings. Decide only: is this finding a real issue in the current code, or not?
```

## flowctl `codex validate` subcommand

```
flowctl codex validate [--findings-file <path>] [--receipt <path>] [--model <m>] [--effort <e>] [--json]
```

Behavior:
1. Read findings JSON from `--findings-file` (one per line: `{id, severity, file, line, title, suggested_fix, classification, confidence}`)
2. Read session from existing receipt at `--receipt` path — use `--receipt` for session continuity
3. Build validator prompt from template + findings
4. Invoke `codex exec` with resumed session (passes `--session-id <id>` from receipt)
5. Parse output lines; build `{dispatched, dropped, reasons}` record
6. Update receipt with `validator` object; preserve all other fields
7. Return JSON record with drops

## flowctl `copilot validate` subcommand

Same signature; uses Copilot CLI session resumption.

## Skill integration

In `impl-review/SKILL.md` argument parsing:

```bash
VALIDATE=false
for arg in $ARGUMENTS; do
  case "$arg" in
    --validate) VALIDATE=true ;;
  esac
done

# Env opt-in
if [[ "${FLOW_VALIDATE_REVIEW:-}" == "1" ]]; then
  VALIDATE=true
fi
```

In workflow.md, after the primary review returns NEEDS_WORK:

```bash
if [[ "$VALIDATE" == "true" && "$VERDICT" == "NEEDS_WORK" ]]; then
  FINDINGS_FILE=$(mktemp)
  # parse primary review output into findings JSON lines
  # ... (parser code; extract file/line/severity/title from review markdown)

  case "$BACKEND" in
    codex) $FLOWCTL codex validate --findings-file "$FINDINGS_FILE" --receipt "$RECEIPT_PATH" ;;
    copilot) $FLOWCTL copilot validate --findings-file "$FINDINGS_FILE" --receipt "$RECEIPT_PATH" ;;
    rp) $FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file "$VALIDATOR_MSG" ;;
  esac

  # Parse validator output, drop false-positives from findings set
  # Re-compute verdict: if all findings dropped → SHIP; else → NEEDS_WORK
fi
```

For rp backend: send the validator prompt in the same chat (session continuity is automatic in rp-cli); parse response from rp chat-send output.

## Receipt extension

Add to each backend's receipt writer:

```python
if validator_result:
    receipt_data["validator"] = {
        "dispatched": validator_result.dispatched,
        "dropped": validator_result.dropped,
        "reasons": validator_result.reasons,  # list of {file, line, reason}
    }
```

## Verdict re-computation

After validator drops, re-evaluate:
- If 0 findings remaining → verdict = SHIP
- If ≥1 finding remaining → verdict stays NEEDS_WORK (with the surviving findings)

Update receipt `verdict` field if upgraded.

## Acceptance

- **AC1:** `--validate` flag parsed correctly; `FLOW_VALIDATE_REVIEW=1` env var also enables.
- **AC2:** Validator pass runs only on NEEDS_WORK verdict from primary review.
- **AC3:** `flowctl codex validate` and `flowctl copilot validate` subcommands exist, accept findings-file + receipt path, return structured results.
- **AC4:** Validator uses same backend session via receipt's `session_id` — no fresh session per validation.
- **AC5:** Validator prompt in `validate-pass.md` follows conservative bias ("when uncertain, keep").
- **AC6:** Parsed validator output correctly identifies `validated: true|false` per finding with reasons.
- **AC7:** Receipt carries `validator` object with `dispatched`, `dropped`, `reasons`.
- **AC8:** If all findings drop, verdict upgrades to SHIP; receipt reflects.
- **AC9:** `--validate` off → existing behavior unchanged; no validator pass invoked.
- **AC10:** Ralph smoke with `FLOW_VALIDATE_REVIEW=1` set: passes, receipts carry validator data.

## Dependencies

- Depends on Epic fn-29 (confidence anchors + pre-existing classification shape findings for validator to work against)

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
