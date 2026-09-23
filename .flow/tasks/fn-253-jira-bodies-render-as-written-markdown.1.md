---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-253-jira-bodies-render-as-written-markdown.1 Implement Jira bodies render as written: Markdown to wiki markup on the v2 wire

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Jira bodies now convert from Markdown to wiki markup on every v2 write (issue create, issue update, comment add and update) and are decoded back to Markdown once, at the point where a read extracts them. The transforms are pure stdlib, in `flowctl_tracker/providers/jira_markup.py`. Issues linked before this change are converted by push or reconcile; a pull, or a reconcile merged against the decoded read, refuses them with `jira_body_unconverted`. The Jira transport doc now names the Wiki Style Renderer prerequisite, and the changelog credits @flecamos (#465).

Tier: session (jev moderate 0.75)
baseline: green (python3 scripts/run_tests_parallel.py, 5026 tests)
verify: green (5040 tests at 7029fb54, receipt written); ruff clean
live check: Jira Cloud (team-managed project), 2026-09-23. The #465 fixture and a real spec (fn-247) were pushed through 7029fb54. The stored body equalled the sent body. Rendered HTML had h1/h2, `<b>`, ul/ol/nested li, `<tt>`, `<pre>`, table, blockquote and links, with no raw Markdown left, and umlauts intact. Comments rendered formatted. Decode followed by re-encode reproduced the stored body, so there is no false divergence.

stage: impl-review - failed(ESCALATE same-not-fixed-lineage after 3/8 rounds; finding #3 fence-terminator collision; third fix 7029fb54 not re-reviewed)
stage: impl-review - human override: the maintainer accepted the remaining finding as a known limit on 2026-09-23 and authorized done. No SHIP verdict was issued.

Known limit (accepted): a fenced code block whose content contains both `{code}` and `{noformat}` is sent as escaped monospace lines, not as a code block. Four of the five review findings were fixed.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 1acf3e2baa5a740a99c4948c5768de8b0a70934d, 31b8d4f1072fb040301d8f11ba2e69b16936169b, 5082ba6ba26d8b6d621f9c2acbeffe449f52d055, 7029fb54509eaf79ad6154fb2413782da66b5dde
- Tests: python3 scripts/run_tests_parallel.py (baseline green 5026; final green 5040, receipt 7029fb54), uvx ruff@0.16.0 check ., python3 -m unittest test_tracker_jira_markup (focused)
- PRs: