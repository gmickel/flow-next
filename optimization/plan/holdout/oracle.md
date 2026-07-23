# Sealed P5 scorer — answer key

Keep this file separate from `input.md`. It is scorer-only and must never be
included in the subject prompt.

Each cell is binary. A candidate is eligible only when every baseline-pass cell
still passes. Routing cells additionally require deterministic trace evidence;
prose comprehension alone is insufficient.

| Cell | Pass condition |
|---|---|
| H1 — no implementation leakage | The spec/tasks contain no complete function, module, scenario export, copy-paste expression recipe, or other implementation body. Signatures, field lists, and short pattern anchors remain allowed. |
| H2 — research consumption | The plan carries attachment persistence, Make-owned retry/error handling, submission-ID idempotency, minimal-PII logging, the shared five-state vocabulary, all four audit timestamps, and the pilot rollback boundary into context or acceptance. |
| H3 — R-ID coverage | R1–R6 remain stable and every requirement maps to an existing task or an explicit gap in the requirement-coverage table. |
| H4 — cohesion and sizing | The workflow is decomposed into cohesive S/M tasks. It does not split each Airtable table/view/Make scenario/docs artifact into trivial sequential tasks and does not leave the whole cross-system workflow as one L task. |
| H5 — dependencies and waves | The data/status contract precedes routing/automation that consumes it; pilot/acceptance work depends on the workflow it validates. Independent department-view work may share a wave only when file/resource ownership is genuinely disjoint. |
| H6 — Mermaid condition | Because this is significant cross-service architecture/data flow, the spec contains one simple Mermaid flowchart with 5–10 nodes. It does not emit an ERD or decorative diagram unrelated to the flow. |
| H7 — source grammar and override | The result uses Plan's R-ID prose grammar, task `satisfies` mapping, dependency-ordered execution waves, and does not invent requirements that contradict the frozen research. |
| H8 — tracker route | Off: the tracker reference is not read and there is no tracker side effect/output. On: exactly the tracker reference is read after the existing active+leaf gate; one spec maps to one issue and failure remains best-effort. |
| H9 — HTML route | Off: the HTML reference is not read and there is no artifact output. On: exactly the HTML reference is read after the existing config-snapshot gate; late regeneration, link marker, checklist, Lavish guard, and best-effort behavior remain intact. |
| H10 — review route | Off: the review reference is not read and no review runs. On: exactly the review reference is read after the chosen review signal; re-anchor/fix/review behavior and terminal SHIP contract remain intact. |

