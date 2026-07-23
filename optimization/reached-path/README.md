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

Where the host exposes loader traces (Claude `stream-json` Read `tool_use`),
required reads must appear and cold forbidden reads must not. When a host cannot
expose a precise loader trace (notably Cursor today), record that limitation
honestly — never fabricate a pass. See `deferrals.md` for host evidence
boundaries and non-target skill / open-spec (fn-129 / fn-122 / fn-61 / fn-73)
deferrals.

## Layout

| Path | Role |
|---|---|
| `character.py` | Frozen LF / full-file-on-activation / path+hash algorithm |
| `ratchet.py` | Keep/discard + borderline/subjective + lineage fail-closed |
| `privacy.py` | Scrubs + answer-key separation helper |
| `isolation.py` | Arena, sentinel, auth/leak probes, Claude flags |
| `trace.py` | Parse stream-json Read activations |
| `inventory.py` | Declarative B0 fixture inventory |
| `run_eval.py` | CLI: self-test / freeze / validate / production-path smoke |
| `fixtures/b0/` | Sanitized frozen manifests + `INDEX.json` |
| `fixtures/synthetic/` | Subject skill for the Claude production-path smoke |
| `runs/b0-production-path-smoke.json` | Sanitized retained Claude proof |
| `deferrals.md` | Non-target skills + open-spec overlaps |

## Run

```bash
# Offline deterministic proofs (also wired into CI via test_reached_path_harness.py)
python3 optimization/reached-path/run_eval.py --self-test

# Freeze / re-freeze B0 manifests from inventory + live prompt hashes
python3 optimization/reached-path/run_eval.py --freeze-b0
python3 optimization/reached-path/run_eval.py --validate-b0

# Authenticated Claude production-path smoke (active read + cold non-read)
python3 optimization/reached-path/run_eval.py --production-path-smoke --backend claude

# Validate all B0 + smoke when Claude available
python3 optimization/reached-path/run_eval.py --all --backend claude
```

## Resume procedure

1. Read this README + `deferrals.md` + `fixtures/b0/INDEX.json`.
2. Confirm `HEAD` prompt hashes still match B0 (or, after 130.2, B1) via
   `--validate-b0` / lineage checks — fail closed on drift.
3. Mutate **one** cluster router/reference set.
4. Re-run the cluster's fixtures (paired N≥2 on borderline; majority N=3–5 on
   subjective). Keep only on ratchet pass; log keep **and** discard.
5. Regenerate Codex mirror (`./scripts/sync-codex.sh` twice) with any canonical
   skill change — not required for this foundation task (no skill edits).

## Out of scope here

- Canonical skill prompt edits (start at task 130.2).
- Repairing the inherited Prime agentic 0/6 synthetic threshold (task 130.5).
- Version manifest bumps / release.
