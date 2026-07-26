---
satisfies: [R5b, R7b]
---
# fn-141-tracker-determinism-c-prose-teardown.7 Capture pre-teardown oracle + authoritative caller matrix

## Description
**Runs before any caller is rewired.** Capturing the oracle after teardown cannot prove preservation - the thing being compared has already changed.

Capture a **hash-addressed oracle** pinned to the post-fn-140 / pre-C commit: per caller, its config reads, argv, imports, stdout and stderr.

Build the **authoritative matrix** naming for every caller: file path, event key, legal configured values, resolved facade `--op`, unconditional behavior, required content input, expected receipt, stream behavior. This cannot be reconstructed from the enum alone - **QA coerces every non-`off` value to `comment`**, **make-pr and land have unconditional paths** (land's merge->Done rides bridge-active alone), and **work events use fixed operations regardless of the configured verb**.

Also build the **explicit path/token inventory** for the teardown sweep, replacing prose counts: `scripts/sync-codex.sh` measured 19 lines / 29 tokens, but a count is pattern-dependent and goes stale (an earlier draft said 18), so the artifact is a list asserted by test.

## Acceptance
- [ ] Oracle captured BEFORE any caller edit, hash-addressed, pinned to a named commit
- [ ] Per-caller record covers config reads, argv, imports, stdout, stderr
- [ ] Matrix names every caller file, event, legal values, resolved op, unconditional behavior, content input, receipt, streams
- [ ] QA coercion, make-pr/land unconditional paths, and work's fixed ops each captured explicitly
- [ ] Sweep inventory is an explicit path/token list asserted by test, not a prose count

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
