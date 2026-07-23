# Reached-path skill prompt optimization harness (fn-130)

Production-path measurement + autoresearch substrate for **reached-path
loading**: how much instruction text a host actually activates on the branch a
user executes. Extends
[`agent_docs/optimizing-skills.md`](../../agent_docs/optimizing-skills.md),
[`optimization/worker-anchor/`](../worker-anchor/README.md),
[`optimization/review-prompt/`](../review-prompt/README.md), and the isolation
pattern in [`optimization/prime/run_agentic_eval.py`](../prime/run_agentic_eval.py).

This is **not** a new runtime command, hook, or flowctl subsystem. It does **not**
structurally edit canonical skill prompts (task 130.1 freezes `B0` only).

## Reached-path character algorithm (frozen)

Deterministic source-size measure — **never** interchangeable with backend
token, cache, or wall-time telemetry.

1. Normalize every counted prompt file to **LF** before counting Unicode characters.
2. Count the complete root `SKILL.md` **exactly once**.
3. Count the complete content of each **successfully reached** direct reference
   **exactly once**, deduplicated by normalized repo-relative path **plus**
   content hash. A host range/subset read activates the **complete** referenced
   file once (reference activation — not tool span size — is the contract).
4. **Exclude** failed reads, repeated reads, catalog metadata, tool output, and
   host-injected text.
5. For **Codex** fixtures, count the actual regenerated mirror files under
   `plugins/flow-next/codex/`, not canonical proxies.
6. Retain **raw trace spans** separately from this calculation (`raw_trace_spans`).

Directory totals are not a token claim. `chars/4` is the token-equivalent of the
deterministic character count only.

## Baseline lineage

| Stage | Owner | Rule |
|---|---|---|
| **B0** | task 130.1 (this harness) | Immutable original-main evidence at commit `1e8d3a95cf12cf1f33fa5c6c7ee50e0998e04e4b`. |
| **V1/B1** | task 130.2 | Fleet version mutation only; hash-addressed structural baseline. |
| **candidate** | tasks 130.3–130.9, 130.11, 130.12 | Compare **only** to `B1`. Fail closed on input hash mismatch. Never compare a structural candidate directly to `B0`. |

## Manifest contract

Each frozen fixture under `fixtures/b0/<cluster>/` carries:

- `fixture_id`, sanitized `branch_inputs` (host, activation form, args, config)
- `required_reads` / `forbidden_reads` (repo-relative direct references)
- `prompt_hashes` + `fixture_hash`
- binary `oracles` for output / tools / writes / receipts (answer keys stay here —
  **never** in subject-visible fixture prose)
- optional `mutation_targets` for later-task expectations (never the B0 answer key)
- `metrics.reached_path_chars` + `metrics.reached_path_chars_div_4` (deterministic)
- `metrics.backend_telemetry` (separate; may be null on freeze)
- `provenance.capture_kind`: `deterministic_freeze` (inventory hash-only; model/cli
  null by design) or `backend_run` (real host/model/CLI telemetry)
- `ratchet` + `privacy` + `resume` lineage
- subjective policy: borderline paired **N≥2**; subjective majority **N=3–5**;
  flat or noisy ⇒ **discard**

Clusters covered at B0: **Version, Setup, Tracker Sync, Prime, Plan Review,
Plan, Work, Strategy, Make PR, Pilot, cross-host**.

## Ratchet

Keep only when every accuracy/coverage/negative-control cell meets or exceeds
baseline **and** at least one predeclared efficiency or quality measure
improves. A flat result is discard, not a win. Every keep **and** discard is
retained in `agent_docs/optimization-log.md`.

## Privacy, isolation, auth

- Scrub emails, tokens, private home paths, sentinel values before commit
  (`privacy.py`).
- Disposable arena + filesystem diff + out-of-arena sentinel
  (`isolation.py` — same tripwire shape as the Prime agentic harness).
  Any create/remove/modify inside the arena after the pre-snapshot makes the
  run unclean and `isolation_breached` (unplanned side effects), in addition to
  sentinel modify/delete/leak.
- Instruction-leak probe + auth probe. Auth uses Claude ``--output-format json``;
  **zero total input/output/cache usage ⇒ invalid run**
  (``zero_token_auth_failure``), not a failed model judgment.
  Positive backend ``usage`` + ``modelUsage`` and an exact successful result are
  required for ``ok``.
- **No live tracker calls.** Fake transports only.
- Claude OAuth isolation: authenticated **default** config +
  `--setting-sources project,local` + `--no-session-persistence`.
  Live Claude runs inherit the process env (keychain refresh) via `claude_env()`
  and strip any `CLAUDE_CONFIG_DIR` override. **Do not** use a fresh config dir
  or `--bare` (both break OAuth — see
  `.flow/memory/bug/integration/claude-p-clean-room-on-oauth-logins-2026-07-16.md`).
  Offline self-tests may use a stripped `minimal_env()` for mock backends only.

## Production-path tracing

Where the host exposes loader traces (Claude `stream-json` Read `tool_use` +
matching completed `tool_result`), required reads must appear and cold forbidden
reads must not. A Read activation counts only when correlated by `tool_use_id`
to a non-error `tool_result`; unpaired / truncated uses and `is_error` results
do not inflate reached-path metrics. When a host cannot expose a precise loader
trace (notably Cursor today), record that limitation honestly — never fabricate
a pass. See `deferrals.md` for host evidence boundaries and non-target skill /
open-spec (fn-129 / fn-122 / fn-61 / fn-73) deferrals.

## Layout

| Path | Role |
|---|---|
| `character.py` | Frozen LF / full-file-on-activation / path+hash algorithm |
| `ratchet.py` | Keep/discard + borderline/subjective + lineage fail-closed |
| `privacy.py` | Scrubs + answer-key separation helper |
| `isolation.py` | Arena, sentinel, auth/leak probes, Claude flags |
| `trace.py` | Parse stream-json Read activations |
| `inventory.py` | Declarative B0 fixture inventory + frozen B1 source commit |
| `run_eval.py` | CLI: self-test / B0+B1 freeze/validate/input checks / production-path smoke |
| `plan_review_candidate.py` | fn-130.6 selected-backend route traces + production plan-prompt corpus checks |
| `fixtures/b0/` | Sanitized frozen manifests + `INDEX.json` |
| `fixtures/b1/` | Post-version V1/B1 manifests + structural input hashes |
| `fixtures/synthetic/` | Subject skill for the Claude production-path smoke |
| `runs/b0-production-path-smoke.json` | Write-once tracked B0 Claude proof (immutable) |
| `runs/plan-review-candidate.json` | fn-130.6 B1→candidate route/corpus ratchet evidence |
| `runs/candidates/` | Ignored timestamped candidate smoke evidence (ordinary runs) |
| `deferrals.md` | Non-target skills + open-spec overlaps |

## Run

```bash
# Offline deterministic proofs (also wired into CI via test_reached_path_harness.py)
python3 optimization/reached-path/run_eval.py --self-test

# B0 manifests are already frozen under fixtures/b0/. --freeze-b0 is
# bootstrap-only: writes only when the output dir is absent/empty. Usable from
# any HEAD — every counted prompt byte is fully materialized via
# `git show BASELINE_COMMIT:<path>` before any output write (never hashed from
# the live worktree). Refuses any nonempty target (even if INDEX.json was deleted).
# Do not check out the pre-harness baseline commit to bootstrap.
# python3 optimization/reached-path/run_eval.py --freeze-b0
python3 optimization/reached-path/run_eval.py --validate-b0

# V1/B1 is already frozen from the committed fleet-version mutation.
python3 optimization/reached-path/run_eval.py --validate-b1
python3 optimization/reached-path/run_eval.py --check-b1-input plan

# Ordinary authenticated Claude production-path smoke → ignored candidate under
# runs/candidates/<UTC µs>-production-path-smoke-<status>.json (never touches
# the tracked B0 proof, including on auth/leak/backend failure).
python3 optimization/reached-path/run_eval.py --production-path-smoke

# One-time initial tracked proof (exclusive create; refuse if already present).
# Pass → runs/b0-production-path-smoke.json; failure → candidate only.
# python3 optimization/reached-path/run_eval.py --freeze-b0-smoke

# Validate all B0 + ordinary candidate smoke when Claude available
python3 optimization/reached-path/run_eval.py --all --backend claude
```

## Resume procedure

1. Read this README + `deferrals.md` + `fixtures/b0/INDEX.json`.
2. Validate immutable evidence with `--validate-b0` and `--validate-b1`, then
   confirm the target cluster's live inputs with `--check-b1-input <cluster>`.
   The last command fails closed on drift before a structural mutation starts.
3. Mutate **one** cluster router/reference set.
4. Re-run the cluster's fixtures (paired N≥2 on borderline; majority N=3–5 on
   subjective). Keep only on ratchet pass; log keep **and** discard.
5. Regenerate Codex mirror (`./scripts/sync-codex.sh` twice) with any canonical
   skill change — not required for this foundation task (no skill edits).

## Out of scope here

- Canonical skill prompt edits (start at task 130.2).
- Repairing the inherited Prime agentic 0/6 synthetic threshold (task 130.5).
- Version manifest bumps / release.
