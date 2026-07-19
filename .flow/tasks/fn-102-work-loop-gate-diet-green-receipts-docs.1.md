---
satisfies: [R1, R2, R5, R7]
---

## Description

New flowctl subcommand group `gate` mirroring the triage-skip architecture (constants near flowctl.py:26652, argparse group pattern like `memory`/`prospect`, registration near 32437). Dual-copy: edit `plugins/flow-next/scripts/flowctl.py`, then `cp` to `.flow/bin/flowctl.py` (byte-identical, both committed together).

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `.flow/bin/flowctl.py`, `plugins/flow-next/tests/test_gate_receipt.py`, `plugins/flow-next/tests/test_gate_classify.py`

1. `gate receipt --gate <id> --command "<exact command>"`: write `.flow/tmp/green-receipts/<sha8>-<gate_id>.json` = `{schema: 1, head_sha, gate_id, command_sha256, timestamp}` via `atomic_write_json`. One file per receipt (no shared ledger, no lock). `command_sha256` = sha256 of the exact command string - the receipt certifies exactly one command. mkdir -p the dir; not-a-git-repo -> exit 2.
2. `gate check --gate <id> --command "<cmd>"`: exit 0 (honored) iff receipt for HEAD sha8 exists AND full `head_sha` matches AND `command_sha256` matches the probe command AND worktree clean per the ignore set (`git status --porcelain=v1 -z --no-renames --untracked-files=all`; ignore ONLY `.flow/**` MINUS `.flow/bin/**` MINUS `.flow/config.json` - dirty `.flow/bin/**` or `.flow/config.json` forces exit 1) AND `0 <= age <= 24h` (future timestamps rejected) AND `schema == 1`. ANY other condition (missing, unparseable, mismatch, dirty, stale, future, no repo) -> exit 1; real errors 2+. Never crashes on malformed JSON.
3. `gate classify --base <ref>`: ordered precedence per spec R2. Paths from `git diff --name-only -z --no-renames <ref>...HEAD` UNION `git status --porcelain=v1 -z --no-renames --untracked-files=all` (NUL-delimited; rename sides both counted; untracked per-file). (1) FORCE-FULL: any code/config extension (`TRIAGE_CODE_EXTS` + `.py .sh .cmd .ps1 .toml .json .yaml .yml`; extension beats prefix), `scripts/**`, `plugins/flow-next/scripts/**`, `plugins/flow-next/tests/**`, `.flow/bin/**`, `.flow/config.json`, `plugins/flow-next/{skills,agents,commands,references,templates,hooks}/**`, `plugins/flow-next/codex/**`; (2) SAFE: `docs/**`, `agent_docs/**`, `optimization/**`, root `CHANGELOG.md README* GLOSSARY.md STRATEGY.md`, `plugins/flow-next/docs/**` (.md/.mdx/.txt only), remaining `.flow/**`; (3) unmatched -> FULL. Exit 0 iff non-empty diff and all SAFE; else 1; errors 2+. Reuse `_classify_triage_path` normalization + TRIAGE constants (no reimplementation). `--json` emits per-path class + reason.
4. Tests (hermetic unittest per `test_qa_receipt.py` conventions - tempdir git repos, no network): receipt round-trip; check honors exact-sha clean-tree fresh receipt with matching command; check fails closed on dirty tree (incl. dirty `.flow/bin/flowctl.py` and `.flow/config.json` specifically), sha mismatch, COMMAND mismatch, stale (>24h), FUTURE timestamp, schema 2, malformed JSON, missing dir, non-repo; classify forces FULL for every skill/agent/command/reference/template/hook md, `.flow/bin/**`, any code extension incl. `.py` under `docs/`, mixed docs+code diffs, empty diff, rename crossing the `.flow/` boundary, filenames with spaces; classify passes pure-SAFE sets; R5 regression: classifier is path-only (no content reads beyond git plumbing); Windows normalization case.

## Acceptance
- [ ] R1: receipt/check contract exactly as spec R1 (command fingerprint, exit codes, 0<=age<=24h, ignore-set cleanliness, per-receipt files)
- [ ] R2: classify contract exactly as spec R2 (ordered precedence, plumbing-safe path collection, fail-closed)
- [ ] R5: regression tests pin path-only predicates
- [ ] R7: dual-copy identical; full suite green pre+post

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
