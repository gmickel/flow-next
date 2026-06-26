# fn-72 QA as an optional pipeline stage — spec-derived test cases, verdict-gated

## Goal & Context
<!-- scope: business -->

`/flow-next:qa` exists today as a **user-invoked, off-to-the-side** skill: a human runs it against a spec when they remember to. It already does the hard part well — derive test scenarios from the spec (AC → scenarios, R-IDs → coverage, boundaries → exclusions, decision context → expected behavior), drive the live app via flow-next-drive, file P0/P1/P2 findings with evidence, and emit a YES/NO `qa_verdict` receipt. But because it is not part of the build pipeline, **live-app verification is the step most likely to be skipped** — pilot's autonomous span (`plan → plan-review → work → make-pr`) ships a draft PR with only *static* review (impl-review, spec-completion-review), never a real-user pass.

This spec makes QA a **fixed-but-optional stage in the pipeline**: when enabled, after `work` produces a runnable build, the pipeline **derives a durable test-case set from the spec + implementation context, runs it against the live app, and gates on the verdict** before (or alongside) `make-pr`. The intent is to move live-app verification from "a thing you remember to do" to "a station on the line you can switch on" — without forcing it on environments that can't run it.

This is the live-app complement to the static `spec-completion-review`, and it slots into the same pipeline pilot/backlog-mode already walk. It is deliberately **optional** because QA needs infrastructure (a runnable app + a driver) that not every repo or CI path has.

## Architecture & Data Models
<!-- scope: technical -->

- **A config-gated pipeline stage, reusing the existing `/flow-next:qa` skill** — not a new skill. The QA skill remains the executor (derive → prepare → execute → file → verdict); this spec wires it into the pipeline as a stage and adds the **durable test-case artifact** + the **gating contract**.
- **Pipeline placement:** `plan → plan-review → work → **qa** → make-pr`. QA runs after `work` (something runnable exists) and gates `make-pr`. *Open: whether it gates the draft-PR creation or runs against the just-created draft PR's preview — see Decision Context.*
- **Spec-derived test cases as a persisted artifact.** QA's `derive` phase output is materialized to a durable, reviewable test-case set (e.g. `.flow/qa/<spec-id>/cases.*`) keyed to **R-IDs** so coverage is traceable (which R-IDs have a live-app case, which don't). Derivation reads the **spec** (AC/R-IDs/boundaries/decision context) **and implementation context** (the diff / changed surfaces) — the host agent authors the cases (agentic); flowctl only persists + lists them (deterministic).
- **Verdict gating contract:** the `qa_verdict` receipt (PASS / FAIL / BLOCKED) routes the stage:
  - **PASS** → advance (→ make-pr).
  - **FAIL** (open P0/P1) → do not advance; surface findings (feed the bug memory track) and route back to `work`, or to the async-question valve in autonomous mode.
  - **BLOCKED** (no runnable app / no driver reachable) → **does not fail the pipeline**: skip with a recorded BLOCKED receipt + a note, because QA needs infra that may legitimately be absent. *(BLOCKED ≠ FAIL — the load-bearing distinction that keeps optional-QA from wedging pipelines that can't run it.)*
- **Reuses, not rebuilds:** the QA skill (executor + the hard PASS-needs-evidence rule), flow-next-drive (the driver ladder — incl. the fn-71 CUA rung for native/Windows/CI reach), receipts (`qa_verdict`), the bug memory track, and pilot's stage machine. Net-new is the test-case artifact + the stage wiring + the gating routing.
- **Pilot / backlog-mode integration:** `qa` becomes a stage pilot can classify-and-dispatch (extends fn-68's pipeline). Autonomy-safe: in autonomous/backlog mode QA never prompts; FAIL surfaces via the question valve, BLOCKED records and proceeds. Default off; opt-in via config.

## API Contracts
<!-- scope: technical -->

- **Config:** a pipeline-QA gate — e.g. `pipeline.qa ∈ {off (default), on}` (+ optional per-spec override). When `on`, pilot inserts the `qa` stage after `work`. Default **off** (infra-dependent).
- **Test-case artifact:** `.flow/qa/<spec-id>/cases.*` (JSON or md) — per case `{r_id?, scenario, expected, surface, status}`; R-ID-keyed for coverage. `flowctl` provides atomic write + list (`flowctl qa cases …` or reuse an existing helper); the **content is host-authored**, never regex-extracted.
- **Stage verdict:** reuses the `qa_verdict` receipt (PASS/FAIL/BLOCKED + open-P0/P1 list). Pilot reads the receipt to route (advance / back-to-work / skip-with-note).
- **Verdict grammar (pilot):** the `qa` stage participates in pilot's existing per-tick verdict line (`ADVANCED <id> qa`, or `NEEDS_HUMAN` on FAIL in interactive mode / `ASKED` via the valve in autonomous mode, or `ADVANCED … qa(blocked)`).
- **Cross-platform:** canonical Claude names; `sync-codex.sh` regenerates; `/goal` driver parity.

## Edge Cases & Constraints
<!-- scope: technical -->

- **BLOCKED never fails the pipeline** — no runnable app / no driver ⇒ recorded BLOCKED + note, pipeline proceeds (optional stage). Only FAIL (real findings on a live app) gates.
- **PASS still requires live evidence** — the QA skill's hard rule is preserved: the stage can NEVER mark PASS from source inspection; a green stage means captured live-app evidence, not narration.
- **Don't-thrash on FAIL** — a FAIL routes back to work bounded (reuse pilot's strike/auto-block reflexes); QA must not loop work↔qa forever. Cap and escalate (NEEDS_HUMAN / valve).
- **Test-case staleness** — cases are R-ID-keyed; when the spec's R-IDs change, surface added/removed coverage rather than silently running stale cases (append-only R-IDs make this tractable).
- **Autonomy-safe** — QA-in-pipeline never prompts in autonomous/backlog mode; FAIL → question valve, BLOCKED → proceed-with-note. Interactive mode may surface findings to the user.
- **Cost awareness** — a live-app pass is expensive (driver + app boot); the stage is opt-in and runs once per spec advance, not per tick spin.
- **Relationship to `spec-completion-review`** — QA is the *live-app* complement to the *static* completion review; both may run; neither replaces the other.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A config gate (`pipeline.qa`, default **off**) inserts a `qa` stage into the pipeline after `work`; with it off, the pipeline is unchanged. Optional per-spec override.
- **R2:** When on, the stage **derives a durable, R-ID-keyed test-case set** from the spec (AC/R-IDs/boundaries/decision context) **+ implementation context**, persisted under `.flow/qa/<spec-id>/`; the cases are host-authored (agentic), flowctl only persists/lists them.
- **R3:** The stage runs the cases against the live app via flow-next-drive (reusing the fn-51 read-and-drive contract, incl. the fn-71 CUA rung where available) and emits the `qa_verdict` receipt (PASS/FAIL/BLOCKED) with evidence.
- **R4:** **Verdict gating:** PASS → advance; FAIL → do not advance, surface findings (bug memory) + route back to work or the async valve; **BLOCKED → record + proceed (never fails the pipeline)**.
- **R5:** PASS-needs-live-evidence is preserved — the stage can never mark PASS from source inspection (the QA skill's load-bearing rule carries into the pipeline).
- **R6:** Pilot/backlog-mode integration — `qa` is a stage pilot classifies-and-dispatches; autonomy-safe (no prompts; FAIL→valve, BLOCKED→proceed); bounded work↔qa retries (no thrash).
- **R7:** Coverage traceability — the test-case set maps cases to R-IDs; the receipt reports which R-IDs have live-app coverage and which don't.
- **R8:** Reuses the existing `/flow-next:qa` skill as executor (no second QA implementation); net-new is the test-case artifact + stage wiring + gating routing.
- **R9:** Docs + flow-next.dev (qa page, pilot/ralph pipeline docs, both navbars, changelog) updated; plugin version bumped; cross-platform parity (sync-codex, `/goal`).

## Boundaries
<!-- scope: business -->

- **Optional, default off** — QA-in-pipeline never becomes mandatory; environments without a runnable app/driver are never blocked by it (BLOCKED proceeds).
- **Reuses the QA skill** — does not fork or reimplement QA; this is wiring + an artifact + gating, not a new QA engine.
- **Not a merge gate** — QA gates the *pipeline stage / draft-PR readiness*, not the human merge; `land` and human review stay the merge authority.
- **Not a static review** — complements `spec-completion-review` / `impl-review`; does not replace them.
- **Driver/sandbox support is fn-71's concern** — this spec consumes flow-next-drive (incl. the CUA rung) but does not implement drivers.
- **Self-improvement / flaky-case management** (learning from repeated QA failures) is out of scope — a possible follow-on once the stage exists.

## Decision Context
<!-- scope: both -->

### Motivation
Live-app verification is the highest-value, most-skipped review because it's the only one that exercises the *running* product — and today it lives outside the pipeline. Making it a switchable station turns "QA if someone remembers" into "QA on the line," while keeping it optional so it never wedges environments that can't run it. The spec already encodes intent (AC/R-IDs/boundaries), so deriving test cases from it is cheap and the cases are traceable.

### Implementation Tradeoffs
- **Stage + artifact + gate, reusing the QA skill — not a new skill:** the executor and its hard rules already exist; the work is wiring it into the pipeline, persisting the derived cases, and defining the verdict routing.
- **BLOCKED ≠ FAIL is the load-bearing choice:** an optional stage that *failed* when infra was absent would make it un-adoptable; BLOCKED-proceeds keeps it switch-on-able everywhere.
- **Agentic derivation, deterministic persistence:** the host authors test cases from the spec + diff (judgment); flowctl only stores/lists them — no regex test-extractor (that would be the deterministic-doing-judgment anti-pattern).
- **Default off:** QA needs infra; forcing it on would break the zero-friction default. Opt-in per the strategy's "improvement that depends on remembering a command doesn't happen" — but here the gate, once on, runs automatically every advance (no per-run remembering).

### Open questions (to resolve in interview/plan)
- **Placement:** gate `make-pr` (QA before the draft PR) vs run against the just-created draft-PR preview (QA after make-pr, attaching status to the PR). The former keeps a red build out of PR; the latter gives reviewers a live-tested PR. *Leaning: before make-pr in autonomous mode (don't surface a failing draft), with an option to run post-make-pr for human-review workflows.*
- **Gating strictness:** hard-block advance on FAIL vs attach QA status + let the human decide. *Leaning: hard-block in autonomous/backlog mode (FAIL → valve), advisory in interactive.*
- **Test-case format/location:** `.flow/qa/<spec-id>/cases.json` vs a section in the spec. *Leaning: separate artifact (keeps the spec clean; R-ID-keyed for coverage).*
- **Dependency on QA execute/verdict phases:** the QA skill's phases 3–6 (prepare/execute/file/verdict) were scaffolded as downstream tasks (fn-53 lineage); this stage depends on them being complete.

## Strategy Alignment
- **Ralph autonomous mode track** — adds a quality station to the pilot/land assembly line; consistent with "multi-model review at every handover, evidence over narration" (QA is evidence-over-narration by construction).
- **Self-improving through normal work** — QA findings feed the bug memory track as a side-effect of running the stage; the test-case set is a durable artifact that compounds.
- **"Host agent IS the intelligence"** — derivation/execution/verdict are agentic; flowctl only persists the artifact + receipt.
- **Cross-platform parity** — canonical names + sync-codex; reach widened by the fn-71 CUA rung (Windows/native/CI).
- Tightens the **idea-to-merge wall-clock** quality, not just speed — a live-tested draft PR.

## Conversation Evidence
> user: "separately we should consider whether QA should become a fixed (pot optional) part of the pipeline with the test cases being extracted from the spec and context and tested etc, probably a sep spec"

Reference: `/flow-next:qa` (fn-53 lineage) — derive (AC→scenarios, R-IDs→coverage) + the hard PASS-needs-live-evidence rule; flow-next-drive (fn-51) driver ladder + the fn-71 CUA rung; pilot pipeline (fn-59 / fn-68 backlog mode).
