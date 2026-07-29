# Structured review-artifact schema in receipts

## Goal & Context
<!-- scope: business -->

Review receipts today carry verdicts plus free prose; downstream consumers (the MergeFoundry cockpit's finding navigation and report cards, but equally any receipt reader) must regex findings out of markdown. The review skills ALREADY mandate a structured finding shape in their prompts (Severity / Location / Problem / Suggestion blocks, ratchet numbering). The structure exists at generation time and is thrown away at receipt-write time. This spec captures it: review receipts gain a structured `findings` array with file and line anchors, severity, R-ID linkage where stated, and per-finding status, emitted by DETERMINISTIC parsing of the reviewer output the passes already produce.

The PR cognitive aid has a related gap. `/flow-next:make-pr` already produces TL;DR, boundaries, R-ID evidence, verification, critical changes, trust calibration, a risk-ranked review plan, generated-noise grouping, and an optional HTML churn map. It does not yet preserve one logically ordered explanation of the change that both GitHub and downstream cockpit-class consumers can render. This spec therefore adds a structured `changeWalkthrough` artifact composed by the existing host agent from the existing cognitive-aid payload, validated and persisted by thin flowctl plumbing, and rendered in GitHub Markdown by `make-pr`. The walkthrough explains the change in intent order, not alphabetical file order or commit order.

Hard constraints (MergeFoundry MASTERPLAN decision 5, binding): NO extra LLM calls anywhere; NO re-bloating of the prompt-dieted review skills; NO meaningful latency; flow-next-only UX must improve or stay unchanged; markdown remains the canonical GitHub review surface; downstream products consume additive receipt/artifact fields rather than internal APIs.

## Reference design

These images are normative interaction and information-architecture references, not a requirement to copy their visual styling. Flow-Next approximates the hierarchy in GitHub Markdown; richer consumers may render the same data interactively.

### Overview, thesis, proof metrics, and logical sequence

![Reference PR aid overview showing thesis, metrics, legend, and ordered change groups](../assets/pr-aid/change-walkthrough-overview.jpeg)

### Progressive disclosure from step to file to diff

![Reference PR aid expanded step showing a file summary and inline diff](../assets/pr-aid/change-walkthrough-expanded-diff.jpeg)

### Grouped files, deliberate non-changes, and verification

![Reference PR aid showing grouped file rows, deliberately unchanged behavior, and verification](../assets/pr-aid/change-walkthrough-grouped-files.jpeg)

## Scope
<!-- scope: technical -->

### 1. Structured review findings

- Receipt schema: `findings: [{ordinal, severity, confidence?, classification?, file?, line?, title, body, suggestion?, rIds: [], status?}]` added to review-shaped receipts (`plan_review`, `impl_review`, `completion_review`, all backends including rp explicit path and host). Severity, confidence, and classification mirror the vocabulary flowctl's review prompt templates already mandate. The field is additive and optional; old receipts remain valid.
- A deterministic finding parser in flowctl (pure stdlib) consumes the reviewer markdown the current prompts mandate. It tolerates label variants observed in real receipts, including ratchet forms such as `Prior finding N - fixed/not-fixed`. Unparseable output degrades to `findings: []` plus existing prose, never an error.
- Backend wrappers attach findings at receipt-write time. Output-format tightening stays inside existing prompt-template Output Format blocks. Any touched skill prose has net-zero-or-negative token delta.
- Receipt validation and docs expose the new field. Fixture coverage uses real Codex, Cursor, Copilot, host, and rp output shapes from the existing fn-130 reached-path harness.

### 2. Structured PR change walkthrough

`/flow-next:make-pr` gains an additive structured artifact with this consumer-facing shape:

```text
pr_cognitive_aid: {
  version: 1,
  changeWalkthrough: {
    thesis: string,
    proof: [{label, value, source}],
    groups: [{
      ordinal,
      kind: problem | principle | step | kept | verify,
      title,
      summary,
      rIds: [],
      taskIds: [],
      files: [{
        path,
        status: new | modified | deleted | renamed | generated | mechanical,
        summary,
        additions?, deletions?,
        diffUrl?
      }]
    }]
  }
}
```

- **Judgment owner:** the existing `make-pr` host agent composes the thesis, intent grouping, summaries, and order from the existing export payload. No deterministic classifier, no second model, and no commit-message storytelling.
- **Plumbing owner:** flowctl validates the bounded schema and writes it through the existing receipt/artifact storage contract as an additive `pr_cognitive_aid` object. The object is the shared render input for GitHub Markdown, optional HTML, and downstream consumers. It is not parsed back into spec/task state.
- **Source discipline:** every claim traces to the spec, task summaries/evidence, R-ID coverage, review/QA receipts, or diff metadata. File rows can only name changed paths. Missing evidence is stated, never inferred.
- **Trigger:** render the full walkthrough when the diff has at least 200 human-review lines or at least six non-generated changed files. Smaller PRs retain the current compact body unless the host determines that multiple logical stages materially improve comprehension. `human-review lines` excludes paths already classified as generated or mechanical.
- **Ordering:** problem and operating principle first when evidenced, then 2-7 numbered implementation steps, then deliberately unchanged behavior, then verification/ship evidence. Groups are ordered by the behavior's causal flow, not filename, directory, churn, task ID, or commit chronology.
- **Noise handling:** generated mirrors, lockfiles, manifests, tracker state, and mechanical release surfaces are collapsed into their own low-attention group. They never crowd out canonical changes.
- **Security/privacy:** raw diff excerpts remain excluded from the Markdown body by default. File rows link to the code host's diff. Optional local HTML may show bounded inline diffs because it is a local review instrument, but it must apply existing secret-redaction and size limits.

### 3. GitHub Markdown approximation

GitHub cannot reproduce the full interactive reference. `make-pr` approximates it with supported primitives:

1. `## The change, top to bottom` with a 2-4 paragraph thesis.
2. A compact proof table for human-review lines, changed files, verification totals, and head commit when available.
3. A text legend for `WHY`, `PRINCIPLE`, `STEP`, `NEW`, `MODIFIED`, `KEPT`, and `VERIFY`.
4. One `<details>` block per logical group. The `<summary>` contains kind, ordinal/title, and one-sentence intent. The open body lists file rows in a Markdown table with status, path, purpose, `+/-` stats, and a diff link.
5. `Deliberately not changed` and `Verification and ship` are first-class groups, never buried in generic notes.
6. Generated/mechanical groups start collapsed; the first canonical step and any high-risk group may start open.
7. The existing risk-ranked `Review plan` remains. The walkthrough explains how the change works; the review plan says where human judgment should be spent.

### 4. Consumer contract

- Downstream renderers must consume `findings[]` and `changeWalkthrough` as optional additive fields. Absence means cold seam/fallback, never an error.
- Consumers may enrich interaction, navigation, collapse state, and inline diff display, but must preserve group order, labels, provenance, file membership, deliberate non-changes, and verification claims.
- Flow-Next Markdown, optional HTML, and downstream UI fixtures share one golden logical walkthrough so semantic drift is test-detectable.

## Boundaries / non-goals

- NO new review passes, validator/deep-pass changes, verdict-grammar changes, or extra LLM calls.
- NO skill-side JSON request to reviewer models. Findings remain parsed deterministically from reviewer prose.
- NO deterministic attempt to infer logical change intent. The host agent already rendering `make-pr` owns that judgment; flowctl only validates and persists.
- NO replacement of the existing R-ID coverage, verification, critical-changes, trust-calibration, review-plan, Mermaid, or optional HTML sections.
- NO requirement that GitHub render interactive inline diffs. Markdown links to the native diff instead.
- Cockpit rendering is downstream. Flow-Next defines the portable data and GitHub behavior, not MergeFoundry component styling.
- No backfill of historical receipts or PRs.

## Acceptance Criteria

- **R1:** Review-shaped receipts across all backends carry optional `findings[]` parsed deterministically from existing reviewer output; absent/legacy receipts remain valid.
- **R2:** The finding parser is pure stdlib, tolerant across real backend fixtures, handles ratchet re-review forms, and degrades to empty findings plus prose without raising.
- **R3:** Review prompt changes are confined to format disambiguation with measured token delta <= 0 for any skill-prose touch; sync-codex is idempotent; no new LLM invocation exists.
- **R4:** Receipt writes add no meaningful latency and no additional network or model I/O.
- **R5:** Receipt/memory docs and the product-neutral downstream consumer contract document `findings[]`, additive versioning, and fallback behavior.
- **R6:** `make-pr` can produce a bounded, schema-validated `pr_cognitive_aid.changeWalkthrough` artifact from existing cognitive-aid inputs with no extra model call; every group/file claim is provenance-grounded.
- **R7:** GitHub Markdown renders the walkthrough using the specified heading, proof table, legend, ordered `<details>` groups, file tables, diff links, deliberate non-changes, and verification group while preserving the existing review plan.
- **R8:** Full rendering triggers at the stated human-review-size/file-count threshold; generated and mechanical paths are excluded from the human-review-line threshold and collapsed separately.
- **R9:** One golden fixture proves semantic parity across structured artifact, Markdown, and optional HTML input: same group order, kinds, file membership, R-ID/task links, deliberate non-changes, and verification facts.
- **R10:** The three checked-in reference images are linked from this spec, survive repository-relative rendering on GitHub, and are explicitly treated as information-architecture references rather than visual-copy requirements.
