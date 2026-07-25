# Structured review-artifact schema in receipts

## Goal & Context
<!-- scope: business -->

Review receipts today carry verdicts plus free prose; downstream consumers (the MergeFoundry cockpit's finding navigation and report cards, but equally any receipt reader) must regex findings out of markdown. The review skills ALREADY mandate a structured finding shape in their prompts (Severity / Location / Problem / Suggestion blocks, ratchet numbering) - the structure exists at generation time and is thrown away at receipt-write time. This spec captures it: review receipts gain a structured `findings` array (file+line anchors, severity, R-ID linkage where stated, per-finding status) emitted by DETERMINISTIC parsing of the reviewer output the passes already produce.

Hard constraints (MergeFoundry MASTERPLAN decision 5, binding): NO extra LLM calls anywhere; NO re-bloating of the prompt-dieted skills (prompt deltas limited to tightening the already-mandated output format, net-zero-or-negative tokens); NO meaningful latency (parsing is string work at receipt-write time); flow-next-only UX must not degrade (receipts stay human-readable; the prose stays).

## Scope
<!-- scope: technical -->

- Receipt schema: `findings: [{ordinal, severity, confidence?, classification?, file?, line?, title, body, suggestion?, rIds: [], status?}]` (severity/confidence/classification mirror the vocabulary flowctl's own review prompt templates already mandate: Critical/Major/Minor/Nitpick + P0-P3, discrete confidence anchors, introduced/pre-existing classification) added to review-shaped receipts (plan_review / impl_review / completion_review, all backends incl. rp explicit path and host). Additive and optional - absent on old receipts, never breaking readers.
- A deterministic finding parser in flowctl (pure stdlib): consumes the reviewer markdown the current prompts mandate (numbered findings with Severity/Location/Problem/Suggestion labels; ratchet forms "Prior finding N - fixed/not-fixed"); tolerant of label variants actually observed in the field (survey existing receipts in this repo + fixture corpus from real runs; BUILD ON the fn-130 reached-path fixture harness - fixtures/b0/plan-review/<backend>.json - rather than a new one); unparseable output degrades to findings: [] plus the existing prose - never an error.
- Backend wrappers (`flowctl codex|copilot|cursor plan-review|impl-review|completion-review`, rp receipt path, host receipt guidance) run the parser at receipt-write time.
- Output-format tightening happens in flowctl's PROMPT TEMPLATES (the '## Output Format' blocks the backends already receive - survey confirmed the mandate lives in flowctl.py, not skill prose), so most backends need ZERO skill-prose delta; any skill-prose touch (rp/host paths) stays token-delta <= 0 (prompt-diet ratchet).
- `flowctl` receipt validation knows the new field; sync-codex transforms pass untouched (schema is code, not prose); docs: memory-schema/receipts documentation updated.
- Fixture corpus: real reviewer outputs (codex sol, cursor, copilot shapes) checked into tests; parser covered per backend shape.

## Boundaries / non-goals

- NO new review passes, no validator/deep-pass changes, no verdict-grammar changes.
- NO skill-side JSON emission (reviewers keep writing markdown; structure is parsed, not requested - requesting JSON risks degrading review quality and burns tokens).
- Cockpit rendering is downstream (MergeFoundry consumes; nothing here depends on it).
- No backfill of historical receipts.

## Acceptance Criteria

- **R1:** Review-shaped receipts across all backends carry `findings[]` parsed deterministically from the existing reviewer output; absent/legacy receipts remain valid (additive schema; validation covers both).
- **R2:** The parser is pure-stdlib, tolerant (fixture corpus from real field outputs per backend; unparseable degrades to empty findings + prose, never an error), and covered by tests incl. ratchet re-review forms.
- **R3:** Skill prose deltas are format-tightening only with measured token delta <= 0 per touched skill; sync-codex idempotent; no new LLM calls introduced anywhere (greppable: no new subprocess/LLM invocations in the diff).
- **R4:** Receipt writes add no measurable latency (parser benchmarked trivially fast; no additional I/O beyond the existing receipt write).
- **R5:** Docs updated (receipt/memory schema pages); a consumer note documents the findings contract for downstream readers.
