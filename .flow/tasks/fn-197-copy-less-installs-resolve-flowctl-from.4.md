# fn-197-copy-less-installs-resolve-flowctl-from.4 Stop dogfooding a tracked .flow/bin in this repo

## Description
**What:** flow-next's own repo stops dogfooding a tracked `.flow/bin` — `scripts/` becomes the single source, matching the product stance shipped in .1-.3.

**Details:**
- Untrack and delete the repo's `.flow/bin/` (tracked: flowctl, flowctl.cmd, flowctl.py, flowctl_bootstrap.py, flowctl-help.txt, flowctl_tracker/ — 20+ files) and `.flow/templates/`/`.flow/usage.md` if present. Use git rm on tracked copies (this is the explicit, spec-mandated deletion). Update `.flow/meta.json` mode stamp per the .3 decision.
- Retarget `tests/test_tracker_distribution.py` — it currently enforces `scripts/` ↔ `.flow/bin/` parity; its surviving job is the `scripts/flowctl_tracker` manifest integrity only.
- Repo `CLAUDE.md`: remove the contributor instruction to copy `flowctl.py` into `.flow/bin` + rsync `flowctl_tracker/` (~line 192) and the copy-mode snippet sections (~lines 87, 142, 166-198, 229, 239) — this repo's own instruction file converges on the same snippet users get.
- `.github/workflows/test-flow-next.yml`: drop `.flow/bin` path triggers (~lines 10, 44, 51, 75); verify the CI trigger-coverage test (`test_ci_trigger_coverage` derives the read surface from the tests) stays green after retargeting.
- Sweep remaining self-references: gate triage FORCE-FULL prefix and cleanliness notes (`docs/flowctl.md:1952,1963` — handled in .5 docs task if doc-only), `makePr.derivedPaths` default dual-copy classifier (`flowctl.py` + `skills/flow-next-make-pr/workflow.md:665`), `skills/flow-next-prime/{classification.md:134,stacks.md:92}`, `docs/memory-schema.md:192`. Code-level bits here, doc-only bits deferred to .5.
- CAUTION: `.flow/**` edits are always-serial; never delete uncommitted `.flow/*` — everything removed here must be tracked at deletion time.

**Touches:** .flow/bin/** (delete, always-serial), .flow/meta.json, plugins/flow-next/tests/test_tracker_distribution.py, CLAUDE.md, .github/workflows/test-flow-next.yml, scripts/flowctl.py (derivedPaths), plugins/flow-next/skills/flow-next-make-pr/**, plugins/flow-next/skills/flow-next-prime/**
## Acceptance
- [ ] `git ls-files .flow/bin` returns nothing; working tree carries no `.flow/bin`, `.flow/templates/`, `.flow/usage.md`.
- [ ] Full local gate green from a clean checkout with no `.flow/bin` (proves the repo's own skills and tests run copy-less end-to-end).
- [ ] `test_tracker_distribution.py` guards the `scripts/flowctl_tracker` manifest only; no test references `.flow/bin`.
- [ ] Repo `CLAUDE.md` contains no copy instructions; CI workflow has no `.flow/bin` path triggers and `test_ci_trigger_coverage` passes.
- [ ] `flowctl gate check` and make-pr derivedPaths behave sanely in this repo without the dual-copy paths.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
