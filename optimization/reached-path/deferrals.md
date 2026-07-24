# Reached-path deferrals & open-spec overlaps (fn-130.1 / R11)

Recorded at B0 freeze and rechecked at closure. Structural rewrite of these skills is **out of scope**
unless a later task creates a new baseline and predeclared oracle that proves a
concrete zero-loss win. Version-ceremony removal alone (task 130.2) is the only
fleet-wide edit that may touch some of these surfaces.

## Non-target skills (no structural rewrite in fn-130)

| Skill | Notes |
|---|---|
| Capture | Accuracy-critical; proximity load-bearing (fn-84). Version removal only if present. |
| Audit | Overlaps open fn-122 verdict-graduation — version ceremony only here. |
| Prospect | Mature critique taxonomy; no structural split. |
| Interview | Beyond version removal — Windows/symlink/NFR coverage must be protected by a new eval before any split. |
| QA | Beyond version removal. |
| Drive | No structural rewrite. |
| Impl Review | Real-engine corpus already optimized (fn-74); no reached-path cluster in fn-130. |
| Spec Completion Review | Same family as impl-review; deferred. |
| Land | Beyond version removal; frozen Pilot/Land grammar wins over open fn-61. |
| Resolve PR | Beyond version removal; forge semantics owned by open fn-73. |
| Ralph Init | Beyond version removal. |
| Sync | Beyond version removal. |
| Map | Beyond version removal. |
| Deps | No structural rewrite. |
| Export Context | No structural rewrite. |
| RP Explorer | No structural rewrite. |
| Flow core (`flow-next`) | No structural rewrite. |
| Worktree Kit | No structural rewrite. |

## Open-spec overlaps (no enabling dependency)

Recheck status before each mutation task and at closure:

| Spec | Status at B0 | Overlap risk | Rule |
|---|---|---|---|
| **fn-129** skill-only invocation architecture | open / deferred | skill naming, frontmatter, commands | Do not touch invocation metadata/names. |
| **fn-122** harden-verdict / graduate recurring | open (hardening sweep done; graduate open) | Audit surfaces | This program removes only version ceremony on Audit. |
| **fn-61** Ralph v2 harness | open | Pilot/Land frozen verdict/receipt grammar | Frozen grammar wins; do not soften. |
| **fn-73** glab git-ops / forge | open (stub) | Make PR / Resolve PR / Land forge semantics | Semantic forge work wins; no conflicting forge edits. |

Closure status:

- fn-129 remains open/deferred; no skill name, frontmatter, command, or alias changed.
- `fn-122-flowctl-hardening-and-performance-completion-sweep` is done; the
  distinct `fn-122-harden-verdict-graduate-recurring` remains open. Audit
  received version-ceremony removal only.
- fn-61 and fn-73 remain open. Pilot/Land terminal grammar and forge semantics
  remain their authoritative surfaces.
- No non-target skill above received a structural rewrite. The final fleet
  result and rationale are recorded in
  [`fleet-results.md`](fleet-results.md).

## Host evidence boundaries

| Host | Contract |
|---|---|
| Claude | Primary production-path loader traces via `stream-json` Read tool_use. |
| Codex | Count **regenerated mirror** files under `plugins/flow-next/codex/`, not canonical proxies. |
| Cursor | No sufficiently precise current primary loader-trace docs — CLI/GUI smoke only; unavailable precise traces are **surfaced**, never silent pass. |
| Droid | Canonical-as-is; smoke where authenticated. |
| Grok | Inspect/TUI where authenticated; unavailable → surface. |
