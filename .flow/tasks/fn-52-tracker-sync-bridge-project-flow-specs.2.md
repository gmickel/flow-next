---
satisfies: [R2, R3, R16]
---

## Description

Scaffold the new `flow-next-tracker-sync` skill: the discovery ceremony, the spec↔issue grain, the identity/naming alias, and the push/pull/reconcile **orchestration skeleton** + **transport-adapter interface contract** that .3/.7 implement (transports) and .4/.5 implement (reconcile). This is the spine; later tasks add files, not rewrite this.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-tracker-sync/SKILL.md`, `steps.md`, `references/` (scaffold dir); NEW command `plugins/flow-next/commands/flow-next/tracker-sync.md`. No flowctl.py edits — calls .1 helpers AND the .10 tracker-first create CLI (`flowctl spec create --tracker-first --tracker-identifier …`); depends on .10 for id assignment + resolution.

## Approach

- Model SKILL.md + steps.md on an existing lifecycle skill (`skills/flow-next-capture/SKILL.md`). Keep interactive conflict-resolution **inline** (subagents can't call `AskUserQuestion`). Use `AskUserQuestion` canonically so `sync-codex.sh` rewrites apply (.9).
- **Discovery ceremony (R2):** probe four signals — Linear MCP registered, `LINEAR_API_KEY`, `gh auth status`, `*.atlassian.net`. Surface present AND absent; ASK; **only on confirmation** write `tracker.enabled = true` + `tracker.type` + `tracker.provenance` (who/what confirmed) + the chosen `perEvent` opt-ins via `flowctl config set`. Resolution model = `cmd_review_backend` env>config>ASK (`flowctl.py:4859`). Negative path: no signal → nothing written → `enabled` stays `false` (never assume).
- **Flexible entry (R2):** author-in-flow-then-push AND link-existing-issue ("grab issue X and spec it") both attach sync state on link. No fixed starting point.
- **Grain (R3):** one spec ↔ one issue; tasks stay flow-local; optional checklist-in-body render — decide + mark in-scope-now vs deferred.
- **Identity/naming (R16) — apply the hybrid via fn-52.10's id layer:** the link / create ceremony assigns the canonical id through .10's generator — **tracker-first link → canonical spec id `wor-17-slug`, canonical tasks `wor-17-slug.M`** (the bare forms `wor-17` / `wor-17.M` are aliases, resolved by .10); branch follows the canonical id; **flow-first → keep `fn-NN-slug`**, store the tracker key in the single `tracker.identifier` field (R4, display form e.g. `WOR-17`, no separate `tracker.alias`) as a resolvable alias, and write the `flow:<id>` label / `[<id>]` title-prefix back-reference into the issue. **Never rename an existing spec.** Resolution itself (`work wor-17`, `show wor-17`, …) is provided by .10's widened resolver; the scaffold just calls flowctl and relies on it. Surface `identifier` in sync listings.
- **Orchestration skeleton + adapter interface:** define transport-blind reconcile entry points — `fetchIssue / writeIssue / listComments / postComment / readStatus / setStatus` — AND the **normalized payload structs** they exchange (so transport-blind reconcile is actually testable): `issue {tracker, type, id, identifier, title, body, status:{raw,normalized}, priority, labels[], url, updatedAt}`, `comment {id, author, body, createdAt, marker}`, `status {raw, normalized}`. Each adapter (.3/.7) maps its wire shape to/from these; .4/.5 only ever see the normalized form. Link & unlink ceremony stubs (first-link base-seeding handled in .4; unlink wipes state via .1 `sync clear` + posts a detached comment).
- **Command wrapper:** add `commands/flow-next/tracker-sync.md` mirroring `commands/flow-next/sync.md` (frontmatter `name: flow-next:tracker-sync` → invokes the `flow-next-tracker-sync` skill). Keep `/flow-next:sync` (= plan-sync) untouched; the two are documented side-by-side (doc note lands in .8).

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-capture/SKILL.md` — scaffold shape + inline `AskUserQuestion` (subagent caveat at ~line 26)
- `plugins/flow-next/skills/flow-next-drive/SKILL.md` — ladder/structure to mirror in .3
- `plugins/flow-next/scripts/flowctl.py:4859` — `cmd_review_backend` (env>config>ASK)

**Optional:**
- `.flow/specs/fn-52-tracker-sync-bridge-project-flow-specs.md` — the spec (R2/R3/R16 source text)
- the .1 sync helpers (config + set-tracker-id + clear)

## Acceptance

- [ ] Discovery ceremony detects all 4 signals, surfaces present + absent, asks via `AskUserQuestion`, writes config only on confirmation with provenance; no-signal → no config written (never assume) [R2]
- [ ] Flexible entry: author-in-flow-then-push AND link-existing-issue both attach sync state on link [R2]
- [ ] Grain enforced: one spec ↔ one issue; tasks stay flow-local; checklist-in-body optional + explicitly scoped (now/deferred) [R3]
- [ ] Link/create ceremony assigns the hybrid id via fn-52.10 (tracker-first → canonical `wor-17-slug` + tasks `wor-17-slug.M`, bare `wor-17`/`wor-17.M` as aliases; flow-first → `fn-NN` + resolvable `tracker.identifier` display alias `WOR-17`), writes the issue back-reference, surfaces `identifier` in listings, and NEVER renames an existing spec [R16]
- [ ] Orchestration skeleton + transport-blind adapter interface contract defined, INCLUDING the normalized `issue`/`comment`/`status` structs, so .3/.7 plug transports and .4/.5 reconcile against the normalized form only
- [ ] NEW `/flow-next:tracker-sync` command wraps the skill; `/flow-next:sync` (plan-sync) untouched
- [ ] SKILL.md uses `AskUserQuestion` canonically (Codex-mirror-ready)

## Done summary
Scaffolded the `flow-next-tracker-sync` skill spine: discovery ceremony (R2: detect/surface/ask/never-assume + provenance + no-signal-no-write), flexible flow-first/tracker-first entry (R2), one-spec-to-one-issue grain with tasks-flow-local + deferred checklist render (R3), hybrid tracker-key identity via fn-52.10's id layer with never-rename (R16), and a transport-blind push/pull/reconcile orchestration skeleton plus a normalized issue/comment/status adapter-interface contract that fn-52.3/.7 (transports) and fn-52.4/.5 (reconcile) plug into. Added the new `/flow-next:tracker-sync` command (distinct from plan-sync's `/flow-next:sync`). No flowctl.py edits — the skill calls the .1 sync helpers and the .10 tracker-first create/resolver. Canonical files are Claude-native (AskUserQuestion, Task); Codex mirror is regenerated in fn-52.9.
## Evidence
- Commits: b423c7e3865aec662acbbd0f8d98c0c3423f9b8e
- Tests: plugins/flow-next/scripts/ci_test.sh (58 passed / 0 failed), flowctl validate --spec fn-52-tracker-sync-bridge-project-flow-specs (valid), impl-review rp backend: SHIP (0 findings, first pass)
- PRs: