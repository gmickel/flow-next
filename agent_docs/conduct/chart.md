# Conduct checklist — /flow-next:chart

A correct run grounds one oversized idea, charts a frontier of decisions, resolves at most one D-ID, and hands a briefing to capture.

- [ ] The invocation ends with exactly one `CHART_VERDICT=<RESOLVED|BLOCKED|NEEDS_HUMAN|COMPLETE|NO_WORK> chart=<id> decision=<D> reason="..."` line and nothing after it; chart mode and status mode also print one, with `decision=-`.
- [ ] Chart mode resolves nothing — it ends after the Grounding Snapshot, the consent read-back, and `chart create --initial-map-file`, with a `NO_WORK` verdict.
- [ ] Work mode claims exactly one D-ID drawn from `flowctl chart frontier` before any evidence work, and a human pin is honored only when that D-ID is still on the frontier.
- [ ] An unattended driver meeting a stored `attendance:attended` decision writes no answer and terminates `NEEDS_HUMAN`. A run that answers a prototype or interview decision without the human side of the exchange has broken this.
- [ ] Nothing is written under `.flow/specs/` and no spec's `ready` flag is touched; chart artefacts are mutated only through `flowctl chart ...`, never by hand-editing the map or sidecars.
- [ ] An idea with no nameable destination, or one with no consequential unknowns, stops and creates nothing — offering narrowing, `/flow-next:prospect`, or `/flow-next:capture` instead.
