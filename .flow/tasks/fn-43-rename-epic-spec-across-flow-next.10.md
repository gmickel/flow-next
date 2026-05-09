---
satisfies: [R5, R12, R17, R24]
---

## Description

Sweep the medium- and low-density skills (everything not covered by T7a, T7b, T8) for `epic` -> `spec` prose updates. Each skill is a small individual change; the bundle keeps T9 a single coherent worker pass since the files are disjoint. **Owns the `flow-next-setup` upgrade-detection branch** -- this task adds the interactive AskUserQuestion-prompted migration path that R5 + R24 require (the deterministic CLI path lives in T3). Setup template files (`flow-next-setup/templates/*.md`) live in this task's scope (R17 -- the templates that get rendered into user repos on `/flow-next:setup`).

**Size:** M
**Files (14 skill directories + 4 agent files):** <!-- Updated by plan-sync: T5 punted agent-prose CLI-verb rewrite into T10 scope -->
- `plugins/flow-next/skills/flow-next/SKILL.md` (25 refs -- bare meta-router skill)
- `plugins/flow-next/skills/flow-next-deps/SKILL.md` (25 refs)
- `plugins/flow-next/skills/flow-next-plan-review/` (60 refs)
- `plugins/flow-next/skills/flow-next-plan/` (40 refs across SKILL.md + steps.md) <!-- Updated by plan-sync: T5 already touched steps.md scout-dispatcher refs (epic-scout -> spec-scout); ref count is now lower for steps.md; rest of T10 scope intact -->
- `plugins/flow-next/skills/flow-next-work/` (34 refs across SKILL.md + phases.md) <!-- Updated by plan-sync: T5 already updated phases.md dispatcher prompt-input keys (EPIC_ID: -> SPEC_ID:) in 2 templates; CLI verb + general prose pass still required -->
- `plugins/flow-next/skills/flow-next-sync/` (14 refs) <!-- Updated by plan-sync: T5 already updated flow-next-sync/SKILL.md dispatcher prompt-input keys; remaining prose pass still required -->
- `plugins/flow-next/skills/flow-next-setup/` (36 refs -- including templates/usage.md, agents-md-snippet.md, claude-md-snippet.md AND new upgrade-detection workflow branch)
- `plugins/flow-next/skills/flow-next-prospect/` (21 refs)
- `plugins/flow-next/skills/flow-next-interview/` (15 refs)
- `plugins/flow-next/skills/flow-next-impl-review/` (7 refs)
- `plugins/flow-next/skills/flow-next-export-context/` (3 refs)
- `plugins/flow-next/skills/flow-next-strategy/` (4 refs)
- `plugins/flow-next/skills/flow-next-audit/` (1 ref)
- `plugins/flow-next/skills/flow-next-memory-migrate/` (1 ref)
- `plugins/flow-next/agents/spec-scout.md` (CLI verbs in legacy-alias mode post-T5; rewrite to canonical) <!-- Updated by plan-sync: T5 punted CLI-verb rewrite to T10 -->
- `plugins/flow-next/agents/plan-sync.md` (CLI verbs in legacy-alias mode post-T5) <!-- Updated by plan-sync: T5 punted CLI-verb rewrite to T10 -->
- `plugins/flow-next/agents/worker.md` <!-- Updated by plan-sync (T10): grep verified zero `epic`/`--epic`/`EPIC_ID` refs at fn-43.10 implementation time; T5 commit 225dc94 already shipped a clean SPEC_ID-aware version. No diff change required. -->
- `plugins/flow-next/agents/quality-auditor.md` <!-- Updated by plan-sync (T10): grep verified zero epic refs; quality-auditor reviews diffs and never references the artifact-type word. No diff change required. -->

## Approach

- Per-skill prose pass: "epic" -> "spec" where it refers to the flow-next artefact; CLI verbs `flowctl epic *` -> `flowctl spec *`; `--epic <id>` flag -> `--spec <id>` in help/prose.
- **Agent-prose CLI verbs (T5 carryover).** T5 reverted CLI verbs in `plugins/flow-next/agents/{spec-scout,plan-sync,worker,quality-auditor}.md` to legacy alias form (`flowctl epics`, `tasks --epic`) because the codex impl-reviewer hallucinated about CLI verb availability. T10 owns the rewrite of those agent prose files to canonical `flowctl specs` / `tasks --spec` once the worker can hold proper context (T1+T2 ship the verbs). Scope was originally 4 agent files under `plugins/flow-next/agents/`. <!-- Updated by plan-sync (T10): re-verified scope at impl time — `worker.md` and `quality-auditor.md` were already cleaned by T5's commit 225dc94 (zero `epic`/`--epic`/`EPIC_ID` grep hits). Active rewrite scope is `spec-scout.md` + `plan-sync.md` only. The "4 files" wording in this paragraph is preserved as historical context per R-ID-stability rule. -->

- Specifically watch for:
  - flow-next-plan/steps.md: 33 refs, includes Step 5 epic spec creation (`flowctl epic create + set-plan` heredoc).
  - flow-next-plan-review: refers to "epic spec" throughout review-prompt construction.
  - flow-next-setup/templates/usage.md, agents-md-snippet.md, claude-md-snippet.md: 28 refs combined (R17 -- these ship to user repos via /flow-next:setup, ending up in user CLAUDE.md / AGENTS.md).
  - flow-next-setup itself: T4's banner-aware upgrade detection lives here as a NEW workflow branch (R5 + R24 interactive arm).
- **flow-next-setup upgrade-detection branch (NEW; R5/R24)**:
  - Detect at workflow entry: pre-1.0 `.flow/` (`.flow/epics/` exists, no `.flow/.flow_version` sentinel).
  - When detected, prompt the user via `AskUserQuestion` with three options: (a) Migrate now (recommended) -- dispatches to `flowctl migrate-rename --yes`, summarizes result; (b) Defer (writes `.flow/.banner-acknowledged` so the next `flowctl` invocation suppresses the banner for 7 days); (c) Suppress banner permanently -- prints instructions for `FLOW_NO_AUTO_MIGRATE=1`.
  - **Defer ack-file format (T4 contract).** The setup defer branch must write `.flow/.banner-acknowledged` with an ISO-8601 UTC timestamp ending in `Z` — the same format `flowctl migrate-rename --dry-run` writes via `now_iso()` (e.g. `2026-05-08T14:23:11.123456Z\n`). T4's `_banner_ack_within_renudge_window` parses both `...Z` and `...+00:00`. Easiest path: dispatch a `flowctl migrate-rename --dry-run` invocation from the defer branch — that already writes the ack file as a side effect AND surfaces the migration plan to the user, which is value-add for the defer experience. Alternative: write directly via Edit/Write but use the exact `now_iso()` shape. Do NOT write a Unix epoch / human-readable date / non-UTC timestamp. <!-- Updated by plan-sync: T4 ships ISO-8601-Z format via now_iso(); setup defer must match -->
  - **Suppression env vars (T4 contract).** Option (c) instructions must name `FLOW_NO_AUTO_MIGRATE=1` (the user-opt-out knob T4 wired). For completeness the prose can also mention that `FLOW_RALPH=1` and `REVIEW_RECEIPT_PATH=...` already suppress the banner during autonomous loops — but those are not user-facing knobs, so keep the user instructions focused on `FLOW_NO_AUTO_MIGRATE=1`. <!-- Updated by plan-sync: T4 ships full suppression matrix; user-facing knob is FLOW_NO_AUTO_MIGRATE -->
  - This is the interactive arm of the consented-migrate design. The deterministic arm (`flowctl migrate-rename --yes`) lives in T3.
  - Use canonical Claude-native tool names (`AskUserQuestion`); sync-codex.sh rewrites for Codex mirror in T13.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next/SKILL.md` (bare meta-router, 25 refs).
- `plugins/flow-next/skills/flow-next-plan/steps.md` (33 refs; some scout-dispatcher refs already updated by T5).
- `plugins/flow-next/skills/flow-next-plan-review/` (60 refs across SKILL.md + workflow.md).
- `plugins/flow-next/skills/flow-next-setup/templates/usage.md, agents-md-snippet.md, claude-md-snippet.md`.
- `plugins/flow-next/skills/flow-next-setup/workflow.md` (add upgrade-detection branch).
- `plugins/flow-next/agents/{spec-scout,plan-sync,worker,quality-auditor}.md` (CLI verbs in legacy-alias mode post-T5; rewrite to canonical). <!-- Updated by plan-sync (T10): worker + quality-auditor verified clean at impl time (T5 commit 225dc94 already shipped them spec-aware); active rewrite landed in spec-scout + plan-sync only. -->

## Key context

- The setup template files are the highest-leverage per-install surface: injected into every user repo on `/flow-next:setup`. Get the spec vocabulary right.
- The upgrade-detection branch is the interactive arm of R5's two-path migration. Without it, only `flowctl migrate-rename --yes` works.

## Acceptance

- [ ] All 14 skill directories scanned and updated; zero remaining `flowctl epic` or `--epic <id>` references in user-facing prose.
- [ ] `plugins/flow-next/agents/{spec-scout,plan-sync,worker,quality-auditor}.md` CLI verbs rewritten from legacy-alias form (`flowctl epics`, `tasks --epic`) to canonical (`flowctl specs`, `tasks --spec`). T5 punted this rewrite. <!-- Updated by plan-sync (T10): grep at impl time showed `worker.md` + `quality-auditor.md` already canonical (zero `epic`/`--epic`/`EPIC_ID` refs); active rewrite landed in `spec-scout.md` + `plan-sync.md` only. Acceptance satisfied for all four files (two via prior T5 work, two via T10 commit). -->
- [ ] flow-next-plan/steps.md Step 5 uses `flowctl spec create + spec set-plan` heredoc.
- [ ] flow-next-setup workflow.md has an "upgrade detected" branch that prompts via `AskUserQuestion` with three options (migrate / defer / suppress) and dispatches to `flowctl migrate-rename --yes` on user accept.
- [ ] flow-next-setup template files (usage.md, agents-md-snippet.md, claude-md-snippet.md) use spec vocabulary -- new user repos get clean prose. (R17 setup templates).
- [ ] `AskUserQuestion` call in setup upgrade branch uses canonical Claude-native name (sync-codex.sh rewrites for Codex mirror in T15). <!-- Updated by plan-sync: T6 done summary confirms Codex mirror regen lives in T15, not T13 -->

## Done summary
Swept 14 skill directories + 4 agent files for `epic` → `spec` prose updates per the fn-43 rename. Added a new `flow-next-setup` Step 1b "Pre-1.0 layout detection" interactive arm (R5/R24): detects `.flow/epics/` + missing `.flow/.flow_version` sentinel, prompts via `AskUserQuestion` for migrate-now / defer / suppress-permanently, and dispatches `flowctl migrate-rename --yes` (or `--dry-run` for the defer path's banner-ack side effect). Updated all `flow-next-setup/templates/*.md` user-repo-bound snippets to spec vocabulary (R17). Renamed internal `EPIC_MODE` → `SPEC_MODE` in `flow-next-work/phases.md`. Rewrote CLI verbs in `agents/{spec-scout,plan-sync}.md` from legacy-alias form to canonical (T5 carryover); confirmed `worker.md` and `quality-auditor.md` were already canonical post-T5 (commit 225dc94) via grep, recorded the finding via plan-sync breadcrumbs in this task spec. Frozen-string slugs preserved for artifact round-trip (`duplicates-open-epic` taxonomy in prospect, `planSync.crossEpic` config key). 57 CI tests pass; codex `gpt-5.5:high` impl-review verdict: SHIP after one NEEDS_WORK→SHIP fix cycle.
## Evidence
- Commits: f36a8180cd2631cb44349ffc2ae72916488d4021, 0c91f502624f6d1f21b9d0608dd2873b0a70d68b, dad5e2891a8aa2e35ac08f3276ffb380c29ed416
- Tests: plugins/flow-next/scripts/ci_test.sh — 57 passed, 0 failed, flowctl codex impl-review --spec codex:gpt-5.5:high — verdict: SHIP
- PRs: