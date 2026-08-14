# Deterministic diagnostics: honest lock unavailability, model on the attempt row (#340, #338 half B)

## Goal & Context

Two deterministic-tier defects, both "the machinery knows the fact and drops it":

- **#340 (@TechupBusiness).** Every tracker op in their repo fails with `could not acquire .flow/.locks/config.d within 10s; holder appears alive (see owner.json)` - but no holder exists. Verified root cause (reporter's own self-reentrancy theory disproven by a runtime probe - 0 nested acquisitions - and an AST call-graph sweep): `config_lock()`'s acquire loop swallows `PermissionError` from `lock.mkdir()` (flowctl_tracker/config_lock.py ~:262-266, a Windows delete-pending carve-out), polls to the deadline, then raises the hard-coded contention text (~:270-274) regardless of whether the lock dir ever existed or an owner.json was ever read. A denied `mkdir` (unwritable `.flow/.locks`, macOS ACL denying add_subdirectory, root-owned dir from a container run) burns the full 10s and reports a live holder that never was. Reproduced byte-for-byte in /tmp against main-tip code. The task runtime lock already has the right precedent ("Runtime lock unavailable ... cannot prepare lock parent", pinned by test_portable_locks ~:261-272); the config lock never got it.
- **#338 half B (@sn-furali).** The review-attempt ledger row records `backend` but not the resolved model/effort - while the receipt payload already carries `model`, `effort`, and the full `backend:model:effort` spec string (flowctl.py ~:41605-41608). The row is where post-hoc analysis reads, and the model CANNOT be re-derived from config later: resolution has a dispatch-time fallback ladder plus `_receipt_model_effort` (~:4525-4551) records downgrades and codex-resume carries. fn-183 added output_bytes/tool_calls/head_sha provenance and simply never considered model/effort - an oversight, not a decision.

Out of scope, deliberately (decided in triage, stated in the issue replies): publishing verdicts to the PR reviews API (#338 half A - a flow-next-published bot review at current head would satisfy land's own independent-review gate on a NEEDS_WORK verdict, workflow.md ~:305-316 selects on login+head-currency with no state/body read, and would suppress the land.reviewTrigger re-summon; plus a measured 61-rows-per-spec flood). A `--model` flag on `review-rounds record` (host/rp path - a narrating agent could claim a model; mirror the measured_tool_calls codex-only gate posture). Hostname/PID-reuse stale-owner deadlocks (real, separate issue, do not bundle).

## Acceptance Criteria

- R1: `config_lock()` remembers the last `mkdir` exception; when the deadline passes AND the lock path does not exist AND the last error was `PermissionError`, it fails FAST (does not burn the deadline) raising `ConfigLockUnavailable` (subclass of ConfigLockTimeout so all ~25 `except ConfigLockTimeout` sites keep working) with a message naming the errno/strerror and the lock parent path - never the "holder appears alive" text. The Windows carve-out is preserved: `PermissionError` while the lock path EXISTS keeps polling to the deadline.
- R2: honest timeout composition when the lock path exists: owner.json readable -> message names pid/host/acquired_at; owner.json absent/unreadable -> message says owner absent plus when the dir becomes stale-reclaimable. The "holder appears alive" text appears only when an owner was actually observed.
- R3: attempt rows gain optional `model` and `effort` keys, written only when the dispatcher resolved them (absent otherwise - never "unknown"/"auto"): plumb `reviewed_model`/`reviewed_effort` kwargs through `_record_review_attempt_locked` (~:10858) from the same `_receipt_model_effort` values that feed the receipt, threaded via `_finish_backend_exec` alongside reviewed_head_sha/reviewed_base_sha, journaled and crash-replayed like the fn-183 fields. rp/host paths record no key. NO `--model` flag on `review-rounds record`.
- R4: `review-rounds attempts --json` surfaces the new keys; docs/architecture.md's review-bookkeeping section documents them under the existing absence-means-unknown paragraph.
- R5: regression tests: (a) non-writable `.locks` -> ConfigLockUnavailable, returns well under timeout, message has permission+path and NOT "holder appears alive" (skipIf Windows/root); (b) held lock still reports pid/host; (c) ownerless fresh config.d -> owner-absent message; (d) PermissionError while path exists -> polls to deadline (pins the Windows path); (e) attempt row carries model/effort on a codex-dispatched attempt and lacks the keys on an rp-recorded one; (f) journal replay preserves them.
- R6: CHANGELOG Unreleased credits both reporters; needs-info reply content for #340 (asking for `ls -laO`/ACL specifics) drafted into the issue reply at release time.

## Boundaries

- No lock semantics changes (timeouts, staleness windows, poll interval are spec-fixed constants - no `tracker.lockTimeout` key).
- No environment diagnoser in the lock code (no uid checks, mount sniffing, ACL parsing - report errno + path + observed owner, let the host interpret).
- No new config keys anywhere.
- No journal row schema changes beyond the two additive optional keys.
- Propagation gate (flowctl.py + flowctl_tracker changed: cp, rsync, gen_tracker_manifest, sync-codex x2) at close-out.
- No version bump in implementation commits.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_tracker_resolved_cache test_portable_locks -q
```
