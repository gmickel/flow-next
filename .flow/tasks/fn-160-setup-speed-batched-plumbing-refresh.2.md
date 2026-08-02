---
satisfies: [R3]
---
# fn-160-setup-speed-batched-plumbing-refresh.2 flowctl setup refresh: zero-question copy-mode upgrade fast path

## Description
Add `flowctl setup refresh` — the deterministic copy-mode upgrade fast path: re-copy snapshots, verify, re-apply docs blocks, restamp `setup_version`, zero questions. Contract per the spec's "Refresh invocation contract", "usage.md provenance", "Filesystem safety", and "Refresh state machine" plan decisions (review round 1).

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_setup_refresh.py` (new), `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/troubleshooting.md`, `README.md`

### Approach
Invocation: `flowctl setup refresh --plugin-root <path> --platform <claude-code|codex|droid|cursor|grok> --json`, called by skill prose from the LIVE plugin CLI (prose owns platform classification). Refusals before any write: `setup_mode=plugin` in `.flow/meta.json`; plugin root missing the expected manifest; resolved copy source under the destination `.flow/bin` (self/local-snapshot source).

Sequence (all outcomes enumerated in output JSON):
1. Copy phase — full Step 4 list (`workflow.md:141-156`): `flowctl`, `flowctl.cmd`, `flowctl.py`, `flowctl_bootstrap.py`, `flowctl-help.txt`, `flowctl_tracker/`, `templates/spec.md`, chmod +x; plus `.codex/agents/*.toml` when `--platform codex` AND `.codex/agents/` exists (never created). Per file: compare-before-write (identical → `unchanged`, no mtime bump), atomic temp+rename in the destination dir (incl. `flowctl.cmd` self-update), containment via the EXISTING `_flow_path_is_contained` / `_flow_leaf_is_safe` helpers — the `.flow` root itself may be a symlink (supported worktree/shared-checkout layout; resolve and use as storage root), symlinked descendants/leaves beneath the resolved root are rejected.
2. Tracker verify (same code path as `scripts/lib/verify_tracker_manifest.py`) — failure → STOP loudly: no docs writes, no stamp; the PRIOR `setup_version` stamp remains (never cleared).
3. Docs blocks — platform selects the snippet template (Codex `$`-syntax AGENTS.md vs slash-syntax elsewhere; plugin template never applies). For each marker-bearing file run the existing setup-block apply state machine (`flowctl.py:2737-2836`); `appended/refreshed/unchanged` proceed; `kept` and `ask` → untouched, listed. NEVER prompt.
4. `.flow/usage.md` provenance: expose a dedicated write API — `flowctl setup usage-record` (exact name free) — that records the normalized hash of the usage.md just written into `.flow/meta.json` `setup.usage_hash`. `setup refresh` calls it internally; the interactive setup prose calls it too (wired in task .3). Refresh: recorded hash matches on-disk → overwrite with new canonical + re-record; file missing → write + record; mismatch → skip + list. No recorded hash (pre-fn-160 installs): identical to current bundled canonical → overwrite + record; different → skip + list (full /flow-next:setup resolves via its ask).
5. Stamp `setup_version` + `setup_date` only when copy+verify succeeded (kept/ask/skipped blocks are listed but do not block the stamp). First flowctl-owned write path for these fields (today raw prose, `workflow.md:282-291`).
- Idempotent: immediate second run → every outcome `unchanged`, zero mtime changes, same stamp.
- Docs: flowctl.md new section; troubleshooting.md L7-14 upgrade remedy + L134/L154 now point at `flowctl setup refresh` (full `/flow-next:setup` remains the reconfigure path); README.md L166-170 upgrade wording.

### Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py:2737-2836` — setup-block apply + its symlink rejection (reuse both; never reimplement hashing)
- `plugins/flow-next/scripts/flowctl.py:17045-17156` — setup-mode invariants (refusal must align)
- `plugins/flow-next/skills/flow-next-setup/workflow.md:141-170,282-291` — copy list + stamp semantics
- `plugins/flow-next/scripts/lib/verify_tracker_manifest.py` — verify contract

**Optional:**
- `plugins/flow-next/tests/test_setup_mode_stamp.py`, `test_setup_block_helper.py` — test patterns
- `agent_docs/setup-modes.md` — refresh semantics prose to stay consistent with

### Key context
- Memory lesson (abort-option copy): output must reflect what actually ran; report partial state honestly.
- `.flow/bin/flowctl` is the 49-line bash launcher (fn-77); never overwrite it with the Python source.
- `setup.usage_hash` is machine-written meta.json state, NOT a config key — no fn-138 schema entry.

### Acceptance
- [ ] Copy-mode repo: one invocation, zero prompts, files+blocks+stamp converged; immediate second run all-`unchanged`, no mtime drift, same stamp
- [ ] Refusals: plugin-mode repo; missing/invalid plugin root; self-source (.flow/bin) — all before any write
- [ ] usage.md provenance tests: old-canonical→new-canonical (recorded hash) overwrites; customized skips+lists; missing writes+records; unrecorded-legacy paths per contract
- [ ] Symlink fixtures: supported symlinked-`.flow`-root layout works; malicious/dangling descendant symlinks rejected; proof of no outside-repo writes
- [ ] `setup usage-record` API exists and is called by refresh; first-setup→later-version-refresh continuity test (hash recorded at setup, changed canonical refreshes cleanly)
- [ ] Verify failure: loud stop before docs/stamp; prior stamp retained; stamps+mtimes asserted at every failure boundary
- [ ] Customized (`kept`/`ask`) docs block: untouched + listed, everything else refreshed and stamped
- [ ] Docs updated (flowctl.md, troubleshooting.md, README.md); ruff + propagation + sync-codex ×2 clean
## Acceptance
- [ ] R3: refresh fast path per the spec's four refresh plan-decision contracts (invocation, provenance, filesystem safety, state machine) — zero questions, plugin-mode + self-source refusals, stamp-on-success-only with prior stamp retained on failure, idempotent
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
