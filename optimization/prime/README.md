# Prime judgment-layer agentic eval (fn-92.11)

A **NON-CI** agentic eval harness for the `/flow-next:prime` **Phase-0.5 judgment
layer**. The deterministic emitter (`flowctl prime classify --json`) decides axes
1-4 mechanically and is covered by the CI unit suite
([`plugins/flow-next/tests/test_prime_eval.py`](../../plugins/flow-next/tests/test_prime_eval.py)).
This harness covers the part CI cannot: the **judgment** a model applies on top of
the raw signals - the Axis-5 delivery shape, the per-axis confidence, the
would-ask discipline, and the playbook selection. Prose contract-tests never
prove judgment (the round-2 finding); this harness is the judgment oracle.

It follows the [`optimization/review-prompt/`](../review-prompt/) precedent:
committed ground-truth corpus + a real backend in the loop + a deterministic
scorer + a documented blocking threshold. It is **never** wired into the unittest
suite - the suite stays green and unaware of it.

## What it does

For each fixture family the runner:

1. Assembles a prompt = [`classification.md`](../../plugins/flow-next/skills/flow-next-prime/classification.md)
   judgment rules (embedded verbatim) + the emitter JSON for that fixture + a
   bounded fixture file listing.
2. Sends it to a backend (`claude -p` headless; `codex exec` fallback) under
   **enforced isolation** (below), asking for a single JSON object: five axes +
   per-axis confidence + `would_ask` list + `playbook`.
3. Scores the structured output against the expectation rows in
   [`expectations.json`](expectations.json) with a **deterministic** scorer (no
   model in the scoring path).
4. Writes a provenance-stamped result to `results/<fixture>-<model>-<date>.json`.

## Run

```bash
# Task-9 entry point (pinned name):
python3 optimization/prime/run_agentic_eval.py --all

# One family:
python3 optimization/prime/run_agentic_eval.py --fixture greenfield

# Offline isolation proof (NO model, deterministic):
python3 optimization/prime/run_agentic_eval.py --self-test

# Pick a backend / model explicitly:
python3 optimization/prime/run_agentic_eval.py --all --backend codex --model gpt-5.6-terra
```

Env: `PRIME_EVAL_MODEL` (default `sonnet`), `PRIME_EVAL_TIMEOUT` (default 180s).
Backend order under `--backend auto`: `claude`, then `codex`.

**Backend unavailable = SKIP, never fail.** If neither `claude` nor `codex` is on
`PATH` (or a chosen backend is missing), the runner prints a SKIP note and exits
0. Before any Claude fixture is scored, the runner executes an OAuth auth
preflight and an instruction-leak probe. An unavailable/expired credential,
zero-token response, or failed leak probe is recorded as `INVALID/SKIP` and exits
0 — it is never scored as model judgment.

Pure stdlib. No third-party deps.

## Fixtures (committed sanitized projections)

The six classification fixture families are the same families the CI oracle
builds; here they are captured as **sanitized metadata snapshots** committed under
[`fixtures/`](fixtures/), so the eval never depends on a live repo or a CI path.
Regenerate them with [`gen_fixtures.py`](gen_fixtures.py) (a self-contained copy of
the CI builders):

```bash
python3 optimization/prime/gen_fixtures.py --real-repo
```

| Fixture | Judgment under test |
|---|---|
| `workspace-parent` | >20-git-dir workspace dampener suppresses auto-confirm; prefix family still routes to a would-ask |
| `tier-a-siblings` | tier-a LIKELY (shared org + prefix) routes to a would-ask, never auto-confirms |
| `tier-b-home-base` | non-git parent + parent CLAUDE.md + compose = CONFIRMED home base; home-base playbook |
| `greenfield` | fresh repo -> greenfield bootstrap playbook, no constellation |
| `greenfield-x-constellation` | greenfield AND a sibling co-fire: bootstrap + a constellation would-ask |
| `worktree-sibling` | **negative control** - a worktree of the same repo is excluded; must NOT invent a constellation |
| `real-repo-flow-next` | example real-repo baseline (soft): brownfield + repository scope |

### Sanitized-snapshot format (real-repo baselines)

Each `fixtures/*.json` is a projection, never a live path:

```json
{
  "family": "<name>",
  "note": "<what this projection is + the safety contract>",
  "emitter": { ...verbatim `flowctl prime classify --json`... },
  "file_listing": ["<bounded, relative, tool-dirs-excluded>", ...]
}
```

Real-repo baselines are generated from a real checkout via the emitter and are
**safe to commit** on two independent grounds: (1) the emitter's redaction
contract is key-names-only (never secret values or complete sensitive config
lines), and (2) `gen_fixtures.py` additionally rewrites every home/absolute/temp
path in the payload to a stable placeholder (`<redacted-path>`, `<fixture-root>`).
`real-repo-flow-next.json` is the worked example, generated from this repo.

## Rubric (deterministic scorer)

Expectations live in [`expectations.json`](expectations.json), one row per family,
as data. Each active predicate is one deterministic check against the model's
structured output:

- `assessment_scope` - exact match (`repository` / `workspace-member` / `constellation-home-base`).
- `lifecycle` - exact match.
- `constellation_member` - exact boolean (a CONFIRMED member, not a would-ask).
- `would_ask_constellation` - a constellation/sibling clarification MUST (or MUST
  NOT) appear in `would_ask` (keyword match). This encodes the Phase-0.6
  discipline: ask only what changes a playbook/verdict and is not already
  answered.
- `playbook` - the chosen playbook must be in the family's acceptable set.

A family **passes** iff every active predicate passes. Predicates set to `null`
are skipped (e.g. `real-repo-flow-next` checks only scope + lifecycle; a live
workspace legitimately surfaces many asks, so would-ask/playbook are left free).

Because the six synthetic fixtures are 1-commit repos, `lifecycle` is `greenfield`
across them; the discriminating signal is the **topology/constellation reasoning +
would-ask discipline + the worktree negative control**, which is exactly the axis
that caused most misfires in the spec's eval passes.

## Blocking threshold (consumed by task 9)

`--all` computes and prints a blocking-threshold block. Ship is blocked unless:

- **every negative-control family passes** (`worktree-sibling` must not invent a
  constellation), AND
- **>= 5 of the 6 synthetic families pass**, AND
- **all synthetic families actually ran** (none dropped to `no_output`).

`real-repo-flow-next` is a **soft baseline** and does not count toward the block.
When a backend ran and the threshold is not met, `--all` exits non-zero (so task 9
can gate on it). A skip (no backend) exits 0 and never blocks. A single
`--fixture` run is exploratory and never returns non-zero on the threshold.

## Provenance

Every result file records, under `provenance`:

```json
{
  "backend": "claude | codex",
  "model": "<model alias/id passed to the backend>",
  "backend_version": "<`claude --version` / `codex --version`>",
  "date_utc": "YYYYMMDD",
  "timeout_s": 180,
  "retries": 1
}
```

The result filename `<fixture>-<model>-<date>.json` also carries model + date.
Result files are run artifacts, not source: `results/` is gitignored except its
`.gitkeep`.

fn-130 completion evidence is the deliberate exception: authenticated B1 and
candidate artifacts are retained under
[`evidence/fn130/`](evidence/fn130/README.md), including scrubbed preflights,
source hashes, nonzero usage, per-fixture outcomes, and isolation reports.

## Enforced isolation (not merely asserted)

A same-user subprocess with no OS sandbox can, in principle, write anywhere it can
name - the harness does **not** pretend otherwise. Its guarantees are layered:

1. **No capability.** The backend is invoked with **no tools / a read-only
   sandbox flag** - `claude -p --permission-mode plan --allowedTools "" --disallowedTools Bash Edit Write Read WebFetch WebSearch`,
   or `codex exec -s read-only`. The prompt is fully self-contained (rules text +
   JSON inline), so the model never needs to read a file to answer.
2. **Throwaway arena.** The backend runs with `cwd` = a fresh temp dir containing
   only the copied projection - never a live checkout path.
3. **OAuth-preserving Claude isolation.** Claude keeps the authenticated default
   config and process environment so keychain refresh works, explicitly removes
   `CLAUDE_CONFIG_DIR`, and limits instruction sources with
   `--setting-sources project,local --no-session-persistence`. A fresh config dir
   and `--bare` are forbidden because both break OAuth. Codex and offline mock
   runs keep the minimal rebuilt environment.
4. **Non-disclosure.** The out-of-arena sentinel's path is never placed in the
   prompt or the env.
5. **Timeout + process-group kill.** Explicit timeout; on expiry the whole process
   group is `SIGTERM`/`SIGKILL`ed (never bare `timeout(1)`, absent on stock macOS).
6. **Detection tripwire.** After every run: a filesystem-diff over the arena, plus
   an out-of-arena sentinel (content hash) and an output token-scan. Any breach sets
   `isolation.clean = false` so a breached run is never trusted.
7. **macOS hard containment.** Where `sandbox-exec` is available, the invocation is
   wrapped in a `deny file-read*/file-write*` rule scoped to the sentinel tree,
   giving OS-enforced containment on top of the tripwire. Degrades gracefully to
   tripwire + native flag elsewhere.

`--self-test` proves the offline isolation layers, with no model: it uses a hostile mock
backend to show (a) the tripwire detects a real breach, (b) macOS `sandbox-exec`
hard-blocks the same breach, (c) the filesystem-diff actually fires on an in-arena
write, and (d) neither the mock env nor the prompt carries a live-repo path. The
live Claude auth/leak probes separately prove the default-config isolation path.

## Reached-path routing ratchet (fn-130.5)

The version-adjusted Prime B1 input was verified before mutation:

```text
OK: prime inputs match B1 (8 files)
```

[`fixtures/routes/modes.json`](fixtures/routes/modes.json) records the four
candidate routes with separate required/forbidden reads and deterministic
LF/full-file/once-per-path-hash measurements. `--classify-only` now routes from
the root directly to `classification.md`, avoiding the full workflow and reducing
the reached path from 96,190 to 32,759 characters (65.94%). Report-only remains
no-write and never reaches remediation templates. Full/no-fix and full/fix retain
their consuming references and are also smaller than B1 because redundant root
phase summaries were removed.

The structural candidate was evaluated only after the repaired current-main
baseline passed all seven judgment fixtures, including the worktree-sibling
negative control (6/6 synthetic, threshold requires at least 5/6).

## Method

Same rules as the review-prompt harness: baseline -> one small change to the
judgment rules / prompt -> `--all` -> compare pass counts -> keep only if it lifts
the pass rate without regressing the negative control. The fixtures + scorer +
blocking threshold are the reusable scaffold; the rules under test evolve.
