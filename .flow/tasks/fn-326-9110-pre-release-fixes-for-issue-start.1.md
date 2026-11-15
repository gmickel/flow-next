---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-326-9110-pre-release-fixes-for-issue-start.1 Issue start: interrupted-capture recovery, cross-ref link resolution, question rounds, Jira site check, always review, no capture status conflict

## Description
Fix fn-325's issue start (merged in #608) for the audit findings in the parent spec: R1 interrupted capture recovery, R2 links on any fetched ref (including JSON-only changes to specs already on the default branch), R3 plain answer then follow-up question posts a new round, R4 Jira URL from another site stops before writes, R5 every work hop of an issue start runs implementation review (Gordon's decision), R6 no backlog-vs-ready status conflict at the capture push. Read the parent spec and the Codex audit reasoning summarised there. Prefer prose fixes in issue-start.md / from-issue.md / auto.md; add flowctl code only where a deterministic fact needs it (R2 cross-ref link lookup, R3 round handling may need wire question support). Update agent_docs/conduct/flow.md and capture.md checklist lines for changed contracts.

Touches: plugins/flow-next/skills/flow-next-flow/references/issue-start.md, plugins/flow-next/skills/flow-next-flow/auto.md, plugins/flow-next/skills/flow-next-capture/references/from-issue.md, plugins/flow-next/skills/flow-next-capture/SKILL.md, plugins/flow-next/skills/flow-next-capture/workflow.md, plugins/flow-next/scripts/flowctl.py, plugins/flow-next/scripts/flowctl-help.txt, plugins/flow-next/scripts/flowctl_tracker/wire/__init__.py, plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json, plugins/flow-next/codex/, agent_docs/conduct/flow.md, agent_docs/conduct/capture.md, plugins/flow-next/tests/test_flow_auto.py, plugins/flow-next/tests/test_capture_chart_handoff.py

## Acceptance
R1-R6 of the parent spec hold, each with the test or prose-contract pin the spec names. Fake-transport tests for any flowctl change; live recording on Linear FLOW for R3 and R6 (issues titled "[fn-326 live check] ...", canceled afterwards).

## Done summary
Fixed issue start for R1-R5. R6 is not fixed: the conflict comes from tracker status policy code outside this task's Touches (see BLOCKED below).

Tier: session (jev intelligent 0.43) at default effort (model: claude-opus-5-5)

What changed (commit 46c5148c8):
- R1: issue-start.md step 2. A linked spec whose spec file has no commit yet is an interrupted capture. The run finishes step 5 from where it stopped (checks, `spec ready`, branch, capture commit, push), and the spec keeps the design review before any work hop. Pinned by test_flow_auto IssueStartContract.test_interrupted_capture_is_finished_before_work.
- R2: new read-only `flowctl specs --refs [--fetch] --tracker-id <durable> [--json]`. It lists every spec whose JSON links the id, in the checkout (committed or not) and on every local and remote-tracking ref. A JSON-only link change and a spec already on the default branch both count. issue-start.md step 2 now uses it in place of the three-place lookup, and a `fetch_error` stops NEEDS_HUMAN. Test: IssueStartLinkedSpecAcrossRefs.test_json_only_link_on_a_remote_branch_is_found (bare origin, spec on main, link added on a pushed branch by a JSON-only commit).
- R3: new `tracker wire question --reply-settles` flag. Any later comment that is not a flow-next question settles the round, so a follow-up after a plain reply posts once and a rerun of an unanswered round dedupes. The default answer-marker protocol (backlog mode) is unchanged and asserted. issue-start.md steps 3 and 6 use the flag. Fake-transport test: IssueStartQuestionRounds.test_plain_reply_settles_the_round_and_a_rerun_dedupes. Live on Linear FLOW-121, now Canceled: round 1 posted; its rerun gave posted:false; plain reply; follow-up posted:true with reopened:true; its rerun gave posted:false; 3 comments in total.
- R4: issue-start.md step 1. A Jira URL counts only when its host is the host of `tracker.perTracker.baseUrl`. A URL from another site stops NEEDS_HUMAN with `issue URL is not on <baseUrl>` before any write. Bare keys and same-site URLs match as before. Pinned by test_jira_url_from_another_site_stops_before_writes.
- R5: issue-start.md has a new "Implementation review on every work hop" paragraph: the risk rule never skips review there. With no backend configured, work's existing skip stands. auto.md's work dispatch appends the context `issue start: run implementation review on every task; the risk rule does not skip it`. Pinned by test_every_work_hop_runs_implementation_review.
- agent_docs/conduct/flow.md: the `--from-issue` row covers R1-R5. Codex mirror synced (21 agents). MANIFEST.json regenerated.

Base vs head: all 5 new tests fail on base a59e4637 (4 assertion failures, 1 TypeError for the missing `reply_settles` keyword) and pass on head.

BLOCKED: DESIGN_CONFLICT
Task: fn-326-9110-pre-release-fixes-for-issue-start.1
Summary: The R6 status conflict comes from flowctl_tracker/status/policy.py decide(), not from readiness order. A spec with no tasks normalizes to `backlog`, and an issue in Todo normalizes to `todo`. decide('backlog', None, 'backlog', 'todo', 'none') returns conflict/unmapped, so running `spec ready` before the push changes nothing. policy.py is outside this task's Touches.
Impact: R6 (and its live Linear recording) stays open. Task 5's end-to-end run will still show the capture-push status conflict.
Suggested resolution: mirror the existing EARLY AGREEMENT branch in decide() so both EARLY orders are a no-op at the tracker's slot. Replace `if (flow_norm == "todo" and tracker_norm == "backlog" and requested_to in ("todo", "backlog")):` with `if ({flow_norm, tracker_norm} == {"todo", "backlog"} and requested_to in ("todo", "backlog")):` and update its comment: an unplanned spec against an issue a person moved into the ready lane is the same "not started" bucket. Add a policy test and a live Linear push recording.

Follow-ups (outside Touches, not done):
- plugins/flow-next/docs/flowctl.md documents `specs --refs` but not `--tracker-id`.
- plugins/flow-next/docs/tracker-sync.md (wire question semantics, line ~407) does not mention `--reply-settles`. That file is in task 2's Touches.
- No capture prose changed. R6 needs no capture change once the policy fix lands, so agent_docs/conduct/capture.md is untouched.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)

Conductor fix after review: find_linked_specs fails closed on a missing or unparseable spec JSON blob (partial clone); issue start stops NEEDS_HUMAN on a failed lookup (commits 0ede9af89 test, aa8cdee9c fix).
R6 moved to task 2 (BLOCKED: DESIGN_CONFLICT here: the conflict comes from status/policy.py decide(), outside this task's Touches).

stage: impl-review - ran codex three lenses NEEDS_WORK (1 finding: unreadable JSON read as no link) then re-review SHIP (model: gpt-6.1-sol)
stage: plan-sync - skipped(config: planSync.enabled=false)
Tier: session (jev intelligent 0.43) at default effort (model: claude-opus-5-5)
## Evidence
- Commits: c060b21f755ec5ba4f280842a9798ddb25879fd8, 0ede9af89a35e00065128bd5902726aecbb911a9, aa8cdee9cdab67dc472f6f2ae3fb62169ac0d5a2
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_flow_auto.py' (+ capture_chart_handoff, tracker_wire, tracker_conformance, flow_routing, spec_ref_index, flowctl_surface, tracker_sync_backlog_mode, tracker_distribution); live Linear FLOW-121 question rounds
- PRs: