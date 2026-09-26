# Worker anchor bundle - fn-74-cursor-review-backend-cursor-agent-cli.2 (spec fn-74-cursor-review-backend-cursor-agent-cli)

Each section is the verbatim output of the command it is labeled with, in fixed order, untruncated. The bundle is a floor, not a ceiling - memory keyword-search and every further read remain available.

===== [1/11] task_show: `flowctl show fn-74-cursor-review-backend-cursor-agent-cli.2 --json` =====
{
  "success": true,
  "assignee": null,
  "claim_note": "",
  "claimed_at": null,
  "created_at": "2026-06-29T11:35:58.977661Z",
  "depends_on": [
    "fn-74-cursor-review-backend-cursor-agent-cli.1"
  ],
  "id": "fn-74-cursor-review-backend-cursor-agent-cli.2",
  "priority": null,
  "spec": "fn-74-cursor-review-backend-cursor-agent-cli",
  "spec_path": ".flow/tasks/fn-74-cursor-review-backend-cursor-agent-cli.2.md",
  "status": "done",
  "title": "cursor review commands \u2014 impl/plan/completion/validate/deep handlers + dispatch + mode:cursor receipts",
  "updated_at": "2026-06-29T11:44:49.743310Z",
  "impl": null,
  "review": null,
  "sync": null,
  "status_source": "committed"
}

===== [2/11] task_md: `flowctl cat fn-74-cursor-review-backend-cursor-agent-cli.2` =====
---
satisfies: [R5, R6, R7, R8, R11, R14]
---

## Description

Wire `cursor` into the five review commands, on top of the foundation from task .1. Add the `impl-review` / `plan-review` / `completion-review` / `validate` / `deep-pass` subcommands + `cmd_cursor_*` handlers (mirroring `cmd_copilot_*`), the `elif backend == "cursor"` branches in the shared validator/deep dispatchers, and **own-mode** `mode: "cursor"` receipts — NOT a copilot clone: each receipt mode-guard must accept `cursor`, and session resume must fire only when the prior receipt's `mode == "cursor"`. This task owns the **clean-tree integration check (R8)** because only a real review (not .1's mocked unit tests) can prove it.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (+ handler/dispatch tests, + an optional live integration test)

## Approach

- Add 5 subcommands to the cursor subparser (mirror the copilot block): `impl-review`, `plan-review`, `completion-review`, `validate`, `deep-pass`. **Only these six (with `check` from .1)** — NOT `classify-result`/`rollback-plan` (codex-only).
- Add `cmd_cursor_impl_review` / `_plan_review` / `_completion_review`, routing validate + deep-pass through the shared dispatchers via new `elif backend == "cursor"` branches.
- Receipts: `mode: "cursor"`, `spec: "cursor:<model>"`, `model: <model>`, **no `effort` key**. Carry copilot's rigor field set — confidence/classification rubric injection, suppressed-count, introduced-vs-pre_existing, unaddressed-R-ID, protected-path filtering (R14).
- The three review handlers' `mode == "copilot"` receipt guards are **cross-backend confusion checks** — give cursor its own-mode acceptance (resume only when prior receipt `mode == "cursor"`; cross-backend receipt ⇒ fresh session) (R7).
- **R8 clean-tree:** add an **optional live integration test** gated on `cursor-agent` availability — run a real `cursor impl-review` against a temp git repo and assert `git status` is identical before/after; skip cleanly when the CLI is absent (never a mocked clean-tree claim). The `--mode ask` flag (asserted in .1) is what guarantees it.
- **Do NOT add cursor to the triage LLM judge** (`--backend choices=["codex","copilot"]`) — per spec §8 it stays codex|copilot; cursor reviews use the deterministic whitelist by default.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:25950-26062` — copilot subparser subcommands (impl/plan/completion/validate/deep-pass) — the template
- `plugins/flow-next/scripts/flowctl.py:22372`,`:22603`,`:22778`,`:19308`,`:19978` — `cmd_copilot_impl_review` / `_plan_review` / `_completion_review` / `_validate` / `_deep_pass`
- `plugins/flow-next/scripts/flowctl.py:19212`,`:19233` — validator-pass `backend == codex`/`copilot` dispatch (add `cursor`)
- `plugins/flow-next/scripts/flowctl.py:19869`,`:19890` — deep-pass dispatch (add `cursor`)
- `plugins/flow-next/scripts/flowctl.py:22481`,`:22687`,`:22870` — receipt `mode == "copilot"` guards (own-mode pattern)
- `run_cursor_exec` from task .1

## Key context

Session-resume pitfall (memory `drop-receipt-to-break-codex`): a stuck/hallucinated review must be re-invokable fresh by dropping the receipt — the `mode == "cursor"` resume guard is what enables that. Resume is resume-only (cursor generates the id; never fabricate a first-call `--resume`).

## Acceptance

- [ ] `flowctl cursor impl-review <task> --base <b> --receipt <r>` writes a `mode:"cursor"` receipt (no `effort` key) and prints `VERDICT=...` (R5)
- [ ] `cursor plan-review` / `completion-review` / `validate` / `deep-pass` dispatch through `run_cursor_exec` and write the same additive receipt shapes as codex/copilot (`mode:"cursor"`) (R6)
- [ ] re-review resumes via `--resume <session_id>` only when the prior receipt's `mode == "cursor"`; a cross-backend receipt starts a fresh session (R7)
- [ ] optional live integration test (gated on `cursor-agent` present) runs a real `cursor impl-review` against a temp git repo and asserts `git status` unchanged; skipped when the CLI is absent (R8)
- [ ] cursor `impl-review` / `completion-review` receipts carry copilot's rigor fields (confidence anchors, suppressed counts, introduced-vs-pre_existing, unaddressed R-ID, protected-path); a parity test asserts those fields AND that `effort` is absent (R14)
- [ ] handler + dispatch tests pass; triage `--backend` choices unchanged (`codex|copilot`); full suite green (R11)

## Done summary
# fn-74.2 — cursor review commands (DONE · codex impl-review SHIP)

Wired `cursor` into the five review commands on top of the .1 foundation:
- subcommands `impl-review` / `plan-review` / `completion-review` / `validate` / `deep-pass` + `cmd_cursor_*` handlers
- `elif backend == "cursor"` branches in the shared validator/deep dispatchers
- own-mode `mode:"cursor"` receipts (no `effort` key; copilot rigor fields) + the session-resume guard (resume only when prior receipt `mode == "cursor"`, cross-backend → fresh)
- optional live clean-tree integration test gated on `cursor-agent` availability

Triage judge left at `codex|copilot` (spec §8). Recovered + finalized after a lost-worker truncation: code was committed (d5c58042); full suite + codex review re-run by the host.

**Tests:** full suite `python3 -m unittest discover -s plugins/flow-next/tests` → 1286 passed, 2 skipped.
**Review:** codex impl-review (base c9834827) → SHIP, no blocking findings.
## Evidence
- Commits: d5c58042
- Tests: python3 -m unittest discover -s plugins/flow-next/tests → 1286 passed, 2 skipped
- PRs:

===== [3/11] spec_show: `flowctl show fn-74-cursor-review-backend-cursor-agent-cli --json` =====
{
  "success": true,
  "branch_name": "fn-74-cursor-review-backend-cursor-agent-cli",
  "completion_review_status": "ship",
  "completion_reviewed_at": "2026-06-29T22:05:58.479281Z",
  "created_at": "2026-06-29T07:52:31.575647Z",
  "default_impl": null,
  "default_review": null,
  "default_sync": null,
  "depends_on_epics": [],
  "id": "fn-74-cursor-review-backend-cursor-agent-cli",
  "next_task": 1,
  "plan_review_status": "unknown",
  "plan_reviewed_at": null,
  "spec_path": ".flow/specs/fn-74-cursor-review-backend-cursor-agent-cli.md",
  "status": "done",
  "title": "Cursor review backend (cursor-agent CLI \u2014 gpt-5.5/codex/opus)",
  "updated_at": "2026-07-10T12:44:02.395308Z",
  "plan_review_rounds": 0,
  "impl_review_rounds": {},
  "tasks": [
    {
      "id": "fn-74-cursor-review-backend-cursor-agent-cli.1",
      "title": "flowctl cursor backend foundation \u2014 registry + run_cursor_exec + check + parser tests",
      "status": "done",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": []
    },
    {
      "id": "fn-74-cursor-review-backend-cursor-agent-cli.2",
      "title": "cursor review commands \u2014 impl/plan/completion/validate/deep handlers + dispatch + mode:cursor receipts",
      "status": "done",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": [
        "fn-74-cursor-review-backend-cursor-agent-cli.1"
      ]
    },
    {
      "id": "fn-74-cursor-review-backend-cursor-agent-cli.3",
      "title": "skill + setup wiring + codex mirror \u2014 workflow-cursor.md x2, --review literals, review.backend, sync-codex",
      "status": "done",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": [
        "fn-74-cursor-review-backend-cursor-agent-cli.2"
      ]
    },
    {
      "id": "fn-74-cursor-review-backend-cursor-agent-cli.4",
      "title": "docs + downstream chain \u2014 flowctl.md/README/GLOSSARY/CHANGELOG + flow-next.dev + AI-x-SDLC + GF + vault",
      "status": "done",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": [
        "fn-74-cursor-review-backend-cursor-agent-cli.3"
      ]
    }
  ],
  "ready": false,
  "no_plan": false
}

===== [4/11] spec_md: `flowctl cat fn-74-cursor-review-backend-cursor-agent-cli` =====
# fn-74 Cursor review backend (cursor-agent CLI — gpt-5.5/codex/opus)

## Goal & Context

flow-next ships three second-model **review backends** today — `rp` (RepoPrompt),
`codex` (OpenAI Codex CLI), `copilot` (GitHub Copilot CLI) — selected via the
`BACKEND_REGISTRY` in `plugins/flow-next/scripts/flowctl.py` and consumed by
`/flow-next:impl-review`, `/flow-next:plan-review`, `/flow-next:spec-completion-review`.
There is **no `cursor` backend**. Cursor is already supported as a *primary host
driver* (the `CURSOR_AGENT`/`install-cursor.sh` path in `flow-next-setup`) — a
**different integration point**, out of scope here.

Add `cursor` as a first-class review backend that shells out to the **`cursor-agent`
CLI** (installed locally, v2026.06). It unlocks Cursor-billed review (the user's
existing Cursor subscription, no separate API key) and Cursor reviewer models the
others can't reach in one place: `gpt-5.5-high` (1M ctx, the default), the
`gpt-5.3-codex` family, `composer-2.5`, `claude-opus-4-8-thinking-high`.

Parity port of the most-recent backend (`copilot`, fn-28) — no new review *features*,
no new architecture. The headless contract was verified live and the spec was then
**dogfooded through a `cursor-agent` gpt-5.5-high plan-review of itself** (see
Decision Context), which corrected the session/repo-scope/triage contracts below.

**Doc-drift this closes:** the GrowthFactors cross-model-review spec
(`~/work/code-factory-package/spec/05-cross-model-review.md`) **already advertises**
"Cursor via its `cursor-agent` headless CLI" as a supported review backend. That
claim is currently false. fn-74 makes the already-published claim true.

## Architecture & Data Models

Mirror the `copilot` backend end-to-end. Paths in
`plugins/flow-next/scripts/flowctl.py` unless noted.

**Verified `cursor-agent` contract** (probed live + dogfood plan-review):
- Invocation: `cursor-agent -p --output-format json --trust --mode ask --model <model> [--resume <session_id>] "<prompt>"`, run with **`cwd=repo_root`** (Cursor scopes to the workspace dir; without it a review launched from a subdir reads the wrong tree — copilot's `--add-dir <repo_root>` analog).
- `--mode ask` = read-only Q&A; the CLI **refuses to edit** in this mode (verified). Reviewer never mutates the tree.
- `--trust` is **mandatory** headless or the CLI blocks on a "Workspace Trust Required" prompt and hangs.
- Result JSON: `{"type":"result","subtype":"success","is_error":false,"result":"<text>","session_id":"<uuid>","usage":{...}}`. Parse `.result`, `.session_id`, `.is_error`.
- **Session model = resume-only (like copilot's Windows/stdin path, NOT its POSIX create-or-resume).** First call: **omit `--resume`**, let Cursor generate `session_id`, capture it from the result, store in the receipt. Continuation: pass `--resume <stored_session_id>`. Verified: a generated id resumes prior history non-interactively under `-p`. Never pass a caller-fabricated uuid as `--resume` on the first call.
- Auth: stored login creds OR `CURSOR_API_KEY`. `--list-models` is the source of truth for model strings; `cursor-agent --version` → `2026.06.xx-<hash>` for `check`.

**Components to add (copilot is the template):**

1. **Registry entry** — `BACKEND_REGISTRY` (~L3449). NEW shape: model accepted,
   **effort folded into the model name** (Cursor convention) so `efforts: None`:
   ```python
   "cursor": {
       "models": {"auto", "gpt-5.5-high", "gpt-5.4-high", "gpt-5.3-codex",
                  "gpt-5.3-codex-high", "gpt-5.3-codex-xhigh", "gpt-5.2",
                  "composer-2.5", "claude-opus-4-8-thinking-high",
                  "claude-opus-4-7-thinking-high"},
       "efforts": None,            # Cursor bakes reasoning effort into the model name
       "default_model": "gpt-5.5-high",
   },
   ```
   `VALID_BACKENDS` (~L3510) derives → free. **Verified: existing `BackendSpec.parse`/`.resolve` + `parse_backend_spec_lenient` handle this model-yes/effort-no shape with no parser edits.**

2. **Helpers** (mirror `require_copilot`/`get_copilot_version`/`run_copilot_exec` ~L3786-3967):
   - `require_cursor()` / `get_cursor_version()`.
   - `run_cursor_exec(prompt, session_id=None, *, spec, repo_root) -> (result_text, returned_session_id, exit_code, stderr)` — `session_id` is **optional input** (None on first call → omit `--resume`; non-None → `--resume <id>`), and the **returned** session id (parsed from `.result` JSON) is what the caller persists. Run with `cwd=repo_root`, `--trust --mode ask`, `timeout=600`; non-zero on `is_error`/timeout/CLI failure. Reuse copilot's argv-vs-temp prompt threshold (POSIX argv handles 60KB — verified).

3. **CLI subcommands** (mirror the `copilot` parser block ~L25968): a `cursor` subparser with `check`, `impl-review`, `plan-review`, `completion-review`, `validate`, `deep-pass` — same args as copilot (incl. `check --skip-probe`).

4. **Command handlers** (mirror `cmd_copilot_*` ~L22405+, and shared dispatchers `_run_validator_pass`/deep-pass at L19245 / L19902 / L23606): add `elif backend == "cursor":` branches + `cmd_cursor_*`. **Receipts must match the copilot field set** — `mode:"cursor"`, `spec:"cursor:<model>"`, `model:<model>`, **no `effort` key** (effort is invalid for cursor), plus the same confidence/classification rubric injection, suppressed-count, introduced-vs-pre_existing, unaddressed-R-ID, and protected-path handling copilot already does.

5. **Resolution plumbing** — `resolve_review_spec` (~L3691) is backend-generic. Env fill: `FLOW_CURSOR_MODEL` (no `FLOW_CURSOR_EFFORT`). The `review-backend` resolver already flows from the registry (verified: `config set review.backend` stores without a separate allowlist; resolution parses via the registry) — config/env/per-task/spec-form accept `cursor` automatically once registered.

6. **Skill wiring:**
   - `flow-next-impl-review`: new `workflow-cursor.md` (mirror `workflow-copilot.md`); add the `cursor` row to the Phase-0 dispatch table in `workflow-common.md`.
   - `flow-next-plan-review`: add a `cursor` section to `workflow.md`.
   - `flow-next-spec-completion-review`: add `cursor` to its `workflow-common.md`.
   - All three SKILL.md + their `commands/flow-next/*.md`: `--review=rp|codex|copilot|cursor|none`.

7. **Setup**: `flow-next-setup` `review.backend` config prompt/validation accepts `cursor` and spec form `cursor:gpt-5.5-high`.

8. **Triage LLM judge stays `codex|copilot`** (`--backend choices=["codex","copilot"]`, L25558 — the *opt-in* judge for ambiguous diffs, default-off behind `FLOW_TRIAGE_LLM`). Do NOT add cursor there. **Precise truth:** with the LLM judge **off (the default)** cursor reviews use the deterministic whitelist — zero extra dependency. A cursor user who opts into `FLOW_TRIAGE_LLM=1` gets the `codex` judge and therefore needs codex/copilot present — **document this, do not auto-wire a cursor judge**. (Keeping cursor out is the lean choice; the judge is a cheap separate concern.)

9. **Codex mirror**: regenerate via `scripts/sync-codex.sh` (never hand-edit `plugins/flow-next/codex/**`); install/sync parity tests stay green.

## API Contracts

- `run_cursor_exec(prompt: str, session_id: Optional[str]=None, *, spec: BackendSpec|None, repo_root: Path) -> tuple[str, str, int, str]` → `(result_text, returned_session_id, exit_code, stderr)`; `session_id=None` ⇒ first call (no `--resume`); non-zero exit on `is_error`/CLI-failure/600s timeout; always invoked with `cwd=repo_root`.
- `flowctl cursor check [--json] [--skip-probe]` → `{available, version, authed}` (schema aligned to copilot's `check`).
- `flowctl cursor impl-review <task> --base <ref> --receipt <path> [--spec cursor:<model>] [--json]`
- `flowctl cursor plan-review <spec> [--files ...] --receipt <path> [--json]`
- `flowctl cursor completion-review <spec> --receipt <path> [--json]`
- `flowctl cursor validate --findings-file <jsonl> --receipt <path> [--json]`
- `flowctl cursor deep-pass --pass <name> --primary-findings <jsonl> --receipt <path> [--json]`
- Receipt (impl): `{"type":"impl_review","id":"<id>","mode":"cursor","verdict":"SHIP|NEEDS_WORK|MAJOR_RETHINK","session_id":"<uuid>","model":"<model>","spec":"cursor:<model>","timestamp":"..."}` — **no `effort` key**; same additive validator/deep/walkthrough blocks + rigor fields as copilot.
- Spec grammar (verified): `cursor` | `cursor:<model>` valid; `cursor:<model>:<effort>` → ValueError ("does not accept an effort"); unknown model → ValueError listing valid models.

## Edge Cases & Constraints

- **NEW registry shape (model-yes / effort-no) — VERIFIED OK.** Existing parser raises on effort, resolves `default_model` with effort `None`, no KeyError. Lock with tests.
- **Session = resume-only — VERIFIED.** Caller must not fabricate a first-call `--resume` id; capture and persist Cursor's returned `session_id`, resume with it only when the receipt at the path has `mode == "cursor"` (cross-backend → fresh). Mirrors copilot's Windows path, not its POSIX path.
- **Repo scoping — REQUIRED.** `run_cursor_exec` runs with `cwd=repo_root`; add a test that invokes from a subdirectory and confirms the correct tree is reviewed.
- **`--trust` mandatory** headless or the CLI hangs on a trust prompt.
- **Read-only — VERIFIED.** `--mode ask` refused a "create a file" instruction; tree stayed clean. R8 asserts `git status` unchanged across a review.
- **Oversized prompts — VERIFIED on POSIX (60KB positional argv).** cursor-agent takes the prompt as a **positional argument** (not stdin). Up to the threshold, pass it positionally. **Above the threshold there is no safe path yet:** copilot's temp-file step just reads the file back into argv (it does NOT bypass any cap), and cursor-agent stdin support is unconfirmed → `run_cursor_exec` must raise an **explicit "prompt too large" error** above the threshold (with a test), NOT silently reuse the read-back-into-argv trick. Implement a stdin path only if cursor-agent confirms stdin input. (The Windows `CreateProcessW` cap is where this bites first.)
- **Triage precision** — see Architecture §8: deterministic by default; opt-in LLM judge stays codex/copilot and is a documented dependency for cursor users who enable it.
- **Auth not configured** → `check` and runners surface a clear error pointing at `cursor-agent` login / `CURSOR_API_KEY` (never a silent empty review).
- **`.result` empty / `is_error:true`** → backend failure (non-zero exit + stderr), never a false SHIP.
- **Effort must not leak** — copying copilot receipt code literally risks writing `effort:"high"`; cursor receipts must omit `effort` (assert in tests).
- **Model-list drift** — Cursor ships model strings without changelog (and auto-updates the CLI); document "keep synced with `cursor-agent --list-models`", copilot-style note.
- **Not the host driver.** Independent of the `CURSOR_AGENT` host-platform path; works on any host with `cursor-agent` installed.

## Acceptance Criteria

- **R1:** `cursor` is in `BACKEND_REGISTRY` and `VALID_BACKENDS`; `flowctl review-backend` reports `cursor` from `.flow/config.json` + `FLOW_REVIEW_BACKEND` (its only two sources); per-task `default_review` and `--spec cursor:<model>` resolve via `resolve_review_spec` / the review commands (NOT `review-backend`).
- **R2:** `BackendSpec.parse("cursor")` / `parse("cursor:gpt-5.5-high")` succeed; `parse("cursor:gpt-5.5-high:high")` raises (effort rejected); `parse("cursor:bogus")` raises listing valid models; `.resolve()` fills `gpt-5.5-high`, effort `None`.
- **R3:** `run_cursor_exec` shells `cursor-agent -p --output-format json --trust --mode ask --model <m>` with `cwd=repo_root`; on a first call it omits `--resume` and returns Cursor's generated `session_id`; on continuation it passes `--resume <session_id>`; parses `.result`/`.session_id`/`.is_error`; returns non-zero on a 600s timeout.
- **R4:** `flowctl cursor check [--skip-probe]` reports availability + version + auth (`authed`) in text and `--json`, schema-aligned to copilot's `check`.
- **R5:** `flowctl cursor impl-review <task> --base <b> --receipt <r>` writes a `mode:"cursor"` receipt (no `effort` key) and prints `VERDICT=...`.
- **R6:** `cursor plan-review`, `completion-review`, `validate`, `deep-pass` dispatch through `run_cursor_exec` and write the same additive receipt shapes as codex/copilot (`mode:"cursor"`).
- **R7:** Re-review with an existing `mode=="cursor"` receipt resumes via `--resume <session_id>` (using the persisted returned id); a cross-backend receipt starts fresh.
- **R8:** A cursor review leaves the working tree unchanged. Unit-level: `run_cursor_exec` is asserted to pass `--mode ask` (read-only) and never an edit/write flag. Integration-level: an **optional live smoke test gated on `cursor-agent` availability** runs a real `cursor impl-review` against a temp git repo and asserts `git status` is identical before/after (skipped when the CLI is absent — never a mocked clean-tree claim).
- **R9:** `/flow-next:impl-review` routes `BACKEND=="cursor"` to `workflow-cursor.md`; `/flow-next:plan-review` and `/flow-next:spec-completion-review` handle `cursor`; every user-facing `--review=rp|codex|copilot|none` string includes `cursor`.
- **R10:** `flow-next-setup` `review.backend` config accepts `cursor` and spec form `cursor:gpt-5.5-high`.
- **R11:** Tests: `test_cursor_run_exec.py` (mock subprocess: success / `is_error` / timeout / **first-call-omits-resume** / **resume-passes-id** / **cwd=repo_root** / **mode-ask-flag** / **prompt-too-large**), `test_backend_spec.py` cursor cases (model-yes/effort-no). Receipt-schema `mode:"cursor"` + the `effort`-absent assertion are the review-command tests (R14, task .2). Full Python suite passes.
- **R12:** `scripts/sync-codex.sh` regenerated; `cursor` surfaces in the codex mirror; install/sync parity tests pass.
- **R13:** Docs chain updated at the concrete targets below; **no version bump** (batched), entries under `## Unreleased`:
  - **Repo:** `plugins/flow-next/docs/flowctl.md` (cmd list L14 + new cursor backend section), `README.md` (L44 / L253 / L290 backend lists), `GLOSSARY.md` (L29 "Backends:" list), root `CHANGELOG.md` `## Unreleased`.
  - **flow-next.dev:** `src/content/docs/review/workflow.mdx` (flip the live "coming next release" Cursor row → shipped) + `review/receipts.mdx` + `install.mdx` backend enumeration + `releases/changelog.mdx`. **No `FLOW_NEXT_VERSION` / `package.json` bump in this spec** — the docs-site version bump is release-only (batched), same rule as the plugin. No new page → navbars unchanged. Run `pnpm build`.
  - **AI-x-SDLC:** `guides/flow-next.md` (L65 "(RepoPrompt, OpenAI Codex, GitHub Copilot)" → add Cursor), `guides/code-review-tools-changelog.md`.
  - **GrowthFactors:** `spec/05-cross-model-review.md` (claim already lists Cursor — verify/tighten), re-render `dist/gf.html` (+ `shd`/`shopfully`/`flooid`) and the bundled `~/work/AI-x-SDLC-Starter-Kit/resources/assets/code-factory-onboarding.html`.
  - **Obsidian vault:** the cross-model-review / Skills Catalog / Release Timeline note(s).
- **R14:** Cursor `impl-review` / `completion-review` receipts carry the same **rigor fields** as copilot — confidence-rubric anchors, suppressed-finding counts, introduced-vs-pre_existing classification, unaddressed-R-ID surfacing, protected-path filtering — asserted by a parity test scoped to **those rigor fields only**, which **also asserts `effort` is absent** (cursor must never write it; effort is not a cursor field).

## Boundaries

- **No new host platform** (Cursor-as-primary-driver already exists).
- **No behavior change** to `rp`/`codex`/`copilot`/`none`, or to the trivial-diff triage judge (stays `codex|copilot`).
- **CLI only.** No Cursor MCP/API/HTTP — `cursor-agent` subprocess only.
- **No new review features.** Pure parity port — same phases, receipt schema, verdict grammar.
- **No new flow-next.dev page** → both navbars untouched.
- **No version bump / release** (staged under `## Unreleased`).
- **RP-style window/session UI** not applicable — cursor is headless like codex/copilot.

## Decision Context

Cursor is the obvious fourth backend: `cursor-agent` is installed, its headless
`-p --output-format json` contract is clean (`.result` + `.session_id`), it exposes
reviewer models the others can't reach together (`gpt-5.5-high` 1M, the
`gpt-5.3-codex` family, `composer-2.5`, Opus-4.8-thinking), billed against the
Cursor subscription, and the GF cross-model-review spec already advertises it.

Chosen approach: **mirror `copilot` (fn-28) exactly**. Closest structural match —
both headless CLIs with `-p`, JSON result, session UUID, `--resume`. The only new
wrinkle is the model-yes/effort-no registry shape, which the existing parser
already handles, so it costs a test not new code.

Rejected: (a) Cursor MCP/HTTP — heavier, no upside, inconsistent; (b) reusing
`codex` since both run GPT-5.5 — different CLI/auth/billing/strings, no
Composer/Opus-via-Cursor; (c) effort-translation layer — needless; Cursor's own
strings are canonical, stored verbatim.

### Smoke-test evidence (verified live, cursor-agent v2026.06)
1. JSON contract parses (`type:result, is_error:false, result, session_id`).
2. Real review on a planted diff (`a+b`→`a-b`, missing zero-guard) found both bugs, `VERDICT=NEEDS_WORK`.
3. Read-only `--mode ask` refused a file-write; tree clean.
4. `--resume <sid>` recalled prior context headless (continuity confirmed).
5. 60KB argv prompt round-tripped on POSIX.
6. Registry-only monkeypatch made `parse`/`resolve`/lenient accept `cursor`/`cursor:<model>`, reject effort, list models — zero parser edits.

### Dogfood (this spec, reviewed by the backend it specifies)
Ran a `cursor-agent` **gpt-5.5-high** read-only plan-review of fn-74 against the
live repo (228s, ~102K input / 662K cache-read tokens). It verified the cited code
anchors and returned `VERDICT=NEEDS_WORK` with 4 valid corrections, now folded in:
(a) **session is resume-only** — capture Cursor's generated id, don't fabricate a
first-call `--resume` [R3/R7]; (b) **`cwd=repo_root` required** for repo scoping
[R3]; (c) **triage "deterministic whitelist" was imprecise** — true only with the
judge off; opt-in judge stays codex/copilot and is a documented cursor-user
dependency [§8]; (d) **receipt parity** — omit `effort`, carry copilot's rigor
fields [R14, R5, R11]. Proves the backend works end-to-end on a real spec.

Natural task seams: (1) flowctl core (registry + helpers + subcommands + handlers +
dispatch + unit tests), (2) skill/setup wiring + codex-mirror regen, (3) docs +
downstream chain.

## Plan (4 tasks)

Decomposed into 4 sequential tasks (a parity port is inherently code → wire → document); the flowctl core is split into **proof** + **commands** so each fits one `/flow-next:work` iteration.

1. **`.1` — flowctl cursor foundation** (M, no deps · **early proof**) — registry entry + `require_cursor`/`get_cursor_version`/`run_cursor_exec` + `cursor check` + parser/run-exec tests. → R1, R2, R3, R4, R11
2. **`.2` — cursor review commands** (M, deps .1) — 5 subcommands + `cmd_cursor_*` handlers + validator/deep dispatch + own-mode `mode:"cursor"` receipts (resume-guard, rigor parity, clean-tree live test). → R5, R6, R7, R8, R11, R14
3. **`.3` — skill + setup wiring + codex mirror** (M–L, deps .2) — `workflow-cursor.md` ×2 + plan-review section + `--review` literals (8 files) + setup config + `sync-codex.sh` regen. → R9, R10, R12
4. **`.4` — docs + downstream chain** (M, deps .3) — repo docs + flow-next.dev (flip the already-live "coming" Cursor row → shipped) + AI×SDLC + GF + vault. No version bump. → R13

### Early proof point
Task `.1` proves the `cursor-agent` contract end-to-end (`run_cursor_exec` + `check` + `BackendSpec` parse/resolve). Already de-risked by the spec's live smoke-tests + dogfood; if `.1` nonetheless fails, re-examine the cursor-agent CLI contract before `.2`+.

### Strategy Alignment
- **Cross-model review** — adds a fourth reviewer backend (Cursor: gpt-5.5-high / codex / composer / opus), widening the disagreement surface and letting teams bill review to an existing Cursor subscription.
- **Host agent IS the intelligence / lean flowctl** — pure parity port: a ~6-line registry entry + mirrored helpers; no new architecture, no new skill/command, no second-LLM-spawn-from-flowctl.

### Requirement coverage

| Req | Task(s) |
|-----|---------|
| R1 registry / resolve | .1 |
| R2 spec grammar (model-yes/effort-no) | .1 |
| R3 run_cursor_exec | .1 |
| R4 cursor check | .1 |
| R5 impl-review receipt mode:cursor | .2 |
| R6 plan/completion/validate/deep dispatch | .2 |
| R7 session-resume guard | .2 |
| R8 read-only / clean tree | .2 (live test) · .1 (`--mode ask` flag) |
| R9 skill routing + --review literals | .3 |
| R10 setup config | .3 |
| R11 tests | .1, .2 |
| R12 codex mirror | .3 |
| R13 docs chain | .4 |
| R14 receipt rigor parity | .2 |

### Soft sequencing note
fn-54 (eval-driven prompt optimization, 0 tasks) also edits the review `workflow*.md` files — coordinate on those edits if fn-54 activates concurrently. Not a hard dependency (spec-scout: standalone).

===== [5/11] git_status: `git status --short --branch` =====
## fn-258-smaller-default-outputs-and-bundles...origin/main [ahead 1]
 M agent_docs/adding-skills.md
 M optimization/worker-anchor/run_eval.py
 M plugins/flow-next/agents/repo-scout.md
 M plugins/flow-next/agents/spec-scout.md
 M plugins/flow-next/agents/worker.md
 M plugins/flow-next/codex/agents/repo-scout.toml
 M plugins/flow-next/codex/agents/spec-scout.toml
 M plugins/flow-next/codex/agents/worker.toml
 M plugins/flow-next/codex/docs/flow-next/flowctl.md
 M plugins/flow-next/codex/docs/flow-next/glossary.md
 M plugins/flow-next/codex/skills/flow-next-capture/workflow.md
 M plugins/flow-next/codex/skills/flow-next-features/SKILL.md
 M plugins/flow-next/codex/skills/flow-next-impl-review/workflow-codex.md
 M plugins/flow-next/codex/skills/flow-next-impl-review/workflow-host.md
 M plugins/flow-next/codex/skills/flow-next-impl-review/workflow-rp.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/SKILL.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-claude.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-codex.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-copilot.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-cursor.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-host.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-rp.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow.md
 M plugins/flow-next/codex/skills/flow-next-plan/references/selected-review.md
 M plugins/flow-next/codex/skills/flow-next-refine/references/pass-business.md
 M plugins/flow-next/codex/skills/flow-next-resolve-pr/SKILL.md
 M plugins/flow-next/codex/skills/flow-next-resolve-pr/workflow.md
 M plugins/flow-next/codex/skills/flow-next-setup/templates/agents-md-snippet.md
 M plugins/flow-next/codex/skills/flow-next-setup/templates/claude-md-snippet.md
 M plugins/flow-next/codex/skills/flow-next-setup/workflow.md
 M plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow-host.md
 M plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow-rp.md
 M plugins/flow-next/codex/skills/flow-next-tracker-sync/references/adapter-interface.md
 M plugins/flow-next/codex/skills/flow-next-tracker-sync/references/body-merge.md
 M plugins/flow-next/codex/skills/flow-next-tracker-sync/references/comments-sync.md
 M plugins/flow-next/codex/skills/flow-next-tracker-sync/references/status-sync.md
 M plugins/flow-next/codex/skills/flow-next-work/SKILL.md
 M plugins/flow-next/codex/skills/flow-next-work/phases.md
 M plugins/flow-next/codex/skills/flow-next-work/references/host-deferred-review.md
 M plugins/flow-next/codex/skills/flow-next/SKILL.md
 M plugins/flow-next/commands/audit.md
 M plugins/flow-next/commands/capture.md
 M plugins/flow-next/commands/chart.md
 M plugins/flow-next/commands/features.md
 M plugins/flow-next/commands/flow.md
 M plugins/flow-next/commands/impl-review.md
 M plugins/flow-next/commands/land.md
 M plugins/flow-next/commands/make-pr.md
 M plugins/flow-next/commands/map.md
 M plugins/flow-next/commands/memory-migrate.md
 M plugins/flow-next/commands/plan-review.md
 M plugins/flow-next/commands/plan.md
 M plugins/flow-next/commands/prime.md
 M plugins/flow-next/commands/prose.md
 M plugins/flow-next/commands/prospect.md
 M plugins/flow-next/commands/qa.md
 M plugins/flow-next/commands/ralph-init.md
 M plugins/flow-next/commands/refine.md
 M plugins/flow-next/commands/resolve-pr.md
 M plugins/flow-next/commands/setup.md
 M plugins/flow-next/commands/spec-completion-review.md
 M plugins/flow-next/commands/strategy.md
 M plugins/flow-next/commands/sync.md
 M plugins/flow-next/commands/tracker-sync.md
 M plugins/flow-next/commands/uninstall.md
 M plugins/flow-next/commands/visual.md
 M plugins/flow-next/commands/work.md
 M plugins/flow-next/docs/flowctl.md
 M plugins/flow-next/docs/glossary.md
 M plugins/flow-next/scripts/flowctl.py
 M plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json
 M plugins/flow-next/skills/flow-next-capture/workflow.md
 M plugins/flow-next/skills/flow-next-features/SKILL.md
 M plugins/flow-next/skills/flow-next-flow/auto.md
 M plugins/flow-next/skills/flow-next-flow/references/backlog-mode.md
 M plugins/flow-next/skills/flow-next-flow/references/gate-selection.md
 M plugins/flow-next/skills/flow-next-flow/references/plan-vs-no-plan.md
 M plugins/flow-next/skills/flow-next-flow/references/route-matrix.md
 M plugins/flow-next/skills/flow-next-flow/references/tail.md
 M plugins/flow-next/skills/flow-next-flow/workflow.md
 M plugins/flow-next/skills/flow-next-impl-review/workflow-codex.md
 M plugins/flow-next/skills/flow-next-impl-review/workflow-host.md
 M plugins/flow-next/skills/flow-next-impl-review/workflow-rp.md
 M plugins/flow-next/skills/flow-next-plan-review/SKILL.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-claude.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-codex.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-copilot.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-cursor.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-host.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow.md
 M plugins/flow-next/skills/flow-next-plan/references/selected-review.md
 M plugins/flow-next/skills/flow-next-refine/SKILL.md
 M plugins/flow-next/skills/flow-next-refine/references/pass-business.md
 M plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md
 M plugins/flow-next/skills/flow-next-resolve-pr/workflow.md
 M plugins/flow-next/skills/flow-next-setup/templates/agents-md-snippet.md
 M plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md
 M plugins/flow-next/skills/flow-next-setup/workflow.md
 M plugins/flow-next/skills/flow-next-spec-completion-review/workflow-host.md
 M plugins/flow-next/skills/flow-next-spec-completion-review/workflow-rp.md
 M plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md
 M plugins/flow-next/skills/flow-next-tracker-sync/references/body-merge.md
 M plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md
 M plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md
 M plugins/flow-next/skills/flow-next-work/SKILL.md
 M plugins/flow-next/skills/flow-next-work/phases.md
 M plugins/flow-next/skills/flow-next-work/references/host-deferred-review.md
 M plugins/flow-next/skills/flow-next-work/references/rolling-scheduler.md
 M plugins/flow-next/skills/flow-next-work/references/wave-join.md
 M plugins/flow-next/skills/flow-next/SKILL.md
 M plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-capture-brief.json
 M plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-chart.json
 M plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-interview.json
 M plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-skip-chart-clear.json
 M plugins/flow-next/tests/test_anchor_bundle.py
 M plugins/flow-next/tests/test_flow_merge_destination.py
 M plugins/flow-next/tests/test_parallel_work_prose.py
 M plugins/flow-next/tests/test_pilot_chain_stages.py
 M plugins/flow-next/tests/test_precheck_mode_contract.py
 M plugins/flow-next/tests/test_review_convergence_cap.py
 M plugins/flow-next/tests/test_setup_snippet_lockstep.py
 M scripts/sync-codex.sh
?? optimization/worker-anchor/gen_fn258_inputs.py
?? optimization/worker-anchor/inputs/fn-64.3/bundle-current.md
?? optimization/worker-anchor/inputs/fn-64.3/bundle-lean.md
?? optimization/worker-anchor/inputs/fn-74.2/bundle-current.md
?? plugins/flow-next/codex/skills/flow-next-tracker-sync/references/chart-subjects.md
?? plugins/flow-next/skills/flow-next-tracker-sync/references/chart-subjects.md
?? plugins/flow-next/tests/test_glossary_match.py
?? plugins/flow-next/tests/test_skill_id_invocations.py

===== [6/11] git_log: `git log -5 --oneline` =====
c13a4d52 chore(flow): record fn-258 direct route and mint the owner task
e5535836 Correctness and hygiene sweep (audit wave 3) (#472)
b4c980af Unattended-run correctness fixes (audit wave 1) (#470)
9509a2cf Test suite and CI wall-clock (audit wave 2) (#471)
b334b5d7 chore(flow-next): bump version to 6.0.2

===== [7/11] git_branch: `git rev-parse --abbrev-ref HEAD` =====
fn-258-smaller-default-outputs-and-bundles

===== [8/11] memory_enabled: `flowctl config get memory.enabled --json` =====
{
  "success": true,
  "key": "memory.enabled",
  "value": true
}

===== [9/11] glossary: `flowctl glossary list --json --match "<task title + description>"` =====
{
  "success": true,
  "groups": [
    {
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/GLOSSARY.md",
      "entries": [
        {
          "term": "Task",
          "definition": "An execution unit under a spec (`fn-N.M`), sized to one `/flow-next:work` iteration (~100k tokens of fresh context). Declares `requires:` dependencies and optionally the R-IDs it `satisfies:`. Implemented by a worker subagent, never by the conductor directly.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Spec, Wave",
          "avoid": [
            "subtask",
            "ticket",
            "issue",
            "story"
          ],
          "relates_to": [
            "Spec",
            "Wave"
          ]
        },
        {
          "term": "Chart",
          "definition": "Optional pre-capture decision mapping (`/flow-next:chart`) for one idea too large or unclear to capture in a single session: decisions (`D1`, `D2`, ...) under `.flow/charts/`, exiting as a briefing package for `/flow-next:capture`. Chart makes an effort understandable enough to plan; plan decomposes work already understood; prospect ranks plural candidate ideas. Never writes a spec, never sets `ready`.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Spec, Task",
          "avoid": [
            "discovery doc",
            "RFC",
            "design doc",
            "plan",
            "prospect"
          ],
          "relates_to": [
            "Spec",
            "Task"
          ]
        },
        {
          "term": "Receipt",
          "definition": "A JSON artefact on disk that proves a step happened and gates the next one \u2014 review receipts under `.flow/review-receipts/`, green receipts under `.flow/tmp/green-receipts/`, QA verdict receipts. A receipt is a file; a verdict is the terminal line a loop skill prints into the transcript for its driver (`PILOT_VERDICT=`, `LAND_VERDICT=`). Never use one word for the other.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Gate, Review backend",
          "avoid": [
            "report",
            "log",
            "verdict",
            "summary"
          ],
          "relates_to": [
            "Gate",
            "Review backend"
          ]
        },
        {
          "term": "Gate",
          "definition": "A pass/fail check the workflow refuses to proceed past \u2014 the repo's full local quality gate (lint, typecheck, tests, docs) run before handoff, plus the review and readiness gates in the pipeline. A green receipt is the proof one exact gate command passed at one exact commit; `flowctl gate check` decides whether that proof still applies. Gates are local and fail-closed; CI is a separate surface.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Receipt",
          "avoid": [
            "check",
            "hook",
            "CI",
            "guardrail"
          ],
          "relates_to": [
            "Receipt"
          ]
        },
        {
          "term": "Driver",
          "definition": "The thing that invokes the unattended conductor and owns repetition: a human running `/flow-next:flow --auto` once per item, a host loop primitive (`/loop`, `/goal`, `cron`) running `flow --auto --tick`, or Ralph (the deprecated repo-local hardened harness). Attended `/flow-next:flow` stops at the next human decision; `flow --auto` stops at the next decision that needs a human and reports it as a verdict. Drivers are never recursively nested. The confined composition exception is flow invoking one land tick as its authorized landing stage for the selected spec and PR. Attended flow refuses under any autonomy marker, `flow --auto` refuses under Ralph, and land never dispatches a second driver.",
          "avoid": [
            "mode",
            "conductor mode",
            "autopilot"
          ],
          "relates_to": [
            "Routing reference",
            "Hop",
            "Tick",
            "Long-horizon run",
            "Pilot"
          ]
        }
      ],
      "count": 5
    }
  ],
  "file_count": 1,
  "total_terms": 5
}

===== [10/11] memory_index: `flowctl memory list` =====
bug/build-errors/
  detectvalidate-must-require-specs-dir-2026-05-08 — "detect/validate must require SPECS_DIR even when EPICS_DIR present" (module: plugins/flow-next/scripts/flowctl.py)
  template-rewrite-env-var-cascade-2026-05-09 — "Env-var cascade in templates + canonical config.env knob alignment" (module: plugins/flow-next/skills/flow-next-ralph-init/templates, config.env, ralph.sh)
  abort-option-copy-must-reflect-pre-2026-05-18 — "Abort-option copy must reflect pre-prompt state mutations (idempotent != no chan" (module: plugins/flow-next/skills/flow-next-setup/workflow.md)
  codex-mirror-smoke-docs-miss-composed-2026-05-18 — "Codex mirror smoke docs miss composed transform output (abort + Other)" (module: agent_docs/local-dev.md)
  fn-44-review-cycle-lessons-2026-05-21 — "fn-44 review-cycle lessons (10+ NEEDS_WORK rounds across 4 tasks)" (module: plugins/flow-next/skills/flow-next-interview, plugins/flow-next/skills/flow-next-capture, plugins/flow-next/scripts/flowctl.py, scripts/sync-codex.sh, plugins/flow-next/templates/spec.md)
  scout-fallback-prose-drifted-from-specs-2026-05-26 — "Scout fallback prose drifted from spec's decision-lock command shape" (module: plugins/flow-next/agents/context-scout.md)
  skill-bash-set-arguments-cant-honor-2026-05-26 — "Skill bash `set -- $ARGUMENTS` can't honor 'verbatim' passthrough" (module: plugins/flow-next/skills/flow-next-map/workflow.md)
  id-grammar-widening-must-cover-the-full-2026-06-03 — "Id-grammar widening must cover the FULL command surface, not just named commands" (module: plugins/flow-next/scripts/flowctl.py)
  env-marker-gate-must-scan-the-namespace-2026-06-04 — "Env-marker gate must scan the namespace, not a fixed var list" (module: plugins/flow-next/skills/flow-next-work/references/codex-delegation.md)
  docs-activation-command-for-string-enum-2026-06-05 — "Docs activation command for string-enum config knob used bool true instead of th" (module: plugins/flow-next/docs/flowctl.md, .flow/usage.md)
  sed-piped-default-masks-empty-source-2026-06-05 — "sed-piped default masks empty source: || fallback never fires" (module: plugins/flow-next/skills/flow-next-qa/workflow.md)
  skill-adding-version-bump-leaves-stale-2026-06-05 — "Skill-adding version bump leaves stale skill/command counts in JSON manifest des" (module: plugins/flow-next/.claude-plugin/plugin.json, .claude-plugin/marketplace.json, plugins/flow-next/.codex-plugin/plugin.json)
  mirror-regen-exposes-latent-canonical-2026-06-11 — "Mirror regen exposes latent canonical gaps: path rewrites, .flow persistence, di" (module: scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-land/workflow.md)
  skill-workflow-snippets-must-enforce-2026-06-11 — "Skill workflow snippets must enforce what the prose mandates (vars, gates, dispa" (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  embedded-self-check-greps-in-reference-2026-06-12 — "Embedded self-check greps in reference docs need POSIX classes + whitespace tole" (module: plugins/flow-next/references/html-artifacts.md)
  lavish-interactive-only-gate-must-check-2026-06-12 — "Lavish interactive-only gate must check MODE var AND env markers in-snippet" (module: plugins/flow-next/skills/flow-next-capture/references/html-lens.md)
  optional-side-effect-snippets-need-2026-06-12 — "Optional side-effect snippets need guarded git steps; check-ignore the exact fil" (module: plugins/flow-next/skills/flow-next-make-pr/html-lens.md)
  policy-claim-inversion-sweep-all-2026-06-18 — "Policy-claim inversion: sweep ALL surfaces (both ceremony copies, docs, CLI head" (module: plugins/flow-next/skills/flow-next-tracker-sync/steps.md)
  status-policy-map-needs-a-matching-2026-06-18 — "Status-policy map needs a matching reconcile-loop branch per rung (map ≠ write)" (module: plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md)
  backlog-select-must-not-drop-a-dep-2026-06-27 — "Backlog SELECT must not drop a dep-blocked item to NO_WORK — it routes to BLOCKE" (module: plugins/flow-next/skills/flow-next-pilot/references/backlog-mode.md)
  r2-ask-block-mis-injected-into-negation-2026-06-27 — "R2 ask-block mis-injected into negation-only autonomy prose on mirror regen" (module: scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-pilot, plugins/flow-next/skills/flow-next-tracker-sync/steps.md)
  verdict-tasks-must-rewrite-not-banner-a-2026-07-03 — "Verdict tasks must rewrite, not banner, a sibling task's flipped scope" (module: .flow/tasks)
  eval-ledger-feature-rows-must-disclaim-2026-07-18 — "Eval-ledger feature rows must disclaim the optimization ratchet + reconcile deno" (module: optimization/interview)
  unit-rename-substitution-broke-trigger-2026-07-18 — "Unit-rename substitution broke trigger thresholds (turns->rounds, fn-100)" (module: plugins/flow-next/skills/flow-next-interview/references/doc-aware.md)
  grep-c-prints-0-and-exits-1-echo-0-2026-07-24 — "grep -c prints 0 AND exits 1: || echo 0 yields a two-line count" (module: plugins/flow-next/skills/flow-next-audit/workflow.md)
  changelog-entry-landed-in-a-released-2026-08-01 — "Changelog entry landed in a released section, not Unreleased" (module: CHANGELOG.md)
  codex-home-rewrite-both-spellings-2026-08-02 — "CODEX_HOME rewrite: both spellings, actionable prose, quoting, sorted-hash idemp" (module: scripts/sync-codex.sh)
  concurrent-gating-draws-soft-terms-2026-08-21 — "Concurrent gating draws + soft terms falsify a 'frozen' eval pre-registration" (module: agent-evals/studies/rolling-frontier-2026-08)
  concurrent-loop-skill-prose-linear-2026-08-22 — "Concurrent-loop skill prose: linear checklist + non-blocking claims contradict" (module: plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md)
  canonical-3c-edits-vanish-from-codex-2026-08-28 — "Canonical 3c edits vanish from Codex mirror via stale SECTION3C heredoc" (module: scripts/sync-codex.sh)
  prose-tick-lock-claim-before-read-2026-08-28 — "Prose tick lock: claim before read, serialized reap, liveness refresh, persisted" (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  delegating-cli-wrapper-inherits-2026-08-30 — "Delegating CLI wrapper inherits delegate guards, prints, truncation, races" (module: plugins/flow-next/scripts/flowctl.py)
  skill-flag-gating-a-durable-write-needs-2026-08-31 — "Skill flag gating a durable write needs exact-token parse, not substring" (module: plugins/flow-next/skills/flow-next-capture/SKILL.md)
  implementer-brief-widened-never-list-2026-09-14 — "Implementer brief widened never-list past the spec; child lost its fan-out" (module: plugins/flow-next/templates/usage.md)

bug/data/
  migrationrollback-cli-10-review-cycle-2026-05-08 — "Migration/rollback CLI: 10 review-cycle pitfalls (fn-43.3)" (module: plugins/flow-next/scripts/flowctl.py)
  paired-snapshot-setter-must-write-both-2026-06-03 — "Paired-snapshot setter must write both halves atomically (merge base)" (module: plugins/flow-next/scripts/flowctl.py)
  fence-preserving-writer-needs-fence-2026-07-02 — "Fence-preserving writer needs fence-aware readers/validators (write/read parity)" (module: plugins/flow-next/scripts/flowctl.py)
  yaml-frontmatter-writer-unescaped-2026-07-24 — "YAML frontmatter writer: unescaped newlines lose the entry; frontmatter-only wri" (module: plugins/flow-next/scripts/flowctl.py)
  adding-a-key-to-a-content-hash-orphans-2026-08-01 — "Adding a key to a content hash orphans records the old binary wrote" (module: plugins/flow-next/scripts/flowctl.py)
  docs-for-a-hash-identity-fix-inherit-2026-08-01 — "Docs for a hash-identity fix inherit the hash's precision" (module: plugins/flow-next/docs/flowctl.md)
  relaxing-a-validator-must-only-admit-2026-09-26 — "Relaxing a validator must only admit values the writer round-trips" (module: plugins/flow-next/scripts/flowctl.py)

bug/integration/
  drop-receipt-to-break-codex-2026-05-09 — "Drop receipt to break codex confabulation in long review fix loops" (module: plugins/flow-next/scripts/flowctl.py)
  set-tracker-id-rejected-github-n-2026-06-03 — "set-tracker-id rejected GitHub #N identifiers (Linear-only handle validator)" (module: plugins/flow-next/scripts/flowctl.py)
  trackers-auto-linkify-issue-key-2026-06-03 — "Trackers auto-linkify issue-key substrings inside markers (even in HTML comments" (module: plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md)
  heredoc-built-json-breaks-on-free-form-2026-06-05 — "Heredoc-built JSON breaks on free-form interpolated values" (module: skills/flow-next-qa/workflow.md)
  rp-builder-file-slices-cause-false-2026-06-10 — "RP builder file slices cause false-positive 'missing docs' review findings" (module: plugins/flow-next/skills/flow-next-impl-review)
  gh-api-f-stringifies-numeric-body-2026-06-17 — "gh api -f stringifies numeric body fields (issue_id) → GitHub 422; use -F" (module: plugins/flow-next/scripts/flowctl_tracker/)
  markerstruct-field-semantics-must-2026-06-27 — "Marker/struct-field semantics must update the PRODUCER adapter contract, not jus" (module: plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md)
  ceremony-validation-must-read-persisted-2026-06-28 — "Ceremony validation must read PERSISTED config, not re-race env; don't collapse " (module: plugins/flow-next/skills/flow-next-tracker-sync/steps.md)
  adding-a-review-backend-sweep-all-2026-06-29 — "Adding a review backend: sweep ALL enumeration sites (config table, stage list, " (module: plugins/flow-next/docs, plugins/flow-next/scripts/flowctl.py)
  byte-for-byte-spec-contract-branch-2026-07-01 — "Byte-for-byte spec contract: branch prose into variants, don't annotate shared l" (module: plugins/flow-next/skills/flow-next-plan-review/SKILL.md)
  skill-bash-blocks-re-declare-every-2026-07-02 — "Skill bash blocks: re-declare EVERY literal path per block (vars die across tool" (module: plugins/flow-next/skills)
  spec-named-config-keys-must-be-checked-2026-07-15 — "Spec-named config keys must be checked against shipped surface; cross-family is" (module: plugins/flow-next/skills/flow-next-setup/workflow.md)
  claude-p-clean-room-on-oauth-logins-2026-07-16 — "claude -p clean-room on OAuth logins: --setting-sources project,local; --bare an" (module: agent_docs/guidance-eval/runner.sh)
  path-handoff-template-id-slots-must-use-2026-07-19 — "Path-handoff template id slots must use canonical ids, not aliases" (module: plugins/flow-next/skills/flow-next-work/references/codex-delegation.md)
  summary-sinks-for-repeatable-mixed-2026-07-19 — "Summary sinks for repeatable mixed-outcome events need per-event lines, not one " (module: plugins/flow-next/skills/flow-next-work/phases.md)
  skill-fence-consolidation-6-contract-2026-07-20 — "Skill-fence consolidation: 6 contract regressions (var-atomicity, symlink, dry-r" (module: plugins/flow-next/skills)
  caller-facade-guards-must-cover-retro-2026-07-29 — "Caller facade guards must cover retro-fire paths" (module: plugins/flow-next/skills/flow-next-capture/workflow.md)
  caller-fakes-must-enforce-lifecycle-2026-07-29 — "Caller fakes must enforce lifecycle facade input contracts" (module: plugins/flow-next/tests/test_tracker_caller_execution.py)
  caller-oracle-must-preserve-historical-2026-07-29 — "Caller oracle must preserve historical quirks and exact observations" (module: plugins/flow-next/tests/test_tracker_caller_oracle.py)
  tracker-ownership-rewrites-require-2026-07-29 — "Tracker ownership rewrites require adjacent fidelity sweeps" (module: plugins/flow-next/docs/tracker-sync.md)
  head-bound-html-artifacts-must-not-2026-07-30 — "Head-bound HTML artifacts must not stale their own input" (module: plugins/flow-next/skills/flow-next-make-pr/html-lens.md)
  land-evidence-field-defaulted-to-off-on-2026-08-19 — "land evidence field defaulted to 'off' on configured-but-not-due paths" (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  installer-must-own-what-it-deletes-2026-08-21 — "(no title)" (module: scripts/install-codex.sh, scripts/sync-codex.sh)
  scheduler-prose-asserted-wrong-config-2026-08-22 — "Scheduler prose asserted wrong config default; slot-hold drain rules deadlock" (module: plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md)
  backend-special-case-in-a-shared-helper-2026-09-05 — "Backend special-case in a shared helper is an enumeration site too" (module: plugins/flow-next/scripts/flowctl.py)
  ci-path-classification-must-include-2026-09-05 — "CI path classification must include rename sources" (module: scripts/ci/classify_changes.py)
  cross-family-review-claims-key-on-the-2026-09-05 — "Cross-family review claims key on the writer's model family, never the host name" (module: plugins/flow-next/docs)
  headless-review-backend-error-envelope-2026-09-05 — "Headless review backend: error-envelope text must never ride the output slot" (module: plugins/flow-next/scripts/flowctl.py)
  forwarded-license-carried-the-wrong-2026-09-14 — "Forwarded license carried the wrong holder's commit contract into the bridged ch" (module: plugins/flow-next/agents/worker.md)
  plan-review-criteria-edits-must-also-2026-09-14 — "Plan-review criteria edits must also sweep workflow-rp.md (CE summary + Classic " (module: plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md)

bug/performance/
  linear-graphql-every-nodes-connection-2026-06-03 — "Linear GraphQL: every {nodes} connection needs first: — incl. workflowStates/tea" (module: plugins/flow-next/scripts/flowctl_tracker/wire/linear.py)

bug/runtime-errors/
  who-wins-ladder-must-check-the-2026-06-03 — "Who-wins ladder must check the collision case before single-field rules" (module: plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md)
  flowctl-on-disk-per-key-counter-count-2026-06-27 — "flowctl on-disk per-key counter: count by stored key + lock + coerce sort" (module: plugins/flow-next/scripts/flowctl.py)
  bash-deadline-watchdogs-orphaned-sleep-2026-07-16 — "Bash deadline watchdogs: orphaned sleep holds pipes; group-kill via setsid, not " (module: agent_docs/guidance-eval/runner.sh)
  forced-color-git-grep-output-defeats-2026-07-19 — "Forced-color git grep output defeats regex post-filter (SGR escapes)" (module: plugins/flow-next/scripts/flowctl.py)
  glob-walk-file-loads-need-lstat-screen-2026-07-19 — "Glob-walk file loads need lstat screen + RecursionError; revalidate TTL post-sta" (module: plugins/flow-next/scripts/flowctl.py)
  empty-value-semantics-leak-null-in-2026-07-20 — "Empty-value semantics leak: {} -> null in snapshot config reads; empty file -> T" (module: plugins/flow-next/scripts/flowctl.py)
  structured-review-parsers-must-2026-07-30 — "Structured review parsers must distinguish invalid from absent" (module: plugins/flow-next/scripts/flowctl.py)
  same-owner-alias-re-registration-must-2026-08-02 — "Same-owner alias re-registration must harden a weak claim, not no-op" (module: plugins/flow-next/scripts/flowctl.py)
  one-shot-keyed-to-an-earlier-captured-2026-08-19 — "One-shot keyed to an earlier-captured SHA: re-validate after the claim, release " (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  land-chain-fences-a-failed-read-is-2026-09-13 — "Land chain fences: a failed read is never permission; write multi-layer records " (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  skill-fences-that-degrade-only-without-2026-09-13 — "Skill fences that degrade only without set -e: masked failures in make-pr chain " (module: plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md)

bug/security/
  rollback-path-sanitizer-must-not-2026-06-05 — "Rollback path-sanitizer must not trim/rewrite bytes; guard git clean against emp" (module: plugins/flow-next/scripts/flowctl.py)
  shell-command-allowlist-gates-must-2026-06-05 — "Shell-command allowlist gates must tokenize argv, not substring-match" (module: plugins/flow-next/scripts/hooks/ralph-guard.py)
  managed-review-transport-must-bound-2026-09-08 — "Managed review transport must bound time and protect scoped credentials" (module: plugins/flow-next/scripts/flowctl.py)
  guard-matcher-narrowing-missed-shell-2026-09-25 — "Guard matcher narrowing missed shell control words and split redirect words" (module: plugins/flow-next/scripts/hooks/ralph-guard.py)

bug/test-failures/
  rename-smoke-rewire-variable-form-cli-2026-05-09 — "Smoke discipline: variable-form CLI, hermetic env, line-level guard scope" (module: plugins/flow-next/scripts)
  test-production-path-not-parallel-construction-2026-05-21 — "Test the production path, not a parallel construction" (module: plugins/flow-next/tests, plugins/flow-next/scripts/flowctl.py)
  test-fixtures-must-mirror-upstream-zod-2026-05-26 — "Test fixtures must mirror upstream Zod enum, not concept" (module: plugins/flow-next/tests/fixtures/clawpatch-map, plugins/flow-next/scripts/flowctl.py)
  archaeology-fn-strip-can-over-strip-a-2026-07-02 — "Archaeology fn-strip can over-strip a test-pinned canonical breadcrumb" (module: plugins/flow-next/skills/flow-next-tracker-sync/steps.md)
  final-gate-grep-for-a-forbidden-token-2026-07-02 — "Final-gate grep for a forbidden token hits the prohibition prose that bans it" (module: plugins/flow-next/skills/flow-next-impl-review)
  test-asserted-a-public-envelope-that-2026-08-01 — "Test asserted a public envelope that never carried the field" (module: plugins/flow-next/tests/test_chart_briefing.py)
  test-runner-timeout-must-kill-a-process-2026-08-04 — "Test-runner timeout must kill a process TREE whose identity outlives the shard" (module: scripts/run_tests_parallel.py)
  two-independent-resolve-calls-faked-a-2026-08-04 — "Two independent resolve() calls faked a path escape on Windows" (module: plugins/flow-next/scripts/flowctl_tracker/lifecycle/helpers.py)
  windows-83-path-test-failures-were-2026-08-04 — "Windows '8.3 path' test failures were cp1252 fixtures + unguarded geteuid" (module: plugins/flow-next/tests/test_normalize_section_content.py)
  flag-substring-assertion-passes-when-a-2026-09-23 — "Flag substring assertion passes when a longer sibling flag is present" (module: plugins/flow-next/tests/test_spec_id_routing_prose.py)

bug/ui/
  flow-nextdev-docs-page-needs-2026-06-03 — "flow-next.dev docs page needs registering in BOTH astro sidebar + site.ts navGro" (module: src/lib/site.ts)

knowledge/best-practices/
  scb-benchmark-proof-fn-163164-2026-08-04 — "SCB benchmark proof: fn-163/164 eliminated ceremony as a cost factor"
  windows-path-shims-cannot-observe-2026-08-11 — "Windows PATH shims cannot observe subprocess spawns (CreateProcess skips PATHEXT" (module: plugins/flow-next/tests)
  failures-after-a-restart-suspect-2026-08-28 — "Failures after a restart: suspect persistent state before code" (module: .flow)

knowledge/conventions/
  unattended-detection-uses-the-full-2026-09-26 — "Unattended detection uses the full autonomy marker namespace" (module: skills)

knowledge/decisions/
  factory-droid-platform-status-2026-05-2026-05-25 — "Factory Droid platform status — 2026-05" (module: plugins/flow-next/docs/platforms.md)
  tracker-sync-is-projection-not-2026-06-01 — "Tracker sync is projection, not coordination (Linear-first)" (module: strategy)
  plan-sync-skip-gate-not-viable-2026-07-03 — "A deterministic plan-sync skip-gate is not viable — do not re-attempt" (module: plugins/flow-next/skills/flow-next-work/phases.md)
  composed-brief-deleted-path-handoff-2026-07-19 — "Composed brief deleted: path-handoff replaces it (fn-103 eval)" (module: plugins/flow-next/skills/flow-next-work/references/codex-delegation.md)
  review-stall-detection-reads-resolution-2026-08-05 — "Review stall detection reads resolution; the trend heuristics are deleted (fn-168)" (module: plugins/flow-next/scripts/flowctl.py)
  bugbot-pre-push-stage-wont-do-patch-id-2026-08-07 — "Bugbot pre-push stage: won't-do - patch-ID dedup falsified live" (module: review)
  pilot-strike-recovery-is-a-cli-verb-not-2026-08-11 — "Pilot strike recovery is a CLI verb, not board-native transition detection" (module: plugins/flow-next/skills/flow-next-pilot)
  ralph-guard-reverts-its-delegation-2026-08-14 — "Ralph guard reverts its delegation amendment; bridge safety is prose-only" (module: plugins/flow-next/scripts/hooks/ralph-guard.py)
  tracked-vs-runtime-durability-contract-2026-08-14 — "Tracked-vs-runtime durability contract - done crosses it, validate respects it" (module: plugins/flow-next/scripts/flowctl.py)

knowledge/workflow/
  audit-sync-codexsh-during-planning-for-2026-04-30 — "Audit sync-codex.sh during planning for Codex mirror impact" (module: planning)
  final-integration-tasks-need-wider-impl-2026-05-26 — "Final-integration tasks need wider impl-review base" (module: review)
  pr-bot-review-loops-do-not-converge-2026-08-04 — "(no title)" (module: review-subsystem)
  split-pr-at-second-adjacent-surface-finding-2026-08-21 — "(no title)" (module: review)
  stacked-pr-squash-close-recovery-2026-08-27 — "Squash-merging a stacked PR's base permanently closes the stacked PR - rebase + successor PR is the recovery" (module: land)
  harness-capability-claims-verify-at-the-2026-08-28 — "Harness capability claims: verify at the installer, not the generator" (module: platforms)
  github-rulesets-need-an-admin-bypass-or-2026-09-11 — "GitHub rulesets need an admin bypass or spec-only commits stall" (module: ci)

===== [11/11] dependencies: ids, titles, statuses, done summaries =====
- fn-74-cursor-review-backend-cursor-agent-cli.1 [done] - flowctl cursor backend foundation — registry + run_cursor_exec + check + parser tests
    Added the `cursor` review backend foundation in flowctl: the BACKEND_REGISTRY entry (model-yes / effort-no shape, default gpt-5.5-high), the require_cursor / get_cursor_version / run_cursor_exec helper trio (positional-argv prompt, resume-only session, cwd=repo_root, --mode ask --trust, no --effort, explicit prompt-too-large raise, non-zero on is_error/timeout), the `cursor check [--skip-probe]` subcommand, and unit tests (test_cursor_run_exec.py + test_backend_spec.py cursor cases). Full Python suite green at 1271 tests.

