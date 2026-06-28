## Goal
Author `references/gitlab.md` — the complete, transport-blind GitLab adapter — modeled section-for-section on `references/github.md`. Covers the transport ladder, all nine adapter-interface methods, reduced-status mapping, identity, relations, and enumeration. Prose the host agent follows, NOT literal code. **Endpoints/limits verified live 2026-06-28** (`~/work/agent-scripts/flow-smoke/out/FINDINGS-gitlab.md`). (Spec R1, R2, R5, R6.)

## Files
- `plugins/flow-next/skills/flow-next-tracker-sync/references/gitlab.md` (new) — authored from `github.md` as the template.
- Reads (no edit): `references/adapter-interface.md` (nine-method contract + normalized structs incl. `authorAuthority`), `references/github.md` (section structure + provenance discipline).

## Approach — mirror github.md's section structure (verified specifics inline)
- **Rung detection** (cf. github.md:33): `glab auth status` exit 0 → **`glab api <path>`** rung (the `gh api` equivalent — glab auth + full REST, incl. issue links the `glab issue` subcommand **lacks**; parse with `-O json --jq`, not `-F`); else `GITLAB_TOKEN`/`CI_JOB_TOKEN` → raw REST `/api/v4` (header `PRIVATE-TOKEN` for `GITLAB_TOKEN`/PAT, **`JOB-TOKEN` for `CI_JOB_TOKEN`** — not `PRIVATE-TOKEN`; **URL-encode** the `project` path (`group%2Fsubgroup%2Fproject`) for **both `glab api` AND raw REST** — verified: a literal slash 404s; encoded or the numeric project id works; store literal, derive `encodedProject` once, never double-encode); else no-op. glab reads `GITLAB_TOKEN` from env — **no `glab auth login`** needed (verified). **Token scope:** classic PAT needs **`api`**; a fine-grained token needs only **project** permissions (issue r/w) — a project-scoped fine-grained token with **0 user permissions** does issue list/create fine, so do **NOT** depend on `GET /user`/user-level scopes (least-privilege). Surface GitLab's `403 insufficient_granular_scope` verbatim on a missing project permission. Self-managed host from `GITLAB_HOST` / `glab config` / `CI_SERVER_URL`; REST base = `<host>/api/v4`, never hardcoded gitlab.com. `CI_JOB_TOKEN` write-scope caveat → degrade writes to no-op + receipt. Self-managed TLS escape hatch (opt-in, never silent).
- **No-op rung** (cf. github.md:57): listOpenIssues → `[]`, relation pair → noop, never crash.
- **State fidelity — reduced** (cf. github.md:109): open/closed via `PUT {state_event:close|reopen}` (`closed_at` set) + optional board label; map flow ready/done ↔ open/closed; readiness label pre-create-and-confirm ceremony (cf. github.md:175).
- **Normalized mapping / firewall** (cf. github.md:197): **global issue `id` → `id`** (the durable dedupe key — immutable, project-independent), `<project>#<iid>` → `identifier` (display; `iid` is project-local), state/labels → status/labels; **`authorAuthority` from project membership `access_level`** (`GET /projects/:id/members/all/:user_id`: ≥30 Developer ⇒ writer, <30/none ⇒ outsider, bot/service ⇒ bot) — fail-closed on unknown.
- **Core six** (cf. github.md:220): fetchIssue / writeIssue (upsert) / setStatus / listComments / postComment / readStatus over `glab` (+ REST fallback). **`listComments` MUST filter `system==true` notes** (GitLab automated events) — only `system==false` are human comments. Body writes inherit github.md's `--body-file -` shell-quoting; GitLab-Flavored Markdown, no ADF layer.
- **listOpenIssues** (cf. github.md:357): `glab issue list --state opened` / REST `GET /projects/:id/issues?state=opened&labels=<readyState>`, exact `tracker.readyState` label filter, no-op + note when unset; normalized structs; linkage from sync state, never label absence.
- **Pagination (bounded):** GitLab notes + issues are paginated — `listComments` and `listOpenIssues` use `glab api --paginate` or REST `per_page=100` with **bounded paging** (an explicit max), and a **receipt note if the page bound truncates** the read. Never silently under-read comments or the promoted lane.
- **Relation transport** (cf. github.md:390): `listIssueRelations`/`setIssueRelation` via native issue links (`POST /issues/{iid}/links`). **`is_blocked_by` needs a Premium/Ultimate-licensed namespace** (native directional links verified in a licensed group; 403 `Blocked issues not available for current license` on Free *and* personal-namespace projects — license is per-namespace) → degrade ladder: try `is_blocked_by` → on 403 write **`relates_to`** for GitLab-UI visibility only (directionless) **AND always write/update the `<!-- flow:deps -->` block** for direction + provenance. **`listIssueRelations` returns directed `{from, to, type:"blocks"}` relations ONLY from native directional links or the flow-owned block — NEVER from a directionless `relates_to`.** additive-only / never-delete-non-ours / defer-on-collision; record reduced fidelity on the receipt.
- **Identity / back-reference**: **`flow:<id>` label** (single colon — canonical `github.md` spelling; NOT GitLab's `::` scoped-label syntax) + body marker.

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
Authored `references/gitlab.md` — the complete nine-method GitLab adapter reference doc for tracker-sync, modeled section-for-section on `references/github.md`. Documents the `glab api` → raw-REST → no-op transport ladder, URL-encoded project paths (both rungs), the PRIVATE-TOKEN/JOB-TOKEN header ladder, reduced open/closed status with `status:` label fidelity, the readiness-label ceremony, global-issue-id durable identity + `flow:<id>` label, `system==true` note filtering, `authorAuthority` from project `access_level`, and the Premium-403 → `relates_to`+`<!-- flow:deps -->` block relation degrade ladder.
## Evidence
- Commits: 901a024db48aa86d413aa92316d851dffafb4613
- Tests: python3 -m py_compile flowctl.py (unchanged, compiles), internal markdown cross-link + anchor resolution check (all OK), section-parity check vs references/github.md (all sections covered), triage-skip docs-only SHIP receipt
- PRs: