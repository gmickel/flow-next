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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
