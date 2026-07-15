# fn-99-setup-block-diet-evidence-schema-inline.1 Block diet + evidence schema + pristine-upgrade hash + lockstep test

## Description
Rework the setup-written "## Flow-Next" block and its refresh path. Satisfies R1, R2, R3, R8, R9, R12.

Scope:
1. Edit `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md` AND its hand-maintained twin `templates/agents-md-snippet.md` in lockstep (differ only by `/flow-next:` vs `$flow-next-` syntax; selection workflow.md:691-696). Diet ~575 -> <=250 tokens (chars/4) keeping, in order: flowctl-only + no-TodoWrite rules; typical-flow quick-command line INCLUDING an inline evidence example that is STRUCTURALLY identical to worker.md's teaching and cmd_done's contract - exactly keys commits/tests/prs, lists of strings, placeholder values (byte equality impossible: worker.md uses concrete values + operative base_commit); spec-creation guidance with the SPEC.md/template discovery cascade; re-anchor rule; `.flow/usage.md` + `--help` pointers. Calibrate against the eval's C-min arm (memory `usage-md-guidance-eval-2026-07-15`). Prohibitions stay literal.
2. Pristine-upgrade mechanics as THIN FLOWCTL PLUMBING (R8, R12; architecture rule - deterministic mechanics in flowctl, judgment in the skill): a helper doing marker-scoped replace + per-target hash record/compare against `.flow/meta.json` `setup.block_hashes` (map keyed by target file; sha256 over newline-normalized block bytes). Transition table per the spec's API Contracts section incl. the `"customized"` sentinel on Keep-with-hash-absent. workflow.md:698-712 calls the helper and owns only the AskUserQuestion.
3. Automated fixture test (R12) covering: both targets simultaneously, pristine refresh, customized Keep/Overwrite, hash-absent migration + sentinel, malformed metadata, outside-marker byte preservation, hash updated only after successful write, idempotent re-run.
4. Lockstep parity test (R9): the two snippets identical modulo documented syntax substitutions (pattern: tests/test_dogfood_template_parity.py:36-45); plus a shape test asserting the block's evidence example parses to exactly {commits,tests,prs} with list-of-string values.
5. Update this repo's own CLAUDE.md "## Flow-Next" block (dogfood).

Gotchas (memory): re-declare paths per skill bash block; bash snippets are executable contracts; setup ask-copy reflects pre-prompt mutations. Overlap: fn-96 touches the same workflow.md neighborhood - rebase order only.
## Acceptance
- Both snippet templates <=250 tok-equiv, keep-list intact; evidence example passes the JSON shape test (keys/types) (R1, R2).
- flowctl block helper + fixture test green across all R12 transitions; content outside markers byte-preserved (R3, R8, R12).
- Lockstep parity test green and fails on twin drift (R9).
- Repo CLAUDE.md dogfood block updated; unit + smoke green.
## Done summary
Dieted the setup-written Flow-Next instruction block from ~575 to ~248 tokens (both claude-md-snippet.md and agents-md-snippet.md twins), inlined the evidence-JSON schema example (the eval's sole correctness-critical content), and added pristine-upgrade detection so existing installs receive template fixes without a spurious "overwrite customized?" prompt.

Delivered R1 (evidence schema inline, structural-equality contract vs worker.md), R2 (both snippets ~248 tok with the full keep-list), R3 (marker-scoped in-place refresh, outside-marker bytes preserved), R8 (per-target setup.block_hashes map + "customized" sentinel), R9 (twin lockstep + evidence-shape tests), R12 (fixture matrix incl. the customized-Keep transition).

Mechanics live in thin flowctl plumbing (setup-block apply/resolve) with a transition table; workflow.md owns only the ask. Codex impl-review (sol-high) took 3 rounds: r1 (worker) initial fixes; r2 fixed symlink-collapse identity bug (Major), skipped-Docs hash backfill, meta.json concurrency lock; r3 scoped the backfill to honor explicit Docs deselection. SHIP on r3.
## Evidence
- Commits: c0f4d7a0, 2f89a776, 56a40052, 22090627
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (1784 OK, skipped=2), python3 -m unittest plugins.flow-next.tests.test_setup_block_helper plugins.flow-next.tests.test_setup_snippet_lockstep (14 OK), codex impl-review sol-high SHIP round 3
- PRs: