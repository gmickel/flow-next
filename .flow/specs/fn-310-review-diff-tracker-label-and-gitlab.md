# Review diff, tracker label and GitLab probe fixes

## Goal & Context

The 9.5.1 patch release closes valid GitHub issues that sat open too long, without adding machinery, wall-clock or tokens. This spec takes the three plumbing defects among them. Each one is a wrong result produced by flowctl with no judgment involved. [paraphrase]

- **#529:** The Copilot reviewer runs with shell denied, yet every review prompt tells it to run `git diff <range>`. It sees the numstat file list and the files as they are now, never the hunks, so deleted code is invisible to it. Claude had the same gap and fn-221 fixed it by writing the reviewed range to a file and pointing the prompt at it. Copilot was never added to that path. The Cursor reviewer runs in ask mode and may have the same gap.
- **#578:** Tracker-sync create-first writes the back-reference as a `flow:<spec-id>` label. GitHub rejects label names over 50 characters (HTTP 422, confirmed against the live API in the issue thread), so every spec id over 45 characters gets no back-reference, and the offered retry can never succeed.
- **PR #546 (no issue):** A Claude reviewer reached through a gateway alias can exit 0 with a valid success envelope and a SHIP result, while stderr carries `[claude-code:unrecognized_model]`. Claude Code's error reference treats that tag as a diagnostic that neither stops the request nor switches models. flowctl reads the tag as model-unavailable first, so it discards the review, or enters the fallback ladder when the model was not pinned. Separately, the model-resolution cache stores a fallback model, or the floor, even when that fallback's run failed. A failed choice can then stick for the 24-hour cache life.
- **#583:** On a repo whose origin is not a GitHub host, the `flow --auto` PR probe (`gh pr list`) fails, the snapshot reports `pr_probe_failed: true`, and auto ends `NEEDS_HUMAN` before its first stage. Every GitLab-hosted run stops there, including a fresh branch where nothing is wrong.

Contributor work exists for three of these. PR #581 (DreamchaserLG) implements the #578 fix and verified both sides of the 50-character boundary live. PR #567 (jcarosi) includes Copilot diff delivery for #529, together with an unrelated effort change. PR #546 (jcarosi) fixes both Claude-review bugs above, with offline regressions. All three PRs conflict with `main`. [inferred]

<!-- Source: 15% user / 25% [paraphrase] / 60% [inferred] -->

## Architecture & Data Models

- **Review diff delivery.** The primary-dispatch boundary already carries the reviewed `(base, head, receipt id)` to the backend adapter, and only the Claude adapter writes the diff and appends the transport note. The Copilot adapter does the same through one shared, backend-neutral helper. Deep and validator passes keep the primary session's file, as they do for Claude. [inferred]
- **Label fit.** Only the GitHub wire label verb changes. Flow ids front-load their unique key (`fn-N-`, `gh-N-`), so cutting at 50 characters keeps the part that tells specs apart. The full id stays in the local link and marker comments. No flowctl code reads the `flow:` label back to find a spec (checked on `main`), so a cut label breaks no lookup. [inferred]
- **Non-GitHub origin.** "No PR forge" is a third probe outcome next to "PRs listed" and "probe failed". It means no PR is visible and the route comes from the lifecycle, the same as a GitHub branch with no PR. gh itself decides whether origin is a GitHub host it knows, which covers GitHub Enterprise hosts without flow-next parsing URLs. [inferred]

## API Contracts

- `pilot snapshot --json` and `judge --preset route --json` keep their shape. On a non-GitHub origin, `pr_probe_failed` is `false` and the decision is the lifecycle decision. [inferred]
- The GitHub wire `label` result keeps its shape. [inferred]
- No new config key, flag or command. [paraphrase]

## Edge Cases & Constraints

- A genuine gh failure on a GitHub origin (outage, auth, timeout, unreadable output) still reports `pr_probe_failed: true` and still stops auto with `NEEDS_HUMAN`. Only the "origin is not a GitHub host" answer becomes "no PR forge". [inferred]
- On a non-GitHub origin, the run that now gets past the probe can reach make-pr, which opens GitHub PRs only (#462 tracks GitLab MRs). make-pr must stop cleanly there, before it closes the spec or pushes. A bare gh error after a close commit is not acceptable. [inferred]
- Two spec ids that agree in their first 45 characters cannot collide, because the numeric key prefix differs. [inferred]
- Windows passes the Copilot prompt on stdin. The transport note must reach the reviewer on both argv and stdin paths. [inferred]

## Acceptance Criteria

- **R1:** A Copilot primary review (impl, plan and completion, resumed or not, and each fan-out draw) gets the reviewed range's diff at a readable path, and its prompt names that path and tells it not to run git. Deep and validator passes reuse the primary's file. Claude delivery is unchanged. Errors: if the diff cannot be written, the review fails with a non-zero result before the Copilot CLI is started (the same rule Claude follows). [inferred]
- **R2:** The Cursor reviewer's gap is settled by one check, live or from Cursor's docs: can an ask-mode session run `git diff`? If it cannot, Cursor primary reviews get the R1 delivery. If it can, Cursor is left unchanged. Either way the PR states what the check found and how it was run. No error surface beyond R1's. [inferred]
- **R3:** The GitHub wire label verb cuts every added or removed label name to its first 50 characters, so a create-first back-reference for a spec id over 45 characters lands, and its retry succeeds. Errors: a name of 50 characters or fewer is sent unchanged. Other providers and the `readyState` status labels are unchanged; a configured status label over the cap still surfaces GitHub's 422. [inferred]
- **R4:** On a repo whose origin gh does not recognize as a GitHub host, `pilot snapshot` and `judge --preset route` report `pr_probe_failed: false`, see no PR, and route from the lifecycle, so `flow --auto` starts its first stage. Errors: any other gh failure, on any origin, still sets `pr_probe_failed: true`. [inferred]
- **R5:** make-pr on a repo whose origin is not a GitHub host stops in preflight, before any spec close, commit or push, with a message saying make-pr opens GitHub pull requests only and naming the origin host. It exits with the needs-human code, so an autonomous run ends `NEEDS_HUMAN` with that reason. No error surface beyond this stop. [inferred]
- **R6:** Each fix has a regression test that fails on `main` and passes with the fix: a Copilot dispatch writes the diff and the prompt names it, plus the failure-before-spawn case (R1); a 51-character label is sent as its 50-character prefix (R3); a non-GitHub-origin probe routes from the lifecycle, while a gh failure on a GitHub origin still fails (R4). [inferred]
- **R7:** The CHANGELOG `## Unreleased` entries credit DreamchaserLG for the #578 fix (PR #581), jcarosi for the Copilot diff delivery taken from PR #567, and TechupBusiness for reporting #578 and #583. [inferred]
- **R8:** A Claude review that exits 0 with a well-formed success envelope (`type` `result`, boolean `is_error` false, string `result`) yields its verdict, whatever stderr says. An explicitly pinned model dispatches exactly once and stays on the receipt. Errors: a malformed or wrong-typed envelope, an error envelope, a non-zero exit, or a timeout yields no verdict, even when stdout holds verdict-shaped text. A genuine model-unavailable response (an error envelope that matches the signature, or the stderr tag with empty stdout) keeps today's fallback ladder. A regression test using the fake-process repro from PR #546 fails on `main` and passes with the fix. [inferred]
- **R9:** The model-resolution cache records a fallback model or the floor only when that dispatch exited 0, and drops a cached choice whose dispatch fails. A test shows that a failed fallback run leaves no cache entry. The CHANGELOG credits jcarosi for R8 and R9 (PR #546). No error surface beyond R8. [inferred]

## Boundaries

- No GitLab merge-request support in make-pr, resolve-pr or land; that is #462 and fn-73. [inferred]
- No change to Copilot reasoning effort for Claude-family models. That half of PR #567 is a separate behaviour change and is answered on that PR, not here. [inferred]
- No `label_truncated` result field and no new provider-constraints docs section from PR #581. One sentence in the create-first back-reference rule states the cap. [inferred]
- `spec.approval pr` and trace approval lookups on a non-GitHub origin are unchanged. [inferred]
- No new machinery, and nothing that slows a run or adds tokens on GitHub repos. [paraphrase]

## Decision Context

Take the contributors' code where it is right and trim it to the fix. PR #581's truncation is correct, but its `label_truncated` mapping reports something any reader can compute from the id, and nothing consumes it, so it goes. From PR #567, take the backend-neutral diff helper and the Copilot call site. Leave out the effort change, which needs its own evidence. From PR #546, take the flowctl fix and its regressions, and leave out its two bundled spec records. The PRs are taken by cherry-pick or by reapplying the reviewed change onto `main`, with the contributors credited, because all three conflict with `main` and PR #567 carries a spec numbered `fn-304`, which already exists here. [inferred]

Letting gh decide "is this a GitHub host" avoids a URL-parsing allowlist that would misread GitHub Enterprise hosts. Stopping make-pr early on a non-GitHub origin is the smallest guard the #583 fix needs. Without it, the unblocked run would reach a gh error after the spec close commit. [inferred]
