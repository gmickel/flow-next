# Conduct checklist — /flow-next:impl-review

A correct run coordinates a Carmack-level review of the branch's implementation through exactly one configured backend and reports that backend's verdict.

- [ ] Phase 0 resolves the backend once — a single `flowctl review-backend` call, or a `--review=<backend>` flag that skips it — and only the matching backend workflow file is read. A transcript that loads two backend workflow files has broken this.
- [ ] The coordinator does not review the diff itself: the verdict comes from the backend's returned output, or from the triage-skip receipt written with `mode: "triage_skip"` / `verdict: "SHIP"`. A self-declared SHIP with no backend response has broken this.
- [ ] When `REVIEW_RECEIPT_PATH` is set, a receipt is written for every verdict, and it carries only the blocks the run's flags enabled — no `validator`, `deep_passes`, or `walkthrough` keys without `--validate`, `--deep`, or `--interactive`.
- [ ] `NEEDS_WORK` drives the internal fix loop (parse findings, fix, run tests and lints, commit, re-review in the same session or chat) while `MAJOR_RETHINK` escalates immediately as `BLOCKED: DESIGN_CONFLICT` instead of being patched finding-by-finding.
- [ ] A delivered verdict is never re-dispatched as a transport failure and the reviewer sandbox stays read-only. A run that reframes `NEEDS_WORK` as a backend problem, claims a refunded round for it, or widens the sandbox has broken this.
- [ ] `--interactive` refuses to run under the Ralph markers (`REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1`), erroring out rather than putting a blocking question to an autonomous loop.
