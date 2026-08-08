# Conduct checklist — /flow-next:guide

A correct run recommends **one** next workflow from the current starting state and creates no specs, charts, tasks, artifacts, or flowctl state.

- [ ] The run emits a single recommendation in the Route / Signal / Skip-narrow / Skip-kind shape, led by the natural-language prompt or slash command the user should run next. A run that leads with flag vocabulary when a plain-language prompt exists has broken this.
- [ ] The recommended route traces to one row of the smallest-sufficient matrix, and the matched positive signal is named rather than paraphrased as general advice.
- [ ] Nothing under `.flow/` is written and no write-capable flowctl subcommand runs — probes stay read-only (`brief`, `list`, `show`, file reads). A transcript containing a create/claim/resolve call, or a Write or Edit tool use, has broken this.
- [ ] At most one blocking question is asked, and only when two routes would materially differ in cost, consent, or discovery-versus-build path; otherwise the run recommends one route outright.
- [ ] Chart appears only as an optional discovery route — never as mandatory onboarding, a pipeline or pilot stage, or the automatic hop after prospect.
- [ ] The Skip kind is stated as `signal absent` or `despite unresolved risk`, and the run never claims that skipping a command also skips the evidence, consent, or review contracts that command would have provided.
