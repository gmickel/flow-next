# fn-64-tracker-sync-project-flow-spec.4 GitHub adapter relation transport (native REST deps + fenced body-block fallback, #N parsing)

## Description
### Goal
Implement the relation transport on the GitHub `gh` adapter — native REST issue dependencies (GA Aug 2025) with a provenance-fenced body-block fallback. **Satisfies R2, R3.**

### Investigation targets
- `references/adapter-interface.md` — the contract from fn-64.2.
- `references/github.md:203-301` — the `gh` transport (6 methods); `:136` `setStatus` reduced-fidelity via `status:` labels is the model for the fallback. Durable key = GraphQL node id (`:85`).
- Native path: REST `GET/POST/DELETE /repos/{o}/{r}/issues/{n}/dependencies/blocked_by` via `gh api`. `issue_id` is the numeric **DB id** (not `#N`) — needs an id-resolution step (`gh api .../issues/{n}` → `.id`). Only `blocked_by` is writable; max 50/type. Feature-detect with a GET probe (404/410 → fallback).
- Fallback path: a provenance-fenced `<!-- flow:deps -->`…`<!-- /flow:deps -->` body block of `#N` references, rewritten only inside the markers. Use opaque tokens, not raw keys, where a marker stores ids (memory: trackers-auto-linkify-issue-key — though GH linkify is milder, keep the pattern consistent).
- `gh` identifier parser must accept `#N`, `owner/repo#N`, and bare `N` (memory: set-tracker-id-rejected-github-n).
## Acceptance
- [ ] Verify GitHub native issue-dependency endpoints against official REST docs / a live `gh api` probe BEFORE coding; keep the fallback required when the probe fails.
- [ ] Native path implements list (`GET`) + add (`POST`) for `/repos/{o}/{r}/issues/{n}/dependencies/blocked_by`; `issue_id` resolved to the numeric DB id (`gh api .../issues/{n}` → `.id`); respect 50/type cap and blocked_by-only-writable. `DELETE` is OPTIONAL/future — not required here; default behavior is safe no-delete (never removes remote relations).
- [ ] Feature-detect with a GET probe (404/410 → fallback).
- [ ] Fallback: provenance-fenced `<!-- flow:deps -->`…`<!-- /flow:deps -->` body block of `#N` refs, rewritten only inside the markers; idempotent (no duplicate `#N` lines on rerun, R3).
- [ ] github.md updated documenting native-vs-fallback selection + completed-blocker behavior. (Bare-`N` identifier widening is owned by fn-64.1.)
## Done summary
Implemented the GitHub adapter relation transport for dependency projection in references/github.md: native REST issue-dependencies via `gh api` (GET feature-detect probe, POST `blocked_by` with numeric DB-id resolution via `-F`, 50/type cap, blocked_by-only-writable, no-delete-default) with a provenance-fenced `<!-- flow:deps -->` `#N` body-block fallback; read-before-write dedup, never-delete-non-ours, completed-blocker semantics, and capability-parity table rows extending the R13 transport-blind proof. Native facts verified against official REST docs + a live `gh api` probe. Satisfies R2, R3.
## Evidence
- Commits: 60a10a72, f626188
- Tests: live `gh api` probe against gmickel/flow-next: GET .../dependencies/blocked_by exit 0 + [] (feature available); gh api repos/.../issues/{n} --jq .id → numeric DB id; native facts cross-checked vs official GitHub REST docs (API 2026-03-10, GA Aug 2025, 50/type cap), impl-review RP backend: SHIP (after NEEDS_WORK→fix: gh api -f→-F numeric issue_id); R2/R3/R5/R6/R8/R13 all covered, no code test suite — docs-as-implementation (github.md adapter reference); markdown fence/marker balance verified
- PRs: