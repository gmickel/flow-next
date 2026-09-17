# flowctl judge: TypeSafe Jev plumbing and the three ungated sites

## Goal & Context
<!-- scope: business -->

The fn-246 evaluation (five passes, recorded in that spec) found where a System One judge helps flow-next: narrow closed questions where code supplies the facts and the option set matches what the data contains. Three sites cleared their majority baseline with the evidence they already have and carry no ship gate: land's clean-review detection, the QA gate under `pipeline.qa=auto`, and the fork gate ahead of prototype-before-ask. This spec ships the shared plumbing and those three sites. Route assist, memory rerank, and tier routing follow in their own specs once their gates (a third-scout pass folded in, a human-labeled memory subset, a ten-task cheap-tier counterfactual) are met.

Users with a TypeSafe key get, for about 600 ms and no host tokens per call: a clean-review detector that catches the rewordings the regex misses (Bugbot "found no new issues", Copilot "Approval recommended") without the regex's false alarms; a QA gate that no longer skips UI specs because a spec body cannot see the dev server; and a fork gate that stops the host inventing forks at low confidence. Users without a key see byte-identical behaviour. The strategy's zero-dependency contract holds: flowctl core imports nothing new, the key is the only switch, and uninstall stays a directory delete.

Reference for the model and API, with the pages this spec relies on:

- Model and primitives: https://docs.typesafe.ai/concepts/system-one.md, https://docs.typesafe.ai/primitives.md (one snap judgment per question; several questions per request are evaluated in parallel and independently).
- Question shapes used here: https://docs.typesafe.ai/primitives/choice.md (Choice with a `criteria` map, returns `choice`, `probabilities`, `confidence`), https://docs.typesafe.ai/primitives/noul.md (yes/no probability, no separate confidence).
- Confidence and floors: https://docs.typesafe.ai/confidence.md and https://docs.typesafe.ai/patterns/confidence-routing.md (act above a floor, fall back below it; thresholds scale with the stakes).
- Fan-out: https://docs.typesafe.ai/patterns/fan-out.md (send every question for one state in one request).
- Architecture stance: https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md (code owns control flow; the model answers narrow typed questions).
- HTTP contract: https://docs.typesafe.ai/api.md (`POST https://api.typesafe.ai/v1/systemone`, bearer auth, `state` + `model` + `questions` in, `answers` + `usage` out).
- Full index: https://docs.typesafe.ai/llms.txt.

## Architecture & Data Models
<!-- scope: technical -->

**One plumbing command.** `flowctl judge --preset <name> --state-file <path> [--json]` sends one request to the System One endpoint with stdlib HTTP (the `http.client` flowctl already imports) and returns the typed answers plus the preset's stated decision. The preset registry lives inside flowctl (the smoke scripts copy flowctl alone, so no sidecar file): each preset names its question ids, types, instruction text, `criteria`, the state fields it expects, and its decision rule (which answer, which floor, what the fallback value is). Judgment stays in the calling skill's contract; the command only transports, validates, and applies the rule the preset states so that every host computes the same decision from the same answers.

**Availability is a fact, never an error.** The key comes from the `TYPESAFE_API_KEY` environment variable at call time. No key, `judge.enabled=false`, a transport failure after the retry budget, a non-2xx response, or an answer missing any option the preset sent all produce `available: false` with a named reason and exit 0. The caller then takes its pre-existing path. The command never guesses an answer, never logs the key, and never writes state or answers anywhere itself; the calling skill records what it used in the stage line it already writes.

**Three presets, three call sites.**

| Preset | Question | Decision rule | Fallback when unavailable |
|---|---|---|---|
| `clean-review` | Choice over `clean` / `findings` / `wrapper_or_status` for one automated review body | `clean` at confidence >= 0.7 counts as a clean review; anything else does not | `land.cleanReviewCommentPattern` regex, unchanged |
| `qa-gate` | Noul "do the acceptance criteria describe behaviour observable in a user-facing UI?" with the startable-target fact supplied by code in the state | UI-observable at >= 0.5 AND startable target present => QA runs; otherwise `skipped(...)` with the failing half named | Today's host judgment |
| `fork-gate` | Noul "does the text pose a design or behaviour fork with two named alternatives?", then Choice `observable` / `product_or_preference` / `none_of_the_above` | Fork present at >= 0.5 else no fork (never a question); classification at >= 0.5 else fall to the host | Today's host judgment |

**Where they plug in.** Land's review-signal gate (the section that reads `cleanReviewCommentPattern`) asks `clean-review` per automated review body before the regex. Flow's QA decision under `pipeline.qa=auto` asks `qa-gate` after code resolves the startable target (a documented start command, a deploy URL, or the features map). Prototype-before-ask, wherever flow or a routed skill classifies a fork, asks `fork-gate` before it decides to ask the user.

**Config.** One new key, `judge.enabled` (boolean, default `true`), so a repo with a keyed environment can still turn the judge off. The key's presence is the switch; the published config schema gains the key. No model selector: the model is `jev-latest`, a preset constant.

## API Contracts
<!-- scope: technical -->

Command output (the fields shown are the contract):

```json
{
  "success": true,
  "available": true,
  "preset": "clean-review",
  "model": "jev-1.13.0",
  "decision": {"value": "clean", "rule": "choice=clean and confidence>=0.7", "met": true},
  "answers": {"kind": {"type": "choice", "choice": "clean", "confidence": 0.91, "probabilities": {"clean": 0.93, "findings": 0.02, "wrapper_or_status": 0.05}}},
  "latency_ms": 612,
  "usage": {"input_tokens": 590, "output_tokens": 40}
}
```

Unavailable output:

```json
{"success": true, "available": false, "preset": "clean-review", "reason": "no_key"}
```

`reason` is one of `no_key`, `disabled`, `http_<status>`, `transport`, `timeout`, `bad_answer`, `over_budget`. `decision.value` is absent when `available` is false. Stage lines written by the callers carry the source and the number they acted on, one of:

```
clean-review: jev(clean 0.91) | regex | jev-unavailable(no_key)->regex
stage: qa - skipped(config: pipeline.qa=auto: no UI-observable criteria (jev 0.12)) | ran (jev ui 0.84, target: <cmd>)
fork-gate: none (jev 0.08) | observable (jev 0.77) | preference (jev 0.71) | host (jev below floor)
```

Retry: two retries on HTTP 429 and 529 with 1 s then 2 s backoff; no retry on anything else. Timeout 10 s per request. State over the request budget (about 32k tokens; the command estimates from character count) returns `over_budget` rather than truncating silently.

## Edge Cases & Constraints
<!-- scope: technical -->

- **The key never persists.** Read from the environment at call time only; never echoed, never in receipts, stage lines, JSON output, logs, or commits. A preset or caller that writes it has broken this.
- **Never a gate skip by prediction.** The three presets classify an existing artifact (a review body, acceptance criteria, an intent text). None predicts a review, QA, or land verdict; that use was falsified in fn-246 and is out of scope.
- **Fail closed to today's behaviour.** Every unavailable reason yields the pre-existing path, byte-identical to a keyless run, and the stage line names the reason. Silence is the failure mode this rule forbids.
- **Presets are versioned in code.** Option ids and instruction text are the contract the evaluation was run against; changing either is a change to the numbers of record and needs a re-run noted in the spec that changes it.
- **Windows stdout is cp1252.** Command output is ASCII only.
- **Cross-host parity.** The Codex mirror and the OpenCode manifest carry the same call sites; a host without the key behaves as today. The smoke scripts that copy flowctl alone must keep passing, which is why the registry is in flowctl and not a template file.
- **Land's null-vs-empty asymmetry** for `cleanReviewCommentPattern` is untouched: the judge runs before the regex and the regex path keeps its exact semantics.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `flowctl judge --preset <name> --state-file <path> --json` sends one request with the preset's questions and the state file's JSON and returns the output shape above with the preset's decision applied. Errors: unknown preset -> non-zero exit naming the registered presets; unreadable or non-JSON state file -> non-zero exit; a state file missing a field the preset requires -> non-zero exit naming the field.
- **R2:** With no `TYPESAFE_API_KEY`, or `judge.enabled=false`, the command returns `available: false` with `reason` `no_key` or `disabled`, exit 0, and sends nothing. Errors: no error surface beyond the reason field.
- **R3:** HTTP 429 and 529 are retried twice (1 s, 2 s); any other non-2xx, a transport error, or a timeout after the budget returns `available: false` with the matching reason; a 2xx whose answers omit any question id or any option the preset sent returns `bad_answer`. Errors: none beyond those reasons; the command never fabricates an answer.
- **R4:** The key appears in no output, receipt, stage line, or log under any path, including error paths. Errors: a unit test asserts the bearer value is absent from stdout, stderr, and every file the run writes.
- **R5:** Land asks `clean-review` for each automated review body before the regex; `clean` at confidence >= 0.7 is a clean review, anything else is not, and unavailable falls to the regex. The land report and ledger carry the `clean-review:` line above. Errors: an unavailable call never blocks the tick and never changes the regex outcome.
- **R6:** Under `pipeline.qa=auto`, flow resolves the startable target in code (documented start command, deploy URL, or features map), then asks `qa-gate`; QA runs only when UI-observable >= 0.5 and a target exists, and the skip line names the failing half with the Jev number. Errors: unavailable falls to today's host judgment and the skip line says so; `pipeline.qa` values other than `auto` never call the judge.
- **R7:** Prototype-before-ask classification asks `fork-gate` first; below 0.5 on fork-present there is no fork and no question; at or above, the Choice at >= 0.5 decides observable vs preference and below the floor the host decides. Errors: unavailable falls to today's judgment; under any autonomy marker a preference fork still stops with `NEEDS_HUMAN` as today.
- **R8:** `judge.enabled` exists in the config schema (boolean, default true) and `flowctl config get judge.enabled` reports it. Errors: a non-boolean value is treated as true with a warning, never a failing tick.
- **R9:** Unit tests cover R1-R4 with a stubbed HTTP layer (no network), and the three call sites are exercised by their existing smoke scripts with the key absent (byte-identical to today's output). Errors: none beyond the tests themselves.
- **R10:** Docs: a `judge` page in the plugin docs (what it is, the three presets, the fallback rule, the key, the cost and latency numbers of record from fn-246, the doc links above), the land, gate-selection, and prototype-before-ask references updated at their call sites, the config schema page and the flowctl reference updated. Errors: none beyond the docs build.

## Boundaries
<!-- scope: business -->

- No SDK dependency; the HTTP call is stdlib. No model selector, no per-preset config knobs beyond `judge.enabled`.
- Route assist (kind Choice plus anchored Nouls for `flow --auto` and `--explain`), memory rerank, and tier routing are separate specs, each gated as recorded in fn-246.
- No verdict prediction for review, QA, or land. No shadow logging.
- No change to the regex semantics, the QA skill's own contract, or the prototype-before-ask question budget (still at most one question per hop).
- No key management: the environment variable is the user's to set; setup prints one line saying the judge is off when the key is absent and nothing more.

## Decision Context
<!-- scope: both -->

- **Why plumbing in flowctl.** Three skills would otherwise carry the same curl, retry, validation, and fallback logic, on five hosts. The strategy's burden-of-proof rule for flowctl is met: transport, schema validation, and a stated decision rule are zero-judgment operations that must behave identically with no agent in the loop, and cross-host determinism is the point of the judge. The judgment (what the answer means for the stage) stays in each skill's contract.
- **Why the key is the switch.** The strategy's zero-dependency and no-external-service contract holds for the base install; an opt-in convenience may carry a prerequisite, and absence must be byte-identical to today. A config default of on with the key absent is off in practice and needs no install step.
- **Why these three first.** Each classifies an artifact that exists, cleared its majority baseline with the evidence it has, and has a fallback that is today's behaviour. Clean-review 100/100 against an eyeball label with the regex at 5/12; QA gate 0.88 against 0.71 once code supplied the startable fact; fork gate 0.88 against 0.76 with invented forks down from 12 to 1.
- **Why floors of 0.7 and 0.5.** The confidence page's stakes rule: clean-review can let a PR merge, so it takes the higher floor; the QA and fork decisions fall back to today's behaviour on a miss, so 0.5 is the sweep's balance point. Both are constants in the presets, not config.
- **Rejected:** a Noul for clean-review (0.69 against a 0.88 baseline; the wrapper and stale-marker bodies read as clean), a separate preset file (smoke scripts copy flowctl alone), the Python SDK (one HTTP call), and shadow logging (the evaluation already ran).
