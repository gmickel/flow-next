# fn-65-land-accept-a-bot-reviewed-clean.1 land silence detection: clean-review comment scan + land.cleanReviewCommentPattern config + tests + Codex mirror

## Description
### Goal
Make land's `silence` signal also recognize a bot's clean-review ISSUE COMMENT (naming the current head SHA) as a satisfying automated review — closing the blind spot where Codex's no-findings comment is invisible to the reviews-API-only check. Detection-only; no merge-mechanics change. Satisfies R1–R5, R7.

### Investigation targets
- `plugins/flow-next/skills/flow-next-land/workflow.md:214-241` (§2.6 Review signal). The comment scan is added **after the `gh api .../pulls/<n>/reviews` loop (:218-232) and BEFORE the draft-PR review-trigger check (~:235)** — and gated on `REVIEW_SIGNAL == silence`. Reuse the allowlist gate verbatim from `:225` (`[[ login == *"[bot]" ]] || in AUTOMATED_REVIEWERS csv`).
- **Draft-trigger interaction (resolved):** the comment scan sets `AUTO_REVIEW_CURRENT=1`, which the draft-trigger branch (`:235`, fires when `AUTO_REVIEW_CURRENT == 0`) then reads. This is CORRECT, not a perturbation — a clean comment naming the head IS proof the bot reviewed the head, so suppressing a now-redundant `@codex review` re-trigger is the intended behavior. (No separate var needed; just run the scan before the trigger check and document the intent.)
- **SHA extraction (no footgun).** Do NOT emit `[[ "$HEAD_OID" == "$comment_sha"* ]]` against an unextracted var (empty → spuriously TRUE). Instead: prefer the token on the `Reviewed commit` marker line; else `grep -oE '[0-9a-fA-F]{7,40}'` over the body. Lowercase; loop the tokens; count head-current iff some token is non-empty, ≥7 chars, AND `[[ "$HEAD_OID" == "$token"* ]]`. No qualifying token → ignored.
- **Config contract (the only off-switch that works).** `plugins/flow-next/scripts/flowctl.py` `get_default_config()` land block (~:1173-1196, fn-60.2): seed `cleanReviewCommentPattern` = a STRUCTURED built-in ERE (requires `Reviewed commit` marker + clean phrase, e.g. `Didn'?t find any (major )?issues`). In workflow.md Phase 0 `cfg` read: **`null`/missing → fall back to the built-in default; explicit empty string `""` → comment scan DISABLED; any other value → use it.** Never "empty → default fallback" (that makes it un-disableable). Update BOTH the canonical `plugins/flow-next/scripts/flowctl.py` AND the dogfood `.flow/bin/flowctl.py` in lockstep.
- **Observability:** set `AUTO_REVIEW_SOURCE=comment` + `AUTO_REVIEW_EVIDENCE` (author + matched SHA prefix); surface in `--dry-run` and the verdict report.
- `plugins/flow-next/skills/flow-next-land/SKILL.md` — land config keys are documented in PROSE (no table); add a sentence near the review-signal prose describing the comment-path supplement + the empty-disables contract.
- Codex mirror: `bash scripts/sync-codex.sh` then commit `plugins/flow-next/codex/skills/flow-next-land/`. REQUIRED — stale mirror = CI red.
- Tests: `plugins/flow-next/tests/test_land_config.py` — add the new key (default present, round-trip, no-clobber, docstring) PLUS an explicit-empty-disables assertion. Detection bash has no host-agent harness — back it with static assertions that workflow.md contains the `--paginate` comment scan, the `REVIEW_SIGNAL == silence` gate, and the SHA non-empty/min-length guard. State the harness limitation honestly.

### Pitfalls (memory)
- Hard-branch the gate — a snippet that only `echo`s on mismatch falls through (`skill-workflow-snippets-must-enforce`). Set/skip explicitly.
- Never count a stale-SHA or empty-token comment (head-current invariant, `:227`).
- Match on STRUCTURE (`Reviewed commit` + SHA), not flow spec ids (auto-linkify; `trackers-auto-linkify-issue-key`).
- `gh api` GET only (dry-run-safe); `-F` not `-f` for numeric fields (`gh-api-f-stringifies-numeric-body`).
- Mirror regen re-exposes the whole land skill as "introduced" (`mirror-regen-exposes-latent-canonical`) — pre-audit path vars before committing.

### Notes
`silence` was built for "bots that comment but never APPROVE" — this restores detection of the exact reviewer it targets. CI/threads/window gates untouched; the scan only ever SETS `AUTO_REVIEW_CURRENT=1`, never resets the reviews-API result.
## Acceptance
- [ ] In workflow.md §2.6, gated on `REVIEW_SIGNAL == silence`, after the reviews-API loop a `gh api --paginate repos/$OWNER_REPO/issues/$PR_NUMBER/comments` scan sets `AUTO_REVIEW_CURRENT=1` when: author passes the `[bot]`-suffix/`AUTOMATED_REVIEWERS` allowlist gate AND body matches the pattern AND a head-current SHA token is found (R1). The scan must NOT run on `approve`/`<login>` and must not perturb the draft review-trigger branch.
- [ ] SHA token: prefer the token on the reviewed-commit marker line (after `Reviewed commit`), fall back to body `grep -oE '[0-9a-fA-F]{7,40}'`; lowercase; require ≥1 non-empty token ≥7 chars that is a prefix of `HEAD_OID`. No `==$var*`-on-empty; empty/absent token NEVER passes; stale-SHA token does not satisfy (R2).
- [ ] A non-automated login is ignored (R3); the scan only ever SETS the flag to 1, never resets the reviews-API result.
- [ ] The comment path never bypasses an unresolved thread or red CI; the scan is a read-only `gh api` GET (dry-run-safe) (R4).
- [ ] Config contract (R5): `get_default_config()` seeds a STRUCTURED built-in ERE for `land.cleanReviewCommentPattern` (requires `Reviewed commit` marker + clean phrase near the SHA). Workflow `cfg` resolves: `null`/missing → built-in default; explicit empty `""` → comment scan DISABLED; other → used. Update BOTH `plugins/flow-next/scripts/flowctl.py` AND the dogfood `.flow/bin/flowctl.py` in lockstep.
- [ ] Comment-driven satisfaction observable: `AUTO_REVIEW_SOURCE=comment` + `AUTO_REVIEW_EVIDENCE` (author + matched SHA prefix) set + surfaced in `--dry-run`/report (R7).
- [ ] SKILL.md prose notes the comment-path supplement to the silence signal.
- [ ] `test_land_config.py` covers the new key: default value present, set/get round-trip, no-clobber, docstring; PLUS an **explicit-empty-disables** assertion (set `""` → reads back `""`, distinct from the seeded default) AND a static assertion that workflow.md contains the comment scan (`--paginate`), the `REVIEW_SIGNAL == silence` gate, and the SHA min-length/non-empty guard. `python3 -m unittest plugins.flow-next.tests.test_land_config` green.
- [ ] Codex mirror regenerated (`scripts/sync-codex.sh`) + committed; `bash plugins/flow-next/tests/ci_test.sh` green. (Pre-audit path vars — mirror regen re-exposes the whole land skill as "introduced".)
## Done summary
Made /flow-next:land's `silence` review signal also accept a review bot's clean-review SHA-named issue comment (e.g. Codex's no-findings comment) as satisfying evidence — closing the blind spot where a clean comment never appears in the reviews API. Added a silence-gated, paginated, head-SHA-anchored comment scan in workflow.md §2.6 with an empty/min-length SHA-token guard, seeded a structured-ERE `land.cleanReviewCommentPattern` config (null→default, explicit ""→disabled) in both flowctl.py copies, documented the supplement in SKILL.md, expanded test_land_config.py (+16 tests) with static §2.6 assertions, and regenerated the Codex mirror.
## Evidence
- Commits: c57f45e33a82485cbd51a867e16bd5b3f72c4b2f
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (1104 OK, skipped=2), bash plugins/flow-next/scripts/ci_test.sh (67 passed, 0 failed), behavioral bash matrix on the §2.6 comment-scan snippet
- PRs: