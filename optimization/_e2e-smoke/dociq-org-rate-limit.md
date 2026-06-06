# E2E smoke — optimized scouts → planner, against a hard DocIQ-Sphere feature

**Purpose:** the integration-level gate the per-skill loops didn't cover — do the *budgeted* (leaner)
scouts still feed `/flow-next:plan` enough to surface hard-to-find code? Run on a deliberately
cross-cutting feature in `~/work/DocIQ-Sphere`.

**Feature:** org-scoped rate limiting on the agent-run pipeline (cap agent-runs/org/rolling-hour,
per-org configurable, clear error when exceeded).

**Hard-to-find answer key (probed manually first):**
- A: `agentRuns.ts:329 start` + `:350 startForApi` — and the *shared* chokepoint they funnel through.
- B: `orgSettings.ts` / `_shared/tableFields.ts orgSettingsFields` — the non-obvious per-org config home.
- C: `apiKeys.ts` `rateLimit{Enabled,Max,TimeWindow}` — the existing convention to mirror.
- D: no `@convex-dev/rate-limiter` component installed → mechanism is a gap; `by_org_createdAt` index fits.

**Result — STRONG PASS.**
- **Optimized repo-scout** (live budgeted prompt) found MORE than the key: the real chokepoint
  `startRunWithIdentity:214-327` (the shared helper both paths funnel through), the external call sites,
  the `by_org_createdAt` index, the full orgSettings wiring, the apiKeys precedent, and gotchas
  (reuse branch :254-290, two entry points, ConvexError). Budget-compliant, [VERIFIED]-tagged.
- **Optimized context-scout** additionally surfaced a **dormant `monthlyAgentRunLimit` field that
  exists but is enforced nowhere** (tableFields.ts:1636-1637) — a reuse insight, plus the REST 429 path.
- **Optimized flow-gap-analyst** surfaced the blocking gaps: sliding-vs-bucket window, concurrent-start
  race, counter semantics (started/active, failed/cancelled), default/limit=0, stacking with the
  per-API-key limit, fail-open/closed.
- **Planner synthesis** (read ONLY the three leaner scout outputs, `tool_uses: 0` — zero repo access)
  produced a concrete, correct 4-task plan that pinned the chokepoint, the config field + 3-place
  threading, the apiKeys/dormant-field precedents, the `by_org_createdAt` rolling-window count, the
  429 mapping, and all blocking decisions.

**Verdict:** the output-budget mutations preserve features at the CONSUMER level, not just at the
scout-output level. The leaner scouts feed the planner as well or better (less clutter, more signal).
This closes the "unit-level only" gap noted on PR #166 — safe to ship.
