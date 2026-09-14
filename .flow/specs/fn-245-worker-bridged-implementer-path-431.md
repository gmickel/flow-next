# Worker runs the bridge itself when the implementer tier is reached by CLI (#431 follow-up)

## Conversation Evidence

Source: the user's request in this session, grounded in GitHub issue gmickel/flow-next#431 (reporter: DanielKillenberger), PR #436 (merged 2026-09-14, closed #431), and a live run observed by the reporter on 2026-09-14.

1. [user] PR #436 "changed the bridge safety rule so a bridged child may commit checkpoints on the branch the host names, and added a timebox-free long-task brief to the usage guide. It explicitly did not touch the in-host worker."
2. [user] "phases.md step 3c says 'Implementation is the implementer tier' with the routing precedence ... and points at docs/reach/ for how a harness reaches a non-session model. But the thing 3c spawns is always the `worker` subagent, and worker.md never reads the implementer tier."
3. [user] "When the routing block pins the implementer to a model the harness reaches only by CLI (e.g. `implementer: gpt-6-astra at high` from Claude Code, reached by `codex exec`), nothing says whether the conductor or the worker runs the bridge."
4. [user] worker.md Phase 1.5 and the minted-task "judicious subagent use" license in no-plan-route.md ("parallel implementation of independent surfaces, background research, scouting") "assume the worker implements itself."
5. [user] Observed on a live run (2026-09-14): "the worker fanned out Claude repo/docs/memory scouts to pre-digest context for codex, which codex then re-read anyway; the scouts cost session-model context and bought nothing."
6. [user] Requested shape: prose only, no flowctl code, no hooks, matching #436's "bridge safety stays prose-only" stance. The worker runs the bridge itself; the conductor never bridges. The worker keeps judgment (prompt composition, diff check, gates, verdict) and the child does the investigation. The conductor-to-worker TIMEBOX stays a worker-level cap and is never copied into the child's brief.

Strategic context (STRATEGY.md): approach "the artifact is the contract"; design principle "remember the bitter lesson: do not build scaffolding around a model's current weaknesses". Active tracks: Ralph autonomous mode, Cross-platform parity, Self-improving through normal work.

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 60% [paraphrase], 30% [user], 10% [inferred] -->

Step 3c of the work skill routes implementation to the implementer tier, but the only thing it ever spawns is the in-host `worker` subagent, and the worker's own phases never consult that tier. When a project's routing block pins the implementer to a model the harness reaches only through a CLI bridge, the two documents disagree by omission: 3c implies a bridge, the worker implements on the session model and investigates for itself. On a live run this gap produced the worst of both: the worker spent session-model context on scout fan-out to pre-digest the repo for a `codex exec` child that re-read the repo anyway (evidence 2-5).

The fix is to name the path. The worker owns the bridge on this route: it anchors, records the base, skips its own investigation, composes a pointer prompt plus the long-task brief from the usage guide, runs the bridge in the foreground, and then reviews the child's commit range and runs the gates exactly as it does for its own code. The conductor never bridges. Judgment stays where #436 put it: the worker composes the prompt, checks the diff, runs the gates, dispatches review, and owns `flowctl done`; the child investigates and implements. This is a prose-only change to the worker, the 3c step, and the minted-task license, consistent with the recorded decision that bridge safety lives in prose rather than a hook (evidence 6).

## Architecture & Data Models
<!-- scope: technical -->

No code or config change. Three canonical prose surfaces change and the Codex mirror is regenerated:

- `agents/worker.md` gains a "Bridged implementer" section gated on the implementer tier resolving to a model this harness reaches by CLI bridge (per the harness reach page). The section states what the worker keeps from its standard phases (Phase 1 anchor, the persisted base commit, Phase 3 onward), what it skips (Phase 1.5 investigation and any scout fan-out), what it composes (the pointer prompt and the verbatim long-task brief from the usage guide), how it runs the bridge (foreground, from the asserted repo root, at the sandbox level that permits commits), and what it does on return (review `<base>..HEAD`, run the gates on that range, commit anything left uncommitted, continue to review dispatch and `flowctl done`).
- `skills/flow-next-work/phases.md` step 3c states that the worker runs the bridge itself on this path, the conductor never bridges, and the `TIMEBOX` line is the worker's cap and never the child's.
- `skills/flow-next-work/references/no-plan-route.md` "Judicious subagent use" scopes the license on the bridged path: parallel implementation of independent surfaces means parallel bridge calls on disjoint surfaces; background research and scouting do not apply because the child investigates.
- `codex/**` is regenerated by `scripts/sync-codex.sh` and committed with the source; mirror-source diffs never classify docs-only, so the full gates run.
- `CHANGELOG.md` gains an Unreleased entry referencing #431 and #436 and crediting the report.

## API Contracts
<!-- scope: technical -->

Prose contract only. The pointer prompt the worker composes carries: the task id, the spec path, the spec's `## Resolved via Research` section when present, the project instruction file, and the instruction to re-anchor on the repo, investigate, implement, and test; followed by the long-task brief from the usage guide verbatim (checkpoint commits on the named branch, the five never clauses, one return condition, no timebox, no "stop if you run out of room"). The worker-level `TIMEBOX` from the 3c dispatch is never copied into the child's brief. The bridge runs in the foreground from the asserted repo root with the sandbox level that permits commits (for codex, `danger-full-access`, since `workspace-write` keeps `.git/` read-only as verified in #436). The worker's return contract to the conductor is unchanged.

## Edge Cases & Constraints
<!-- scope: technical -->

- The implementer tier resolves to the session model or to an in-host subagent model: the standard worker phases apply unchanged, including Phase 1.5; the bridged section is inert. [paraphrase]
- The named model is unreachable from this harness: the reach page's degradation applies (fall back to the session model, say so once, continue on the standard path). [inferred]
- The child returns with commits on the named branch plus uncommitted work: the worker commits the remainder under Phase 3's convention before review; a commit landing on another branch is a review finding. [inferred]
- The sandbox denied the child's commits: the usage guide's fallback applies (the child reports it in its digest, the worker commits on its behalf); the worker never stalls or loops. [paraphrase]
- Under `PARALLEL_WAVE` or `REVIEW_MODE: host-deferred`, the bridged path changes only who writes the code; the handover and deferral contracts stand. [inferred]
- The Codex mirror is generated, never hand-edited; `scripts/sync-codex.sh` must be idempotent after the change. [paraphrase]
- No hook, guard, or flowctl subcommand enforces the path; bridge safety stays prose-only. [user]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `agents/worker.md` carries a "Bridged implementer" section gated on the implementer tier resolving to a model this harness reaches by CLI bridge per its reach page. On that path the worker runs Phase 1 as today, persists the base commit, and skips Phase 1.5 investigation and any scout fan-out. Errors: none. [user]
- **R2:** The section states the pointer prompt's contents (task id, spec path, the spec's `## Resolved via Research` section if present, the project instruction file, the instruction to re-anchor on the repo, investigate, implement, and test) and that the usage guide's long-task brief is appended verbatim: checkpoint commits on the named branch, the five never clauses, one return condition, no timebox, no "stop if you run out of room". The worker-level `TIMEBOX` is never copied into the child's brief. Errors: none. [user]
- **R3:** The section states that the bridge runs in the foreground from the asserted repo root with the sandbox level that permits commits (codex `workspace-write` keeps `.git/` read-only; `danger-full-access` commits, verified in #436), and that on return the worker reviews `<base>..HEAD`, runs the gates on that range, then continues with Phase 3 onward as today: the worker still commits anything uncommitted, dispatches review, and runs `flowctl done`. The worker keeps judgment (prompt composition, diff check, gates, verdict); the child does the investigation. Errors: none. [user]
- **R4:** `phases.md` step 3c states that the worker runs the bridge itself on this path, the conductor never bridges, and the `TIMEBOX` line is the worker's cap, never the child's. Errors: none. [user]
- **R5:** `no-plan-route.md` "Judicious subagent use" scopes the license on the bridged path: parallel implementation of independent surfaces means parallel bridge calls on disjoint surfaces; background research and scouting do not apply because the child investigates. Errors: none. [user]
- **R6:** The Codex mirror under `plugins/flow-next/codex/` is regenerated by `scripts/sync-codex.sh`, committed with the source, and a second run produces no diff. Errors: a non-idempotent second run is a failed gate. [user]
- **R7:** `CHANGELOG.md` gains an Unreleased entry that names the gap, the new worker path, references #431 and #436, and credits the report. Errors: none. [user]

## Boundaries
<!-- scope: business -->

- No flowctl code, hook, guard, or config key; the path is prose, consistent with #436. [user]
- The bridge safety rule and the long-task brief in the usage guide are not changed; the worker references them. [inferred]
- No change to the conductor's dispatch template fields, the parallel-wave and host-deferred contracts, the review backends, or `flowctl done`. [inferred]
- No change to the reach pages or the orchestration guide beyond what a reader needs to find the worker path. [inferred]
- No site (flow-next.dev) changes in this PR. [inferred]

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
<!-- scope: business -->

After #436 the bridge route has a safe commit rule and a brief shape, but the worker that 3c spawns has no path that uses them, so a pinned CLI implementer either silently runs on the session model or is bridged ad hoc with the worker's own investigation machinery still running. The scout fan-out observed on the live run is that machinery doing work the child redoes: session-model context spent on pre-digestion the bridged model does not consume. Naming the path removes the ambiguity and the wasted context without adding scaffolding. [paraphrase]

### Implementation Tradeoffs
<!-- scope: technical -->

Having the conductor run the bridge was rejected: the conductor's 3c contract is to spawn a fresh-context worker and read a pointer back, and bridging from the conductor would put a multi-hour foreground call in the conductor's context and duplicate the worker's gate and commit ownership. Keeping the worker's Phase 1.5 investigation on the bridged path was rejected: the child re-anchors and investigates in its own context, so worker-side investigation is spent twice. A mechanical gate on the tier resolution was rejected per the standing decision that bridge routing is prose. [paraphrase]
