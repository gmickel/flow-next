# Tracker projection (optional; best-effort)

Read this file only when the Phase 0.2b gate sentinel printed - bridge active AND `tracker.charts` is the literal `on`. When the gate is closed, flowctl still succeeds and `tracker_projection.skipped` names the reason (`tracker.charts_off` / `bridge_inactive`); nothing here applies.

Chart projection rides the post-fn-141 lifecycle facade. Local chart
mutations always commit first; remote projection never blocks them.

Gate (both required): bridge active AND `tracker.charts` is the literal `on`.
The perEvent vocabulary (`off | pull | push | reconcile | comment`) does not
select chart ops - chart is always a local-first **push** of the committed
revision when the gate is open. When the gate is closed, flowctl still
succeeds and `tracker_projection.skipped` names the reason
(`tracker.charts_off` / `bridge_inactive`).

With the gate open:

```bash
# flowctl chart mutations already call the facade once per committed revision
# (event: chart.create|chart.wire|chart.claim|chart.release|chart.resolve|
#  chart.supersede|chart.outOfScope|chart.briefing|chart.abandon|chart.reopen).
# Host recovery handoff on partial remote success: re-invoke the same chart
# command or rely on the next mutation - event markers + aggregate receipt
# dedupe so retry converges without duplicate issues/comments/relations.
# Equivalent one-shot surface (automation):
#   "$FLOWCTL" tracker sync "chart:<chart-id>" --op push --event chart \
#     <legal file flags>
# Evidence for any synthesized comment: evidence=<chart-revision-sha>.
# Chart synthesizes owned parent rollup / decision body blocks only - never
# free-form status masquerading as provider workflow.
# Best-effort - a tracker failure never rolls back local chart state.
```
