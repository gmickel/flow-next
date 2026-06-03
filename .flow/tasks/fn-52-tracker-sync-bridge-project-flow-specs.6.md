---
satisfies: [R10, R16]
---

## Description

Wire the **optional, opt-in** tracker touchpoints into the seven lifecycle skills, plus the unlink lifecycle. Every touchpoint is gated on the bridge being **active** via the single activation predicate from .1 (active iff raw `tracker.enabled == true` OR raw `tracker.type ∈ {linear,github}`) — NOT "`get_default_config` returned a `tracker` block," and NOT a stray `type:null`. When inactive, the execution path is behaviorally unchanged — only config-gated optional prose runs (Boundaries). When active, each touchpoint reads its nested `perEvent` leaf (`tracker.perEvent.work.firstClaim`, `tracker.perEvent.work.done`, `tracker.perEvent.capture`, … — all default `off`) to decide pull/push/reconcile/comment/off. Touches the lifecycle skill dirs only — disjoint from the tracker-sync skill dir, so it parallelizes with .7.

**Size:** M (seven light, uniform touches + skill-side handle recognition)
**Files:** `skills/flow-next-capture/`, `flow-next-interview/`, `flow-next-plan/`, `flow-next-work/`, `flow-next-make-pr/`, `flow-next-resolve-pr/`, `flow-next-spec-completion-review/` (SKILL.md / phases.md), plus `flow-next-sync/` (plan-sync — for the id-check only). No edits to `flow-next-tracker-sync/`.

## Approach

Each touchpoint = an optional, clearly-marked opt-in step that calls the tracker-sync skill's push/pull/reconcile, gated on config:
- **capture / interview:** spec push/pull + merge after the read-back write.
- **plan:** no sub-issues by default (optional body checklist only).
- **work:** `phases.md:88` first claim → move issue In-Progress; `phases.md:98` (done) → post status comment + evidence (tests / PR).
- **make-pr:** `phases.md:132` PR URL → attach to the issue.
- **resolve-pr:** optional resolution comment.
- **spec-completion-review:** on SHIP → flip the issue Done/verified + post verdict / R-ID coverage — hook at the **caller** that sets `completion_review_status` (`flow-next-work/phases.md:205`), not inside the review skill.
- **Unlink lifecycle:** clears sync state via `flowctl sync clear` (.1) + posts a one-line "detached" comment; re-link re-seeds the base (.4).
- **Skill-side handle recognition (R16 — so `plan wor-17` / `work wor-17` resolve, not create):** the input grammars for `flow-next-plan`, `flow-next-work`, `flow-next-interview`, and `flow-next-sync` currently detect a Flow ID as `fn-*` only — so a tracker handle could fall through to "freeform idea → create a new spec." Update them to **route any candidate id arg through `flowctl show <arg> --json` (which now resolves tracker handles via .10) BEFORE treating it as idea text**, and remove the hard "must start with `fn-`" checks (incl. in `flow-next-sync`). A resolvable `wor-17` / `wor-17.1` is treated as the existing spec/task, never as a new idea.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-work/phases.md:88,98,205` — claim / done / completion-status anchors
- `plugins/flow-next/skills/flow-next-make-pr/phases.md:132` — PR-URL capture anchor
- `plugins/flow-next/skills/flow-next-capture/SKILL.md` — spec-write anchor (push/pull hook)
- the .1 sync helpers + the .4/.5 reconcile entry points

**Optional:**
- `plugins/flow-next/skills/flow-next-spec-completion-review/SKILL.md` — SHIP verdict surface

## Acceptance

- [ ] Each of capture/interview/plan/work/make-pr/resolve-pr/spec-completion-review gains an opt-in tracker touchpoint, gated via the .1 activation predicate, reading its nested `perEvent` leaf (`work.firstClaim` / `work.done` / `capture` / …); inactive path behaviorally unchanged (only config-gated optional prose runs) [R10]
- [ ] work: first claim moves the issue In-Progress; task done posts a status comment + evidence [R10]
- [ ] make-pr attaches the PR link; spec-completion-review SHIP flips the issue Done/verified + posts verdict / R-ID coverage [R10]
- [ ] Unlink clears sync state + posts a detached comment; re-link re-seeds the base [R10]
- [ ] Skill-side handle recognition: `/flow-next:plan wor-17`, `/flow-next:work wor-17.1`, `/flow-next:interview wor-17`, `/flow-next:sync wor-17` resolve the existing spec/task (routed through `flowctl show`), NOT treated as a new idea; the `fn-`-only checks are removed [R16]

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
