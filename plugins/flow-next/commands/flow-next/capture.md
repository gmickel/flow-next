---
name: flow-next:capture
description: Synthesize the current conversation into a flow-next spec at `.flow/specs/<spec-id>.md` — source-tagged, mandatory read-back, no silent overwrite
argument-hint: "[mode:autofix] [--rewrite <spec-id>] [--from-compacted-ok] [--yes]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-capture`

The ONLY purpose of this command is to call the `flow-next-capture` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill verbatim. The skill handles mode detection (`mode:autofix` token + `--rewrite <id>` + `--from-compacted-ok` + `--yes`), pre-flight checks (duplicate / compaction / idempotency), conversation evidence extraction, source-tagged synthesis, must-ask cases, mandatory read-back loop, and the flowctl `spec create` + `spec set-plan` write.
