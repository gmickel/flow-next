---
satisfies: [R7, R8, R9, R11, R20]
---
# fn-134-spec-id-collisions-widen-allocation.4 Skills: route on tracker.specIds, setup question, discoverability

## Description

Wire the skills: spec-creating skills route on `tracker.specIds`, `/flow-next:setup` asks the id-scheme question, and tracker-first becomes discoverable from where specs are actually born rather than only from the tracker-sync skill's own files.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-capture/workflow.md`
- `plugins/flow-next/skills/flow-next-plan/steps.md`
- `plugins/flow-next/skills/flow-next-work/phases.md`
- `plugins/flow-next/skills/flow-next-qa/references/bug-filing.md`
- `plugins/flow-next/skills/flow-next-interview/references/write-back.md`
- `plugins/flow-next/skills/flow-next-setup/workflow.md` (+ `SKILL.md` if it enumerates questions)
- `plugins/flow-next/codex/**` (regenerated, never hand-edited)

## Approach

**Routing gate.** Each spec-creating site reads `tracker.specIds` from the config snapshot the skill ALREADY holds (fn-110 root snapshot). No new `config get` call. When the value is `tracker` and the bridge is active: mint from a named issue if the request has one, otherwise create the tracker issue first via tracker-sync, then `spec create --tracker-first --tracker-identifier <key>`. Degrade silently to flow-first when the bridge is inactive or no transport is reachable; an explicit user override always wins.

Known mint call sites, confirmed by scouting: `plan/steps.md:291-297` (Route B, the brand-new-idea mint), `work/phases.md:110,117` (spec-less and markdown-file starts), `qa/references/bug-filing.md:127`, `interview/references/write-back.md:31`, and capture's touchpoint around `capture/workflow.md:826`. A site that genuinely inherits the gate from another skill may say so instead of repeating it, but it must say which.

**Setup question.** Follow the existing question pattern in `setup/workflow.md` (the GitHub Scout question around `:429-441` is the closest shape, gated on "include if config unset"). Gate on **tracker configured AND `tracker.specIds` unset**, default to `tracker`, and state the collision rationale rather than offering a bare preference. Add it to the Step 6d question list (~`:386`) and wire it into the Step 7 write-back. Never re-ask once the key is set to either value.

**Discoverability.** `plan` and `work` prose currently never mention tracker-first at all. Name it as the recommended team default, briefly, where a spec is minted - not a mechanical flag description.

**No runtime advisory.** A nag line at spec-creation time was considered and explicitly rejected during planning (see the spec's Setup section and withdrawn R10). Do not add one. Discoverability is handled by the setup question plus the notable-updates surface in tasks `.4` / `.5`.

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-plan/steps.md:285-300` - Route B mint call
- `plugins/flow-next/skills/flow-next-work/phases.md:105-120` - both spec-less mint paths
- `plugins/flow-next/skills/flow-next-setup/workflow.md:380-450` - question list and an existing config-gated question
- `plugins/flow-next/docs/tracker-sync.md:40-62` - the flow-first vs tracker-first flows the prose must match

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-capture/workflow.md:810-840`
- `plugins/flow-next/skills/flow-next-qa/references/bug-filing.md:120-135`

## Key context

**Skill prose must name the CLI surface that task `.2` actually shipped**, not this task file's description of it. Read the real `--help` and the landed config behavior before writing. This is a repeat offender in this repo and is now enforced by a CI gate.

**Bash blocks in skill prose re-declare their own variables.** Vars do not survive across tool calls, so every block that needs `$FLOWCTL` or a path declares it literally.

Cross-platform: canonical prose changes require `./scripts/sync-codex.sh` run TWICE with the mirror diff committed. Audit the sync script if any new tool-name or dispatch phrasing is introduced.


## Acceptance

- [ ] Every spec-creating skill (capture, plan, work, qa, interview) routes on `tracker.specIds` using the existing config snapshot and adds **no new config read**; each degrades to flow-first when the bridge is inactive or no transport is reachable (R7).
- [ ] A site that inherits the gate rather than implementing it says so explicitly and names the owning skill.
- [ ] With `tracker.specIds=tracker` and an active bridge, a fresh idea produces a `KEY-N-slug` id, having created the tracker issue first (R8).
- [ ] Network cost is stated **conditionally and accurately**, matching epic R8: no net new call when the matching `tracker.perEvent.*` touchpoint is already active; **one earlier remote write when it is off**, because those leaves default to `off` and a bridge-active repo can legitimately have every lifecycle event disabled. The blanket "no net cost" claim is not repeated anywhere (R8).
- [ ] `/flow-next:setup` asks the id-scheme question when a tracker is configured AND `tracker.specIds` is unset, states the collision rationale, **discloses that choosing `tracker` makes spec creation contact the tracker immediately** (creating an issue before the spec exists), and defaults to `tracker`. It never asks again once the key is set to either value, including an explicit `flow` (R9).
- [ ] `plan`, `work`, and `capture` prose name tracker-first as the recommended team default (R11).
- [ ] No runtime advisory or nag was added at any mint site (withdrawn R10).
- [ ] `./scripts/sync-codex.sh` run twice: idempotent, validation guards green, mirror diff committed.
- [ ] **Contract tests, not prose assertions** (R20): every one of the five mint sites routes correctly; issue-first linking happens; degradation to flow-first when no transport is reachable; explicit-override precedence beats the config; and a fake-adapter integration test proving create -> mint -> attach -> a later touchpoint fires **without** creating a second issue. Reuse the existing fake-transport routing harness.
- [ ] Setup raw-unset gating is tested: tracker configured + key absent asks; key set to either value does not.
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_flowctl_surface test_startup_bootstrap -q` plus the new routing and setup tests.

## Done summary
All five spec-creating sites (plan, work, capture, interview, qa) now route on `tracker.specIds`, reading it from the config snapshot each skill already holds so no new config read is added. Setup gained the id-scheme question. Tracker-first is named as the team default where specs are minted.

Implemented by grok-4.5 via the grok CLI bridge; reviewed in-host (opus-5). Verified: no runtime nag at any mint site (withdrawn R10), no new leaf `config get` at mint sites, no blanket zero-cost claim, and the setup question carries both gate conditions plus the immediate-remote-write disclosure.

REVIEW FINDING, the significant one. Grok's focused suite passed but the FULL suite caught three failures, and one was substantive: `test_measured_default_and_active_paths_shrink` refused because fn-134 had pushed the work skill's delegation-active reached path ABOVE the fn-130 baseline (102627 vs 100851). fn-130 shipped to shrink that path; this change was erasing the optimization and going negative.

Root cause: the ~25-line mint gate was inlined TWICE in phases.md (spec-file and spec-less starts) plus verbose comments and prose, adding +3654 chars (~913 tokens) to an always-loaded file in one of the most-run skills. Same class as the fn-122 round-5 duplication finding.

Fixed structurally rather than by relaxing the assertion, which would have been the weaken-the-gate anti-pattern: collapsed the duplicate to a pointer, tightened the block, then moved the gate entirely into `references/spec-id-mint.md`, read only when actually minting. Work on an EXISTING spec id never mints, so the gate was dead weight on the default path for the common case. Final: +372 chars (90% reduction from grok's version), delegation-active path back below the fn-130 baseline.

Reached-path evidence for both work and setup regenerated against the final bytes, with a `revisions` entry recording the growth, the cause, and the review correction. Baselines untouched; only candidate measurements revised.

Two other full-suite failures were mechanical: reached-path hashes needed regenerating after legitimate prose edits, and the routing-prose contract tests needed their work-site file set widened to include the new reference (identical assertions, corrected location).

Also made the allocation benchmark from task .1 load-aware: it measures wall-clock and the full suite runs 14 jobs in parallel, which reliably pushed a ~155ms measurement past any fixed bound. It now skips on a contended machine and still runs standalone. Correctness properties do not depend on timing and are covered by the other tests.
## Evidence
- Commits: 805a21e1
- Tests: python3 scripts/run_tests_parallel.py (files=132 ran=2389 failures=0 errors=0 skipped=4), cd plugins/flow-next/tests && python3 -m unittest test_spec_id_routing_prose -q (14 tests OK), ./scripts/sync-codex.sh twice - idempotent, guards green, reached-path: work default 50628 -> 51000 (+372, was +3654); delegation-active 100796 vs baseline 100851 (BELOW), verified: no runtime nag, no new leaf config get at mint sites, no blanket zero-cost claim, setup question has both gate conditions + immediate-write disclosure
- PRs: