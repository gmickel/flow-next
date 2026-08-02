---
satisfies: [R3]
---
# fn-160-setup-speed-batched-plumbing-refresh.2 flowctl setup refresh: zero-question copy-mode upgrade fast path

## Description
Add `flowctl setup refresh` — the deterministic copy-mode upgrade fast path: re-copy snapshots, verify, re-apply docs blocks, restamp `setup_version`, zero questions.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_setup_refresh.py` (new), `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/troubleshooting.md`, `README.md`

### Approach
Sequence (stamp LAST — fn-121 invariant):
1. Refuse hard (non-zero, clear message) when `.flow/meta.json` `setup_mode` is `plugin` — plugin mode has nothing to refresh; never convert modes.
2. Re-copy the full Step 4 list from the plugin root (`workflow.md:141-156`): `flowctl`, `flowctl.cmd`, `flowctl.py`, `flowctl_bootstrap.py`, `flowctl-help.txt`, `flowctl_tracker/` (delete-then-copy), `templates/spec.md`, chmod +x. Plus `.codex/agents/*.toml` re-copy IFF `.codex/agents/` already exists in the repo (presence = the platform signal; never create it).
3. Verify via the same code path as `scripts/lib/verify_tracker_manifest.py` — on failure STOP loudly (corrupt install; same contract as today's Step 4, no rollback).
4. For each file already carrying the `<!-- BEGIN FLOW-NEXT -->` marker: run the existing setup-block apply state machine (`flowctl.py:2737-2836`). `appended/refreshed/unchanged/kept` proceed silently; `ask` → leave the block untouched, record it, continue. NEVER prompt.
5. `.flow/usage.md`: overwrite only when byte-identical to a canonical prior version cannot be disproven cheaply — implement as: write when missing; overwrite when identical to the bundled canonical after CRLF/trailing-newline normalization is FALSE→ skip+list, TRUE→ no-op; i.e. only untouched-or-missing gets written, customized is skipped and listed.
6. Restamp `setup_version` + `setup_date` in `.flow/meta.json` (this becomes the first flowctl-owned write path for those fields — today they are raw prose, `workflow.md:282-291`). Stamp only after steps 2-5 succeeded.
7. Output JSON: copied files, verify result, per-file block action, skipped/ambiguous list ("resolve via /flow-next:setup"), stamped version.
- Idempotent: second run → `unchanged` everywhere, no mtime bumps on unchanged files.
- Docs: flowctl.md new section; troubleshooting.md L7-14 upgrade remedy + L134/L154 re-run references now point at `flowctl setup refresh` (full `/flow-next:setup` remains the reconfigure path); README.md L166-170 upgrade wording.

### Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py:2737-2836` — setup-block apply to call through (never reimplement hashing)
- `plugins/flow-next/scripts/flowctl.py:17045-17156` — setup-mode invariants (refusal must align)
- `plugins/flow-next/skills/flow-next-setup/workflow.md:141-170,282-291` — copy list + stamp semantics
- `plugins/flow-next/scripts/lib/verify_tracker_manifest.py` — verify contract

**Optional:**
- `plugins/flow-next/tests/test_setup_mode_stamp.py`, `test_setup_block_helper.py` — test patterns
- `agent_docs/setup-modes.md` — refresh semantics prose to stay consistent with

### Key context
- Memory lesson (abort-option copy): any "nothing changed" claim in output must reflect what actually ran; report partial state honestly.
- Windows: refresh runs through the live launcher; copying `flowctl.cmd` over itself mid-run is the one self-update hazard — copy it via temp+rename.
- `.flow/bin/flowctl` is the 49-line bash launcher (fn-77); never overwrite it with the Python source.

### Acceptance
- [ ] Copy-mode repo: one invocation, zero prompts, files+blocks+stamp converged; second run is a clean no-op
- [ ] Plugin-mode repo: hard refusal, no writes
- [ ] Customized docs block: skipped + listed, everything else still refreshed and stamped
- [ ] Verify failure: loud stop before any docs/stamp write
- [ ] Docs updated (flowctl.md, troubleshooting.md, README.md); ruff + propagation + sync-codex ×2 clean

## Acceptance
- [ ] R3: refresh fast path — full snapshot re-copy (+.codex/agents when present), verify, marker-scoped block apply, stamp-last, zero questions, plugin-mode refusal, idempotent


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
