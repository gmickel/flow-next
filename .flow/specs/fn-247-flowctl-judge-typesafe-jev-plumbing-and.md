# flowctl judge: TypeSafe Jev plumbing and the six judged sites

## Goal & Context
<!-- scope: business -->

The fn-246 evaluation (five passes, recorded in that spec) found where a System One judge helps flow-next: narrow closed questions where code supplies the facts and the option set matches what the data contains. Six sites cleared their majority baselines. This spec ships the shared plumbing and all six, in their most efficient form: one Jev request per decision point carrying every question that point needs, code owning the control flow, and the host model touched only for the residue Jev cannot decide. Dogfooding on further spec sets and simple evals happens before release, not before implementation.

What users with a `TYPESAFE_API_KEY` get, at about 600 ms and no host tokens per call:

- **Land** stops missing clean reviews the regex cannot see (Bugbot "found no new issues", Copilot "Approval recommended") and stops false-alarming on wrapper bodies, so PRs merge on the tick they converge.
- **Flow** routes five inputs in six without spending a host turn, prints `--explain` in under a second, and hands the host only the ambiguous sixth with candidates attached. Unattended runs route identically on every host.
- **QA under auto** runs on UI specs it used to skip, because code supplies the startable target and Jev answers only the UI-observable question.
- **Prototype-before-ask** stops inventing forks: a gate Noul ahead of the observable-vs-preference call.
- **The memory scout** disappears as a subagent: BM25 hits are reranked by one call with fifteen Score questions, saving a spawn (10 to 30 s and its tokens) per plan and work run.
- **Workers and scouts** get a per-task tier: confidently mechanical tasks go to the fast tier, confidently long-running ones recommend the bridge, everything else stays on the session model as today.

Users without a key see byte-identical behaviour. The strategy's zero-dependency contract holds: flowctl core imports nothing new, the key is the only switch, and uninstall stays a directory delete.

Reference for the model and API, the pages this spec relies on:

- Model and primitives: https://docs.typesafe.ai/concepts/system-one.md, https://docs.typesafe.ai/primitives.md (one snap judgment per question; every question in a request is evaluated in parallel and independently, so adding questions barely moves latency).
- Question shapes used here: https://docs.typesafe.ai/primitives/choice.md (Choice with a `criteria` map, returns `choice`, `probabilities`, `confidence`), https://docs.typesafe.ai/primitives/noul.md (yes/no probability, no separate confidence), https://docs.typesafe.ai/primitives/score.md (ordered levels, returns `score` and `confidence`).
- Confidence and floors: https://docs.typesafe.ai/confidence.md, https://docs.typesafe.ai/patterns/confidence-routing.md (act above a floor, fall back below it; the floor scales with the stakes).
- Fan-out: https://docs.typesafe.ai/patterns/fan-out.md (send every question for one state in one request, including speculative ones the code may ignore).
- Architecture stance: https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md (code owns control flow; the model answers narrow typed questions).
- Structured instructions: https://docs.typesafe.ai/primitives/advanced.md (criteria and instructions accept JSON structure; state fields are referenced by backticked dot paths).
- HTTP contract: https://docs.typesafe.ai/api.md (`POST https://api.typesafe.ai/v1/systemone`, bearer auth, `state` + `model` + `questions` in, `answers` + `usage` out; request budget about 32k tokens shared by state and questions).
- Full index: https://docs.typesafe.ai/llms.txt.

## Architecture & Data Models
<!-- scope: technical -->

**One plumbing command.** `flowctl judge --preset <name> --state-file <path> [--json]` sends one request to the System One endpoint with stdlib HTTP (the `http.client` flowctl already imports) and returns the typed answers plus the preset's stated decision. The preset registry lives inside flowctl (the smoke scripts copy flowctl alone, so no sidecar file): each preset names its question ids, types, instruction text, `criteria`, the state fields it requires, and its decision rule (which answers, which floors, what the fallback value is). The command transports, validates, and applies the rule the preset states, so every host computes the same decision from the same answers. What the decision means for a stage stays in that skill's contract.

**Availability is a fact, never an error.** The key comes from the `TYPESAFE_API_KEY` environment variable at call time. No key, `judge.enabled=false`, a transport failure after the retry budget, a non-2xx response, or an answer missing any option the preset sent all produce `available: false` with a named reason and exit 0. The caller then takes its pre-existing path. The command never guesses an answer, never logs the key, and never writes state or answers anywhere itself; the calling skill records what it used in the stage line it already writes.

**Six presets, five call sites, one request per call site.** The route step's single request carries the kind Choice, the anchored Nouls, the fork gate, and the QA question together (the fan-out pattern); code reads only the answers the route needs.

| Preset | Questions (one request) | Decision rule | Fallback when unavailable |
|---|---|---|---|
| `clean-review` | Choice over `clean` / `findings` / `wrapper_or_status` for one automated review body | `clean` at confidence >= 0.7 is a clean review; anything else is not | `land.cleanReviewCommentPattern` regex, unchanged |
| `route` | Choice `kind` over the 13 kinds plus `none_of_the_above`; 12 anchored Nouls; the `fork-gate` pair; the `qa-gate` Noul | Lifecycle rows decided by code first; `kind` at confidence >= 0.7 routes; below the floor or `none_of_the_above` the host decides with the top-3 kinds and probabilities as candidates; lifecycle kinds masked on non-live views | Today's host routing |
| `qa-gate` | Noul "do the acceptance criteria describe behaviour observable in a user-facing UI?" (rides in `route`; standalone preset for the all-done hop) | UI-observable >= 0.5 AND a startable target resolved by code => QA runs; otherwise `skipped(...)` naming the failing half | Today's host judgment |
| `fork-gate` | Noul "does the text pose a design or behaviour fork with two named alternatives?"; Choice `observable` / `product_or_preference` / `none_of_the_above` (rides in `route`; standalone preset for routed skills) | Fork present at >= 0.5 else no fork and no question; classification at >= 0.5 else the host decides | Today's host judgment |
| `memory-rerank` | Fifteen Score questions, one per BM25 hit, levels `not relevant` / `tangential` / `directly relevant` | Order by score, keep entries scoring >= 1.0, cap at 10; ties keep BM25 order | BM25 order from `flowctl memory search`, today's behaviour |
| `tier` | Choice over `mechanical` / `moderate` / `intelligent` / `long_running`; Noul `purely_mechanical_edit`; Noul `needs_long_uninterrupted_run` | `mechanical` at >= 0.8 => fast tier; `long_running` at >= 0.8 => bridge recommended; otherwise session model (today) | Today's static routing block |

**Kind criteria text.** Each kind's criterion is the route matrix's starting-state cell followed by its positive-signal cell, verbatim, joined by a period. That shape scored 0.95 raw against stable labels; the positive-signal cell alone scored 0.82 and adding the safe-skip text dropped it to 0.81. The thirteen kinds and the matrix row each maps to: `build` (one meaningful idea), `capture_brief` (structured brief), `defect` (reported defect), `cleanup` (structural change, behaviour kept), `slowness` (measured slowness), `hillclimb` (one metric through repeated attempts), `question` (read-only question), `fork` (observable design fork), `tiny` (tiny local change), `theme` (theme or direction), `discovery` (no direction, prospect, or chart), `refine` (unresolved product or authority questions), `plan_review` (design needs independent assessment). Lifecycle kinds `existing_pr_tail`, `all_done_make_pr`, `work_planned` are decided by code and never asked.

**Anchored Nouls** (instruction text in the preset, each a one-sentence question about the input): `reports_defect`, `defect_has_repro`, `structural_change_behaviour_kept`, `names_metric_and_surface`, `repeated_metric_target`, `read_only_question`, `theme_no_end_state`, `no_written_direction`, `large_idea_several_unknowns`, `names_unfamiliar_library_or_api`, `tiny_one_context_change`, `intent_and_boundaries_stateable`. The fact-grade ones (agreement >= 0.9 in fn-246) feed the `Signal:` line and the defect repro branch; the two judgment ones (`tiny_one_context_change`, `intent_and_boundaries_stateable`) print as hints only and never decide. `asks_for_plan`, `separate_owners`, `staged_prs` are code regexes over the text (0.99-1.0), not questions. The research fact is the Noul (0.97) with the deterministic dependency scan naming the tokens for the `--explain` line.

**Route state fields**, nothing else: `view` (`intent` | `brief` | `live`), `view_meaning` (one sentence each), `repo`, `intent` or `spec_title` + `spec_body`, `status`, `ready`, `no_plan`, `tasks_total`, `tasks_done`, `pr_exists`, `pr_ref`, `startable_target_fact`. `pr_exists` comes from a live `gh pr list --head` (or the tracker bridge), never from commit messages.

**Tier state fields:** `task_title`, `task_body`, `acceptance`, `touches_count`, `has_quick_commands`, `repo`. Level descriptions in the preset: mechanical (a rename, config bump, mirrored doc, fixture add: one obvious edit, no design), moderate (a bounded feature in one module with tests), intelligent (design judgment, cross-module change, or ambiguous acceptance), long_running (multi-hour implementation across many files that needs an isolated harness).

**Where they plug in.**

- Land's review-signal gate (the section that reads `cleanReviewCommentPattern`) asks `clean-review` per automated review body before the regex.
- Flow's route step (workflow Step 2) assembles the route state in code, asks `route` once, and applies the decision order: lifecycle rows, then kind at the floor, then host fallback. `--explain` prints from the same answers: `Next:`, `Route:`, `Signal:` (the firing fact-grade Noul), `Skip/narrow:` (the matrix cell), `Why not the alternatives:` (the next two kinds with probabilities). Attended and `--auto` use the same call; attended flow shows the host the candidates when it falls back.
- Flow's QA decision under `pipeline.qa=auto` reads the `qa-gate` answer from the route call at the all-done hop (or asks the standalone preset when no route call happened this hop), after code resolves the startable target from a documented start command, a deploy URL, or the features map.
- Prototype-before-ask reads the `fork-gate` answers from the route call; a routed skill that classifies a fork on its own asks the standalone preset.
- The memory scout's search step becomes `flowctl memory search <query> --rerank`, which runs BM25, asks `memory-rerank` on the top 15, and returns the reranked list with scores; plan and work call the command directly instead of spawning the scout when the judge is available, and spawn it as today when not.
- The worker's implementer resolution (worker Phase 1b) and the conductor's scout dispatch ask `tier` once per task: `mechanical` at the floor selects the fast-scout model from the routing block for the implementer tier (session model when the block names none); `long_running` at the floor adds a `Tier: long_running (jev 0.86) - bridge recommended` line to the dispatch and the done summary; everything else is unchanged.

**Config.** One new key, `judge.enabled` (boolean, default `true`), so a keyed environment can still turn the judge off. The key's presence is the switch; the published config schema gains the key. No model selector: the model is `jev-latest`, a preset constant.

## API Contracts
<!-- scope: technical -->

Command output (the fields shown are the contract):

```json
{
  "success": true,
  "available": true,
  "preset": "route",
  "model": "jev-1.13.0",
  "decision": {"value": "defect", "rule": "kind confidence>=0.7", "met": true, "candidates": [["defect", 0.91], ["build", 0.06], ["tiny", 0.02]]},
  "answers": {"kind": {"type": "choice", "choice": "defect", "confidence": 0.91, "probabilities": {"defect": 0.91, "build": 0.06, "tiny": 0.02}}, "reports_defect": {"type": "noul", "noul": 0.94}},
  "latency_ms": 612,
  "usage": {"input_tokens": 2310, "output_tokens": 180}
}
```

`decision.candidates` is present for `route` and `tier` (top three by probability) and absent otherwise. `memory-rerank` returns `decision.value` as the ordered list of entry ids with their scores.

Unavailable output:

```json
{"success": true, "available": false, "preset": "route", "reason": "no_key"}
```

`reason` is one of `no_key`, `disabled`, `http_<status>`, `transport`, `timeout`, `bad_answer`, `over_budget`. `decision.value` is absent when `available` is false.

Stage and report lines written by the callers, one of each shape:

```
clean-review: jev(clean 0.91) | regex | jev-unavailable(no_key)->regex
Route: defect (jev 0.91) | host (jev below floor: build 0.52, tiny 0.31, defect 0.10) | host (jev-unavailable(timeout))
stage: qa - skipped(config: pipeline.qa=auto: no UI-observable criteria (jev 0.12)) | ran (jev ui 0.84, target: <cmd>)
fork-gate: none (jev 0.08) | observable (jev 0.77) | preference (jev 0.71) | host (jev below floor)
memory: reranked (jev, 15 -> 6) | bm25 (jev-unavailable(no_key))
Tier: mechanical (jev 0.88) -> <model> | long_running (jev 0.86) - bridge recommended | session (jev moderate 0.61)
```

`flowctl memory search <query> --rerank --json` returns today's shape with two added fields per match, `jev_score` and `jev_rank`, and a top-level `rerank: "jev" | "bm25"`.

Retry: two retries on HTTP 429 and 529 with 1 s then 2 s backoff; no retry on anything else. Timeout 10 s per request. State over the request budget (about 32k tokens; the command estimates from character count at four characters per token) returns `over_budget` rather than truncating silently; the route caller trims `spec_body` to its first 100k characters before calling, and says so in the state as `spec_body_truncated: true`.

## Edge Cases & Constraints
<!-- scope: technical -->

- **The key never persists.** Read from the environment at call time only; never echoed, never in receipts, stage lines, JSON output, logs, or commits. A preset or caller that writes it has broken this.
- **Never a gate skip by prediction.** Every preset classifies an existing artifact or the input text. None predicts a review, QA, or land verdict; that use was falsified in fn-246 and is out of scope.
- **Fail closed to today's behaviour.** Every unavailable reason yields the pre-existing path, byte-identical to a keyless run, and the stage line names the reason. Silence is the failure mode this rule forbids.
- **The host is never handed raw Nouls as facts.** fn-246 measured a cheap host second-guessing itself when given Jev's answers (0.93 alone, 0.86 with the facts). On fallback the host receives the top-3 candidates with probabilities and nothing else; the Nouls feed code and the `Signal:` line only.
- **Floors are preset constants.** 0.7 for clean-review (it can let a PR merge) and kind (held-out: 85% coverage at 95%); 0.8 for tier (mechanical 20/20 and long-running 13/13 at that floor, and a wrong mechanical costs one bounded failed attempt); 0.5 for the fork and QA Nouls (a miss falls back to today). Not config.
- **Presets are versioned in code.** Option ids and instruction text are the contract the evaluation was run against; changing either changes the numbers of record and is noted in the spec that changes it.
- **Windows stdout is cp1252.** Command output is ASCII only.
- **Cross-host parity.** The Codex mirror and the OpenCode manifest carry the same call sites; a host without the key behaves as today. The smoke scripts that copy flowctl alone must keep passing, which is why the registry is in flowctl and not a template file.
- **Land's null-vs-empty asymmetry** for `cleanReviewCommentPattern` is untouched: the judge runs before the regex and the regex path keeps its exact semantics.
- **Tier never routes up.** A `moderate` or `intelligent` answer changes nothing; the routing block and the session model stay authoritative. Only the two confident extremes act, and `long_running` only recommends.
- **Memory rerank keeps the scout's contract.** The reranked list prints in the scout's `## Memory findings` table shape so plan and work read it unchanged; hardened and stale entries stay excluded by the same status filter.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `flowctl judge --preset <name> --state-file <path> --json` sends one request with the preset's questions and the state file's JSON and returns the output shape above with the preset's decision applied. Errors: unknown preset -> non-zero exit naming the registered presets; unreadable or non-JSON state file -> non-zero exit; a state file missing a field the preset requires -> non-zero exit naming the field.
- **R2:** With no `TYPESAFE_API_KEY`, or `judge.enabled=false`, the command returns `available: false` with `reason` `no_key` or `disabled`, exit 0, and sends nothing. Errors: no error surface beyond the reason field.
- **R3:** HTTP 429 and 529 are retried twice (1 s, 2 s); any other non-2xx, a transport error, or a timeout after the budget returns `available: false` with the matching reason; a 2xx whose answers omit any question id or any option the preset sent returns `bad_answer`; an estimated over-budget state returns `over_budget` without sending. Errors: none beyond those reasons; the command never fabricates an answer.
- **R4:** The key appears in no output, receipt, stage line, or log under any path, including error paths. Errors: a unit test asserts the bearer value is absent from stdout, stderr, and every file the run writes.
- **R5:** Land asks `clean-review` for each automated review body before the regex; `clean` at confidence >= 0.7 is a clean review, anything else is not, and unavailable falls to the regex. The land report and ledger carry the `clean-review:` line above. Errors: an unavailable call never blocks the tick and never changes the regex outcome.
- **R6:** Flow's route step assembles the route state in code (view, lifecycle fields, live `pr_exists`, startable target), asks `route` once per hop, decides lifecycle rows in code first, routes on `kind` at confidence >= 0.7, and otherwise hands the host the top-3 candidates. The `Route:` line above is printed on every hop. Errors: unavailable routes as today with the reason in the line; `none_of_the_above` is a fallback, never a route; lifecycle kinds are masked on `intent` and `brief` views.
- **R7:** `flow --explain` prints the full recommendation shape (`Next:`, `Route:`, `Signal:`, `Skip/narrow:`, `Why not the alternatives:`) from code plus the one `route` call, with the `Signal:` line quoting the firing fact-grade Noul and its probability and the why-not line naming the next two kinds with probabilities. Errors: below the floor it prints the three candidates and says the host decides; unavailable prints today's host recommendation.
- **R8:** Under `pipeline.qa=auto`, flow resolves the startable target in code (documented start command, deploy URL, or features map), reads the `qa-gate` answer from the route call or asks the standalone preset, and runs QA only when UI-observable >= 0.5 and a target exists; the skip line names the failing half with the Jev number. Errors: unavailable falls to today's host judgment and the skip line says so; `pipeline.qa` values other than `auto` never call the judge.
- **R9:** Prototype-before-ask reads `fork-gate` first; below 0.5 on fork-present there is no fork and no question; at or above, the Choice at >= 0.5 decides observable vs preference and below the floor the host decides. Errors: unavailable falls to today's judgment; under any autonomy marker a preference fork still stops with `NEEDS_HUMAN` as today; the one-question-per-hop budget is unchanged.
- **R10:** `flowctl memory search <query> --rerank --json` runs BM25, asks `memory-rerank` over the top 15 hits in one request, and returns the list ordered by Jev score with `jev_score`, `jev_rank`, and `rerank` fields; entries scoring below 1.0 are dropped and the result is capped at 10. Plan and work call it directly when the judge is available and spawn the memory scout as today when not, and the findings render in the scout's table shape either way. Errors: unavailable returns BM25 order with `rerank: "bm25"`; fewer than 15 hits sends fewer questions; zero hits sends nothing.
- **R11:** The worker's implementer resolution and the conductor's scout dispatch ask `tier` once per task with the tier state above; `mechanical` at >= 0.8 selects the fast-scout model from the routing block for that task's implementer (session model when none is named); `long_running` at >= 0.8 adds the bridge-recommended line; every other answer leaves routing unchanged. The `Tier:` line is written to the dispatch and the task's done summary. Errors: unavailable leaves routing unchanged with the reason in the line; an explicit `IMPLEMENTER:` in the invocation always wins over the tier answer.
- **R12:** `judge.enabled` exists in the config schema (boolean, default true) and `flowctl config get judge.enabled` reports it. Errors: a non-boolean value is treated as true with a warning, never a failing tick.
- **R13:** Unit tests cover R1-R4 and the decision rule of every preset with a stubbed HTTP layer (no network, fixture answers per preset), and the six call sites are exercised by their existing smoke scripts with the key absent (byte-identical to today's output). Errors: none beyond the tests themselves.
- **R14:** Docs: a `judge` page in the plugin docs (what it is, the six presets with their question text and floors, the decision order, the fallback rule, the key, the cost and latency numbers of record from fn-246, the doc links above); the land, flow workflow, route-matrix, gate-selection, prototype-before-ask, memory-scout, and worker references updated at their call sites; the config schema page, the flowctl reference, and the setup skill's one-line key notice updated; the Codex mirror regenerated. Errors: none beyond the docs build.

## Boundaries
<!-- scope: business -->

- No SDK dependency; the HTTP call is stdlib. No model selector, no per-preset config knobs beyond `judge.enabled`.
- No verdict prediction for review, QA, or land. No review preflight, no spec-count tripwire, no plan-vs-no-plan Nouls, no CI-failure classifier: each was dropped on evidence in fn-246.
- No shadow logging and no ship gates inside this spec; dogfooding on more spec sets and simple evals happens before release.
- No change to the regex semantics, the QA skill's own contract, the prototype-before-ask question budget, the memory scout's output shape, or the routing block's precedence (explicit invocation, block, agent default, session model).
- The host keeps refine, plan-review, split, chart-vs-capture, the lenses, and every below-floor route; Jev never asks the user anything.
- No key management: the environment variable is the user's to set; setup prints one line saying the judge is off when the key is absent and nothing more.

## Decision Context
<!-- scope: both -->

- **Why plumbing in flowctl.** Six call sites on five hosts would otherwise carry the same HTTP, retry, validation, and fallback logic. The strategy's burden-of-proof rule for flowctl is met: transport, schema validation, and a stated decision rule are zero-judgment operations that must behave identically with no agent in the loop, and cross-host determinism is the point of the judge. The judgment (what a decision means for a stage) stays in each skill's contract.
- **Why one request per call site.** Questions in a request are independent and parallel, so the route hop asks kind, facts, fork, and QA together and reads what it needs; the fan-out pattern makes the extra questions free. Two-phase and coarse-then-fine kind shapes cost a second call and scored lower.
- **Why the key is the switch.** The strategy's zero-dependency contract holds for the base install; an opt-in convenience may carry a prerequisite, and absence must be byte-identical to today. Default on with the key absent is off in practice and needs no install step.
- **Why all six now.** Each cleared its majority baseline in fn-246: clean-review 100/100 against the eyeball label with the regex at 5/12; kind 0.95 raw on 196 stable samples, 85% coverage at 95% held-out at the 0.7 floor, one call self-consistent on 195/196; QA gate 0.88 against 0.71 once code supplied the startable fact; fork gate 0.88 against 0.76 with invented forks down from 12 to 1; memory rerank precision@5 0.66 against BM25 0.48; tier 0.91 exact and 121/121 within one tier with mechanical 20/20 and long-running 13/13 at 0.8. The remaining uncertainty is best reduced by dogfooding, not by more offline gates.
- **Why the host keeps the residue.** The judgment stages (refine, plan-review, split, chart, lenses) were predicted on 9-11 of 16 builds against 0-3 labels; no fact in the state answers "would this stage change the outcome". Handing the host Jev's answers made a cheap host worse, so fallback carries candidates only.
- **Why tier acts only at the extremes.** Mis-routing down costs one bounded failed attempt and an escalation the review loop already handles; mis-routing up costs money silently. Confident mechanical and confident long-running are the two decisions with a safe failure mode; the moderate/intelligent boundary is where the labelers themselves disagree.
- **Rejected:** a Noul for clean-review (0.69 against a 0.88 baseline; wrapper and stale-marker bodies read as clean), a Noul precedence tree as the router (0.80 against the Choice's 0.95), the `Next:`-line framing for kind (0.51), a separate preset file (smoke scripts copy flowctl alone), the Python SDK (one HTTP call), shadow logging (the evaluation already ran), and offline ship gates for the last three sites (dogfooding is the cheaper test).
