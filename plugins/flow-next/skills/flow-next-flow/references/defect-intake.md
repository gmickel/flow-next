# Defect intake from the feature map (gated reference)

> **Loaded only when** the route is a reported defect that still needs a reproduction and `.flow/features/` exists (workflow.md Step 3). Without a map the reproduction runs exactly as before and this file is never read.

The map says how a user reaches a feature, never what the bug is. The report and the reproduction stay the defect's evidence. Flow reads the map and never edits it; the features skill (`flow-next:flow-next-features`) stays its only seeder and maintainer.

## 1. Resolve the report to one mapped feature

Read `.flow/features/README.md`, then the candidate feature files. Match the report against each feature's H1, its user-visible paragraph and its `## Sub-features` lines:

- **Text:** the report's wording, the page or command it names, any console or error text.
- **Screenshot:** its visible content as well as the text - headings, table columns, labels, controls, empty-state copy. A screenshot with no page title or URL still resolves when that content matches a feature's description. An unreadable image, or one whose content matches nothing, falls back to text-only matching.

Select by the contract's `**Surface:**` identifier plus sub-feature ID ([feature-entry-contract.md](../../flow-next-features/references/feature-entry-contract.md)).

- **One plausible match:** that feature.
- **Several:** name the candidates, most specific first (the sub-feature whose description covers the most of the report's specifics), and try them in that order. The one that reproduced is the resolution.
- **None:** the resolution is `unmapped`. Reproduce by today's live discovery. A missing feature is information for the next feature-map maintain pass, not an error.

## 2. Drive the reproduction along the feature file

Invoke `flow-next:flow-next-drive` naming the resolved feature file and sub-feature, so drive follows that file's `How to get to it (user POV)`, `Driving it` preconditions and commands, and `Gotchas` instead of rediscovering which feature the report is about or how to reach it.

A mapped route that no longer matches the live app is stale: file the drift note exactly as the contract's "Writers and drift notes" section specifies (QA's §5.5 fence in `flow-next-qa/workflow.md` is the reference invocation), then reproduce by live discovery for this run. Never edit `.flow/features/` from flow. The resolution still names the feature; only its route was stale.

## 3. Record the resolution

Build the resolved-feature record defined in the contract's "Resolved-feature record" section, with `stage` set to `flow`, or `unmapped` when nothing matched. The spec the fix runs under carries it as one line in its reproduction evidence (`resolved_feature: unmapped` for no match):

```text
resolved_feature: {"surface": "web", "sub_feature": "notes.list", "file": "notes-list.md", "last_proven": "2026-09-20 at 4f2c9ab", "stage": "flow"}
```

When flow routes to capture, hand the line over with the reproduction; after the save, confirm `$FLOWCTL cat <spec-id>` shows it verbatim and add it to the reproduction evidence with Edit if it is missing. When flow writes the spec directly, write the line itself. Work's worker copies the value into its done evidence, and review, QA and make-pr read it from there, so no later stage re-derives navigation to the defect.
