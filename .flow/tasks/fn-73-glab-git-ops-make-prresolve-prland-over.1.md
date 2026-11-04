---
satisfies: [R4, R5, R11, R12]
---
# fn-73-glab-git-ops-make-prresolve-prland-over.1 Forge rule and adapter registry for the route judge and pilot snapshot

## Description
Builds the seam: the origin-host forge rule, the internal adapter registry, the GitHub adapter wrapping today's `gh` listings unchanged, and the GitLab adapter reading MRs through `glab`. The route judge and the pilot snapshot (both listings) dispatch through it; the snapshot gains the `forge` field. This is the early proof point, so it comes first and carries the live fixture recording for the reads.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/scripts/flowctl_tracker/types.py`, `plugins/flow-next/scripts/flowctl_tracker/executor.py`, `plugins/flow-next/tests/test_forge.py` (new), `plugins/flow-next/tests/fixtures/gitlab/` (new)
**Touches:** [plugins/flow-next/scripts/flowctl.py, plugins/flow-next/scripts/flowctl_tracker/types.py, plugins/flow-next/scripts/flowctl_tracker/executor.py, plugins/flow-next/tests/test_forge.py, plugins/flow-next/tests/fixtures/gitlab/**, plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json]

### Approach
- Forge rule (one function, cached per repo path with a reset hook for tests): origin URL -> host (keep the port), SSH alias via `ssh -G`, github.com / ssh.github.com -> github, gitlab.com or `CI_SERVER_HOST` -> gitlab, else ask each adapter whether it owns the host (`gh auth token --hostname`, then `glab auth status --hostname`; glab first when `GH_ENTERPRISE_TOKEN`/`GITHUB_ENTERPRISE_TOKEN` is set). No origin or unknown -> `None`.
- Registry: a dict of forge name -> adapter reads, following `BACKEND_REGISTRY` (`flowctl.py:7309`) / `wire._PROVIDERS` (`flowctl_tracker/wire/__init__.py:457`). Readers resolve the adapter once; `None` uses the GitHub adapter so fn-310's no-PR answer and its tests hold (R4, R10).
- GitHub adapter: move the existing `gh pr list` calls of `judge_route_state` (:24039) and `pilot_snapshot.list_prs` (:43686) behind it byte-for-byte (argv, timeouts, `_gh_no_pr_forge`, truncation checks). Do not add subprocess calls before `gh` on this path (tests stub on `command[0] == 'gh'`).
- GitLab adapter: `glab api` through the tracker executor with `provider="gitlab"` (gets the stdout-noise strip), lazily imported; add an optional `env` to `Request` and pass it in `_cli` so `GITLAB_HOST=<host:port>` reaches glab. Map MRs into the shared row (state map: opened/locked -> OPEN). Filter to MRs whose source project is the origin project. Paginate open listings (per_page 100); unprovable completeness -> probe failure. Keep the probe timeouts: no executor retry/backoff that exceeds the judge's 10s.
- Spec-approval rows (`_gh_pr_rows`, :23590): resolve the forge; on a forge whose adapter lacks the approval read, report one generic "unsupported on this forge" message.
- `pilot snapshot` output gains top-level `forge`.
- Record fixtures live (maintainer's local GitLab test project; `GITLAB_HOST=localhost:8929`): MR list by source branch (all, open), a locked MR if reachable, pagination with a small per_page, `glab auth status` logged in and for an unknown host, a fork-less project. Save raw output under `tests/fixtures/gitlab/` with the command that produced it.
- Regenerate `flowctl_tracker/MANIFEST.json` (`python3 scripts/gen_tracker_manifest.py`) after the last flowctl.py edit.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:23580-23660` — `_gh_no_pr_forge`, `_gh_pr_rows`, spec-approval caller
- `plugins/flow-next/scripts/flowctl.py:24030-24120` — `judge_route_state` PR probe and `pr_ref`
- `plugins/flow-next/scripts/flowctl.py:43646-43810` — `pilot_snapshot` `list_prs`, `observe`, `current_branch_prs`
- `plugins/flow-next/scripts/flowctl_tracker/executor.py:225-300` — `_cli`, noise strip, `execute`
- `plugins/flow-next/tests/test_pilot_snapshot.py:30-95` and `plugins/flow-next/tests/test_judge_route.py:15-140` — how gh is stubbed

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl_tracker/wire/__init__.py:205-235,455-470` — glab argv with Content-Type and the provider dict
- `plugins/flow-next/scripts/flowctl_tracker/types.py:75-130` — `Request`, `gitlab_cli_hostname`

### Key context
- `glab api --hostname host:port` is rejected ("invalid hostname"); use `GITLAB_HOST`. Inside a checkout whose origin is GitHub, glab otherwise targets that host.
- glab may keep the token in the OS keyring; never read tokens yourself, let glab authenticate.
- flowctl.py imports the tracker package lazily (`flowctl.py:288-291`); keep it that way.

## Acceptance
- [ ] Forge rule classifies github.com, ssh alias, gitlab.com, `CI_SERVER_HOST`, a self-managed host with port, a logged-out host and no origin, with tests
- [ ] Route judge and pilot snapshot read through the registry; their existing tests pass unmodified (R10)
- [ ] GitLab adapter rows from live-recorded fixtures map to the shared row (opened/locked -> OPEN, iid, sha, source_branch, merged_at); glab failure, malformed rows and incomplete pagination are probe failures
- [ ] A fake forge registered in a test is detected and answers the shared lookup with no caller change (R12)
- [ ] Spec-approval on a non-GitHub forge reports unsupported in one generic message
- [ ] `pilot snapshot --json` carries `forge`
- [ ] MANIFEST.json regenerated; focused tests and ruff pass

## Done summary
Added the forge seam to flowctl. `repo_forge` (cached per repo, reset with `repo_forge.cache_clear()`) classifies the origin remote. The internal `FORGE_ADAPTERS` registry holds a GitHub adapter (today's `gh pr list` listings and the spec-approval read) and a GitLab adapter that lists MRs through `glab api` via the tracker executor, with `GITLAB_HOST` passed through the new `Request.env`. The route judge and both pilot snapshot listings read through `forge_list_prs`. Spec-approval rows report "spec approval is unsupported on this forge (<forge>)" off GitHub. `pilot snapshot` now has a top-level `forge` field.

Tier: session (jev long_running 0.44) at default effort (model: claude-opus-5-5[1m])

Evidence (measured):
- `flowctl pilot snapshot --spec <id> --json` in a scratch Flow repo whose origin is the live GitLab project returned `forge: gitlab`, open MR !2, closed !1, and route `existing_pr_tail`. A fork's MR !7 on the same branch name was excluded.
- Focused suites passed: test_forge, test_judge_route, test_pilot_snapshot, test_evidence_and_spec_approval, make-pr preflight/close, flow_auto, tracker executor/distribution (228 tests). `ruff check .` and `sync-codex.sh --check` passed. The existing route, pilot and approval tests are unmodified (R10).
- Fixtures under plugins/flow-next/tests/fixtures/gitlab/ are live recordings (argv, env, exit code, raw stdout/stderr) from GitLab EE 19.5.3 with glab 1.124.0.
- Baseline: green with `PYTHONPATH=plugins/flow-next/tests`. The Quick command as written (`python3 -m unittest plugins/flow-next/tests/test_...py`) fails to import `test_pilot_strikes` without that path. This was the case before the change.

Decisions:
- The route judge's gh argv now matches the pilot snapshot's (`--head B --state all --limit 100 --json number,url,state,headRefName,headRefOid,mergedAt`), so one GitHub listing serves both. Before, the judge's argv had a different flag order and no headRefName. Behaviour and tests are unchanged.
- A locked MR could not be produced on the test project (it is a transient mid-merge state). The opened/locked -> OPEN mapping is tested on a recorded row with only `state` changed. The open listing queries `state=opened` and `state=locked` separately, because GitLab's `opened` filter excludes locked.
- For an SSH origin, the port is dropped because it is the SSH port, not the API port. So a self-managed GitLab reached over SSH on a non-default web port reads as unknown unless `CI_SERVER_HOST` matches. In that case the readers fall back to the GitHub adapter (fn-310's no-PR answer). Follow-up if needed.
- Only glab's recorded logged-out answer counts as "not this host". Any other `glab auth status` failure, such as an offline host or a timeout, ends detection as unknown, so an enterprise gh token never claims a GitLab host.
- Review: NEEDS_WORK on three findings, all fixed: malformed MR rows raised instead of failing the probe, offline glab fell through to gh, and underscore SSH aliases were rejected. The re-review returned SHIP.

Left on the live test instance for later tasks: branches fn73-fx-*, MRs !1-!7 (!3 merged, !1 closed), and fork project root/flownext-fork (id 2).

stage: impl-review - ran [2026-11-04..2026-11-04]

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: f4de7b9e84981b6acfe393fd01348502a6a766bf, 42476807f08617508d0bf30a6a5b1ac29baefec9
- Tests: PYTHONPATH=plugins/flow-next/tests python3 -m unittest plugins/flow-next/tests/test_forge.py plugins/flow-next/tests/test_judge_route.py plugins/flow-next/tests/test_pilot_snapshot.py plugins/flow-next/tests/test_make_pr_preflight_auth.py plugins/flow-next/tests/test_make_pr_close.py plugins/flow-next/tests/test_flow_auto.py plugins/flow-next/tests/test_evidence_and_spec_approval.py plugins/flow-next/tests/test_tracker_executor.py plugins/flow-next/tests/test_tracker_distribution.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check
- PRs: