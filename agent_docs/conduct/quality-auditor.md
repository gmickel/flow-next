# Conduct checklist — `quality-auditor`

A correct run audits the diff along **one** named axis of the two-axis in-host audit — correctness or standards — and reports within that axis's tiers, caps, and output budget.

- [ ] The report covers exactly the axis named in the dispatch's `AXIS:` line and nothing else. A single report carrying both the correctness charter's scope (self-regression, security, test coverage) and the standards charter's scope (smells, vocabulary drift, design conformance) has broken this.
- [ ] A dispatch with no `AXIS:` line produces a correctness-axis report opened by the literal line `Axis defaulted: correctness (no AXIS line in dispatch)`. A silent default, or a both-axes pass, has broken this.
- [ ] A standards-axis report contains no `### Critical` section and no finding tiered Critical, and its summary carries `Blocking: none possible (standards axis)` in place of a `Ship:` verdict.
- [ ] Finding caps hold — at most 8 tiered / 3 Consider on the correctness axis, at most 5 tiered / 3 Consider on standards — and any overflow is declared as `+N over cap` in the `Suppressed findings:` line rather than dropped silently.
- [ ] A diff that cannot be produced yields `Audit FAILED: <reason>` and stops. A clean or no-issues verdict emitted over an unresolved base or an empty diff has broken this.
- [ ] Findings belonging to the other axis appear as at most 2 untier'd `Out-of-axis observation:` lines, never as tiered findings in this axis's sections.
