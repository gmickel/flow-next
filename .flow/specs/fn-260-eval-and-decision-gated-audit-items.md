# Eval- and decision-gated audit items (audit wave 6)

## Goal & Context
<!-- Goal & Context: 50% [paraphrase], 50% [inferred] -->

The 2026-09-24 efficiency audit produced a set of gains that cannot ship on code review alone. Some move instruction text between files or change what a model reads by default; the maintainer's earlier studies showed that moving text to another reachable file does not prove the same behaviour, so each of these needs a preregistered study before it ships. The rest depend on a design call only the maintainer can make. This spec holds both groups in one place so they are not lost and not re-litigated by later work.

Each eval item states the hypothesis, the endpoint that decides it, and the regression evidence that must not get worse. Studies follow the agent-evals methodology (`METHODOLOGY.md`, `lib/evalkit.py`) with the model held constant, a written preregistration before any draw, and KEEP / PARK / negative / inconclusive outcomes all retained. A change ships only on a KEEP.

## Edge Cases & Constraints

- Silence or omission must never win a cost metric: every study scores correctness or coverage alongside tokens, calls or wall time. [inferred]
- Studies use representative external repos where the skill is repository-context sensitive, not only this repo. [inferred]
- Earlier negative results stand as prior evidence: the big-bang review redesign (falsified), delta-scoped review (parked), and the conservative prose rewrite (parked) are not reopened by anything here. [paraphrase]

## Acceptance Criteria

- **R1:** A preregistered agent-evals study decides whether dieting the Claude Code skill-listing descriptions (generated from the existing Codex description table, plus the skills Codex already hides) keeps skill selection accurate. Hypothesis: the dieted listing (about 6.2K characters, under Claude Code's default 8K listing budget on a 200K window) routes natural-language requests to the same skills as the current listing. Endpoint: correct invocation and abstention on positive, negative and ambiguous prompts with the skill listing present (the earlier routing-accuracy study ran without a listing and does not answer this). Regression evidence: no drop in correct selection for any skill. The diet ships only on a KEEP. Errors: a study that cannot reproduce the listing budget behaviour is inconclusive, not a KEEP. [paraphrase]
- **R2:** A preregistered study decides whether splitting `flow --auto`'s instructions by autonomy mode and lifecycle stage keeps autonomous-run behaviour. Hypothesis: loading only the hop's relevant content (backlog-only fences, all-done PR verification, dry-run text, the deprecated chain-stages block and the intake-only routing rows are about 45 KB of the ~115 KB loaded per tick) preserves stage choice and verdicts. Endpoint: identical stage selection and `PILOT_VERDICT` on a fixture set covering ready, backlog, all-done and dry-run hops. Regression evidence: no new wrong-stage dispatch, missed gate or changed verdict. Ships only on a KEEP. Errors: a split that makes any hop read a file it previously never read counts as a regression to investigate, not a pass. [paraphrase]
- **R3:** A preregistered study decides whether moving the work skill's wave-route content into a reference read only when the route decision prints the wave route, and deleting the reviewer-overlap text that no route can reach any more, keeps conductor behaviour. Hypothesis: about 10-12 KB less per rolling conductor with no scheduling change. Endpoint: same route decision, admissions and review scheduling on rolling and wave fixtures. Regression evidence: work's reached-path route tests stay green or are updated to assert structure, not prose (G2). Ships only on a KEEP. Errors: no error surface beyond the route decision. [paraphrase]
- **R4:** A preregistered study decides whether the worker agent can load its rare branches (the CLI-bridge phase and the post-review memory capture phase, about 15 KB together) only when their condition holds. Hypothesis: gated loading keeps implementation quality while cutting per-worker context. Endpoint: task correctness, verification behaviour and scope preservation on the worker-stage bank fixtures, bridged and non-bridged. Regression evidence: no drop in bridged-task success or memory capture on NEEDS_WORK to SHIP transitions. Ships only on a KEEP. Errors: a worker that reaches a gated branch without reading its reference is a failure. [paraphrase]
- **R5:** A preregistered study decides whether moving the drive skill's native-app detail and the triplicated Cursor browser-ask procedure into their existing references keeps drive and QA behaviour on web targets and native targets. Hypothesis: about 1.2K tokens less per drive or QA run. Endpoint: surface detection, driver choice and degradation behaviour on web, Electron and native fixtures. Regression evidence: no wrong-rung selection. Ships only on a KEEP. Errors: no error surface beyond driver selection. [paraphrase]
- **R6:** A preregistered study decides whether rolling workers may run only focused suites plus lint at baseline and verify, with the full gate running once at quiesce as the rolling design intends. Hypothesis: up to two full-suite runs saved per task (about 4-7 minutes on each lane's critical path) without letting cross-module breaks reach the PR. Endpoint: defects caught before the PR opens and total wall time, on multi-task fixtures with a seeded cross-module break. Regression evidence: every seeded break is still caught before make-pr. Ships only on a KEEP. Errors: a break found only after the PR opens is a failure. [paraphrase]
- **R7:** A preregistered study decides whether prime's fact-gathering scouts can be replaced by an ID-keyed inventory emitted by `flowctl prime classify`, keeping the claude-md scout for its real judgment. Hypothesis: about 300K fewer subagent tokens and about 2 minutes less per prime run with the same findings. Endpoint: per-criterion status agreement with the current scouts on representative repos. Regression evidence: no criterion misreported. Ships only on a KEEP. Errors: an inventory field that requires judgment belongs to the host, not flowctl, and disqualifies that field. [paraphrase]
- **R8:** A preregistered study decides whether refine's "40+ questions" anchors should give way to its own "a frontier slot is earned" rule. Hypothesis: question count driven by material uncertainty reduces redundant turns without missing requirements. Endpoint: critical ambiguity discovery and resolution against a sealed answer key. Regression evidence: no premature completion or missed requirement. Ships only on a KEEP. Errors: no error surface beyond question selection. [paraphrase]

## Boundaries

- No change in this spec ships without its study's KEEP; a study result alone does not authorize edits outside the item it decided. [paraphrase]
- Items already assigned to waves 1-5 (fn-255 to fn-259) are out of scope here, including the command-shim hiding, the anchor projection and the quiesce gate receipt. [inferred]
- No study builds new harness machinery when `lib/evalkit.py` already covers the need, and no decision item grows new config keys or flags. [inferred]
- Reopening falsified or parked research (big-bang review, delta-scoped review, generic prose rewrite) is out of scope. [paraphrase]

## Decision Context

These items were separated from the implementation waves because each either changes what a model reads (proven risky by earlier proximity and layout experiments) or needs a product call. Grouping them keeps the implementation waves free of eval gates and keeps the evidence requirement explicit per item. The alternative, folding each eval into the wave that touches the same files, was rejected because it would block otherwise-safe fixes on study timelines.

## Strategy Alignment

"Remember the bitter lesson" asks that compensating scaffolding be evaluated against its absence; R1-R8 apply that to instruction placement. "flowctl grows only under burden of proof" governs R7's inventory and the `flowctl deps` question below: only zero-judgment facts may move into flowctl.

## Parked unknowns

- Product-side importable flowctl entry: fn-190 records the deferral and its reopening triggers; resolved by a real per-call-cost complaint or a compiled-binary port, per fn-190.
- A `flowctl deps --json` command (about 79 s of per-spec calls today, and the deps skill's 10-level phase cap reports deep chains as deadlocked) against backlog mode's "reuse the topo-sort, build no new graph engine" rule; resolved by the maintainer choosing between a flowctl command and fixing the cap in place.
- Whether land may read head-bound spec state from a fetched head commit instead of per-blob GitHub API reads; resolved by the maintainer's call on land's "never trust local state" rule.
- Whether the spec template gains an optional `## Quick commands` section (13 of the last 14 specs have none, so workers run no baseline); resolved by a template decision.
- Which branch follow-up work uses when a merged spec is reopened by a new task (routing cannot resolve it today); resolved by a branch-policy decision.
- Whether tracker push is meant to force-overwrite tracker-side edits; resolved by the maintainer, and it gates fn-255's push divergence check.
- Cleanup sequencing: consolidating flowctl's git wrappers and the four copies of plugin-root template lookup, retiring the pre-1.0 `epics/` layout (still read at about 20 sites), and lazy argparse construction (worth it only after fn-190); resolved by a maintainer decision to schedule them.

## Requirement coverage

| R-ID | Task |
|------|------|
| R1 | fn-N.M (TBD - populate via /flow-next:plan) |
| R2 | fn-N.M (TBD - populate via /flow-next:plan) |
| R3 | fn-N.M (TBD - populate via /flow-next:plan) |
| R4 | fn-N.M (TBD - populate via /flow-next:plan) |
| R5 | fn-N.M (TBD - populate via /flow-next:plan) |
| R6 | fn-N.M (TBD - populate via /flow-next:plan) |
| R7 | fn-N.M (TBD - populate via /flow-next:plan) |
| R8 | fn-N.M (TBD - populate via /flow-next:plan) |
