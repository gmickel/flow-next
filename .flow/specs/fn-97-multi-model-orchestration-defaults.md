# fn-97 Multi-model orchestration defaults: delegate model steering, setup scaffold, docs

## Goal & Context
<!-- scope: business -->

A controlled multi-model pipeline eval (2026-07-14, cronlite benchmark: 39-check hidden oracle suite, planted-bug review eval with 3 reps per arm at matched reasoning efforts, dual-judge blind plan scoring; full data in the maintainer's session scratchpad `mmx/RESULTS.md` and memory note `multimodel-pipeline-eval-2026-07-14`) validated the orchestration shape flow-next already supports and exposed four small gaps. Findings that drive this spec:

- Work stage saturates on correctness when the spec is frontier-authored: all 11 workers scored 39/39. Terra-medium fastest (144s); effort ladders terra 144/192/326s and luna 164/397/535s at identical hidden-suite correctness. Quality differs elsewhere: edge-case assertion coverage in worker-written tests spans 27-61 (GPT tiers) vs 78-155 (Claude/Grok/Composer), by family not effort; every worker kept the plan's brute-force oracle test, which is why correctness tied. Terra-medium stays the delegate default (correctness + speed + tightest code); the assertion-coverage spread is documented as an observation, not a routing rule (single task).
- Review is the discriminating stage (n=3 per arm, matched effort, objective recall vs 4 known bugs): sol-high 12/12 recall, 0 FP, 103s mean (fastest); sol-xhigh and luna-xhigh 12/12; luna-high 12/12 with the fleet's only false positive; Fable at xhigh (session effort, inherited by native subagents) 11/12 with uniquely correct severity tiering; grok-4.5-high 9/12 - missed the subtle latent bug in all 3 runs. Build-tier reviewers (single runs): sonnet-5 missed a planted bug; composer-2.5 gave a false all-clear.
- Plan: two cross-family blind judges, identical ranking - Fable 38/40 avg > sol-xhigh 32.5 > sol-high 31. Gap = test-plan concreteness + scope discipline; effort did not close it.
- Reliability: raw `codex exec` / `cursor-agent` calls fail SILENTLY outside trusted git dirs (fast exit, empty output) - fatal in autonomous loops. A thin sonnet-5 wrapper subagent self-healed both failures at identical output quality.

Goal: make the proven defaults reachable without hand-rolled bridge commands, and harden the documented recipes. Everything here is small direct edits + docs; one task.

## Architecture & Data Models
<!-- scope: technical -->

Four pieces, no new subsystems:

1. **Delegate model steering (flowctl config + work skill).** AMENDED during implementation (fn-97.1): the steering keys ALREADY exist from fn-55 as `work.delegateModel` / `work.delegateEffort` (camelCase, the flow config convention), are already read by the codex-delegation bridge, and are ALWAYS passed explicitly as `-m <model>` / `-c model_reasoning_effort=<effort>` (the bridge runs `--ignore-user-config`, so there is deliberately NO defer-to-`~/.codex/config.toml` path - the earlier snake_case/omit-when-unset wording described keys that never shipped anywhere). The actual delta: flip the default `work.delegateModel` from `gpt-5.6-sol` to `gpt-5.6-terra` (eval-motivated; `work.delegateEffort` stays `medium`) and document the steering keys in flowctl.md + orchestration.md + the usage.md template.
2. **Setup scaffold question.** `/flow-next:setup` gains one optional question, asked only when at least one bridge CLI is detected on PATH (`codex`, `cursor-agent`, `grok`): "Scaffold a recommended multi-model pipeline?" Yes writes a routing block into the project instruction file's model-routing section (frontier plan + review, terra-medium delegated work, cross-family `review.backend codex`, wrapper pattern pointer for autonomous loops) and offers to set `flowctl config set review.backend codex`. No = no change. Customization is scaffold-then-edit: the written block is explicitly "yours now - edit freely", and AskUserQuestion's built-in Other option accepts free-text steering; no in-setup table editor (deliberate scope cut, see Decision Context).
3. **Codex mirror worker pin - OPT-IN (amended post-SHIP, maintainer review).** `sync-codex.sh` gains `CODEX_MODEL_WORKER` / `CODEX_REASONING_EFFORT_WORKER` sync-time knobs; DEFAULT IS UNSET and the worker keeps `inherit` on both platforms - the session model rules, and flow-next never hardcodes a model opinion into generated config (routing opinions live in the prompted layer / scaffold prose). The terra-medium recommendation is documented, not imposed. Rationale: Codex `spawn_agent` has no per-spawn model choice, so role config is the only steering mechanism there - which argues for user-set config, not a shipped pin; a hard pin would silently downgrade a Codex-driver user running sol as their session. Keep the map_model FAST/INTELLIGENT tier mapping consistent.
4. **Docs hardening + defaults example.** (a) usage.md template bridge recipes: `--skip-git-repo-check` always on `codex exec` lines; cursor-agent "run inside a git repo" warning (edits already made locally on main, fold into this task's commit). (b) orchestration.md: add a "proven default pipeline" host-relative table (plan on session frontier / plan-review cross-family frontier / work terra-medium / impl-review: sol-high cross-family first pass + session-model final gate for severity calibration; luna-xhigh documented as the equal-recall-slower alternative; grok-4.5 documented as classic-bug quick pass ONLY - it consistently missed the subtle latent bug at n=3 and must never be the gate), a wrapper-pattern subsection (thin sonnet wrapper for unattended loops; wrapper MUST run the bridge in the foreground; self-heal license limited to environment/flags, never judgment), and a review-prompt note for the RAW-BRIDGE recipe examples ONLY (ad-hoc codex exec reviews consumed directly by a human, outside the packaged review subsystem): include P0-P3 severity so edge findings do not flip ship gates, and optionally request minimal fix + blast radius when no fix loop follows - control runs showed the artifact is prompt-shaped. The PACKAGED impl-review prompt is explicitly NOT changed: its find-vs-fix split (reviewer returns findings; the internal fix loop investigates and fixes, with validator + iteration caps) is by design.

## API Contracts
<!-- scope: technical -->

- `flowctl config set work.delegateModel <model-id>` / `flowctl config set work.delegateEffort <none|low|medium|high|xhigh>` - pre-existing fn-55 string config keys (camelCase per flow config convention; amended from this spec's earlier snake_case spelling, which never shipped); `flowctl config get` round-trips them and returns the defaults (`gpt-5.6-terra` / `medium`) when unset.
- Delegation bridge command shape (unchanged from fn-55): `-m` and `-c model_reasoning_effort=` are ALWAYS passed explicitly from the resolved config values - never omitted, never deferred to the user's codex config (`--ignore-user-config` isolation).
- Setup question is additive and optional; non-interactive/autonomous setup runs skip it (no prompt, no scaffold).

## Edge Cases & Constraints
<!-- scope: technical -->

- Model ids are volatile vendor strings: never hardcode validation lists; defaults live in ONE place (skill reference doc) so a vendor rename is a one-line fix.
- `work.delegate` remains the activation switch; the new keys are inert unless delegation is active.
- Codex mirror worker pin must not leak into the Claude-side agents (Claude worker stays `inherit`).
- usage.md is a setup-managed copy: canonical edit in `plugins/flow-next/skills/flow-next-setup/templates/usage.md`, mirror regenerated via `sync-codex.sh`, existing projects pick it up on next `/flow-next:setup` re-run.
- Wrapper pattern is documentation only in this spec (no new agent definition); the foreground-bridge rule is the critical sentence.
- Single-subscription reality (maintainer field note, 2026-07-15): most orgs run ONE harness subscription, not several. All docs framing must present multi-model routing as optional garnish; the setup question already degrades naturally (fires only for detected CLIs), and the defaults table must read sensibly when every row resolves to the same family.

## Acceptance Criteria
<!-- scope: both -->

- R1 (amended fn-97.1 to the as-shipped fn-55 contract): `work.delegateModel` + `work.delegateEffort` config keys exist, are read by the work skill's codex delegation bridge, and always produce explicit `-m`/`-c model_reasoning_effort=` flags; the shipped default flips to `gpt-5.6-terra`/`medium` (eval-motivated), and a user-set value passes through unchanged.
- R2: `/flow-next:setup` asks the multi-model scaffold question only when a bridge CLI is detected, and Yes writes the routing block + offers `review.backend codex`; customization is scaffold-then-edit (no in-setup table editor); the question never fires in autonomous/non-interactive runs.
- R3: `sync-codex.sh` supports opt-in `CODEX_MODEL_WORKER` / `CODEX_REASONING_EFFORT_WORKER`; default regeneration leaves the worker at `inherit` (both platforms); the terra-medium recommendation is documented in platforms.md/orchestration.md, never emitted by default.
- R4: usage.md template bridge recipes carry `--skip-git-repo-check` on all codex exec lines and the cursor-agent git-repo warning; codex mirror regenerated.
- R5: orchestration.md contains the host-relative default-pipeline table, the wrapper-pattern subsection with the foreground rule, and the severity-tier review-verdict note.
- R6: CHANGELOG `## Unreleased` entry (repo). No version bump (batched releases).
- R7: Docs downstreams updated in the same workstream per project practice (docs site orchestration page + changelog entry staged).

## Boundaries
<!-- scope: business -->

- NOT building a new wrapper agent type, review backend, or scoring harness - docs + config plumbing only.
- NOT changing default behavior for users who set nothing (all additions opt-in or inert-by-default) except the recipe hardening flags, which are strictly safer, and the R1 delegate-default flip (`gpt-5.6-sol` -> `gpt-5.6-terra`, only visible when delegation is actively enabled) - which is the point of R1 (amended fn-97.1).
- NOT encoding benchmark numbers as normative claims in docs - the eval is one task; docs may cite it as motivation, not as a guarantee.
- Vendor model names in defaults are starting opinions, same contract as the existing model-routing scaffold.

## Decision Context
<!-- scope: both -->

- Terra-medium as delegate default: +0 quality / -37% wall-clock vs sol-high on frontier-authored specs; effort above medium is pure overhead (terra 144/192/326s, luna 164/397/535s - all 39/39). Luna-medium is the documented budget alternative (39/39 at 164s, tightest code, lowest API-cost tier); alternative not default because agentic wall-clock tracks tool-loop iteration count, which tracks capability tier (terra-med 4 round-trips vs luna-med 6 at fewer tokens).
- Review defaults (n=3 matched-effort data): cross-family first pass = sol-high (12/12 recall, 0 FP, fastest at 103s mean); session-model final gate for unprompted judgment: under a terse prompt Fable alone volunteered fixes, blast radius and severity tiering; control runs showed sol/luna produce the same artifact when the prompt demands it. Artifact quality is prompt-shaped (documented for raw-bridge recipes via R5; packaged review prompt unchanged - its find-vs-fix split is by design), while recall (grok 0/3 on the subtle bug) and unprompted judgment remain model-shaped; luna-xhigh = equal recall at 2.5x time. grok-4.5: classic-bug quick pass only, never the gate (0/3 on the subtle latent bug). sonnet-5 and composer-2.5 are excluded from review roles (missed planted bug / false all-clear).
- Measurement lesson (applies to future evals, e.g. fn-84-style work): single-run review comparisons and single-judge text scores are noise - a single run had grok level with sol, and a single text-judge ranked luna above sol; both reversed under 3 reps + objective recall. Eval guidance: >=3 reps, objective recall vs known ground truth, dual cross-family judges for text quality.
- The latent-bug twist: the year-overflow ValueError behavior that reviewers flagged was actually licensed by the plan-review amendment - reviewers flag spec-gray edges as bugs, which is why severity tiers + spec-grounded verdicts are required (packaged review rubric has them; raw-bridge recipes get them via R5).
- Wrapper pattern scoped to autonomous loops: interactive hosts see stderr and self-heal anyway; the silent-failure class only kills unattended runs.
- Plan-stage data (two cross-family blind judges, identical ranking: Fable 38 avg > sol-xhigh 32.5 > sol-high 31) supports "plan on the session frontier" rather than always bridging plan out; effort inflation does not close plan-quality gaps.
- Host-independence of the defaults (maintainer note, 2026-07-15): bridges run both directions, so the recommended roles are model-per-role, not host-relative - Fable can plan from a Codex host via `claude -p`, sol can review from a Claude host via `codex exec`. Packaged support today: review (`review.backend`) and work (this spec's delegate keys) are host-independent; PLAN remains session-native by design (no packaged cross-family plan rung; ad-hoc bridging works but `claude -p` on Fable can hit CLI credit limits - observed 2026-07-14). Docs should present the defaults as roles with a per-host reach column, not as separate per-host tables.
- R2 Customize amendment (completion-review round 1, 2026-07-15): the originally specced in-setup "Customize = present the table for editing" route was cut in favor of scaffold-then-edit - an interactive table editor inside setup is over-engineering for a block whose header already says "edit freely; re-run setup to regenerate", and AskUserQuestion always carries a free-text Other option. Contract amended rather than implemented; reviewer offered both routes.
- R3 amended opt-in (post-SHIP maintainer review, 2026-07-15): the initially shipped hard pin of the Codex-mirror worker to terra-medium silently overrode the Codex user's session-model choice out of the box - asymmetric with the Claude-side `inherit` worker and against the prompted-layer routing philosophy. Amended to unset-by-default env knobs + documented recommendation.
