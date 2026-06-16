---
satisfies: [R5]
---

## Description
Add the standard GitHub community-health docs the repo is missing and give new contributors a single entry point. Currently absent: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/`. Present: `LICENSE`, `.github/pull_request_template.md`, `.github/FUNDING.yml`. Contributor guidance today is scattered across `agent_docs/` and `CLAUDE.md` with no front door.

`CONTRIBUTING.md` should be a thin router to the existing onboarding (don't duplicate it): point to `agent_docs/local-dev.md` (local plugin dev + smoke tests + Ralph e2e), `agent_docs/adding-skills.md` (how to add a skill — the three-edit rule), `agent_docs/releasing.md` (cutting a release), and the PR workflow in `CLAUDE.md`. `SECURITY.md` should give a private reporting channel (use the repo author contact from CLAUDE.md metadata: gordon@mickel.tech). Issue templates: a bug report + feature request under `.github/ISSUE_TEMPLATE/` following GitHub conventions.

**Size:** M
**Files:** `CONTRIBUTING.md`, `SECURITY.md`, `.github/ISSUE_TEMPLATE/bug_report.md` (or `.yml`), `.github/ISSUE_TEMPLATE/feature_request.md` (or `.yml`); optionally `CODE_OF_CONDUCT.md`.

## Approach
- `CONTRIBUTING.md`: links + a short "how to propose a change" (use `/flow-next:plan` / `/flow-next:capture`), relative paths only (R17). Keep it short — route, don't restate.
- `SECURITY.md`: supported-versions note + private disclosure contact; standard GitHub format.
- Issue templates: minimal, GitHub-native; align labels with whatever the repo already uses.
- These are pure-docs additions → no plugin version bump (CLAUDE.md docs-only rule). They are root/.github files, not synced → no `sync-codex.sh` needed.

## Investigation targets
**Required** (read before coding):
- `agent_docs/local-dev.md`, `agent_docs/adding-skills.md`, `agent_docs/releasing.md` — what CONTRIBUTING should route to
- `CLAUDE.md` — PR workflow section + repo metadata (author/contact) for SECURITY.md
- `.github/pull_request_template.md` — existing template style to match

**Optional** (reference as needed):
- `.github/FUNDING.yml` — confirms `.github/` layout conventions

## Acceptance
- [ ] `CONTRIBUTING.md` exists and routes contributors to `agent_docs/{local-dev,adding-skills,releasing}.md` + the CLAUDE.md PR workflow (relative links, no duplication).
- [ ] `SECURITY.md` exists with a private reporting channel and supported-versions note.
- [ ] `.github/ISSUE_TEMPLATE/` has at least bug-report and feature-request templates.
- [ ] No plugin version bump (docs-only); `bash scripts/ci_test.sh` passes.

## Done summary
Landed via PR #175 (commit 669fba2) — GitHub docs overhaul. Spec/task scaffold was never committed; deliverables shipped without flow bookkeeping. Closing retroactively.
## Evidence
- Commits:
- Tests:
- PRs: