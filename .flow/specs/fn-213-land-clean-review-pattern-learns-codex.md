# Land clean-review pattern learns Codex's summary-table format

## Problem

Codex's PR-review bot changed its clean-verdict surface: instead of (or in addition to) a "Didn't find any major issues. Reviewed commit: `<sha>`" issue comment, it now maintains a single edited-in-place summary comment (`<!-- codex-pull-request-review-summary -->`) whose table row reads `📝 **Code Review** | ✅ **Completed** <time> | \`<sha7>\` | <trigger>`, and reacts 👍 when all reviews finish with no findings. The seeded `land.cleanReviewCommentPattern` default only matches the old phrase, so land's silence-signal comment scan (§2.6, fn-65.1) cannot see a clean verdict delivered in the new format: a fully converged PR (green CI, zero unresolved threads, elapsed window, bot demonstrably reviewed the current head clean) dead-ends at `NEEDS_HUMAN: no automated review arrived within the patience window`. Observed live on PR #385 (2026-08-30): the merge required manual evidence reading. An unattended `/loop`-driven land cannot do that.

## Decision Context

- Extending the comment pattern to the summary-table row is semantically consistent with the existing reviews-API path: a COMMENTED review of the current head sets `AUTO_REVIEW_CURRENT=1` regardless of findings, because findings gate separately via unresolved threads. A summary row naming the current head is the same class of evidence, and the scan's other two conjuncts (automated-reviewer allowlist, ≥7-char head-SHA prefix in the same body) are unchanged.
- The summary comment is edited in place and present on every round, including rounds that produced findings — that is safe for the same reason: threads from those findings hold the gate open, and a row naming a stale head fails the SHA-prefix conjunct.
- The 👍 reaction is stronger no-findings evidence but a different API surface (reactions, not comments); wiring it into the gate is out of scope (YAGNI) — the pattern extension alone restores unattended convergence.

## Acceptance criteria

- **R1:** The seeded `land.cleanReviewCommentPattern` default (flowctl `get_default_config()`) gains an alternative that matches Codex's summary-table row — structured, requiring the literal bold `**Code Review**` followed by `**Completed**` in one body (ERE, case-insensitive as consumed by the workflow's `grep -Ei`) — while continuing to match the two legacy clean phrases exactly as before. A bare "completed" or "code review" mention without the paired bold markers must not match.
- **R2:** Every carrier of the default is updated in the same change and stays byte-consistent where tests pin equality: the flowctl seeded default, the land workflow.md Phase 0 hardcoded fallback ERE (used when the key reads `null` on unseeded repos), the `docs/flowctl.md` config-table row (default column + prose naming the new format), and this repo's machine-seeded `.flow/config.json` value. `./scripts/sync-codex.sh` run twice, mirror committed.
- **R3:** `test_land_config.py`'s behavioral anchors extend: the new default matches a realistic summary-table body naming a 7-char SHA (e.g. `| 📝 **Code Review** | ✅ **Completed** <relative-time ...> | ` + backticked sha + ` | New commits |`), still matches both legacy clean-comment shapes, and still rejects the existing negative cases plus a new negative (plain prose containing "code review completed" without the bold-marker structure). `EXPECTED_CLEAN_PATTERN`-style equality pins are updated in the same commit.
- **R4:** Land skill prose (SKILL.md §gate bullet and workflow.md §2.6 commentary) names both accepted forms — the legacy clean-phrase comment and the summary-table row — so a transcript reader understands why either satisfies the gate. No change to the scan's algorithm, conjuncts, or the `""`-disables contract.
- **R5:** Repo CHANGELOG gains an `## Unreleased` entry (user-outcome-first: unattended land no longer dead-ends on a clean Codex verdict in the new format). No version bump in this change — the batched release happens separately.

## Boundaries

- No reaction-API probe, no new config keys, no changes to the reviews-API path, window anchoring, or any other gate.
- `flowctl gate`/schema untouched (value change only; `cleanReviewCommentPattern` is already a known key).

## Quick commands

- `cd plugins/flow-next/tests && python3 -m unittest test_land_config -q`
- `uvx ruff@0.16.0 check plugins/flow-next/scripts/flowctl.py`
