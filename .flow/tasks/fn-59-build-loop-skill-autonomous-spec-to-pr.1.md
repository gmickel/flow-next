---
satisfies: [R1, R2, R3, R5, R6, R7, R8, R9]
---

## Description

The new `flow-next-pilot` skill — a single-tick build-loop conductor for host drivers (`/loop`, `/goal`), plus its slash command and sync-codex registration. The spec's "### Resolved at planning" section IS the contract — read it first; every bullet there is binding.

**Size:** M/L
**Files:** `plugins/flow-next/skills/flow-next-pilot/SKILL.md` + `workflow.md` (new), `plugins/flow-next/commands/flow-next/pilot.md` (new — mirror qa.md's 13-line shape), `scripts/sync-codex.sh` (`generate_openai_yaml` call + `REQUIRED_OPENAI_YAML_SKILLS` entry)

## Approach

Tick phases (one invocation = one tick; report LAST, nothing after the verdict line):
- **Phase 0 guards:** hard-error under `FLOW_RALPH`/`REVIEW_RECEIPT_PATH` (alternative drivers, never nested); dirty non-`.flow/` tree at tick start → `NEEDS_HUMAN`.
- **SELECT (two-pass):** `flowctl specs --json` (minimal listing: id/status/ready/tasks/done) → per candidate `show <id> --json` for `depends_on_epics` (satisfied = dep `status==done`), review statuses, `branch_name`, task assignees. Skip: not ready, deps unsatisfied, `in_progress` by another actor, strikes≥2 (unless re-blessed → clear entry). PR state is NOT checked at SELECT — it lives exclusively in the all-done classification branch (below). `--dry-run` stops here with the classification report.
- **Classify:** 0 tasks → plan; `plan_review_status != ship` → plan-review (skip when backend `none` OR `ASK`); ready/in_progress (own/unassigned) tasks → work; **all done + `completion_review_status != ship` (backend configured) → work** (its Phase-3g gate runs completion review; make-pr must never fire before completion ship); all done + completion ship-or-ungated → PR probe (the ONLY gh touch, `flow-next-make-pr/workflow.md:218-242` OPEN-filter gotcha): open PR → skip to next candidate; CLOSED-not-MERGED → `NEEDS_HUMAN`; gh missing/unauth/API-failure → `NEEDS_HUMAN`; no PR → make-pr.
- **Branch resolution matrix (pilot owns it):** branch exists + work → checkout `branch_name`, dispatch `--branch=current mode:autonomous`; branch absent + first work → dispatch `--branch=new`; make-pr → require + checkout existing `branch_name` (absent → NEEDS_HUMAN).
- **DISPATCH** the one sub-skill with `mode:autonomous` + passthroughs (`--review`, plan's `--research`/`--depth`). Stage plan-review dispatches **`/flow-next:plan-review <spec> --review=<backend>` explicitly** — that skill sets `plan_review_status` ITSELF (its workflow Phase 4); pilot only re-reads the field to verify. Completion review is the opposite convention: reached through work, whose 3g gate invokes spec-completion-review and the CALLER sets `completion_review_status=ship` (`flow-next-work/phases.md:391-431`). Do not conflate the two setter conventions.
- **VERIFY + evidence echo:** the `/goal` validator is transcript-blind — echo the checked evidence into output and judge advancement on it, never on sub-skill narration. Per stage: plan → tasks exist; plan-review → `plan_review_status==ship`; work → task/spec status transitions (+ completion ship when gated); **make-pr → gh-confirmed OPEN PR URL (no flowctl transition exists for it — a successful PR tick must never strike)**.
- **REPORT (terminal line):** `PILOT_VERDICT=<ADVANCED|NO_WORK|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason="<one line>"`.
- **Strikes ledger:** `$(git rev-parse --git-common-dir)/flow-next/pilot-strikes.json` (under `.git` — worktree-shared, never committable by `git add -A`), schema `{<spec-id>: {count, stage, reason, ts}}`; healthy-no-advance → strike (1/2 = stays ready, 2/2 = `flowctl spec unready` + reason persisted); cleared on ADVANCED; ready-again + count≥2 = human re-bless → clear. Crash/dirty-tree → `NEEDS_HUMAN`, no cleanup.
- Cross-platform: canonical `AskUserQuestion` never used in the tick path (autonomous by nature); `Task` only if dispatch needs it; keep prose sync-codex-friendly (memory: R2-block placement, complete-sentence anchors).

## Investigation targets

**Required:**
- `.flow/specs/fn-59-build-loop-skill-autonomous-spec-to-pr.md` §Resolved at planning (the contract)
- `agent_docs/adding-skills.md` — 9-step checklist; qa's footprint (commit 1affea6) is the template
- `plugins/flow-next/skills/flow-next-work/phases.md:391-431` — skill-invokes-skill + caller-sets-status convention
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:218-242` — OPEN-filter gh probe to reuse (+ extend for CLOSED≠MERGED)
- `plugins/flow-next/commands/flow-next/qa.md` — command wrapper shape

**Optional:**
- `plugins/flow-next/skills/flow-next-capture/SKILL.md:31-44` — arg-token parse shape (pilot parses its own flags the same way)
- `.flow/review-deferred/` sink precedent for skill-owned scratch files

## Acceptance

- [ ] Bare tick selects per the full predicate (ready, deps done, not other-actor-claimed, strikes<2 — PR state checked only at the all-done branch) in stable ID order; `--spec` scope-lock + `--dry-run` work
- [ ] Stage classification matches the spec table incl. backend `none`/`ASK` gate-skip AND the all-done-but-completion-unshipped → work route (make-pr never fires before completion ship when a backend is configured); stage set is exactly {plan, plan-review, work, make-pr}
- [ ] plan-review stage dispatches `/flow-next:plan-review` explicitly and verifies the skill-set `plan_review_status`; gh-probe failure at the all-done branch → NEEDS_HUMAN
- [ ] Branch matrix: exists+work → checkout + `--branch=current`; absent+first-work → `--branch=new`; make-pr requires existing branch (absent → NEEDS_HUMAN)
- [ ] Evidence echoed before the verdict; `PILOT_VERDICT=...` is the terminal line, exact grammar, nothing after
- [ ] Strikes ledger lifecycle per spec (record/clear/re-bless-reset, reason persisted); 2nd strike runs `spec unready`; a successful make-pr tick (gh-confirmed PR URL) counts ADVANCED, never a strike
- [ ] `FLOW_RALPH` invocation hard-errors; dirty tree → NEEDS_HUMAN with state untouched
- [ ] Command wrapper + sync-codex registration done; `./scripts/sync-codex.sh` run locally as VERIFICATION ONLY (validators green) — the regenerated `codex/**` tree is reverted/not committed here; .3 owns the committed mirror

## Done summary
Built the flow-next-pilot skill (SKILL.md + workflow.md): a single-tick autonomous build-loop conductor for /loop and /goal drivers that selects one ready spec, classifies its stage, dispatches one sub-skill with mode:autonomous, verifies advancement from flowctl state (gh OPEN-PR URL for make-pr), manages the .git-common-dir strikes ledger, and ends with the terminal PILOT_VERDICT line. Added the slash-command wrapper and sync-codex.sh registration; sync run as verification only with the regenerated mirror reverted (fn-59.3 owns the committed mirror). RP impl-review SHIP after 2 fix rounds.
## Evidence
- Commits: 21de8473cd6e6a07733b78dd72c4b6f2d885a1b9, 9247c0c, 90b3287, 1a1198289f64b1b936768f718422590bd95992e4
- Tests: ./scripts/sync-codex.sh (all validators green, 20 required skills have openai.yaml; regenerated codex/** mirror reverted per task acceptance — fn-59.3 owns the committed mirror), bash -n scripts/sync-codex.sh, rp impl-review SHIP after 2 NEEDS_WORK fix rounds (base 3478ec0)
- PRs: