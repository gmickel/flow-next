# Conduct checklist — /flow-next:make-pr

A correct run authors a grounded aid artifact, renders its briefing through flowctl, and opens the PR via `gh`.

- [ ] Claims trace to the export payload, task evidence and review receipts. Missing attribution stays honest; raw diff code is not quoted.
- [ ] On a real create with all tasks done, the spec-close commit exists before export and aid composition. A failed close stops the run. Incomplete tasks proceed interactively as a draft without closing; autonomous runs stop; dry-run and body-only updates never close.
- [ ] The structured aid runs on every invocation, including `--dry-run`. flowctl renders the body; invalid artifacts use the grounded fallback without mixing their fields into it.
- [ ] Empty briefing sections disappear. Scope carries grouped file purposes and requirement coverage; only unevidenced or undeclared requirements need the coverage table. Verification marks pass only from a gate that ran green; failed, inconclusive, and unrun gates stay explicit.
- [ ] The PR is created without a confirmation gate. Questions only resolve information that cannot be derived, such as the spec or base ref. Draft/ready rules, chain and stack linking, and the tracker touchpoint remain in force.
- [ ] `--dry-run` prints the body and stops before push, PR creation, or a spec-close commit. Identity is carried by the renderer's invisible comment; no generated-by footer or make-pr marker is appended.
