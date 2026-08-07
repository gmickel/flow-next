# fn-98 Codex MAv2: steering re-check, docs currency, and the read-only guarantee

## Goal & Context
<!-- scope: business -->

Watch stub. **Re-checked 2026-08-07:** of the four issues, the spawn-layer pair is FIXED upstream (openai/codex#32782 agent_type, #33268 dropped overrides - both closed 2026-07-16), but #33314 (role-profile application not VERIFIABLE) and #33267 (codex exec + MAv2 children return undecodable results) remain open as of codex 0.147.0. Unverifiable steering fails our routing-evidence bar (read the host record, never the model self-report), so the recommendation is UNCHANGED: `codex exec -m` same-family self-bridge stays the robust route from a Codex host; the sync-time worker pin stays opt-in. Docs date-refreshed (orchestration.md, platforms.md, usage.md canonical + dogfood copy) in the same pass.

**Next check: ~2026-09-15**, or sooner if #33314/#33267 close. Closing condition unchanged: a live probe where a role registered with developer_instructions + a model pin, spawned from a Sol parent, shows the pinned model in the CHILD session_meta (host record, not self-report). If both issues are fixed then: simplify the three doc notes, consider promoting the worker-pin recommendation (still opt-in - prompted-layer principle stands).

## Edge Cases & Constraints
<!-- scope: technical -->

- The prompted-layer principle (no hardcoded model opinions in generated config) survives any upstream fix - only the reliability caveats get removed.
- Absorbed fn-161 (Codex read-only guarantee) 2026-08-03 - same probe matrix closes both.
