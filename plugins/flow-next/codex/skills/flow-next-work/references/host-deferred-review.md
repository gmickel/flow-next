# Host-deferred review contract (gated reference)

> **Loaded only on the wave route's single-worker path when THIS task's resolved review mode is `host`** (worker flag
> `REVIEW_MODE: host-deferred`, phases.md 3c). Every other backend (`none`, `rp`,
> `codex`, `copilot`, `cursor`, `claude`) keeps the worker-owned review dispatch + worker-owned
> `flowctl done` unchanged and never reads this file.

Contents:

- [Worker/conductor contract](#workerconductor-contract) — phases.md 3c: what changes when review mode is `host`
- [3d.0 gate](#3d0-gate) — phases.md 3d.0: the mandatory conductor-run gate before `done`

## Worker/conductor contract

**Host review routes OUTSIDE the worker — and gates BEFORE `done`.** Verdict independence: the agent that wrote the code never dispatches or issues its own review verdict, so the fresh reviewer subagent the `host` backend requires is dispatched by the conductor, never the worker. When the resolved review mode is `host`, pass `REVIEW_MODE: host-deferred` to the worker, and the completion contract changes:

1. The worker skips its in-worker review dispatch in Phase 4 (never self-certifies SHIP) **and defers Phase 5's `flowctl done`**: it implements, commits, writes its summary + evidence files to the handover paths, and returns WITHOUT calling `flowctl done` (the task stays `in_progress`).
2. The conductor then runs `/flow-next:impl-review <task-id> --review=host` itself — this is the mandatory gate.
3. On `SHIP`: the conductor runs `flowctl done <task-id> --summary-file <worker summary> --evidence-json <worker evidence>` (append the review receipt path/model to the evidence). On terminal `NEEDS_WORK`: escalate; impl-review already exhausted its bounded fix loop. Never re-invoke it or call `done`.
4. Mirror this exact contract on the Codex mirror path (`$flow-next-work` / `spawn_agent` worker): host-deferred defers `done` there too.

## 3d.0 gate

phases.md **3d.0 — runs FIRST on the single-worker path when this task's REVIEW_MODE was `host-deferred`.**

A host-deferred worker returns with the task still `in_progress` BY DESIGN — that is the contract, not a failure. Before any failure classification:

1. Resolve `BASE_COMMIT` from the conductor's recorded task base; if unavailable, read `base_commit` from that task's handover evidence or `$FLOWCTL show` evidence. Never read a shared `.flow/tmp/base_commit` or run with an empty base; a missing base is `BLOCKED`. Rolling review uses its own normalized integrated-base record in [rolling-scheduler.md](rolling-scheduler.md#3d-per-return-integrate-review-complete), not this gate.
2. Confirm the worker's handover: commits present since `$BASE_COMMIT`, summary + evidence files at the handover paths it reported. (Missing handover WITH `in_progress` status = genuine worker failure — fall through to the failure path in phases.md 3d.)
3. Run the mandatory gate: `$flow-next-impl-review <task-id> --base $BASE_COMMIT --review=host`.
4. On `SHIP`: UPDATE the evidence JSON before completing — append the review receipt path + reviewer model, AND when impl-review's internal fix loop committed changes, add those commits and any test commands run during fixes (the worker's pre-review evidence alone omits exactly the changes that earned the SHIP). Before `done`, read [worker.md Phase 4.5](../../../agents/worker.md#phase-45-auto-capture-on-successful-fix-after-needs_work-ship) and execute its memory auto-capture as conductor using the recorded review rounds and fix commits. Check `memory.enabled`; disabled skips and capture failures warn without blocking completion. Then run `$FLOWCTL done <task-id> --summary-file <worker summary> --evidence-json <updated evidence>` and re-run `$FLOWCTL show` — status is now `done`; continue to 3d.1/plan-sync as normal.
5. On terminal `NEEDS_WORK` or `MAJOR_RETHINK`: escalate exactly like the failure path in phases.md 3d (NEEDS_HUMAN under autonomy; surface and stop interactively). The skill already owns the bounded fix loop; do not re-invoke it.

Review-counter reset and `--force` review dispatch/increment are human-only
recovery tools; on escalation, surface the terminal rather than using either.

Only after this gate does phases.md 3d's standard not-`done` rule apply to host-deferred tasks.
