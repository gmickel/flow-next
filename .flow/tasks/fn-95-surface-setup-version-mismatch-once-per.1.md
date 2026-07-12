---
satisfies: [R1, R2, R3, R5, R6, R8]
---

## Description
Escalate the version-mismatch pre-check in INTERACTIVE skills from silent echo to a once-per-version blocking ask, with acknowledgment persisted.

**Size:** M | **Files:** every canonical skill carrying the `## Pre-check: Local setup version` block EXCEPT pilot/land (enumerate by grep at implementation time; spec cites interview SKILL.md:22-33 as the reference block), NO flowctl changes

## Approach
- Per the spec (read .flow/specs/fn-95-surface-setup-version-mismatch-once-per.md in full - it carries exact anchors and the frozen three-option set): extend the existing pre-check with one jq read of the new optional `version_ack` field in `.flow/meta.json`; on mismatch with no matching ack, ask via the blocking question tool with the frozen options (Refresh now = instruct user to run /flow-next:setup; Remind me next version = write version_ack via jq + same-dir tmp + atomic mv, matching setup's own meta.json write pattern; Skip this run = per-run, re-asks next invocation).
- Autonomy suppression: under the existing marker family (FLOW_RALPH / REVIEW_RECEIPT_PATH / FLOW_AUTONOMOUS / mode:autonomous - same set setup honors), fall back to today's echo. NEVER name the ask tool in autonomous-branch prose (memory R2 rule; sync-codex anchors).
- Fail-open preserved: missing meta.json/field = silent continue, exactly as today.
- Keep the pre-check detection lines byte-identical where they are sync-codex anchors; the ask addition uses the canonical AskUserQuestion form that sync-codex.sh already rewrites.

## Key context
- Prose is executable contract: every jq/field verified against real meta.json shape; each fenced block re-declares its vars; POSIX classes.
- fn-92 interaction (recorded in fn-92 plan): this ask sits OUTSIDE fn-92's R15 one-question budget.

## Acceptance
- [ ] All interactive pre-check skills escalate on mismatch, ask at most once per plugin version (ack persisted in meta.json version_ack, re-arms on new version)
- [ ] Skip = per-run; Remind-me = per-version; Refresh instructs /flow-next:setup
- [ ] Autonomy markers suppress the ask (echo fallback); fail-open when meta.json/field absent
- [ ] version_ack written atomically (same-dir tmp + mv); init/doctor tolerate the new field
- [ ] No ask-tool token in autonomous prose; sync-codex validation passes

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
