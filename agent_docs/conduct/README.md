# Conduct checklists

A conduct checklist is a per-skill regression harness for **prose** changes. Each page lists 4–6 falsifiable, observable behaviors a session correctly running that skill exhibits — anchored on the skill's own terminal outputs (verdict lines, receipts, files written under `.flow/`, flowctl state transitions, refusal conditions) so a maintainer can check each item true or false from a transcript in seconds.

Two moments to use one:

- **Reviewing a PR that touches a skill's prose** — load that skill's checklist and use its items as the review criteria.
- **After editing a skill's prose** — dogfood the skill once and mark every item pass/fail before handing off.

These pages are maintainer documentation. They are never loaded at runtime by an agent executing the skill, and no `SKILL.md` or skill reference file points at them. When a skill's contract genuinely changes, update its checklist in the same change.

## Checklists

**Pre-build**

- [`strategy.md`](strategy.md) — `/flow-next:strategy`, the repo-root `STRATEGY.md` anchor
- [`prospect.md`](prospect.md) — `/flow-next:prospect`, plural ranked ideas
- [`chart.md`](chart.md) — `/flow-next:chart`, decision map and briefing package
- [`capture.md`](capture.md) — `/flow-next:capture`, conversation to source-tagged spec
- [`interview.md`](interview.md) — `/flow-next:interview`, question rounds and scoped write-back
- [`guide.md`](guide.md) — `/flow-next:guide`, read-only workflow router

**Plan and review**

- [`plan.md`](plan.md) — `/flow-next:plan`, spec plus right-sized tasks
- [`plan-review.md`](plan-review.md) — `/flow-next:plan-review`, backend spec review
- [`impl-review.md`](impl-review.md) — `/flow-next:impl-review`, backend implementation review
- [`spec-completion-review.md`](spec-completion-review.md) — `/flow-next:spec-completion-review`, combined-implementation verification
- [`quality-auditor.md`](quality-auditor.md) — `quality-auditor`, single-axis in-host quality audit
- [`visual.md`](visual.md) — `/flow-next:visual`, compact markdown digest of a spec, task, diff, or topic
- [`prose.md`](prose.md) — `/flow-next:prose`, prose-contract application to a substantial reply

**Build**

- [`work.md`](work.md) — `/flow-next:work`, spec execution with fresh-context workers
- [`work-rolling.md`](work-rolling.md) — `/flow-next:work-rolling`, experimental rolling-frontier work variant (thin delta over work; canonical checklist applies too)
- [`sync.md`](sync.md) — `/flow-next:sync`, manual plan-sync after drift
- [`qa.md`](qa.md) — `/flow-next:qa`, live-app QA and ship verdict
- [`drive.md`](drive.md) — `flow-next-drive`, surface-aware UI automation

**Ship**

- [`make-pr.md`](make-pr.md) — `/flow-next:make-pr`, cognitive-aid PR body
- [`resolve-pr.md`](resolve-pr.md) — `/flow-next:resolve-pr`, PR feedback resolution
- [`land.md`](land.md) — `/flow-next:land`, cadence-tick ship loop
- [`pilot.md`](pilot.md) — `/flow-next:pilot`, single-tick build-loop conductor

**Repo and state**

- [`flow-next.md`](flow-next.md) — flow-next task management, quick `.flow/` operations
- [`deps.md`](deps.md) — `flow-next-deps`, dependency graph and execution phases
- [`map.md`](map.md) — `/flow-next:map`, semantic feature index
- [`prime.md`](prime.md) — `/flow-next:prime`, agent-readiness assessment
- [`audit.md`](audit.md) — `/flow-next:audit`, memory entry audit
- [`memory-migrate.md`](memory-migrate.md) — `/flow-next:memory-migrate`, flat-to-categorized memory lift
- [`tracker-sync.md`](tracker-sync.md) — `/flow-next:tracker-sync`, spec-to-tracker projection
- [`setup.md`](setup.md) — `/flow-next:setup`, platform detection and install
- [`ralph-init.md`](ralph-init.md) — `/flow-next:ralph-init`, repo-local Ralph harness scaffold
- [`export-context.md`](export-context.md) — `flow-next-export-context`, review context export

## Skills without a checklist

- `flow-next-worktree-kit` — wrapper; all behavior lives in `scripts/worktree.sh`, not in prose.
