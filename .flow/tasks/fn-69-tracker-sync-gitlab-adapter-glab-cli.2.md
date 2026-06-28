## Goal
Author `references/gitlab.md` — the complete, transport-blind GitLab adapter — modeled section-for-section on `references/github.md`. Covers the transport ladder, all nine adapter-interface methods, reduced-status mapping, identity, relations, and enumeration. Prose the host agent follows, NOT literal code. **Endpoints/limits verified live 2026-06-28** (`~/work/agent-scripts/flow-smoke/out/FINDINGS-gitlab.md`). (Spec R1, R2, R5, R6.)

## Files
- `plugins/flow-next/skills/flow-next-tracker-sync/references/gitlab.md` (new) — authored from `github.md` as the template.
- Reads (no edit): `references/adapter-interface.md` (nine-method contract + normalized structs incl. `authorAuthority`), `references/github.md` (section structure + provenance discipline).

## Approach — mirror github.md's section structure (verified specifics inline)
- **Rung detection** (cf. github.md:33): `glab auth status` exit 0 → **`glab api <path>`** rung (the `gh api` equivalent — glab auth + full REST, incl. issue links the `glab issue` subcommand **lacks**; parse with `-O json --jq`, not `-F`); else `GITLAB_TOKEN`/`CI_JOB_TOKEN` → raw REST `/api/v4` (header `PRIVATE-TOKEN: <pat>`); else no-op. glab reads `GITLAB_TOKEN` from env — **no `glab auth login`** needed (verified). **Token scope:** classic PAT needs **`api`**; a fine-grained token needs only **project** permissions (issue r/w) — a project-scoped fine-grained token with **0 user permissions** does issue list/create fine, so do **NOT** depend on `GET /user`/user-level scopes (least-privilege). Surface GitLab's `403 insufficient_granular_scope` verbatim on a missing project permission. Self-managed host from `GITLAB_HOST` / `glab config` / `CI_SERVER_URL`; REST base = `<host>/api/v4`, never hardcoded gitlab.com. `CI_JOB_TOKEN` write-scope caveat → degrade writes to no-op + receipt. Self-managed TLS escape hatch (opt-in, never silent).
- **No-op rung** (cf. github.md:57): listOpenIssues → `[]`, relation pair → noop, never crash.
- **State fidelity — reduced** (cf. github.md:109): open/closed via `PUT {state_event:close|reopen}` (`closed_at` set) + optional board label; map flow ready/done ↔ open/closed; readiness label pre-create-and-confirm ceremony (cf. github.md:175).
- **Normalized mapping / firewall** (cf. github.md:197): IID/global-id → `id`, `<project>#<iid>` → `identifier`, state/labels → status/labels; **`authorAuthority` from project membership `access_level`** (`GET /projects/:id/members/all/:user_id`: ≥30 Developer ⇒ writer, <30/none ⇒ outsider, bot/service ⇒ bot) — fail-closed on unknown.
- **Core six** (cf. github.md:220): fetchIssue / writeIssue (upsert) / setStatus / listComments / postComment / readStatus over `glab` (+ REST fallback). **`listComments` MUST filter `system==true` notes** (GitLab automated events) — only `system==false` are human comments. Body writes inherit github.md's `--body-file -` shell-quoting; GitLab-Flavored Markdown, no ADF layer.
- **listOpenIssues** (cf. github.md:357): `glab issue list --state opened` / REST `GET /projects/:id/issues?state=opened&labels=<readyState>`, exact `tracker.readyState` label filter, no-op + note when unset; normalized structs; linkage from sync state, never label absence.
- **Relation transport** (cf. github.md:390): `listIssueRelations`/`setIssueRelation` via native issue links (`POST /issues/{iid}/links`). **`is_blocked_by` needs a Premium/Ultimate-licensed namespace** (native directional links verified in a licensed group; 403 `Blocked issues not available for current license` on Free *and* personal-namespace projects — license is per-namespace) → degrade ladder: try `is_blocked_by` → on 403 fall back to **`relates_to`** (all tiers, directionless, reduced fidelity) and/or the `<!-- flow:deps -->` fenced-body block; additive-only / never-delete-non-ours / defer-on-collision; record reduced fidelity on the receipt.
- **Identity / back-reference**: `flow::<id>` label + body marker (the `::`-named label sticks on Free; scoped-label *behavior* is Premium but unneeded).

## Acceptance
- gitlab.md documents all nine methods with concrete `glab`/REST commands + the normalized mapping (R1).
- Transport ladder (glab → token → no-op), self-managed host + TLS, token-scope (`api` vs fine-grained), `CI_JOB_TOKEN` degrade (R2).
- Reduced status + readiness-label ceremony (R5).
- Relations via issue links with the **Premium-403 → relates_to/body-block** degrade ladder (R6).
- `listComments` filters `system==true`; `authorAuthority` from `access_level`.
- Canonical Claude tool names throughout (Codex mirror regen is fn-69.3).
- Self-hosted MCP route noted as available-but-not-wired (per spec Decision Context).

## Test notes
- Reference doc — correctness is the prose contract + build-time read-through. flowctl-testable bits live in fn-69.1; mirror-safety in fn-69.3. Endpoints/limits already smoke-tested live.

## Description
TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
