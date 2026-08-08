# Conduct checklist — /flow-next:prospect

A correct run grounds itself in the repo, generates many candidates, critiques every one with an explicit rejection reason, ranks the survivors into buckets, and writes a ranked artifact under `.flow/prospects/<slug>-<date>.md` before offering a handoff.

- [ ] Running under Ralph (`REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1`) exits 2 before any scan, prompt, or artifact directory is created. A prospect artifact produced inside a Ralph loop has broken this.
- [ ] The critique runs as a fresh-context read-only subagent whose inputs are the grounding snapshot, the candidate list, the taxonomy, and the floor — the focus hint, persona texts, and generation prompt stay out of that dispatch.
- [ ] Every dropped candidate carries one slug from the frozen rejection taxonomy plus one specific sentence, and a rejection rate under the floor surfaces the `regenerate | loosen-floor | ship-anyway` question rather than proceeding quietly.
- [ ] The grounding snapshot is a structured 30-50 lines of titles and tags, with `scanned: none (<reason>)` for each absent source and no raw file bodies pasted in.
- [ ] The artifact is on disk before the handoff prompt fires, with High leverage capped at three entries and every survivor stamped `Small-diff lever because <X>; impact lands on <Y>.` and no numeric scores.
- [ ] The handoff prints the artifact path and routes promote / chart / interview / skip without auto-invoking chart or interview, and `.flow/specs/` is written only by `flowctl prospect promote`.
