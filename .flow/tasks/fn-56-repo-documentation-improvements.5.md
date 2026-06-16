---
satisfies: [R7]
---

## Description
Add a markdown link-check CI gate so internal relative-link drift (a recurring failure mode in this repo's memory) can't recur silently. Use `lychee` via `lycheeverse/lychee-action@v2` to validate internal relative links across the canonical docs surface and fail the build on dead links. Scope it to the hand-authored docs (root `*.md`, `agent_docs/**`, `plugins/flow-next/docs/**`, skill `SKILL.md`s) and **exclude the auto-generated `plugins/flow-next/codex/**` mirror and `.flow/` work artifacts** to keep signal high and runtime low.

**Size:** S/M
**Files:** `.github/workflows/docs-linkcheck.yml` (new), `lychee.toml` or inline action args, optionally `.lycheeignore`.

## Approach
- Add a workflow triggered on PRs touching `**/*.md` (path filter), running `lychee` with `fail: true`.
- Restrict to internal/relative link verification first (offline-style); optionally allow external links but be lenient (external flakiness shouldn't block) — internal dead links are the real target given the relative-paths-only (R17) discipline.
- Exclude the Codex mirror, `.flow/`, and `node_modules`.
- Mind the `lychee` `--base` → `--root-dir` deprecation noted in research.
- Keep it self-contained — no new repo runtime dependency (it's a GitHub Action).

## Investigation targets
**Required** (read before coding):
- `plugins/flow-next/docs/README.md:32-36` — the relative-paths-only link convention this gate enforces
- `.github/workflows/` — existing workflow style/conventions to match
- `plugins/flow-next/docs/ci-workflow-example.yml` — existing CI example to align format with

**Optional** (reference as needed):
- `scripts/ci_test.sh` — how the repo currently gates (R17 vocabulary guard lives here)

## Key context
- Research: `lycheeverse/lychee-action@v2` is current best-in-class; `markdownlint-cli2` is an option but risks noise across 600+ files — link-check is the high-value/low-noise core, so keep this task to link-checking only.
- Pure CI/docs tooling addition → no plugin version bump.

## Acceptance
- [ ] A GitHub Actions workflow runs `lychee` on the canonical docs surface and fails on dead internal links.
- [ ] The auto-generated `plugins/flow-next/codex/**` mirror and `.flow/` artifacts are excluded.
- [ ] The workflow passes against the current repo state (fix any dead links it surfaces, or coordinate with .2/.4 which also touch links).
- [ ] No plugin version bump.

## Done summary
Landed via PR #175 (commit 669fba2) — GitHub docs overhaul. Spec/task scaffold was never committed; deliverables shipped without flow bookkeeping. Closing retroactively.
## Evidence
- Commits:
- Tests:
- PRs: