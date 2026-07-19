---
satisfies: [R1, R2, R5, R7]
---

## Description

New flowctl subcommand group `gate` mirroring the triage-skip architecture (constants near flowctl.py:26652, argparse group pattern like `memory`/`prospect` at ~31218/31489, registration near 32437). Dual-copy: edit `plugins/flow-next/scripts/flowctl.py`, then `cp` to `.flow/bin/flowctl.py` (byte-identical, both committed together).

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `.flow/bin/flowctl.py`, `plugins/flow-next/tests/test_gate_receipt.py`, `plugins/flow-next/tests/test_gate_classify.py`

1. `gate receipt --gate <unittest|smoke>`: write `.flow/tmp/green-receipts/<sha8>-<gate_id>.json` = `{schema: 1, head_sha, gate_id, timestamp}` via `atomic_write_json` (flowctl.py:2034). One file per receipt - no shared ledger, no lock, no read-modify-write. mkdir -p the dir; not-a-git-repo -> exit 2.
2. `gate check --gate <id>`: exit 0 (honored) iff receipt exists for current HEAD sha8 AND `head_sha` matches full HEAD AND worktree clean outside `.flow/` (`git status --porcelain` minus `^.. \.flow/` lines) AND age <= 24h AND `schema == 1`. ANY other condition (missing, unparseable, dirty, stale, schema mismatch, no repo) -> exit 1 (run full gates); real errors exit 2+. Never crashes on malformed JSON.
3. `gate classify --base <ref>`: classify the cumulative diff (`git diff --name-only <ref>...HEAD` UNION staged+unstaged `git status --porcelain` paths). Exit 0 (docs-only tier-B) iff EVERY path matches the non-executable class: `docs/**`, `agent_docs/**`, `optimization/**`, `CHANGELOG.md`, `README*`, `GLOSSARY.md`, `STRATEGY.md`, `plugins/flow-next/docs/**` md/mdx, `.flow/**` EXCEPT `.flow/bin/**`. Everything else (scripts/**, plugins/flow-next/scripts/**, tests/**, `plugins/flow-next/{skills,agents,commands,references}/**`, codex mirror, unknown) -> exit 1 (full gates). Empty diff -> exit 1 (fail-closed). Reuse `_classify_triage_path`'s `\\`->`/` normalization (shared helper, do not reimplement) and `TRIAGE_DOC_EXTS` where semantics align. Also emit `--json` detail (paths + class + reason) for evidence lines.
4. Tests (hermetic unittest per `test_qa_receipt.py` conventions - tempdir git repos, no network): receipt round-trip + atomicity; check honors exact-sha clean-tree fresh receipt; check fails closed on dirty tree / sha mismatch / stale (>24h) / schema 2 / malformed JSON / missing dir / non-repo; classify forces FULL for every skill/agent/command md, `.flow/bin/flowctl.py`, any `.py`, mixed docs+code diffs; classify passes docs-only sets; R5 regression: classifier has no content inspection (path-only - assert no file reads beyond git plumbing); Windows path normalization case.

## Acceptance
- [ ] R1: receipt/check contract exactly as spec R1 (exit codes 0/1/2+, 24h TTL, clean-tree-outside-.flow, per-receipt files)
- [ ] R2: classify contract exactly as spec R2 (fail-closed, carve-outs, shared normalization)
- [ ] R5: regression tests pin path-only predicates (no semantic/content probes)
- [ ] R7: dual-copy identical; full suite green pre+post

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
