# Worker anchor bundle - fn-74-cursor-review-backend-cursor-agent-cli.2 (spec fn-74-cursor-review-backend-cursor-agent-cli)

Verbatim outputs of the worker Phase-1 re-anchor reads, fixed order, no filtering or truncation. The bundle is a floor, not a ceiling - memory keyword-search and every further read remain available.

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
  "tracker": {
    "baseHashFlow": "0a0f825ee1c0bc24efc5d9cb90cb060821f0cf76b5a4acbeaf849b33c529c0d8",
    "baseHashTracker": "0a0f825ee1c0bc24efc5d9cb90cb060821f0cf76b5a4acbeaf849b33c529c0d8",
    "depRelations": [],
    "id": "cbe47014-0a43-4d8b-b07d-7914a936f235",
    "identifier": "FLOW-22",
    "lastSyncedAt": "2026-06-29T12:08:52.494201Z",
    "mergeBaseFlow": "# fn-74 Cursor review backend (cursor-agent CLI \u2014 gpt-5.5/codex/opus)\n\n## Goal & Context\n\nflow-next ships three second-model **review backends** today \u2014 `rp` (RepoPrompt),\n`codex` (OpenAI Codex CLI), `copilot` (GitHub Copilot CLI) \u2014 selected via the\n`BACKEND_REGISTRY` in `plugins/flow-next/scripts/flowctl.py` and consumed by\n`/flow-next:impl-review`, `/flow-next:plan-review`, `/flow-next:spec-completion-review`.\nThere is **no `cursor` backend**. Cursor is already supported as a *primary host\ndriver* (the `CURSOR_AGENT`/`install-cursor.sh` path in `flow-next-setup`) \u2014 a\n**different integration point**, out of scope here.\n\nAdd `cursor` as a first-class review backend that shells out to the **`cursor-agent`\nCLI** (installed locally, v2026.06). It unlocks Cursor-billed review (the user's\nexisting Cursor subscription, no separate API key) and Cursor reviewer models the\nothers can't reach in one place: `gpt-5.5-high` (1M ctx, the default), the\n`gpt-5.3-codex` family, `composer-2.5`, `claude-opus-4-8-thinking-high`.\n\nParity port of the most-recent backend (`copilot`, fn-28) \u2014 no new review *features*,\nno new architecture. The headless contract was verified live and the spec was then\n**dogfooded through a `cursor-agent` gpt-5.5-high plan-review of itself** (see\nDecision Context), which corrected the session/repo-scope/triage contracts below.\n\n**Doc-drift this closes:** the GrowthFactors cross-model-review spec\n(`~/work/code-factory-package/spec/05-cross-model-review.md`) **already advertises**\n\"Cursor via its `cursor-agent` headless CLI\" as a supported review backend. That\nclaim is currently false. fn-74 makes the already-published claim true.\n\n## Architecture & Data Models\n\nMirror the `copilot` backend end-to-end. Paths in\n`plugins/flow-next/scripts/flowctl.py` unless noted.\n\n**Verified `cursor-agent` contract** (probed live + dogfood plan-review):\n- Invocation: `cursor-agent -p --output-format json --trust --mode ask --model <model> [--resume <session_id>] \"<prompt>\"`, run with **`cwd=repo_root`** (Cursor scopes to the workspace dir; without it a review launched from a subdir reads the wrong tree \u2014 copilot's `--add-dir <repo_root>` analog).\n- `--mode ask` = read-only Q&A; the CLI **refuses to edit** in this mode (verified). Reviewer never mutates the tree.\n- `--trust` is **mandatory** headless or the CLI blocks on a \"Workspace Trust Required\" prompt and hangs.\n- Result JSON: `{\"type\":\"result\",\"subtype\":\"success\",\"is_error\":false,\"result\":\"<text>\",\"session_id\":\"<uuid>\",\"usage\":{...}}`. Parse `.result`, `.session_id`, `.is_error`.\n- **Session model = resume-only (like copilot's Windows/stdin path, NOT its POSIX create-or-resume).** First call: **omit `--resume`**, let Cursor generate `session_id`, capture it from the result, store in the receipt. Continuation: pass `--resume <stored_session_id>`. Verified: a generated id resumes prior history non-interactively under `-p`. Never pass a caller-fabricated uuid as `--resume` on the first call.\n- Auth: stored login creds OR `CURSOR_API_KEY`. `--list-models` is the source of truth for model strings; `cursor-agent --version` \u2192 `2026.06.xx-<hash>` for `check`.\n\n**Components to add (copilot is the template):**\n\n1. **Registry entry** \u2014 `BACKEND_REGISTRY` (~L3449). NEW shape: model accepted,\n   **effort folded into the model name** (Cursor convention) so `efforts: None`:\n   ```python\n   \"cursor\": {\n       \"models\": {\"auto\", \"gpt-5.5-high\", \"gpt-5.4-high\", \"gpt-5.3-codex\",\n                  \"gpt-5.3-codex-high\", \"gpt-5.3-codex-xhigh\", \"gpt-5.2\",\n                  \"composer-2.5\", \"claude-opus-4-8-thinking-high\",\n                  \"claude-opus-4-7-thinking-high\"},\n       \"efforts\": None,            # Cursor bakes reasoning effort into the model name\n       \"default_model\": \"gpt-5.5-high\",\n   },\n   ```\n   `VALID_BACKENDS` (~L3510) derives \u2192 free. **Verified: existing `BackendSpec.parse`/`.resolve` + `parse_backend_spec_lenient` handle this model-yes/effort-no shape with no parser edits.**\n\n2. **Helpers** (mirror `require_copilot`/`get_copilot_version`/`run_copilot_exec` ~L3786-3967):\n   - `require_cursor()` / `get_cursor_version()`.\n   - `run_cursor_exec(prompt, session_id=None, *, spec, repo_root) -> (result_text, returned_session_id, exit_code, stderr)` \u2014 `session_id` is **optional input** (None on first call \u2192 omit `--resume`; non-None \u2192 `--resume <id>`), and the **returned** session id (parsed from `.result` JSON) is what the caller persists. Run with `cwd=repo_root`, `--trust --mode ask`, `timeout=600`; non-zero on `is_error`/timeout/CLI failure. Reuse copilot's argv-vs-temp prompt threshold (POSIX argv handles 60KB \u2014 verified).\n\n3. **CLI subcommands** (mirror the `copilot` parser block ~L25968): a `cursor` subparser with `check`, `impl-review`, `plan-review`, `completion-review`, `validate`, `deep-pass` \u2014 same args as copilot (incl. `check --skip-probe`).\n\n4. **Command handlers** (mirror `cmd_copilot_*` ~L22405+, and shared dispatchers `_run_validator_pass`/deep-pass at L19245 / L19902 / L23606): add `elif backend == \"cursor\":` branches + `cmd_cursor_*`. **Receipts must match the copilot field set** \u2014 `mode:\"cursor\"`, `spec:\"cursor:<model>\"`, `model:<model>`, **no `effort` key** (effort is invalid for cursor), plus the same confidence/classification rubric injection, suppressed-count, introduced-vs-pre_existing, unaddressed-R-ID, and protected-path handling copilot already does.\n\n5. **Resolution plumbing** \u2014 `resolve_review_spec` (~L3691) is backend-generic. Env fill: `FLOW_CURSOR_MODEL` (no `FLOW_CURSOR_EFFORT`). The `review-backend` resolver already flows from the registry (verified: `config set review.backend` stores without a separate allowlist; resolution parses via the registry) \u2014 config/env/per-task/spec-form accept `cursor` automatically once registered.\n\n6. **Skill wiring:**\n   - `flow-next-impl-review`: new `workflow-cursor.md` (mirror `workflow-copilot.md`); add the `cursor` row to the Phase-0 dispatch table in `workflow-common.md`.\n   - `flow-next-plan-review`: add a `cursor` section to `workflow.md`.\n   - `flow-next-spec-completion-review`: add `cursor` to its `workflow-common.md`.\n   - All three SKILL.md + their `commands/flow-next/*.md`: `--review=rp|codex|copilot|cursor|none`.\n\n7. **Setup**: `flow-next-setup` `review.backend` config prompt/validation accepts `cursor` and spec form `cursor:gpt-5.5-high`.\n\n8. **Triage LLM judge stays `codex|copilot`** (`--backend choices=[\"codex\",\"copilot\"]`, L25558 \u2014 the *opt-in* judge for ambiguous diffs, default-off behind `FLOW_TRIAGE_LLM`). Do NOT add cursor there. **Precise truth:** with the LLM judge **off (the default)** cursor reviews use the deterministic whitelist \u2014 zero extra dependency. A cursor user who opts into `FLOW_TRIAGE_LLM=1` gets the `codex` judge and therefore needs codex/copilot present \u2014 **document this, do not auto-wire a cursor judge**. (Keeping cursor out is the lean choice; the judge is a cheap separate concern.)\n\n9. **Codex mirror**: regenerate via `scripts/sync-codex.sh` (never hand-edit `plugins/flow-next/codex/**`); install/sync parity tests stay green.\n\n## API Contracts\n\n- `run_cursor_exec(prompt: str, session_id: Optional[str]=None, *, spec: BackendSpec|None, repo_root: Path) -> tuple[str, str, int, str]` \u2192 `(result_text, returned_session_id, exit_code, stderr)`; `session_id=None` \u21d2 first call (no `--resume`); non-zero exit on `is_error`/CLI-failure/600s timeout; always invoked with `cwd=repo_root`.\n- `flowctl cursor check [--json] [--skip-probe]` \u2192 `{available, version, authed}` (schema aligned to copilot's `check`).\n- `flowctl cursor impl-review <task> --base <ref> --receipt <path> [--spec cursor:<model>] [--json]`\n- `flowctl cursor plan-review <spec> [--files ...] --receipt <path> [--json]`\n- `flowctl cursor completion-review <spec> --receipt <path> [--json]`\n- `flowctl cursor validate --findings-file <jsonl> --receipt <path> [--json]`\n- `flowctl cursor deep-pass --pass <name> --primary-findings <jsonl> --receipt <path> [--json]`\n- Receipt (impl): `{\"type\":\"impl_review\",\"id\":\"<id>\",\"mode\":\"cursor\",\"verdict\":\"SHIP|NEEDS_WORK|MAJOR_RETHINK\",\"session_id\":\"<uuid>\",\"model\":\"<model>\",\"spec\":\"cursor:<model>\",\"timestamp\":\"...\"}` \u2014 **no `effort` key**; same additive validator/deep/walkthrough blocks + rigor fields as copilot.\n- Spec grammar (verified): `cursor` | `cursor:<model>` valid; `cursor:<model>:<effort>` \u2192 ValueError (\"does not accept an effort\"); unknown model \u2192 ValueError listing valid models.\n\n## Edge Cases & Constraints\n\n- **NEW registry shape (model-yes / effort-no) \u2014 VERIFIED OK.** Existing parser raises on effort, resolves `default_model` with effort `None`, no KeyError. Lock with tests.\n- **Session = resume-only \u2014 VERIFIED.** Caller must not fabricate a first-call `--resume` id; capture and persist Cursor's returned `session_id`, resume with it only when the receipt at the path has `mode == \"cursor\"` (cross-backend \u2192 fresh). Mirrors copilot's Windows path, not its POSIX path.\n- **Repo scoping \u2014 REQUIRED.** `run_cursor_exec` runs with `cwd=repo_root`; add a test that invokes from a subdirectory and confirms the correct tree is reviewed.\n- **`--trust` mandatory** headless or the CLI hangs on a trust prompt.\n- **Read-only \u2014 VERIFIED.** `--mode ask` refused a \"create a file\" instruction; tree stayed clean. R8 asserts `git status` unchanged across a review.\n- **Oversized prompts \u2014 VERIFIED on POSIX (60KB positional argv).** cursor-agent takes the prompt as a **positional argument** (not stdin). Up to the threshold, pass it positionally. **Above the threshold there is no safe path yet:** copilot's temp-file step just reads the file back into argv (it does NOT bypass any cap), and cursor-agent stdin support is unconfirmed \u2192 `run_cursor_exec` must raise an **explicit \"prompt too large\" error** above the threshold (with a test), NOT silently reuse the read-back-into-argv trick. Implement a stdin path only if cursor-agent confirms stdin input. (The Windows `CreateProcessW` cap is where this bites first.)\n- **Triage precision** \u2014 see Architecture \u00a78: deterministic by default; opt-in LLM judge stays codex/copilot and is a documented dependency for cursor users who enable it.\n- **Auth not configured** \u2192 `check` and runners surface a clear error pointing at `cursor-agent` login / `CURSOR_API_KEY` (never a silent empty review).\n- **`.result` empty / `is_error:true`** \u2192 backend failure (non-zero exit + stderr), never a false SHIP.\n- **Effort must not leak** \u2014 copying copilot receipt code literally risks writing `effort:\"high\"`; cursor receipts must omit `effort` (assert in tests).\n- **Model-list drift** \u2014 Cursor ships model strings without changelog (and auto-updates the CLI); document \"keep synced with `cursor-agent --list-models`\", copilot-style note.\n- **Not the host driver.** Independent of the `CURSOR_AGENT` host-platform path; works on any host with `cursor-agent` installed.\n\n## Acceptance Criteria\n\n- **R1:** `cursor` is in `BACKEND_REGISTRY` and `VALID_BACKENDS`; `flowctl review-backend` reports `cursor` from `.flow/config.json` + `FLOW_REVIEW_BACKEND` (its only two sources); per-task `default_review` and `--spec cursor:<model>` resolve via `resolve_review_spec` / the review commands (NOT `review-backend`).\n- **R2:** `BackendSpec.parse(\"cursor\")` / `parse(\"cursor:gpt-5.5-high\")` succeed; `parse(\"cursor:gpt-5.5-high:high\")` raises (effort rejected); `parse(\"cursor:bogus\")` raises listing valid models; `.resolve()` fills `gpt-5.5-high`, effort `None`.\n- **R3:** `run_cursor_exec` shells `cursor-agent -p --output-format json --trust --mode ask --model <m>` with `cwd=repo_root`; on a first call it omits `--resume` and returns Cursor's generated `session_id`; on continuation it passes `--resume <session_id>`; parses `.result`/`.session_id`/`.is_error`; returns non-zero on a 600s timeout.\n- **R4:** `flowctl cursor check [--skip-probe]` reports availability + version + auth (`authed`) in text and `--json`, schema-aligned to copilot's `check`.\n- **R5:** `flowctl cursor impl-review <task> --base <b> --receipt <r>` writes a `mode:\"cursor\"` receipt (no `effort` key) and prints `VERDICT=...`.\n- **R6:** `cursor plan-review`, `completion-review`, `validate`, `deep-pass` dispatch through `run_cursor_exec` and write the same additive receipt shapes as codex/copilot (`mode:\"cursor\"`).\n- **R7:** Re-review with an existing `mode==\"cursor\"` receipt resumes via `--resume <session_id>` (using the persisted returned id); a cross-backend receipt starts fresh.\n- **R8:** A cursor review leaves the working tree unchanged. Unit-level: `run_cursor_exec` is asserted to pass `--mode ask` (read-only) and never an edit/write flag. Integration-level: an **optional live smoke test gated on `cursor-agent` availability** runs a real `cursor impl-review` against a temp git repo and asserts `git status` is identical before/after (skipped when the CLI is absent \u2014 never a mocked clean-tree claim).\n- **R9:** `/flow-next:impl-review` routes `BACKEND==\"cursor\"` to `workflow-cursor.md`; `/flow-next:plan-review` and `/flow-next:spec-completion-review` handle `cursor`; every user-facing `--review=rp|codex|copilot|none` string includes `cursor`.\n- **R10:** `flow-next-setup` `review.backend` config accepts `cursor` and spec form `cursor:gpt-5.5-high`.\n- **R11:** Tests: `test_cursor_run_exec.py` (mock subprocess: success / `is_error` / timeout / **first-call-omits-resume** / **resume-passes-id** / **cwd=repo_root** / **mode-ask-flag** / **prompt-too-large**), `test_backend_spec.py` cursor cases (model-yes/effort-no). Receipt-schema `mode:\"cursor\"` + the `effort`-absent assertion are the review-command tests (R14, task .2). Full Python suite passes.\n- **R12:** `scripts/sync-codex.sh` regenerated; `cursor` surfaces in the codex mirror; install/sync parity tests pass.\n- **R13:** Docs chain updated at the concrete targets below; **no version bump** (batched), entries under `## Unreleased`:\n  - **Repo:** `plugins/flow-next/docs/flowctl.md` (cmd list L14 + new cursor backend section), `README.md` (L44 / L253 / L290 backend lists), `GLOSSARY.md` (L29 \"Backends:\" list), root `CHANGELOG.md` `## Unreleased`.\n  - **flow-next.dev:** `src/content/docs/review/workflow.mdx` (flip the live \"coming next release\" Cursor row \u2192 shipped) + `review/receipts.mdx` + `install.mdx` backend enumeration + `releases/changelog.mdx`. **No `FLOW_NEXT_VERSION` / `package.json` bump in this spec** \u2014 the docs-site version bump is release-only (batched), same rule as the plugin. No new page \u2192 navbars unchanged. Run `pnpm build`.\n  - **AI-x-SDLC:** `guides/flow-next.md` (L65 \"(RepoPrompt, OpenAI Codex, GitHub Copilot)\" \u2192 add Cursor), `guides/code-review-tools-changelog.md`.\n  - **GrowthFactors:** `spec/05-cross-model-review.md` (claim already lists Cursor \u2014 verify/tighten), re-render `dist/gf.html` (+ `shd`/`shopfully`/`flooid`) and the bundled `~/work/AI-x-SDLC-Starter-Kit/resources/assets/code-factory-onboarding.html`.\n  - **Obsidian vault:** the cross-model-review / Skills Catalog / Release Timeline note(s).\n- **R14:** Cursor `impl-review` / `completion-review` receipts carry the same **rigor fields** as copilot \u2014 confidence-rubric anchors, suppressed-finding counts, introduced-vs-pre_existing classification, unaddressed-R-ID surfacing, protected-path filtering \u2014 asserted by a parity test scoped to **those rigor fields only**, which **also asserts `effort` is absent** (cursor must never write it; effort is not a cursor field).\n\n## Boundaries\n\n- **No new host platform** (Cursor-as-primary-driver already exists).\n- **No behavior change** to `rp`/`codex`/`copilot`/`none`, or to the trivial-diff triage judge (stays `codex|copilot`).\n- **CLI only.** No Cursor MCP/API/HTTP \u2014 `cursor-agent` subprocess only.\n- **No new review features.** Pure parity port \u2014 same phases, receipt schema, verdict grammar.\n- **No new flow-next.dev page** \u2192 both navbars untouched.\n- **No version bump / release** (staged under `## Unreleased`).\n- **RP-style window/session UI** not applicable \u2014 cursor is headless like codex/copilot.\n\n## Decision Context\n\nCursor is the obvious fourth backend: `cursor-agent` is installed, its headless\n`-p --output-format json` contract is clean (`.result` + `.session_id`), it exposes\nreviewer models the others can't reach together (`gpt-5.5-high` 1M, the\n`gpt-5.3-codex` family, `composer-2.5`, Opus-4.8-thinking), billed against the\nCursor subscription, and the GF cross-model-review spec already advertises it.\n\nChosen approach: **mirror `copilot` (fn-28) exactly**. Closest structural match \u2014\nboth headless CLIs with `-p`, JSON result, session UUID, `--resume`. The only new\nwrinkle is the model-yes/effort-no registry shape, which the existing parser\nalready handles, so it costs a test not new code.\n\nRejected: (a) Cursor MCP/HTTP \u2014 heavier, no upside, inconsistent; (b) reusing\n`codex` since both run GPT-5.5 \u2014 different CLI/auth/billing/strings, no\nComposer/Opus-via-Cursor; (c) effort-translation layer \u2014 needless; Cursor's own\nstrings are canonical, stored verbatim.\n\n### Smoke-test evidence (verified live, cursor-agent v2026.06)\n1. JSON contract parses (`type:result, is_error:false, result, session_id`).\n2. Real review on a planted diff (`a+b`\u2192`a-b`, missing zero-guard) found both bugs, `VERDICT=NEEDS_WORK`.\n3. Read-only `--mode ask` refused a file-write; tree clean.\n4. `--resume <sid>` recalled prior context headless (continuity confirmed).\n5. 60KB argv prompt round-tripped on POSIX.\n6. Registry-only monkeypatch made `parse`/`resolve`/lenient accept `cursor`/`cursor:<model>`, reject effort, list models \u2014 zero parser edits.\n\n### Dogfood (this spec, reviewed by the backend it specifies)\nRan a `cursor-agent` **gpt-5.5-high** read-only plan-review of fn-74 against the\nlive repo (228s, ~102K input / 662K cache-read tokens). It verified the cited code\nanchors and returned `VERDICT=NEEDS_WORK` with 4 valid corrections, now folded in:\n(a) **session is resume-only** \u2014 capture Cursor's generated id, don't fabricate a\nfirst-call `--resume` [R3/R7]; (b) **`cwd=repo_root` required** for repo scoping\n[R3]; (c) **triage \"deterministic whitelist\" was imprecise** \u2014 true only with the\njudge off; opt-in judge stays codex/copilot and is a documented cursor-user\ndependency [\u00a78]; (d) **receipt parity** \u2014 omit `effort`, carry copilot's rigor\nfields [R14, R5, R11]. Proves the backend works end-to-end on a real spec.\n\nNatural task seams: (1) flowctl core (registry + helpers + subcommands + handlers +\ndispatch + unit tests), (2) skill/setup wiring + codex-mirror regen, (3) docs +\ndownstream chain.\n\n## Plan (4 tasks)\n\nDecomposed into 4 sequential tasks (a parity port is inherently code \u2192 wire \u2192 document); the flowctl core is split into **proof** + **commands** so each fits one `/flow-next:work` iteration.\n\n1. **`.1` \u2014 flowctl cursor foundation** (M, no deps \u00b7 **early proof**) \u2014 registry entry + `require_cursor`/`get_cursor_version`/`run_cursor_exec` + `cursor check` + parser/run-exec tests. \u2192 R1, R2, R3, R4, R11\n2. **`.2` \u2014 cursor review commands** (M, deps .1) \u2014 5 subcommands + `cmd_cursor_*` handlers + validator/deep dispatch + own-mode `mode:\"cursor\"` receipts (resume-guard, rigor parity, clean-tree live test). \u2192 R5, R6, R7, R8, R11, R14\n3. **`.3` \u2014 skill + setup wiring + codex mirror** (M\u2013L, deps .2) \u2014 `workflow-cursor.md` \u00d72 + plan-review section + `--review` literals (8 files) + setup config + `sync-codex.sh` regen. \u2192 R9, R10, R12\n4. **`.4` \u2014 docs + downstream chain** (M, deps .3) \u2014 repo docs + flow-next.dev (flip the already-live \"coming\" Cursor row \u2192 shipped) + AI\u00d7SDLC + GF + vault. No version bump. \u2192 R13\n\n### Early proof point\nTask `.1` proves the `cursor-agent` contract end-to-end (`run_cursor_exec` + `check` + `BackendSpec` parse/resolve). Already de-risked by the spec's live smoke-tests + dogfood; if `.1` nonetheless fails, re-examine the cursor-agent CLI contract before `.2`+.\n\n### Strategy Alignment\n- **Cross-model review** \u2014 adds a fourth reviewer backend (Cursor: gpt-5.5-high / codex / composer / opus), widening the disagreement surface and letting teams bill review to an existing Cursor subscription.\n- **Host agent IS the intelligence / lean flowctl** \u2014 pure parity port: a ~6-line registry entry + mirrored helpers; no new architecture, no new skill/command, no second-LLM-spawn-from-flowctl.\n\n### Requirement coverage\n\n| Req | Task(s) |\n|-----|---------|\n| R1 registry / resolve | .1 |\n| R2 spec grammar (model-yes/effort-no) | .1 |\n| R3 run_cursor_exec | .1 |\n| R4 cursor check | .1 |\n| R5 impl-review receipt mode:cursor | .2 |\n| R6 plan/completion/validate/deep dispatch | .2 |\n| R7 session-resume guard | .2 |\n| R8 read-only / clean tree | .2 (live test) \u00b7 .1 (`--mode ask` flag) |\n| R9 skill routing + --review literals | .3 |\n| R10 setup config | .3 |\n| R11 tests | .1, .2 |\n| R12 codex mirror | .3 |\n| R13 docs chain | .4 |\n| R14 receipt rigor parity | .2 |\n\n### Soft sequencing note\nfn-54 (eval-driven prompt optimization, 0 tasks) also edits the review `workflow*.md` files \u2014 coordinate on those edits if fn-54 activates concurrently. Not a hard dependency (spec-scout: standalone).\n",
    "mergeBaseTracker": "# fn-74 Cursor review backend (cursor-agent CLI \u2014 gpt-5.5/codex/opus)\n\n## Goal & Context\n\nflow-next ships three second-model **review backends** today \u2014 `rp` (RepoPrompt),\n`codex` (OpenAI Codex CLI), `copilot` (GitHub Copilot CLI) \u2014 selected via the\n`BACKEND_REGISTRY` in `plugins/flow-next/scripts/flowctl.py` and consumed by\n`/flow-next:impl-review`, `/flow-next:plan-review`, `/flow-next:spec-completion-review`.\nThere is **no `cursor` backend**. Cursor is already supported as a *primary host\ndriver* (the `CURSOR_AGENT`/`install-cursor.sh` path in `flow-next-setup`) \u2014 a\n**different integration point**, out of scope here.\n\nAdd `cursor` as a first-class review backend that shells out to the **`cursor-agent`\nCLI** (installed locally, v2026.06). It unlocks Cursor-billed review (the user's\nexisting Cursor subscription, no separate API key) and Cursor reviewer models the\nothers can't reach in one place: `gpt-5.5-high` (1M ctx, the default), the\n`gpt-5.3-codex` family, `composer-2.5`, `claude-opus-4-8-thinking-high`.\n\nParity port of the most-recent backend (`copilot`, fn-28) \u2014 no new review *features*,\nno new architecture. The headless contract was verified live and the spec was then\n**dogfooded through a `cursor-agent` gpt-5.5-high plan-review of itself** (see\nDecision Context), which corrected the session/repo-scope/triage contracts below.\n\n**Doc-drift this closes:** the GrowthFactors cross-model-review spec\n(`~/work/code-factory-package/spec/05-cross-model-review.md`) **already advertises**\n\"Cursor via its `cursor-agent` headless CLI\" as a supported review backend. That\nclaim is currently false. fn-74 makes the already-published claim true.\n\n## Architecture & Data Models\n\nMirror the `copilot` backend end-to-end. Paths in\n`plugins/flow-next/scripts/flowctl.py` unless noted.\n\n**Verified `cursor-agent` contract** (probed live + dogfood plan-review):\n- Invocation: `cursor-agent -p --output-format json --trust --mode ask --model <model> [--resume <session_id>] \"<prompt>\"`, run with **`cwd=repo_root`** (Cursor scopes to the workspace dir; without it a review launched from a subdir reads the wrong tree \u2014 copilot's `--add-dir <repo_root>` analog).\n- `--mode ask` = read-only Q&A; the CLI **refuses to edit** in this mode (verified). Reviewer never mutates the tree.\n- `--trust` is **mandatory** headless or the CLI blocks on a \"Workspace Trust Required\" prompt and hangs.\n- Result JSON: `{\"type\":\"result\",\"subtype\":\"success\",\"is_error\":false,\"result\":\"<text>\",\"session_id\":\"<uuid>\",\"usage\":{...}}`. Parse `.result`, `.session_id`, `.is_error`.\n- **Session model = resume-only (like copilot's Windows/stdin path, NOT its POSIX create-or-resume).** First call: **omit `--resume`**, let Cursor generate `session_id`, capture it from the result, store in the receipt. Continuation: pass `--resume <stored_session_id>`. Verified: a generated id resumes prior history non-interactively under `-p`. Never pass a caller-fabricated uuid as `--resume` on the first call.\n- Auth: stored login creds OR `CURSOR_API_KEY`. `--list-models` is the source of truth for model strings; `cursor-agent --version` \u2192 `2026.06.xx-<hash>` for `check`.\n\n**Components to add (copilot is the template):**\n\n1. **Registry entry** \u2014 `BACKEND_REGISTRY` (~L3449). NEW shape: model accepted,\n   **effort folded into the model name** (Cursor convention) so `efforts: None`:\n   ```python\n   \"cursor\": {\n       \"models\": {\"auto\", \"gpt-5.5-high\", \"gpt-5.4-high\", \"gpt-5.3-codex\",\n                  \"gpt-5.3-codex-high\", \"gpt-5.3-codex-xhigh\", \"gpt-5.2\",\n                  \"composer-2.5\", \"claude-opus-4-8-thinking-high\",\n                  \"claude-opus-4-7-thinking-high\"},\n       \"efforts\": None,            # Cursor bakes reasoning effort into the model name\n       \"default_model\": \"gpt-5.5-high\",\n   },\n   ```\n   `VALID_BACKENDS` (~L3510) derives \u2192 free. **Verified: existing `BackendSpec.parse`/`.resolve` + `parse_backend_spec_lenient` handle this model-yes/effort-no shape with no parser edits.**\n\n2. **Helpers** (mirror `require_copilot`/`get_copilot_version`/`run_copilot_exec` ~L3786-3967):\n   - `require_cursor()` / `get_cursor_version()`.\n   - `run_cursor_exec(prompt, session_id=None, *, spec, repo_root) -> (result_text, returned_session_id, exit_code, stderr)` \u2014 `session_id` is **optional input** (None on first call \u2192 omit `--resume`; non-None \u2192 `--resume <id>`), and the **returned** session id (parsed from `.result` JSON) is what the caller persists. Run with `cwd=repo_root`, `--trust --mode ask`, `timeout=600`; non-zero on `is_error`/timeout/CLI failure. Reuse copilot's argv-vs-temp prompt threshold (POSIX argv handles 60KB \u2014 verified).\n\n3. **CLI subcommands** (mirror the `copilot` parser block ~L25968): a `cursor` subparser with `check`, `impl-review`, `plan-review`, `completion-review`, `validate`, `deep-pass` \u2014 same args as copilot (incl. `check --skip-probe`).\n\n4. **Command handlers** (mirror `cmd_copilot_*` ~L22405+, and shared dispatchers `_run_validator_pass`/deep-pass at L19245 / L19902 / L23606): add `elif backend == \"cursor\":` branches + `cmd_cursor_*`. **Receipts must match the copilot field set** \u2014 `mode:\"cursor\"`, `spec:\"cursor:<model>\"`, `model:<model>`, **no `effort` key** (effort is invalid for cursor), plus the same confidence/classification rubric injection, suppressed-count, introduced-vs-pre_existing, unaddressed-R-ID, and protected-path handling copilot already does.\n\n5. **Resolution plumbing** \u2014 `resolve_review_spec` (~L3691) is backend-generic. Env fill: `FLOW_CURSOR_MODEL` (no `FLOW_CURSOR_EFFORT`). The `review-backend` resolver already flows from the registry (verified: `config set review.backend` stores without a separate allowlist; resolution parses via the registry) \u2014 config/env/per-task/spec-form accept `cursor` automatically once registered.\n\n6. **Skill wiring:**\n   - `flow-next-impl-review`: new `workflow-cursor.md` (mirror `workflow-copilot.md`); add the `cursor` row to the Phase-0 dispatch table in `workflow-common.md`.\n   - `flow-next-plan-review`: add a `cursor` section to `workflow.md`.\n   - `flow-next-spec-completion-review`: add `cursor` to its `workflow-common.md`.\n   - All three SKILL.md + their `commands/flow-next/*.md`: `--review=rp|codex|copilot|cursor|none`.\n\n7. **Setup**: `flow-next-setup` `review.backend` config prompt/validation accepts `cursor` and spec form `cursor:gpt-5.5-high`.\n\n8. **Triage LLM judge stays `codex|copilot`** (`--backend choices=[\"codex\",\"copilot\"]`, L25558 \u2014 the *opt-in* judge for ambiguous diffs, default-off behind `FLOW_TRIAGE_LLM`). Do NOT add cursor there. **Precise truth:** with the LLM judge **off (the default)** cursor reviews use the deterministic whitelist \u2014 zero extra dependency. A cursor user who opts into `FLOW_TRIAGE_LLM=1` gets the `codex` judge and therefore needs codex/copilot present \u2014 **document this, do not auto-wire a cursor judge**. (Keeping cursor out is the lean choice; the judge is a cheap separate concern.)\n\n9. **Codex mirror**: regenerate via `scripts/sync-codex.sh` (never hand-edit `plugins/flow-next/codex/**`); install/sync parity tests stay green.\n\n## API Contracts\n\n- `run_cursor_exec(prompt: str, session_id: Optional[str]=None, *, spec: BackendSpec|None, repo_root: Path) -> tuple[str, str, int, str]` \u2192 `(result_text, returned_session_id, exit_code, stderr)`; `session_id=None` \u21d2 first call (no `--resume`); non-zero exit on `is_error`/CLI-failure/600s timeout; always invoked with `cwd=repo_root`.\n- `flowctl cursor check [--json] [--skip-probe]` \u2192 `{available, version, authed}` (schema aligned to copilot's `check`).\n- `flowctl cursor impl-review <task> --base <ref> --receipt <path> [--spec cursor:<model>] [--json]`\n- `flowctl cursor plan-review <spec> [--files ...] --receipt <path> [--json]`\n- `flowctl cursor completion-review <spec> --receipt <path> [--json]`\n- `flowctl cursor validate --findings-file <jsonl> --receipt <path> [--json]`\n- `flowctl cursor deep-pass --pass <name> --primary-findings <jsonl> --receipt <path> [--json]`\n- Receipt (impl): `{\"type\":\"impl_review\",\"id\":\"<id>\",\"mode\":\"cursor\",\"verdict\":\"SHIP|NEEDS_WORK|MAJOR_RETHINK\",\"session_id\":\"<uuid>\",\"model\":\"<model>\",\"spec\":\"cursor:<model>\",\"timestamp\":\"...\"}` \u2014 **no `effort` key**; same additive validator/deep/walkthrough blocks + rigor fields as copilot.\n- Spec grammar (verified): `cursor` | `cursor:<model>` valid; `cursor:<model>:<effort>` \u2192 ValueError (\"does not accept an effort\"); unknown model \u2192 ValueError listing valid models.\n\n## Edge Cases & Constraints\n\n- **NEW registry shape (model-yes / effort-no) \u2014 VERIFIED OK.** Existing parser raises on effort, resolves `default_model` with effort `None`, no KeyError. Lock with tests.\n- **Session = resume-only \u2014 VERIFIED.** Caller must not fabricate a first-call `--resume` id; capture and persist Cursor's returned `session_id`, resume with it only when the receipt at the path has `mode == \"cursor\"` (cross-backend \u2192 fresh). Mirrors copilot's Windows path, not its POSIX path.\n- **Repo scoping \u2014 REQUIRED.** `run_cursor_exec` runs with `cwd=repo_root`; add a test that invokes from a subdirectory and confirms the correct tree is reviewed.\n- **`--trust` mandatory** headless or the CLI hangs on a trust prompt.\n- **Read-only \u2014 VERIFIED.** `--mode ask` refused a \"create a file\" instruction; tree stayed clean. R8 asserts `git status` unchanged across a review.\n- **Oversized prompts \u2014 VERIFIED on POSIX (60KB positional argv).** cursor-agent takes the prompt as a **positional argument** (not stdin). Up to the threshold, pass it positionally. **Above the threshold there is no safe path yet:** copilot's temp-file step just reads the file back into argv (it does NOT bypass any cap), and cursor-agent stdin support is unconfirmed \u2192 `run_cursor_exec` must raise an **explicit \"prompt too large\" error** above the threshold (with a test), NOT silently reuse the read-back-into-argv trick. Implement a stdin path only if cursor-agent confirms stdin input. (The Windows `CreateProcessW` cap is where this bites first.)\n- **Triage precision** \u2014 see Architecture \u00a78: deterministic by default; opt-in LLM judge stays codex/copilot and is a documented dependency for cursor users who enable it.\n- **Auth not configured** \u2192 `check` and runners surface a clear error pointing at `cursor-agent` login / `CURSOR_API_KEY` (never a silent empty review).\n- **`.result` empty / `is_error:true`** \u2192 backend failure (non-zero exit + stderr), never a false SHIP.\n- **Effort must not leak** \u2014 copying copilot receipt code literally risks writing `effort:\"high\"`; cursor receipts must omit `effort` (assert in tests).\n- **Model-list drift** \u2014 Cursor ships model strings without changelog (and auto-updates the CLI); document \"keep synced with `cursor-agent --list-models`\", copilot-style note.\n- **Not the host driver.** Independent of the `CURSOR_AGENT` host-platform path; works on any host with `cursor-agent` installed.\n\n## Acceptance Criteria\n\n- **R1:** `cursor` is in `BACKEND_REGISTRY` and `VALID_BACKENDS`; `flowctl review-backend` reports `cursor` from `.flow/config.json` + `FLOW_REVIEW_BACKEND` (its only two sources); per-task `default_review` and `--spec cursor:<model>` resolve via `resolve_review_spec` / the review commands (NOT `review-backend`).\n- **R2:** `BackendSpec.parse(\"cursor\")` / `parse(\"cursor:gpt-5.5-high\")` succeed; `parse(\"cursor:gpt-5.5-high:high\")` raises (effort rejected); `parse(\"cursor:bogus\")` raises listing valid models; `.resolve()` fills `gpt-5.5-high`, effort `None`.\n- **R3:** `run_cursor_exec` shells `cursor-agent -p --output-format json --trust --mode ask --model <m>` with `cwd=repo_root`; on a first call it omits `--resume` and returns Cursor's generated `session_id`; on continuation it passes `--resume <session_id>`; parses `.result`/`.session_id`/`.is_error`; returns non-zero on a 600s timeout.\n- **R4:** `flowctl cursor check [--skip-probe]` reports availability + version + auth (`authed`) in text and `--json`, schema-aligned to copilot's `check`.\n- **R5:** `flowctl cursor impl-review <task> --base <b> --receipt <r>` writes a `mode:\"cursor\"` receipt (no `effort` key) and prints `VERDICT=...`.\n- **R6:** `cursor plan-review`, `completion-review`, `validate`, `deep-pass` dispatch through `run_cursor_exec` and write the same additive receipt shapes as codex/copilot (`mode:\"cursor\"`).\n- **R7:** Re-review with an existing `mode==\"cursor\"` receipt resumes via `--resume <session_id>` (using the persisted returned id); a cross-backend receipt starts fresh.\n- **R8:** A cursor review leaves the working tree unchanged. Unit-level: `run_cursor_exec` is asserted to pass `--mode ask` (read-only) and never an edit/write flag. Integration-level: an **optional live smoke test gated on `cursor-agent` availability** runs a real `cursor impl-review` against a temp git repo and asserts `git status` is identical before/after (skipped when the CLI is absent \u2014 never a mocked clean-tree claim).\n- **R9:** `/flow-next:impl-review` routes `BACKEND==\"cursor\"` to `workflow-cursor.md`; `/flow-next:plan-review` and `/flow-next:spec-completion-review` handle `cursor`; every user-facing `--review=rp|codex|copilot|none` string includes `cursor`.\n- **R10:** `flow-next-setup` `review.backend` config accepts `cursor` and spec form `cursor:gpt-5.5-high`.\n- **R11:** Tests: `test_cursor_run_exec.py` (mock subprocess: success / `is_error` / timeout / **first-call-omits-resume** / **resume-passes-id** / **cwd=repo_root** / **mode-ask-flag** / **prompt-too-large**), `test_backend_spec.py` cursor cases (model-yes/effort-no). Receipt-schema `mode:\"cursor\"` + the `effort`-absent assertion are the review-command tests (R14, task .2). Full Python suite passes.\n- **R12:** `scripts/sync-codex.sh` regenerated; `cursor` surfaces in the codex mirror; install/sync parity tests pass.\n- **R13:** Docs chain updated at the concrete targets below; **no version bump** (batched), entries under `## Unreleased`:\n  - **Repo:** `plugins/flow-next/docs/flowctl.md` (cmd list L14 + new cursor backend section), `README.md` (L44 / L253 / L290 backend lists), `GLOSSARY.md` (L29 \"Backends:\" list), root `CHANGELOG.md` `## Unreleased`.\n  - **flow-next.dev:** `src/content/docs/review/workflow.mdx` (flip the live \"coming next release\" Cursor row \u2192 shipped) + `review/receipts.mdx` + `install.mdx` backend enumeration + `releases/changelog.mdx`. **No `FLOW_NEXT_VERSION` / `package.json` bump in this spec** \u2014 the docs-site version bump is release-only (batched), same rule as the plugin. No new page \u2192 navbars unchanged. Run `pnpm build`.\n  - **AI-x-SDLC:** `guides/flow-next.md` (L65 \"(RepoPrompt, OpenAI Codex, GitHub Copilot)\" \u2192 add Cursor), `guides/code-review-tools-changelog.md`.\n  - **GrowthFactors:** `spec/05-cross-model-review.md` (claim already lists Cursor \u2014 verify/tighten), re-render `dist/gf.html` (+ `shd`/`shopfully`/`flooid`) and the bundled `~/work/AI-x-SDLC-Starter-Kit/resources/assets/code-factory-onboarding.html`.\n  - **Obsidian vault:** the cross-model-review / Skills Catalog / Release Timeline note(s).\n- **R14:** Cursor `impl-review` / `completion-review` receipts carry the same **rigor fields** as copilot \u2014 confidence-rubric anchors, suppressed-finding counts, introduced-vs-pre_existing classification, unaddressed-R-ID surfacing, protected-path filtering \u2014 asserted by a parity test scoped to **those rigor fields only**, which **also asserts `effort` is absent** (cursor must never write it; effort is not a cursor field).\n\n## Boundaries\n\n- **No new host platform** (Cursor-as-primary-driver already exists).\n- **No behavior change** to `rp`/`codex`/`copilot`/`none`, or to the trivial-diff triage judge (stays `codex|copilot`).\n- **CLI only.** No Cursor MCP/API/HTTP \u2014 `cursor-agent` subprocess only.\n- **No new review features.** Pure parity port \u2014 same phases, receipt schema, verdict grammar.\n- **No new flow-next.dev page** \u2192 both navbars untouched.\n- **No version bump / release** (staged under `## Unreleased`).\n- **RP-style window/session UI** not applicable \u2014 cursor is headless like codex/copilot.\n\n## Decision Context\n\nCursor is the obvious fourth backend: `cursor-agent` is installed, its headless\n`-p --output-format json` contract is clean (`.result` + `.session_id`), it exposes\nreviewer models the others can't reach together (`gpt-5.5-high` 1M, the\n`gpt-5.3-codex` family, `composer-2.5`, Opus-4.8-thinking), billed against the\nCursor subscription, and the GF cross-model-review spec already advertises it.\n\nChosen approach: **mirror `copilot` (fn-28) exactly**. Closest structural match \u2014\nboth headless CLIs with `-p`, JSON result, session UUID, `--resume`. The only new\nwrinkle is the model-yes/effort-no registry shape, which the existing parser\nalready handles, so it costs a test not new code.\n\nRejected: (a) Cursor MCP/HTTP \u2014 heavier, no upside, inconsistent; (b) reusing\n`codex` since both run GPT-5.5 \u2014 different CLI/auth/billing/strings, no\nComposer/Opus-via-Cursor; (c) effort-translation layer \u2014 needless; Cursor's own\nstrings are canonical, stored verbatim.\n\n### Smoke-test evidence (verified live, cursor-agent v2026.06)\n1. JSON contract parses (`type:result, is_error:false, result, session_id`).\n2. Real review on a planted diff (`a+b`\u2192`a-b`, missing zero-guard) found both bugs, `VERDICT=NEEDS_WORK`.\n3. Read-only `--mode ask` refused a file-write; tree clean.\n4. `--resume <sid>` recalled prior context headless (continuity confirmed).\n5. 60KB argv prompt round-tripped on POSIX.\n6. Registry-only monkeypatch made `parse`/`resolve`/lenient accept `cursor`/`cursor:<model>`, reject effort, list models \u2014 zero parser edits.\n\n### Dogfood (this spec, reviewed by the backend it specifies)\nRan a `cursor-agent` **gpt-5.5-high** read-only plan-review of fn-74 against the\nlive repo (228s, ~102K input / 662K cache-read tokens). It verified the cited code\nanchors and returned `VERDICT=NEEDS_WORK` with 4 valid corrections, now folded in:\n(a) **session is resume-only** \u2014 capture Cursor's generated id, don't fabricate a\nfirst-call `--resume` [R3/R7]; (b) **`cwd=repo_root` required** for repo scoping\n[R3]; (c) **triage \"deterministic whitelist\" was imprecise** \u2014 true only with the\njudge off; opt-in judge stays codex/copilot and is a documented cursor-user\ndependency [\u00a78]; (d) **receipt parity** \u2014 omit `effort`, carry copilot's rigor\nfields [R14, R5, R11]. Proves the backend works end-to-end on a real spec.\n\nNatural task seams: (1) flowctl core (registry + helpers + subcommands + handlers +\ndispatch + unit tests), (2) skill/setup wiring + codex-mirror regen, (3) docs +\ndownstream chain.\n\n## Plan (4 tasks)\n\nDecomposed into 4 sequential tasks (a parity port is inherently code \u2192 wire \u2192 document); the flowctl core is split into **proof** + **commands** so each fits one `/flow-next:work` iteration.\n\n1. **`.1` \u2014 flowctl cursor foundation** (M, no deps \u00b7 **early proof**) \u2014 registry entry + `require_cursor`/`get_cursor_version`/`run_cursor_exec` + `cursor check` + parser/run-exec tests. \u2192 R1, R2, R3, R4, R11\n2. **`.2` \u2014 cursor review commands** (M, deps .1) \u2014 5 subcommands + `cmd_cursor_*` handlers + validator/deep dispatch + own-mode `mode:\"cursor\"` receipts (resume-guard, rigor parity, clean-tree live test). \u2192 R5, R6, R7, R8, R11, R14\n3. **`.3` \u2014 skill + setup wiring + codex mirror** (M\u2013L, deps .2) \u2014 `workflow-cursor.md` \u00d72 + plan-review section + `--review` literals (8 files) + setup config + `sync-codex.sh` regen. \u2192 R9, R10, R12\n4. **`.4` \u2014 docs + downstream chain** (M, deps .3) \u2014 repo docs + flow-next.dev (flip the already-live \"coming\" Cursor row \u2192 shipped) + AI\u00d7SDLC + GF + vault. No version bump. \u2192 R13\n\n### Early proof point\nTask `.1` proves the `cursor-agent` contract end-to-end (`run_cursor_exec` + `check` + `BackendSpec` parse/resolve). Already de-risked by the spec's live smoke-tests + dogfood; if `.1` nonetheless fails, re-examine the cursor-agent CLI contract before `.2`+.\n\n### Strategy Alignment\n- **Cross-model review** \u2014 adds a fourth reviewer backend (Cursor: gpt-5.5-high / codex / composer / opus), widening the disagreement surface and letting teams bill review to an existing Cursor subscription.\n- **Host agent IS the intelligence / lean flowctl** \u2014 pure parity port: a ~6-line registry entry + mirrored helpers; no new architecture, no new skill/command, no second-LLM-spawn-from-flowctl.\n\n### Requirement coverage\n\n| Req | Task(s) |\n|-----|---------|\n| R1 registry / resolve | .1 |\n| R2 spec grammar (model-yes/effort-no) | .1 |\n| R3 run_cursor_exec | .1 |\n| R4 cursor check | .1 |\n| R5 impl-review receipt mode:cursor | .2 |\n| R6 plan/completion/validate/deep dispatch | .2 |\n| R7 session-resume guard | .2 |\n| R8 read-only / clean tree | .2 (live test) \u00b7 .1 (`--mode ask` flag) |\n| R9 skill routing + --review literals | .3 |\n| R10 setup config | .3 |\n| R11 tests | .1, .2 |\n| R12 codex mirror | .3 |\n| R13 docs chain | .4 |\n| R14 receipt rigor parity | .2 |\n\n### Soft sequencing note\nfn-54 (eval-driven prompt optimization, 0 tasks) also edits the review `workflow*.md` files \u2014 coordinate on those edits if fn-54 activates concurrently. Not a hard dependency (spec-scout: standalone).\n",
    "url": "https://linear.app/gmickel/issue/FLOW-22"
  },
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

===== [5/11] git_status: `git status` =====
On branch fn-258-smaller-default-outputs-and-bundles
Your branch is ahead of 'origin/main' by 1 commit.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   agent_docs/adding-skills.md
	modified:   optimization/worker-anchor/run_eval.py
	modified:   plugins/flow-next/agents/repo-scout.md
	modified:   plugins/flow-next/agents/spec-scout.md
	modified:   plugins/flow-next/agents/worker.md
	modified:   plugins/flow-next/codex/agents/repo-scout.toml
	modified:   plugins/flow-next/codex/agents/spec-scout.toml
	modified:   plugins/flow-next/codex/agents/worker.toml
	modified:   plugins/flow-next/codex/docs/flow-next/flowctl.md
	modified:   plugins/flow-next/codex/docs/flow-next/glossary.md
	modified:   plugins/flow-next/codex/skills/flow-next-capture/workflow.md
	modified:   plugins/flow-next/codex/skills/flow-next-features/SKILL.md
	modified:   plugins/flow-next/codex/skills/flow-next-impl-review/workflow-codex.md
	modified:   plugins/flow-next/codex/skills/flow-next-impl-review/workflow-host.md
	modified:   plugins/flow-next/codex/skills/flow-next-impl-review/workflow-rp.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/SKILL.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-claude.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-codex.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-copilot.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-cursor.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-host.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-rp.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan/references/selected-review.md
	modified:   plugins/flow-next/codex/skills/flow-next-refine/references/pass-business.md
	modified:   plugins/flow-next/codex/skills/flow-next-resolve-pr/SKILL.md
	modified:   plugins/flow-next/codex/skills/flow-next-resolve-pr/workflow.md
	modified:   plugins/flow-next/codex/skills/flow-next-setup/templates/agents-md-snippet.md
	modified:   plugins/flow-next/codex/skills/flow-next-setup/templates/claude-md-snippet.md
	modified:   plugins/flow-next/codex/skills/flow-next-setup/workflow.md
	modified:   plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow-host.md
	modified:   plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow-rp.md
	modified:   plugins/flow-next/codex/skills/flow-next-tracker-sync/references/adapter-interface.md
	modified:   plugins/flow-next/codex/skills/flow-next-tracker-sync/references/body-merge.md
	modified:   plugins/flow-next/codex/skills/flow-next-tracker-sync/references/comments-sync.md
	modified:   plugins/flow-next/codex/skills/flow-next-tracker-sync/references/status-sync.md
	modified:   plugins/flow-next/codex/skills/flow-next-work/SKILL.md
	modified:   plugins/flow-next/codex/skills/flow-next-work/phases.md
	modified:   plugins/flow-next/codex/skills/flow-next-work/references/host-deferred-review.md
	modified:   plugins/flow-next/codex/skills/flow-next/SKILL.md
	modified:   plugins/flow-next/commands/audit.md
	modified:   plugins/flow-next/commands/capture.md
	modified:   plugins/flow-next/commands/chart.md
	modified:   plugins/flow-next/commands/features.md
	modified:   plugins/flow-next/commands/flow.md
	modified:   plugins/flow-next/commands/impl-review.md
	modified:   plugins/flow-next/commands/land.md
	modified:   plugins/flow-next/commands/make-pr.md
	modified:   plugins/flow-next/commands/map.md
	modified:   plugins/flow-next/commands/memory-migrate.md
	modified:   plugins/flow-next/commands/plan-review.md
	modified:   plugins/flow-next/commands/plan.md
	modified:   plugins/flow-next/commands/prime.md
	modified:   plugins/flow-next/commands/prose.md
	modified:   plugins/flow-next/commands/prospect.md
	modified:   plugins/flow-next/commands/qa.md
	modified:   plugins/flow-next/commands/ralph-init.md
	modified:   plugins/flow-next/commands/refine.md
	modified:   plugins/flow-next/commands/resolve-pr.md
	modified:   plugins/flow-next/commands/setup.md
	modified:   plugins/flow-next/commands/spec-completion-review.md
	modified:   plugins/flow-next/commands/strategy.md
	modified:   plugins/flow-next/commands/sync.md
	modified:   plugins/flow-next/commands/tracker-sync.md
	modified:   plugins/flow-next/commands/uninstall.md
	modified:   plugins/flow-next/commands/visual.md
	modified:   plugins/flow-next/commands/work.md
	modified:   plugins/flow-next/docs/flowctl.md
	modified:   plugins/flow-next/docs/glossary.md
	modified:   plugins/flow-next/scripts/flowctl.py
	modified:   plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json
	modified:   plugins/flow-next/skills/flow-next-capture/workflow.md
	modified:   plugins/flow-next/skills/flow-next-features/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-flow/auto.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/backlog-mode.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/gate-selection.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/plan-vs-no-plan.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/route-matrix.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/tail.md
	modified:   plugins/flow-next/skills/flow-next-flow/workflow.md
	modified:   plugins/flow-next/skills/flow-next-impl-review/workflow-codex.md
	modified:   plugins/flow-next/skills/flow-next-impl-review/workflow-host.md
	modified:   plugins/flow-next/skills/flow-next-impl-review/workflow-rp.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-claude.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-codex.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-copilot.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-cursor.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-host.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow.md
	modified:   plugins/flow-next/skills/flow-next-plan/references/selected-review.md
	modified:   plugins/flow-next/skills/flow-next-refine/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-refine/references/pass-business.md
	modified:   plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-resolve-pr/workflow.md
	modified:   plugins/flow-next/skills/flow-next-setup/templates/agents-md-snippet.md
	modified:   plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md
	modified:   plugins/flow-next/skills/flow-next-setup/workflow.md
	modified:   plugins/flow-next/skills/flow-next-spec-completion-review/workflow-host.md
	modified:   plugins/flow-next/skills/flow-next-spec-completion-review/workflow-rp.md
	modified:   plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md
	modified:   plugins/flow-next/skills/flow-next-tracker-sync/references/body-merge.md
	modified:   plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md
	modified:   plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md
	modified:   plugins/flow-next/skills/flow-next-work/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-work/phases.md
	modified:   plugins/flow-next/skills/flow-next-work/references/host-deferred-review.md
	modified:   plugins/flow-next/skills/flow-next-work/references/rolling-scheduler.md
	modified:   plugins/flow-next/skills/flow-next-work/references/wave-join.md
	modified:   plugins/flow-next/skills/flow-next/SKILL.md
	modified:   plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-capture-brief.json
	modified:   plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-chart.json
	modified:   plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-interview.json
	modified:   plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-skip-chart-clear.json
	modified:   plugins/flow-next/tests/test_anchor_bundle.py
	modified:   plugins/flow-next/tests/test_flow_merge_destination.py
	modified:   plugins/flow-next/tests/test_parallel_work_prose.py
	modified:   plugins/flow-next/tests/test_pilot_chain_stages.py
	modified:   plugins/flow-next/tests/test_precheck_mode_contract.py
	modified:   plugins/flow-next/tests/test_review_convergence_cap.py
	modified:   plugins/flow-next/tests/test_setup_snippet_lockstep.py
	modified:   scripts/sync-codex.sh

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	optimization/worker-anchor/gen_fn258_inputs.py
	optimization/worker-anchor/inputs/fn-64.3/bundle-current.md
	optimization/worker-anchor/inputs/fn-64.3/bundle-lean.md
	plugins/flow-next/codex/skills/flow-next-tracker-sync/references/chart-subjects.md
	plugins/flow-next/skills/flow-next-tracker-sync/references/chart-subjects.md
	plugins/flow-next/tests/test_glossary_match.py
	plugins/flow-next/tests/test_skill_id_invocations.py

no changes added to commit (use "git add" and/or "git commit -a")

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

===== [9/11] glossary: `flowctl glossary list --json` =====
{
  "success": true,
  "groups": [
    {
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/GLOSSARY.md",
      "entries": [
        {
          "term": "Spec",
          "definition": "The unit of intent: `.flow/specs/<id>.md` (body) + `.flow/specs/<id>.json` (metadata sidecar). Reviewable on its own, cross-model reviewed, frozen at handover. One spec is a stream of work, not a sprint item \u2014 it holds acceptance criteria (R-IDs), not a to-do list.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Task, R-ID, Chart",
          "avoid": [
            "epic",
            "ticket",
            "story",
            "PRD",
            "requirements doc"
          ],
          "relates_to": [
            "Task",
            "R-ID",
            "Chart"
          ]
        },
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
          "term": "R-ID",
          "definition": "A numbered acceptance criterion in a spec, written `**R1:** ...`. Renumber-forbidden after the first review cycle: deletions leave gaps, new criteria take the next unused number. The load-bearing identity of a requirement across the spec, the tasks that satisfy it, the commits, and the PR coverage table. `G1`, `G2` in `.flow/criteria.md` are the same grammar lifted to project scope. An R-ID is judged against evidence at review; it is never required to pre-exist as an executable test (the ATDD contract, which flow-next deliberately does not adopt).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Spec, Task",
          "avoid": [
            "AC-1",
            "requirement #1",
            "renumbering",
            "req id"
          ],
          "relates_to": [
            "Spec",
            "Task"
          ]
        },
        {
          "term": "Wave",
          "definition": "A set of tasks whose dependencies are all satisfied at the same point \u2014 the parallel candidates `/flow-next:plan` reports. A wave is a scheduling fact derived from the dependency graph, not a time box and not a mandate to share one checkout: parallel workers get isolated workspaces and the conductor joins the wave before review.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Task",
          "avoid": [
            "sprint",
            "phase",
            "batch",
            "iteration"
          ],
          "relates_to": [
            "Task"
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
          "term": "Anchor",
          "definition": "Re-reading the spec, the task, and git state before work continues, so long sessions do not drift. `flowctl anchor <task-id>` is the per-task bundle a worker reads every iteration; `flowctl brief` is the cold-session equivalent. Not `/flow-next:prime`, which assesses whether a repo is ready for agents at all.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Task, Spec",
          "avoid": [
            "context refresh",
            "priming",
            "warm-up",
            "reload"
          ],
          "relates_to": [
            "Task",
            "Spec"
          ]
        },
        {
          "term": "plan-sync",
          "definition": "`/flow-next:sync` \u2014 the internal pass that updates *downstream task specs* after implementation drift, inside `.flow/`. Do not confuse it with tracker-sync (`/flow-next:tracker-sync`), which projects a spec *outward* to Linear / GitHub / GitLab / Jira and reconciles body, status, and comments. Bare \"sync\" is ambiguous and should not be used for either.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Spec, Task",
          "avoid": [
            "sync",
            "tracker-sync",
            "resync"
          ],
          "relates_to": [
            "Spec",
            "Task"
          ]
        },
        {
          "term": "Review backend",
          "definition": "The engine that performs a cross-model review: `rp` (RepoPrompt), `codex`, `copilot`, `cursor`, `claude`, `host`, or `none`, resolved by the `review.backend` grammar (env > per-spec/task > config). The backend is the review *mechanism*, distinct from the model it happens to run and from the reviewing agent's findings.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Receipt",
          "avoid": [
            "judge",
            "provider",
            "model"
          ],
          "relates_to": [
            "Receipt"
          ]
        },
        {
          "term": "Memory",
          "definition": "Categorized durable learnings under `.flow/memory/` \u2014 `bug/<category>/` and `knowledge/<category>/` entries with YAML frontmatter, searched via `flowctl memory search`. Memory is audited, superseded, and graduated into gates; it is not a scratchpad and not a substitute for docs or code comments.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Gate",
          "avoid": [
            "notes",
            "scratchpad",
            "context files",
            "learnings dump"
          ],
          "relates_to": [
            "Gate"
          ]
        },
        {
          "term": "Spine",
          "definition": "The always-loaded body of a `SKILL.md` under branch disclosure: the universal path every run needs, with branch-only content read from `references/*.md` at the branch point. A reference is the cold-path file; the spine is the hot path. Safety nets and every-run contracts stay in the spine by rule.",
          "avoid": [
            "prompt",
            "main file",
            "header",
            "preamble"
          ],
          "relates_to": []
        },
        {
          "term": "Tier",
          "definition": "What kind of model a job wants: `reviewer`, `implementer`, `fast scout`, `thinking scout`, or unset (the session model). A tier binds a model to a stage's execution, never to which stages run \u2014 which stages run is decided by what you invoked. The four names are a user-facing interface defined in exactly one place, [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants); an unrecognized name is treated as unset with one advisory.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Reach, Review backend",
          "avoid": [
            "pin",
            "model tier",
            "capability level",
            "role map"
          ],
          "relates_to": [
            "Reach",
            "Review backend"
          ]
        },
        {
          "term": "Reach",
          "definition": "How the active harness obtains a model for a tier: the in-session model, an in-host subagent, shelling out to another CLI, or not available. Documented once per harness under [`plugins/flow-next/docs/reach/`](plugins/flow-next/docs/reach/README.md) and never inside a skill \u2014 a skill asks for a tier and names no spawn primitive, CLI flag, or vendor path. An undetectable harness resolves to the generic page and says so.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier",
          "avoid": [
            "dispatch mechanism",
            "availability",
            "probe"
          ],
          "relates_to": [
            "Tier"
          ]
        },
        {
          "term": "Reviewer tier",
          "definition": "The tier for anything grading work someone else produced. The only tier carrying a family rule: a reviewer from the writer's own family is not an independent verdict. The rule is advice, not enforcement \u2014 the receipt records what ran, and nothing fails closed on it. Canonical definition: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier, Review backend",
          "avoid": [
            "grader",
            "review model",
            "critic"
          ],
          "relates_to": [
            "Tier",
            "Review backend"
          ]
        },
        {
          "term": "Implementer tier",
          "definition": "The tier for work handed to another harness \u2014 plan on the session model, implement somewhere cheaper or faster. Absent, the session model implements. Canonical definition: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier, Task",
          "avoid": [
            "bridged worker",
            "executor"
          ],
          "relates_to": [
            "Tier",
            "Task"
          ]
        },
        {
          "term": "Fast scout tier",
          "definition": "The tier for mechanical inventory scanning, where the cheapest model is the correct one. Canonical definition: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier",
          "avoid": [
            "cheap tier",
            "scanner model",
            "fast model",
            "low tier"
          ],
          "relates_to": [
            "Tier"
          ]
        },
        {
          "term": "Thinking scout tier",
          "definition": "The tier for analysis that degrades badly on a fast model \u2014 requirement analysis and pattern judgment, not scans. Canonical definition: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier",
          "avoid": [
            "judgment tier",
            "smart scout",
            "intelligent scout",
            "deep scout"
          ],
          "relates_to": [
            "Tier"
          ]
        },
        {
          "term": "Emission point",
          "definition": "A named step in a skill or agent where durable user-facing prose is drafted (make-pr body rendering, tracker-sync comment composition, capture/refine/plan spec prose, chart briefings, strategy sections, qa finding bodies, land verdict output, prospect candidates, prime glossary definitions, audit memory entries, worker done summaries, resolve-pr replies, changelog entries). Emission points cite the prose contract by path, passing the identity and never a copied payload.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "No-plan route",
          "definition": "Execution through `/flow-next:work <spec-id> --no-plan`, the default route for a ready cohesive spec and a capable coding agent. Plan is chosen only on a positive signal; the signals and the exclusions are in [`plan-vs-no-plan.md`](plugins/flow-next/skills/flow-next-flow/references/plan-vs-no-plan.md). Work records the accepted choice and creates one implicit owner task covering every spec R-ID. Resume and `flow --auto` continuation retain that route. Separate task planning and its automatic plan review are omitted; explicit spec/design review, configured implementation review, coverage, completion-review policy and opt-in QA retain their contracts.",
          "avoid": [
            "plan-less mode",
            "skip-plan flag",
            "zero-task execution"
          ],
          "relates_to": [
            "Spec",
            "Task",
            "R-ID"
          ]
        },
        {
          "term": "Feature map",
          "definition": "The committed user-POV directory (`.flow/features/`) recording how a user reaches and drives each user-facing feature, consumed by QA/drive for navigation; distinct from the code-POV `/flow-next:map` index.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Doctor",
          "definition": "The one read-only health check a drive-capable run performs before driving an instance (right build, owned port, valid auth), answering \"is this instance worth driving\".",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Routing reference",
          "definition": "The set of six small reference files the flow skill owns under `plugins/flow-next/skills/flow-next-flow/references/`, one per routing rule, progressively disclosed through step-scoped conditional pointers so the agent reads only the files the current step needs: `route-matrix.md`, `spec-count.md`, `plan-vs-no-plan.md`, `gate-selection.md`, `prototype-before-ask.md`, and `tail.md`. Each opens with a decision record. Flow, `flow --explain`, `flow --auto`, capture's closer, plan's next-steps menu, and work's zero-task ask read the same files. The same directory also holds two gated auto-only references (`backlog-mode.md`, `qa-stage.md`) that `auto.md` reads under `--backlog` and the QA gate; they are workflow, not routing rules, and carry no decision record.",
          "avoid": [],
          "relates_to": []
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
        },
        {
          "term": "Hop",
          "definition": "One route-run-re-evaluate cycle of `/flow-next:flow`: classify the item from the routing reference, run the routed stage, verify from observed state, record the outcome. Under `--auto` every hop ends with committed receipts, one evidence echo, one `stage: <name> - ran | skipped(<reason>) | failed(<reason>)` line, and a ledger write, so a run that dies mid-way resumes from disk on the next invocation; nothing is resumed from transcript. The hop is the handover unit between the driver and the pipeline.",
          "avoid": [
            "step",
            "iteration",
            "turn"
          ],
          "relates_to": [
            "Driver",
            "Tick",
            "Long-horizon run"
          ]
        },
        {
          "term": "Tick",
          "definition": "Exactly one hop of `flow --auto`, selected with `--tick`. The run classifies, dispatches one stage, verifies, records, and stops with the verdict line. A landing hop consumes at most one land tick. The portable floor for hosts without stable long sessions, run under the host's loop primitive (`/loop 30m /flow-next:flow --auto --tick`). What a `/flow-next:pilot` invocation was.",
          "avoid": [
            "pilot tick",
            "single-stage run"
          ],
          "relates_to": [
            "Hop",
            "Long-horizon run",
            "Driver",
            "Pilot"
          ]
        },
        {
          "term": "Long-horizon run",
          "definition": "The default shape of `flow --auto`: one invocation drives one ready item hop after hop until a terminal (a PR exists, deferred to land, asked, blocked, needs human, no work). With `--until=merge`, it can continue through land ticks and external waits until the selected PR is confirmed merged, or an existing stop condition applies. The verdict line names every dispatched stage in order joined by `+` (`stage=work+qa+make-pr`) and carries the last hop's verdict. One item per run; the next invocation selects the next item.",
          "avoid": [
            "multi-stage tick",
            "chained tick",
            "autopilot run"
          ],
          "relates_to": [
            "Hop",
            "Tick",
            "Verdict line"
          ]
        },
        {
          "term": "Verdict line",
          "definition": "The terminal line every `flow --auto` run and every `/flow-next:land` tick prints last, for the driver to read: `PILOT_VERDICT=<ADVANCED|ASKED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason=\"<one line>\"` and `LAND_VERDICT=...`. The `PILOT_VERDICT` name is kept unchanged across the pilot retirement so existing drivers keep parsing; `TRIAGED` appears under `--explain` and `--dry-run` only. Under a merge destination, the reason and observed evidence distinguish landing progress, external waiting, blockage, confirmed merge, and any tracker touchpoint failure; the original `LAND_VERDICT` is retained in the evidence.",
          "avoid": [
            "exit status",
            "summary line",
            "result banner"
          ],
          "relates_to": [
            "Driver",
            "Long-horizon run",
            "Tick"
          ]
        },
        {
          "term": "Pilot",
          "definition": "The deprecated alias for `/flow-next:flow --auto --tick`. Its `/flow-next:pilot` command is removed; the `flow-next-pilot` skill stub remains until the next release and maps `--spec <id>` to the positional id, passes `--backlog`, `--dry-run`, `--review`, `--research`, `--depth` through, prints one deprecation line to stderr, and behaves byte-for-byte as the tick. The spelling survives in config keys (`pilot.autonomy`, `pilot.gateClasses`), flowctl verbs (`flowctl pilot strikes`, `flowctl pilot-log`), the ledger and decision-log paths (`.flow/pilot-runs/`), and the `PILOT_VERDICT` name; those are not renamed.",
          "avoid": [
            "the pilot skill",
            "pilot loop",
            "build-loop conductor"
          ],
          "relates_to": [
            "Tick",
            "Driver",
            "Verdict line"
          ]
        },
        {
          "term": "Variant",
          "definition": "One worked route through the pipeline menu, named by its driving signal in `docs/pipeline-variations.md` and matched by a row of the route matrix: epic, feature with known requirements, no-plan, small task, bug or defect, refactoring, performance, hill climb, investigation, prototype, and docs or chore. Every variant keeps the same evidence, gate, and receipt contract; they differ only in which unknown they pay to convert.",
          "avoid": [
            "pipeline mode",
            "preset",
            "template pipeline"
          ],
          "relates_to": [
            "Routing reference",
            "No-plan route"
          ]
        },
        {
          "term": "Prototype-before-ask",
          "definition": "Classify a fork before asking the user. An answer observable by running something (behavior, output, timing, layout) is settled by a prototype or experiment. Only a product or preference call no experiment can settle becomes a question.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Refine",
          "definition": "The `/flow-next:refine` skill (`flow-next-refine`, renamed from `interview` in the flow release). A deep question pass over a spec, task, or spec file under a `business`, `technical`, or `both` scope, or the read-first research pass under `--scope=research`.",
          "avoid": [
            "interview skill",
            "interview command"
          ],
          "relates_to": []
        },
        {
          "term": "Research pass",
          "definition": "`/flow-next:refine --scope=research`: asks nothing; runs the read-only docs, practice, docs-gap, and memory scouts (github when gated on) and writes one `## Resolved via Research` section with a sub-block per scout and a source on every line. Skipped, with the reason printed, when the section or plan's scout findings already exist; `--force` reruns. Plan writes the same section when its research scouts run, so the pass never runs twice.",
          "avoid": [],
          "relates_to": [
            "Read-first signal",
            "Refine"
          ]
        },
        {
          "term": "Read-first signal",
          "definition": "The positive signal on the route matrix's ready-spec row: the spec names a library or API the repo does not already use. It sends the spec through the research pass before work on either route and is satisfied by a `## Resolved via Research` section or a plan that ran the scouts.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Why-scout",
          "definition": "The read-only agent for rationale questions. It anchors on `git blame` and the PRs behind the commits, reads the tracker thread through access the session already has, then the bug and decision memory tracks, and tiers each finding `direct`, `supported`, `inferred`, or `unknown`; the caller may not rewrite a tier. Named by the route matrix's investigation row for why questions.",
          "avoid": [],
          "relates_to": [
            "Thinking scout tier"
          ]
        },
        {
          "term": "Chain",
          "definition": "A dependent PR whose base is the parent spec's branch instead of the default branch (fn-152). Exists on any code host because it is only a branch and a base ref. A dependent spec is chain-eligible when its parent is open with every task done and its branch on origin, judged by `flowctl spec chain`, the one predicate every consumer calls; work then branches from the parent's remote tip and make-pr targets the parent's branch. Chains are linear: one open parent, one child at a time.",
          "avoid": [
            "stacked branch",
            "dependent branch",
            "branch-on-branch"
          ],
          "relates_to": [
            "Stack",
            "Layer",
            "Frontier",
            "Spec"
          ]
        },
        {
          "term": "Stack",
          "definition": "GitHub's server-side object over a chain: the linked PRs, the stack map in the merge box, sequential merge, and auto-retarget of the layers above a merged one. An enhancement of a chain, present only when the host is GitHub and make-pr's link call succeeded; on any other host, or after a failed link, the PR stands as a plain chain layer. Never a local file: the gh-stack extension is not required or read.",
          "avoid": [
            "gh-stack",
            "stacked diff",
            "Graphite stack"
          ],
          "relates_to": [
            "Chain",
            "Layer",
            "Frontier"
          ]
        },
        {
          "term": "Layer",
          "definition": "One PR in a chain or stack. The bottom layer is the open layer whose base is the chain's base branch (the default branch, or the branch a human chose); every other layer's base is the branch of the layer below it, so a reviewer sees only that layer's own diff.",
          "avoid": [
            "sub-PR",
            "child PR",
            "stacked PR"
          ],
          "relates_to": [
            "Chain",
            "Stack",
            "Frontier"
          ]
        },
        {
          "term": "Frontier",
          "definition": "The bottom open layer of a chain or stack, the only one that can merge next. Land merges at most one frontier per tick, from the bottom up; a human merging from GitHub's stack UI does the same. Distinct from the task frontier `flowctl ready` reports inside one spec.",
          "avoid": [
            "head of the stack",
            "top layer",
            "mergeable PR"
          ],
          "relates_to": [
            "Chain",
            "Stack",
            "Layer"
          ]
        }
      ],
      "count": 39
    }
  ],
  "file_count": 1,
  "total_terms": 39
}

===== [10/11] memory_index: `flowctl memory list --json` =====
{
  "success": true,
  "entries": [
    {
      "entry_id": "bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18",
      "title": "Abort-option copy must reflect pre-prompt state mutations (idempotent != no chan",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-setup/workflow.md",
      "tags": [
        "fn-45",
        "abort-option",
        "setup-skill",
        "copy-drift",
        "codex-review",
        "user-consent"
      ],
      "date": "2026-05-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18.md"
    },
    {
      "entry_id": "bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27",
      "title": "Backlog SELECT must not drop a dep-blocked item to NO_WORK \u2014 it routes to BLOCKE",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-pilot/references/backlog-mode.md",
      "tags": [
        "fn-68",
        "pilot",
        "backlog-mode",
        "skill-authoring",
        "select-vs-triage",
        "terminal-grammar",
        "rp-review",
        "review-feedback"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27.md"
    },
    {
      "entry_id": "bug/build-errors/canonical-3c-edits-vanish-from-codex-2026-08-28",
      "title": "Canonical 3c edits vanish from Codex mirror via stale SECTION3C heredoc",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh",
      "tags": [
        "fn-208",
        "sync-codex",
        "codex-mirror",
        "section3c",
        "dispatch-template",
        "codex-review"
      ],
      "date": "2026-08-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/canonical-3c-edits-vanish-from-codex-2026-08-28.md"
    },
    {
      "entry_id": "bug/build-errors/changelog-entry-landed-in-a-released-2026-08-01",
      "title": "Changelog entry landed in a released section, not Unreleased",
      "track": "bug",
      "category": "build-errors",
      "module": "CHANGELOG.md",
      "tags": [
        "changelog",
        "release",
        "docs"
      ],
      "date": "2026-08-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/changelog-entry-landed-in-a-released-2026-08-01.md"
    },
    {
      "entry_id": "bug/build-errors/codex-home-rewrite-both-spellings-2026-08-02",
      "title": "CODEX_HOME rewrite: both spellings, actionable prose, quoting, sorted-hash idemp",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh",
      "tags": [
        "codex",
        "installer",
        "generated-artifacts",
        "shell-quoting",
        "idempotency"
      ],
      "date": "2026-08-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/codex-home-rewrite-both-spellings-2026-08-02.md"
    },
    {
      "entry_id": "bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18",
      "title": "Codex mirror smoke docs miss composed transform output (abort + Other)",
      "track": "bug",
      "category": "build-errors",
      "module": "agent_docs/local-dev.md",
      "tags": [
        "sync-codex",
        "codex",
        "mirror",
        "fn-45",
        "smoke-docs",
        "AskUserQuestion",
        "abort-option"
      ],
      "date": "2026-05-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18.md"
    },
    {
      "entry_id": "bug/build-errors/concurrent-gating-draws-soft-terms-2026-08-21",
      "title": "Concurrent gating draws + soft terms falsify a 'frozen' eval pre-registration",
      "track": "bug",
      "category": "build-errors",
      "module": "agent-evals/studies/rolling-frontier-2026-08",
      "tags": [
        "fn-203",
        "eval-design",
        "pre-registration",
        "wall-clock",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/concurrent-gating-draws-soft-terms-2026-08-21.md"
    },
    {
      "entry_id": "bug/build-errors/concurrent-loop-skill-prose-linear-2026-08-22",
      "title": "Concurrent-loop skill prose: linear checklist + non-blocking claims contradict",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md",
      "tags": [
        "fn-203",
        "work-rolling",
        "scheduler",
        "event-driven",
        "plan-sync-barrier",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-22",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/concurrent-loop-skill-prose-linear-2026-08-22.md"
    },
    {
      "entry_id": "bug/build-errors/delegating-cli-wrapper-inherits-2026-08-30",
      "title": "Delegating CLI wrapper inherits delegate guards, prints, truncation, races",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-212",
        "memory-upsert",
        "delegation",
        "codex-review",
        "review-feedback",
        "concurrency"
      ],
      "date": "2026-08-30",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/delegating-cli-wrapper-inherits-2026-08-30.md"
    },
    {
      "entry_id": "bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08",
      "title": "detect/validate must require SPECS_DIR even when EPICS_DIR present",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-43",
        "rename",
        "detect",
        "validate",
        "write-location",
        "backward-compat",
        "deprecation",
        "env-vars",
        "acceptance-criteria",
        "review-feedback"
      ],
      "date": "2026-05-08",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08.md"
    },
    {
      "entry_id": "bug/build-errors/docs-activation-command-for-string-enum-2026-06-05",
      "title": "Docs activation command for string-enum config knob used bool true instead of th",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/docs/flowctl.md, .flow/usage.md",
      "tags": [
        "fn-55",
        "work.delegate",
        "config-enum",
        "docs-drift",
        "activation-predicate",
        "codex-delegation",
        "review-feedback"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/docs-activation-command-for-string-enum-2026-06-05.md"
    },
    {
      "entry_id": "bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12",
      "title": "Embedded self-check greps in reference docs need POSIX classes + whitespace tole",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/references/html-artifacts.md",
      "tags": [
        "fn-62",
        "reference-doc",
        "grep",
        "portability",
        "bsd-grep",
        "self-check",
        "copy-paste-blocks",
        "review-feedback"
      ],
      "date": "2026-06-12",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12.md"
    },
    {
      "entry_id": "bug/build-errors/env-marker-gate-must-scan-the-namespace-2026-06-04",
      "title": "Env-marker gate must scan the namespace, not a fixed var list",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-work/references/codex-delegation.md",
      "tags": [
        "fn-55",
        "skill-prose-gate",
        "env-markers",
        "opencode",
        "platform-gate",
        "codex-delegation"
      ],
      "date": "2026-06-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/env-marker-gate-must-scan-the-namespace-2026-06-04.md"
    },
    {
      "entry_id": "bug/build-errors/eval-ledger-feature-rows-must-disclaim-2026-07-18",
      "title": "Eval-ledger feature rows must disclaim the optimization ratchet + reconcile deno",
      "track": "bug",
      "category": "build-errors",
      "module": "optimization/interview",
      "tags": [
        "fn-100",
        "eval-ledger",
        "ratchet",
        "denominator-reconciliation",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-07-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/eval-ledger-feature-rows-must-disclaim-2026-07-18.md"
    },
    {
      "entry_id": "bug/build-errors/fn-44-review-cycle-lessons-2026-05-21",
      "title": "fn-44 review-cycle lessons (10+ NEEDS_WORK rounds across 4 tasks)",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-interview, plugins/flow-next/skills/flow-next-capture, plugins/flow-next/scripts/flowctl.py, scripts/sync-codex.sh, plugins/flow-next/templates/spec.md",
      "tags": [
        "fn-44",
        "scope-flag",
        "impl-review",
        "codex-review",
        "json-contract",
        "html-comments",
        "r17-cross-link",
        "r21-drift-guard",
        "merge-contract",
        "auxiliary-sections",
        "scoped-diff",
        "relative-paths",
        "codex-mirror"
      ],
      "date": "2026-05-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/fn-44-review-cycle-lessons-2026-05-21.md"
    },
    {
      "entry_id": "bug/build-errors/grep-c-prints-0-and-exits-1-echo-0-2026-07-24",
      "title": "grep -c prints 0 AND exits 1: || echo 0 yields a two-line count",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-audit/workflow.md",
      "tags": [
        "bash",
        "skill-prose",
        "grep",
        "shell-pitfall"
      ],
      "date": "2026-07-24",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/grep-c-prints-0-and-exits-1-echo-0-2026-07-24.md"
    },
    {
      "entry_id": "bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03",
      "title": "Id-grammar widening must cover the FULL command surface, not just named commands",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-52",
        "tracker-sync",
        "id-resolution",
        "canonicalizer",
        "enumeration",
        "impl-review",
        "case-rule",
        "validator-separation",
        "sync-receipt",
        "sync-defer",
        "final-integration",
        "merge-base"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03.md"
    },
    {
      "entry_id": "bug/build-errors/implementer-brief-widened-never-list-2026-09-14",
      "title": "Implementer brief widened never-list past the spec; child lost its fan-out",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/templates/usage.md",
      "tags": [
        "fn-245",
        "fn-244",
        "bridge",
        "long-task-brief",
        "never-list",
        "delegation",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-09-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/implementer-brief-widened-never-list-2026-09-14.md"
    },
    {
      "entry_id": "bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12",
      "title": "Lavish interactive-only gate must check MODE var AND env markers in-snippet",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-capture/references/html-lens.md",
      "tags": [
        "fn-62",
        "lavish",
        "skill-authoring",
        "safety-gates",
        "review-feedback",
        "html-artifacts"
      ],
      "date": "2026-06-12",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12.md"
    },
    {
      "entry_id": "bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11",
      "title": "Mirror regen exposes latent canonical gaps: path rewrites, .flow persistence, di",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-60",
        "sync-codex",
        "codex-mirror",
        "land",
        "flow-persistence",
        "tracker-dispatch",
        "ledger",
        "review-feedback",
        "release"
      ],
      "date": "2026-06-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11.md"
    },
    {
      "entry_id": "bug/build-errors/optional-side-effect-snippets-need-2026-06-12",
      "title": "Optional side-effect snippets need guarded git steps; check-ignore the exact fil",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-make-pr/html-lens.md",
      "tags": [
        "fn-62",
        "make-pr",
        "html-artifacts",
        "skill-authoring",
        "set-e",
        "check-ignore",
        "review-feedback"
      ],
      "date": "2026-06-12",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/optional-side-effect-snippets-need-2026-06-12.md"
    },
    {
      "entry_id": "bug/build-errors/policy-claim-inversion-sweep-all-2026-06-18",
      "title": "Policy-claim inversion: sweep ALL surfaces (both ceremony copies, docs, CLI head",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/steps.md",
      "tags": [
        "fn-66",
        "tracker-sync",
        "ceremony-duplicate",
        "dispatch-grammar",
        "docs-parity",
        "steps.md",
        "SKILL.md"
      ],
      "date": "2026-06-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/policy-claim-inversion-sweep-all-2026-06-18.md"
    },
    {
      "entry_id": "bug/build-errors/prose-tick-lock-claim-before-read-2026-08-28",
      "title": "Prose tick lock: claim before read, serialized reap, liveness refresh, persisted",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-208",
        "land",
        "concurrency",
        "ledger",
        "skill-prose",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/prose-tick-lock-claim-before-read-2026-08-28.md"
    },
    {
      "entry_id": "bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27",
      "title": "R2 ask-block mis-injected into negation-only autonomy prose on mirror regen",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-pilot, plugins/flow-next/skills/flow-next-tracker-sync/steps.md",
      "tags": [
        "fn-68",
        "sync-codex",
        "codex-mirror",
        "pilot",
        "backlog-mode",
        "tracker-sync",
        "AskUserQuestion",
        "R2-injection",
        "is_negative_context",
        "autonomy",
        "review-feedback"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27.md"
    },
    {
      "entry_id": "bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26",
      "title": "Scout fallback prose drifted from spec's decision-lock command shape",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/agents/context-scout.md",
      "tags": [
        "fn-50",
        "clawpatch",
        "scouts",
        "decision-lock-in",
        "flag-drift",
        "codex-review"
      ],
      "date": "2026-05-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26.md"
    },
    {
      "entry_id": "bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05",
      "title": "sed-piped default masks empty source: || fallback never fires",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-qa/workflow.md",
      "tags": [
        "fn-53",
        "skill-bash",
        "base-ref-detection",
        "branch-match",
        "sed-exit-code",
        "make-pr-pattern",
        "codex-review"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05.md"
    },
    {
      "entry_id": "bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05",
      "title": "Skill-adding version bump leaves stale skill/command counts in JSON manifest des",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/.claude-plugin/plugin.json, .claude-plugin/marketplace.json, plugins/flow-next/.codex-plugin/plugin.json",
      "tags": [
        "fn-53",
        "version-bump",
        "bump.sh",
        "skill-count",
        "manifest",
        "marketplace",
        "codex-mirror",
        "docs-drift",
        "release"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05.md"
    },
    {
      "entry_id": "bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26",
      "title": "Skill bash `set -- $ARGUMENTS` can't honor 'verbatim' passthrough",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-map/workflow.md",
      "tags": [
        "fn-50",
        "skill-bash",
        "argument-parsing",
        "set-minus-f",
        "codex-review",
        "passthrough",
        "clawpatch-wrap"
      ],
      "date": "2026-05-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26.md"
    },
    {
      "entry_id": "bug/build-errors/skill-flag-gating-a-durable-write-needs-2026-08-31",
      "title": "Skill flag gating a durable write needs exact-token parse, not substring",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-capture/SKILL.md",
      "tags": [
        "fn-214",
        "skill-bash",
        "argument-parsing",
        "capture",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-31",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/skill-flag-gating-a-durable-write-needs-2026-08-31.md"
    },
    {
      "entry_id": "bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11",
      "title": "Skill workflow snippets must enforce what the prose mandates (vars, gates, dispa",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-60",
        "land",
        "skill-authoring",
        "codex-review",
        "safety-gates",
        "review-feedback"
      ],
      "date": "2026-06-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11.md"
    },
    {
      "entry_id": "bug/build-errors/status-policy-map-needs-a-matching-2026-06-18",
      "title": "Status-policy map needs a matching reconcile-loop branch per rung (map \u2260 write)",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md",
      "tags": [
        "fn-66",
        "tracker-sync",
        "status",
        "reconcile",
        "who-wins",
        "in-review",
        "merge-evidence",
        "rp-review"
      ],
      "date": "2026-06-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/status-policy-map-needs-a-matching-2026-06-18.md"
    },
    {
      "entry_id": "bug/build-errors/template-rewrite-env-var-cascade-2026-05-09",
      "title": "Env-var cascade in templates + canonical config.env knob alignment",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-ralph-init/templates, config.env, ralph.sh",
      "tags": [
        "template",
        "ralph",
        "config-env",
        "env-var-cascade",
        "review-feedback"
      ],
      "date": "2026-05-09",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/template-rewrite-env-var-cascade-2026-05-09.md"
    },
    {
      "entry_id": "bug/build-errors/unit-rename-substitution-broke-trigger-2026-07-18",
      "title": "Unit-rename substitution broke trigger thresholds (turns->rounds, fn-100)",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-interview/references/doc-aware.md",
      "tags": [
        "interview",
        "rounds",
        "doc-aware",
        "thresholds",
        "spec-contract",
        "impl-review",
        "fn-100"
      ],
      "date": "2026-07-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/unit-rename-substitution-broke-trigger-2026-07-18.md"
    },
    {
      "entry_id": "bug/build-errors/verdict-tasks-must-rewrite-not-banner-a-2026-07-03",
      "title": "Verdict tasks must rewrite, not banner, a sibling task's flipped scope",
      "track": "bug",
      "category": "build-errors",
      "module": ".flow/tasks",
      "tags": [
        "fn-83",
        "plan-sync-gate",
        "task-marking",
        "verdict",
        "workflow"
      ],
      "date": "2026-07-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/verdict-tasks-must-rewrite-not-banner-a-2026-07-03.md"
    },
    {
      "entry_id": "bug/test-failures/archaeology-fn-strip-can-over-strip-a-2026-07-02",
      "title": "Archaeology fn-strip can over-strip a test-pinned canonical breadcrumb",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/steps.md",
      "tags": [
        "fn-82",
        "archaeology",
        "fn-strip",
        "sync-codex",
        "mirror",
        "test-pinned",
        "allowlist",
        "final-gate"
      ],
      "date": "2026-07-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/archaeology-fn-strip-can-over-strip-a-2026-07-02.md"
    },
    {
      "entry_id": "bug/test-failures/final-gate-grep-for-a-forbidden-token-2026-07-02",
      "title": "Final-gate grep for a forbidden token hits the prohibition prose that bans it",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/skills/flow-next-impl-review",
      "tags": [
        "acceptance-gates",
        "grep",
        "spec-authoring",
        "fn-81",
        "review-feedback",
        "rp-slices"
      ],
      "date": "2026-07-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/final-gate-grep-for-a-forbidden-token-2026-07-02.md"
    },
    {
      "entry_id": "bug/test-failures/flag-substring-assertion-passes-when-a-2026-09-23",
      "title": "Flag substring assertion passes when a longer sibling flag is present",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests/test_spec_id_routing_prose.py",
      "tags": [
        "prose-test",
        "cli-flags",
        "false-green"
      ],
      "date": "2026-09-23",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/flag-substring-assertion-passes-when-a-2026-09-23.md"
    },
    {
      "entry_id": "bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09",
      "title": "Smoke discipline: variable-form CLI, hermetic env, line-level guard scope",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/scripts",
      "tags": [
        "smoke",
        "env-hermeticity",
        "variable-form-cli",
        "line-level-guard",
        "review-feedback"
      ],
      "date": "2026-05-09",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09.md"
    },
    {
      "entry_id": "bug/test-failures/test-asserted-a-public-envelope-that-2026-08-01",
      "title": "Test asserted a public envelope that never carried the field",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests/test_chart_briefing.py",
      "tags": [
        "chart",
        "test-design",
        "review-feedback",
        "api-surface",
        "scope"
      ],
      "date": "2026-08-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/test-asserted-a-public-envelope-that-2026-08-01.md"
    },
    {
      "entry_id": "bug/test-failures/test-fixtures-must-mirror-upstream-zod-2026-05-26",
      "title": "Test fixtures must mirror upstream Zod enum, not concept",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests/fixtures/clawpatch-map, plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-50",
        "clawpatch",
        "zod-schema",
        "fixture-drift",
        "confidence-enum",
        "codex-review",
        "duck-typing"
      ],
      "date": "2026-05-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/test-fixtures-must-mirror-upstream-zod-2026-05-26.md"
    },
    {
      "entry_id": "bug/test-failures/test-production-path-not-parallel-construction-2026-05-21",
      "title": "Test the production path, not a parallel construction",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests, plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "testing",
        "production-form",
        "mock-patch",
        "argparse-two-token",
        "routing-table",
        "dual-emit",
        "review-feedback"
      ],
      "date": "2026-05-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/test-production-path-not-parallel-construction-2026-05-21.md"
    },
    {
      "entry_id": "bug/test-failures/test-runner-timeout-must-kill-a-process-2026-08-04",
      "title": "Test-runner timeout must kill a process TREE whose identity outlives the shard",
      "track": "bug",
      "category": "test-failures",
      "module": "scripts/run_tests_parallel.py",
      "tags": [
        "windows",
        "subprocess",
        "process-group",
        "job-object",
        "timeout",
        "ci",
        "test-runner"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/test-runner-timeout-must-kill-a-process-2026-08-04.md"
    },
    {
      "entry_id": "bug/test-failures/two-independent-resolve-calls-faked-a-2026-08-04",
      "title": "Two independent resolve() calls faked a path escape on Windows",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/scripts/flowctl_tracker/lifecycle/helpers.py",
      "tags": [
        "windows",
        "flake",
        "path-safety",
        "tracker",
        "concurrency"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/two-independent-resolve-calls-faked-a-2026-08-04.md"
    },
    {
      "entry_id": "bug/test-failures/windows-83-path-test-failures-were-2026-08-04",
      "title": "Windows '8.3 path' test failures were cp1252 fixtures + unguarded geteuid",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests/test_normalize_section_content.py",
      "tags": [
        "fn-120",
        "windows",
        "encoding",
        "cp1252",
        "utf-8",
        "8.3-short-path",
        "geteuid",
        "skipif",
        "json-stdout"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/windows-83-path-test-failures-were-2026-08-04.md"
    },
    {
      "entry_id": "bug/runtime-errors/bash-deadline-watchdogs-orphaned-sleep-2026-07-16",
      "title": "Bash deadline watchdogs: orphaned sleep holds pipes; group-kill via setsid, not ",
      "track": "bug",
      "category": "runtime-errors",
      "module": "agent_docs/guidance-eval/runner.sh",
      "tags": [
        "bash",
        "timeout",
        "process-group",
        "setsid",
        "watchdog",
        "eval-harness",
        "fn-99"
      ],
      "date": "2026-07-16",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/bash-deadline-watchdogs-orphaned-sleep-2026-07-16.md"
    },
    {
      "entry_id": "bug/runtime-errors/empty-value-semantics-leak-null-in-2026-07-20",
      "title": "Empty-value semantics leak: {} -> null in snapshot config reads; empty file -> T",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "config-snapshot",
        "empty-values",
        "truthiness",
        "fn-110"
      ],
      "date": "2026-07-20",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/empty-value-semantics-leak-null-in-2026-07-20.md"
    },
    {
      "entry_id": "bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27",
      "title": "flowctl on-disk per-key counter: count by stored key + lock + coerce sort",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-68",
        "pilot-log",
        "tick-counter",
        "race-condition",
        "flock",
        "rp-review",
        "review-feedback",
        "fn-102",
        "gate-diet",
        "path-normalization",
        "fail-open",
        "codex-review"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27.md"
    },
    {
      "entry_id": "bug/runtime-errors/forced-color-git-grep-output-defeats-2026-07-19",
      "title": "Forced-color git grep output defeats regex post-filter (SGR escapes)",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "git",
        "subprocess",
        "regex",
        "export",
        "ansi"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/forced-color-git-grep-output-defeats-2026-07-19.md"
    },
    {
      "entry_id": "bug/runtime-errors/glob-walk-file-loads-need-lstat-screen-2026-07-19",
      "title": "Glob-walk file loads need lstat screen + RecursionError; revalidate TTL post-sta",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "gate",
        "green-receipt",
        "fail-closed",
        "fifo",
        "json"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/glob-walk-file-loads-need-lstat-screen-2026-07-19.md"
    },
    {
      "entry_id": "bug/runtime-errors/land-chain-fences-a-failed-read-is-2026-09-13",
      "title": "Land chain fences: a failed read is never permission; write multi-layer records ",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-149",
        "land",
        "chains",
        "stacks",
        "cascade",
        "skill-prose",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-09-13",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/land-chain-fences-a-failed-read-is-2026-09-13.md"
    },
    {
      "entry_id": "bug/runtime-errors/one-shot-keyed-to-an-earlier-captured-2026-08-19",
      "title": "One-shot keyed to an earlier-captured SHA: re-validate after the claim, release ",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-200",
        "land",
        "one-shot",
        "concurrency",
        "claim-dir",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/one-shot-keyed-to-an-earlier-captured-2026-08-19.md"
    },
    {
      "entry_id": "bug/runtime-errors/same-owner-alias-re-registration-must-2026-08-02",
      "title": "Same-owner alias re-registration must harden a weak claim, not no-op",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "chart",
        "aliases",
        "two-pass-validation",
        "flowctl"
      ],
      "date": "2026-08-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/same-owner-alias-re-registration-must-2026-08-02.md"
    },
    {
      "entry_id": "bug/runtime-errors/skill-fences-that-degrade-only-without-2026-09-13",
      "title": "Skill fences that degrade only without set -e: masked failures in make-pr chain ",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md",
      "tags": [
        "set-e",
        "bash-fence",
        "fixtures",
        "make-pr",
        "chain",
        "stack"
      ],
      "date": "2026-09-13",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/skill-fences-that-degrade-only-without-2026-09-13.md"
    },
    {
      "entry_id": "bug/runtime-errors/structured-review-parsers-must-2026-07-30",
      "title": "Structured review parsers must distinguish invalid from absent",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-136",
        "review-findings",
        "fail-closed",
        "parser",
        "impl-review"
      ],
      "date": "2026-07-30",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/structured-review-parsers-must-2026-07-30.md"
    },
    {
      "entry_id": "bug/runtime-errors/who-wins-ladder-must-check-the-2026-06-03",
      "title": "Who-wins ladder must check the collision case before single-field rules",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md",
      "tags": [
        "fn-52",
        "tracker-sync",
        "who-wins",
        "status",
        "deadlock",
        "conflictTiebreak",
        "ordering",
        "impl-review"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/who-wins-ladder-must-check-the-2026-06-03.md"
    },
    {
      "entry_id": "bug/performance/linear-graphql-every-nodes-connection-2026-06-03",
      "title": "Linear GraphQL: every {nodes} connection needs first: \u2014 incl. workflowStates/tea",
      "track": "bug",
      "category": "performance",
      "module": "plugins/flow-next/scripts/flowctl_tracker/wire/linear.py",
      "tags": [
        "fn-52",
        "tracker-sync",
        "linear",
        "graphql",
        "rate-limit",
        "complexity",
        "connection",
        "first",
        "impl-review"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/performance/linear-graphql-every-nodes-connection-2026-06-03.md"
    },
    {
      "entry_id": "bug/security/guard-matcher-narrowing-missed-shell-2026-09-25",
      "title": "Guard matcher narrowing missed shell control words and split redirect words",
      "track": "bug",
      "category": "security",
      "module": "plugins/flow-next/scripts/hooks/ralph-guard.py",
      "tags": [
        "ralph-guard",
        "shell-parsing",
        "bypass"
      ],
      "date": "2026-09-25",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/security/guard-matcher-narrowing-missed-shell-2026-09-25.md"
    },
    {
      "entry_id": "bug/security/managed-review-transport-must-bound-2026-09-08",
      "title": "Managed review transport must bound time and protect scoped credentials",
      "track": "bug",
      "category": "security",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "managed-review",
        "transport",
        "credentials"
      ],
      "date": "2026-09-08",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/security/managed-review-transport-must-bound-2026-09-08.md"
    },
    {
      "entry_id": "bug/security/rollback-path-sanitizer-must-not-2026-06-05",
      "title": "Rollback path-sanitizer must not trim/rewrite bytes; guard git clean against emp",
      "track": "bug",
      "category": "security",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-55",
        "codex-delegation",
        "rollback",
        "git-clean",
        "path-sanitization",
        "review-feedback"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/security/rollback-path-sanitizer-must-not-2026-06-05.md"
    },
    {
      "entry_id": "bug/security/shell-command-allowlist-gates-must-2026-06-05",
      "title": "Shell-command allowlist gates must tokenize argv, not substring-match",
      "track": "bug",
      "category": "security",
      "module": "plugins/flow-next/scripts/hooks/ralph-guard.py",
      "tags": [
        "fn-55",
        "ralph-guard",
        "codex-delegation",
        "shlex",
        "allowlist",
        "bypass",
        "security",
        "review-feedback"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/security/shell-command-allowlist-gates-must-2026-06-05.md"
    },
    {
      "entry_id": "bug/integration/adding-a-review-backend-sweep-all-2026-06-29",
      "title": "Adding a review backend: sweep ALL enumeration sites (config table, stage list, ",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/docs, plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "review-backend",
        "enumeration-drift",
        "docs-sweep",
        "cursor",
        "fn-74",
        "claude",
        "fn-221"
      ],
      "date": "2026-06-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/adding-a-review-backend-sweep-all-2026-06-29.md"
    },
    {
      "entry_id": "bug/integration/backend-special-case-in-a-shared-helper-2026-09-05",
      "title": "Backend special-case in a shared helper is an enumeration site too",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "review-backend",
        "claude",
        "enumeration-sweep",
        "fn-221",
        "tracker-manifest"
      ],
      "date": "2026-09-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/backend-special-case-in-a-shared-helper-2026-09-05.md"
    },
    {
      "entry_id": "bug/integration/byte-for-byte-spec-contract-branch-2026-07-01",
      "title": "Byte-for-byte spec contract: branch prose into variants, don't annotate shared l",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-plan-review/SKILL.md",
      "tags": [
        "fn-78",
        "skill-prose",
        "review-feedback",
        "rp-eligibility",
        "byte-for-byte"
      ],
      "date": "2026-07-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/byte-for-byte-spec-contract-branch-2026-07-01.md"
    },
    {
      "entry_id": "bug/integration/caller-facade-guards-must-cover-retro-2026-07-29",
      "title": "Caller facade guards must cover retro-fire paths",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-capture/workflow.md",
      "tags": [
        "fn-141",
        "tracker-sync",
        "facade",
        "retro-fire",
        "oracle"
      ],
      "date": "2026-07-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/caller-facade-guards-must-cover-retro-2026-07-29.md"
    },
    {
      "entry_id": "bug/integration/caller-fakes-must-enforce-lifecycle-2026-07-29",
      "title": "Caller fakes must enforce lifecycle facade input contracts",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/tests/test_tracker_caller_execution.py",
      "tags": [
        "fn-141",
        "tracker-sync",
        "caller-harness",
        "facade",
        "impl-review"
      ],
      "date": "2026-07-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/caller-fakes-must-enforce-lifecycle-2026-07-29.md"
    },
    {
      "entry_id": "bug/integration/caller-oracle-must-preserve-historical-2026-07-29",
      "title": "Caller oracle must preserve historical quirks and exact observations",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/tests/test_tracker_caller_oracle.py",
      "tags": [
        "fn-141",
        "tracker-sync",
        "oracle",
        "impl-review"
      ],
      "date": "2026-07-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/caller-oracle-must-preserve-historical-2026-07-29.md"
    },
    {
      "entry_id": "bug/integration/ceremony-validation-must-read-persisted-2026-06-28",
      "title": "Ceremony validation must read PERSISTED config, not re-race env; don't collapse ",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/steps.md",
      "tags": [
        "tracker-sync",
        "jira",
        "fn-70",
        "discovery-ceremony",
        "readyState",
        "persisted-config",
        "authScheme",
        "rp-review"
      ],
      "date": "2026-06-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/ceremony-validation-must-read-persisted-2026-06-28.md"
    },
    {
      "entry_id": "bug/integration/ci-path-classification-must-include-2026-09-05",
      "title": "CI path classification must include rename sources",
      "track": "bug",
      "category": "integration",
      "module": "scripts/ci/classify_changes.py",
      "tags": [
        "ci",
        "git",
        "renames",
        "path-classification"
      ],
      "date": "2026-09-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/ci-path-classification-must-include-2026-09-05.md"
    },
    {
      "entry_id": "bug/integration/claude-p-clean-room-on-oauth-logins-2026-07-16",
      "title": "claude -p clean-room on OAuth logins: --setting-sources project,local; --bare an",
      "track": "bug",
      "category": "integration",
      "module": "agent_docs/guidance-eval/runner.sh",
      "tags": [
        "claude-cli",
        "clean-room",
        "eval-harness",
        "oauth",
        "setting-sources",
        "bare",
        "fn-99"
      ],
      "date": "2026-07-16",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/claude-p-clean-room-on-oauth-logins-2026-07-16.md"
    },
    {
      "entry_id": "bug/integration/cross-family-review-claims-key-on-the-2026-09-05",
      "title": "Cross-family review claims key on the writer's model family, never the host name",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/docs",
      "tags": [
        "review-backend",
        "claude",
        "cross-family",
        "docs",
        "fn-221"
      ],
      "date": "2026-09-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/cross-family-review-claims-key-on-the-2026-09-05.md"
    },
    {
      "entry_id": "bug/integration/drop-receipt-to-break-codex-2026-05-09",
      "title": "Drop receipt to break codex confabulation in long review fix loops",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "review",
        "codex",
        "confabulation",
        "receipt",
        "fn-43"
      ],
      "date": "2026-05-09",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/drop-receipt-to-break-codex-2026-05-09.md"
    },
    {
      "entry_id": "bug/integration/forwarded-license-carried-the-wrong-2026-09-14",
      "title": "Forwarded license carried the wrong holder's commit contract into the bridged ch",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/agents/worker.md",
      "tags": [
        "fn-245",
        "bridge",
        "worker",
        "phase-1b",
        "license",
        "dispatch-field",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-09-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/forwarded-license-carried-the-wrong-2026-09-14.md"
    },
    {
      "entry_id": "bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17",
      "title": "gh api -f stringifies numeric body fields (issue_id) \u2192 GitHub 422; use -F",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl_tracker/",
      "tags": [
        "fn-64",
        "tracker-sync",
        "github",
        "gh-api",
        "rest",
        "422",
        "issue-dependencies"
      ],
      "date": "2026-06-17",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17.md"
    },
    {
      "entry_id": "bug/integration/head-bound-html-artifacts-must-not-2026-07-30",
      "title": "Head-bound HTML artifacts must not stale their own input",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-make-pr/html-lens.md",
      "tags": [
        "fn-136",
        "make-pr",
        "html",
        "currentness",
        "semantic-carrier",
        "impl-review"
      ],
      "date": "2026-07-30",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/head-bound-html-artifacts-must-not-2026-07-30.md"
    },
    {
      "entry_id": "bug/integration/headless-review-backend-error-envelope-2026-09-05",
      "title": "Headless review backend: error-envelope text must never ride the output slot",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "review-backend",
        "claude",
        "transport",
        "verdict-channel",
        "fn-221"
      ],
      "date": "2026-09-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/headless-review-backend-error-envelope-2026-09-05.md"
    },
    {
      "entry_id": "bug/integration/heredoc-built-json-breaks-on-free-form-2026-06-05",
      "title": "Heredoc-built JSON breaks on free-form interpolated values",
      "track": "bug",
      "category": "integration",
      "module": "skills/flow-next-qa/workflow.md",
      "tags": [
        "json",
        "shell",
        "receipt",
        "escaping",
        "skill-authoring"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/heredoc-built-json-breaks-on-free-form-2026-06-05.md"
    },
    {
      "entry_id": "bug/integration/installer-must-own-what-it-deletes-2026-08-21",
      "title": "",
      "track": "bug",
      "category": "integration",
      "module": "scripts/install-codex.sh, scripts/sync-codex.sh",
      "tags": [
        "installer",
        "ownership",
        "namespace",
        "data-loss",
        "codex",
        "mirror"
      ],
      "date": "2026-08-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/installer-must-own-what-it-deletes-2026-08-21.md"
    },
    {
      "entry_id": "bug/integration/land-evidence-field-defaulted-to-off-on-2026-08-19",
      "title": "land evidence field defaulted to 'off' on configured-but-not-due paths",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "land",
        "evidence",
        "report-vocabulary"
      ],
      "date": "2026-08-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/land-evidence-field-defaulted-to-off-on-2026-08-19.md"
    },
    {
      "entry_id": "bug/integration/markerstruct-field-semantics-must-2026-06-27",
      "title": "Marker/struct-field semantics must update the PRODUCER adapter contract, not jus",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md",
      "tags": [
        "fn-68",
        "tracker-sync",
        "adapter-interface",
        "marker",
        "comments-sync",
        "listComments",
        "question-valve",
        "nine-method",
        "cross-model-review",
        "fn-141",
        "facade",
        "comments",
        "prose-teardown"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/markerstruct-field-semantics-must-2026-06-27.md"
    },
    {
      "entry_id": "bug/integration/path-handoff-template-id-slots-must-use-2026-07-19",
      "title": "Path-handoff template id slots must use canonical ids, not aliases",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-work/references/codex-delegation.md",
      "tags": [
        "fn-103",
        "codex-delegation",
        "path-handoff",
        "alias-resolution",
        "prose-contract",
        "review-feedback"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/path-handoff-template-id-slots-must-use-2026-07-19.md"
    },
    {
      "entry_id": "bug/integration/plan-review-criteria-edits-must-also-2026-09-14",
      "title": "Plan-review criteria edits must also sweep workflow-rp.md (CE summary + Classic ",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md",
      "tags": [
        "plan-review",
        "repoprompt",
        "prompt-pins",
        "codex-review"
      ],
      "date": "2026-09-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/plan-review-criteria-edits-must-also-2026-09-14.md"
    },
    {
      "entry_id": "bug/integration/rp-builder-file-slices-cause-false-2026-06-10",
      "title": "RP builder file slices cause false-positive 'missing docs' review findings",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-impl-review",
      "tags": [
        "rp",
        "impl-review",
        "builder-slices",
        "false-positive",
        "select-get",
        "review-feedback"
      ],
      "date": "2026-06-10",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/rp-builder-file-slices-cause-false-2026-06-10.md"
    },
    {
      "entry_id": "bug/integration/scheduler-prose-asserted-wrong-config-2026-08-22",
      "title": "Scheduler prose asserted wrong config default; slot-hold drain rules deadlock",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md",
      "tags": [
        "fn-203",
        "work-rolling",
        "planSync",
        "config-defaults",
        "deadlock",
        "skill-prose"
      ],
      "date": "2026-08-22",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/scheduler-prose-asserted-wrong-config-2026-08-22.md"
    },
    {
      "entry_id": "bug/integration/set-tracker-id-rejected-github-n-2026-06-03",
      "title": "set-tracker-id rejected GitHub #N identifiers (Linear-only handle validator)",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-52",
        "tracker-sync",
        "github",
        "identifier",
        "validator",
        "smoke-test"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/set-tracker-id-rejected-github-n-2026-06-03.md"
    },
    {
      "entry_id": "bug/integration/skill-bash-blocks-re-declare-every-2026-07-02",
      "title": "Skill bash blocks: re-declare EVERY literal path per block (vars die across tool",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills",
      "tags": [
        "path-persistence",
        "skill-authoring",
        "rp-review",
        "fn-81"
      ],
      "date": "2026-07-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/skill-bash-blocks-re-declare-every-2026-07-02.md"
    },
    {
      "entry_id": "bug/integration/skill-fence-consolidation-6-contract-2026-07-20",
      "title": "Skill-fence consolidation: 6 contract regressions (var-atomicity, symlink, dry-r",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills",
      "tags": [
        "skill-prose",
        "fences",
        "dry-run",
        "symlink-safety",
        "fn-110"
      ],
      "date": "2026-07-20",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/skill-fence-consolidation-6-contract-2026-07-20.md"
    },
    {
      "entry_id": "bug/integration/spec-named-config-keys-must-be-checked-2026-07-15",
      "title": "Spec-named config keys must be checked against shipped surface; cross-family is",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-setup/workflow.md",
      "tags": [
        "fn-97",
        "config-contract",
        "spec-amendment",
        "cross-family-review",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-07-15",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/spec-named-config-keys-must-be-checked-2026-07-15.md"
    },
    {
      "entry_id": "bug/integration/summary-sinks-for-repeatable-mixed-2026-07-19",
      "title": "Summary sinks for repeatable mixed-outcome events need per-event lines, not one ",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-work/phases.md",
      "tags": [
        "prose-contract",
        "summary-template",
        "gate-diet",
        "fn-102",
        "review-finding"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/summary-sinks-for-repeatable-mixed-2026-07-19.md"
    },
    {
      "entry_id": "bug/integration/tracker-ownership-rewrites-require-2026-07-29",
      "title": "Tracker ownership rewrites require adjacent fidelity sweeps",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/docs/tracker-sync.md",
      "tags": [
        "fn-141",
        "tracker-sync",
        "docs-contract",
        "provider-fidelity",
        "impl-review"
      ],
      "date": "2026-07-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/tracker-ownership-rewrites-require-2026-07-29.md"
    },
    {
      "entry_id": "bug/integration/trackers-auto-linkify-issue-key-2026-06-03",
      "title": "Trackers auto-linkify issue-key substrings inside markers (even in HTML comments",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md",
      "tags": [
        "fn-52",
        "tracker-sync",
        "linear",
        "marker",
        "dedup",
        "linkify",
        "smoke-test"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/trackers-auto-linkify-issue-key-2026-06-03.md"
    },
    {
      "entry_id": "bug/data/adding-a-key-to-a-content-hash-orphans-2026-08-01",
      "title": "Adding a key to a content hash orphans records the old binary wrote",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fingerprint",
        "idempotence",
        "upgrade-compat",
        "golden-fixture",
        "chart"
      ],
      "date": "2026-08-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/adding-a-key-to-a-content-hash-orphans-2026-08-01.md"
    },
    {
      "entry_id": "bug/data/docs-for-a-hash-identity-fix-inherit-2026-08-01",
      "title": "Docs for a hash-identity fix inherit the hash's precision",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/docs/flowctl.md",
      "tags": [
        "chart",
        "fingerprint",
        "changelog",
        "docs-pin",
        "review-feedback"
      ],
      "date": "2026-08-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/docs-for-a-hash-identity-fix-inherit-2026-08-01.md"
    },
    {
      "entry_id": "bug/data/fence-preserving-writer-needs-fence-2026-07-02",
      "title": "Fence-preserving writer needs fence-aware readers/validators (write/read parity)",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-79",
        "task-sections",
        "fenced-code",
        "markdown-parsing",
        "cursor-review"
      ],
      "date": "2026-07-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/fence-preserving-writer-needs-fence-2026-07-02.md"
    },
    {
      "entry_id": "bug/data/migrationrollback-cli-10-review-cycle-2026-05-08",
      "title": "Migration/rollback CLI: 10 review-cycle pitfalls (fn-43.3)",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-43",
        "migration",
        "rollback",
        "lockfile",
        "sentinel",
        "atomic-write",
        "crash-recovery",
        "cross-platform",
        "review-feedback"
      ],
      "date": "2026-05-08",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/migrationrollback-cli-10-review-cycle-2026-05-08.md"
    },
    {
      "entry_id": "bug/data/paired-snapshot-setter-must-write-both-2026-06-03",
      "title": "Paired-snapshot setter must write both halves atomically (merge base)",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-52",
        "tracker-sync",
        "merge-base",
        "3-way-merge",
        "invariant",
        "setter",
        "impl-review"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/paired-snapshot-setter-must-write-both-2026-06-03.md"
    },
    {
      "entry_id": "bug/data/relaxing-a-validator-must-only-admit-2026-09-26",
      "title": "Relaxing a validator must only admit values the writer round-trips",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-257",
        "memory",
        "frontmatter",
        "validation",
        "round-trip"
      ],
      "date": "2026-09-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/relaxing-a-validator-must-only-admit-2026-09-26.md"
    },
    {
      "entry_id": "bug/data/yaml-frontmatter-writer-unescaped-2026-07-24",
      "title": "YAML frontmatter writer: unescaped newlines lose the entry; frontmatter-only wri",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "memory",
        "yaml",
        "frontmatter",
        "round-trip"
      ],
      "date": "2026-07-24",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/yaml-frontmatter-writer-unescaped-2026-07-24.md"
    },
    {
      "entry_id": "bug/ui/flow-nextdev-docs-page-needs-2026-06-03",
      "title": "flow-next.dev docs page needs registering in BOTH astro sidebar + site.ts navGro",
      "track": "bug",
      "category": "ui",
      "module": "src/lib/site.ts",
      "tags": [
        "flow-next.dev",
        "docs-site",
        "starlight",
        "navigation",
        "navGroups",
        "DocsRail",
        "fn-52"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/ui/flow-nextdev-docs-page-needs-2026-06-03.md"
    },
    {
      "entry_id": "knowledge/conventions/unattended-detection-uses-the-full-2026-09-26",
      "title": "Unattended detection uses the full autonomy marker namespace",
      "track": "knowledge",
      "category": "conventions",
      "module": "skills",
      "tags": [
        "autonomy",
        "mode:autonomous",
        "tracker-sync",
        "flow-auto",
        "defer"
      ],
      "date": "2026-09-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/conventions/unattended-detection-uses-the-full-2026-09-26.md"
    },
    {
      "entry_id": "knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30",
      "title": "Audit sync-codex.sh during planning for Codex mirror impact",
      "track": "knowledge",
      "category": "workflow",
      "module": "planning",
      "tags": [
        "sync-codex",
        "codex",
        "planning",
        "mirror",
        "validation",
        "subagents",
        "tool-rewrites",
        "openai-yaml"
      ],
      "date": "2026-04-30",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30.md"
    },
    {
      "entry_id": "knowledge/workflow/final-integration-tasks-need-wider-impl-2026-05-26",
      "title": "Final-integration tasks need wider impl-review base",
      "track": "knowledge",
      "category": "workflow",
      "module": "review",
      "tags": [
        "fn-50",
        "impl-review",
        "review-scope",
        "final-task",
        "multi-task-spec",
        "base-commit",
        "merge-base",
        "codex"
      ],
      "date": "2026-05-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/final-integration-tasks-need-wider-impl-2026-05-26.md"
    },
    {
      "entry_id": "knowledge/workflow/github-rulesets-need-an-admin-bypass-or-2026-09-11",
      "title": "GitHub rulesets need an admin bypass or spec-only commits stall",
      "track": "knowledge",
      "category": "workflow",
      "module": "ci",
      "tags": [
        "github",
        "rulesets",
        "ci",
        "flow-state"
      ],
      "date": "2026-09-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/github-rulesets-need-an-admin-bypass-or-2026-09-11.md"
    },
    {
      "entry_id": "knowledge/workflow/harness-capability-claims-verify-at-the-2026-08-28",
      "title": "Harness capability claims: verify at the installer, not the generator",
      "track": "knowledge",
      "category": "workflow",
      "module": "platforms",
      "tags": [
        "scouts",
        "opencode",
        "installers",
        "negative-claims"
      ],
      "date": "2026-08-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/harness-capability-claims-verify-at-the-2026-08-28.md"
    },
    {
      "entry_id": "knowledge/workflow/pr-bot-review-loops-do-not-converge-2026-08-04",
      "title": "",
      "track": "knowledge",
      "category": "workflow",
      "module": "review-subsystem",
      "tags": [
        "bot-review",
        "land",
        "convergence",
        "triage",
        "severity-inflation"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/pr-bot-review-loops-do-not-converge-2026-08-04.md"
    },
    {
      "entry_id": "knowledge/workflow/split-pr-at-second-adjacent-surface-finding-2026-08-21",
      "title": "",
      "track": "knowledge",
      "category": "workflow",
      "module": "review",
      "tags": [
        "resolve-pr",
        "land",
        "scope",
        "review-rounds",
        "pr-hygiene"
      ],
      "date": "2026-08-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/split-pr-at-second-adjacent-surface-finding-2026-08-21.md"
    },
    {
      "entry_id": "knowledge/workflow/stacked-pr-squash-close-recovery-2026-08-27",
      "title": "Squash-merging a stacked PR's base permanently closes the stacked PR - rebase + successor PR is the recovery",
      "track": "knowledge",
      "category": "workflow",
      "module": "land",
      "tags": [
        "stacked-prs",
        "squash-merge",
        "land",
        "gh",
        "rebase",
        "delete-branch",
        "github-behavior"
      ],
      "date": "2026-08-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/stacked-pr-squash-close-recovery-2026-08-27.md"
    },
    {
      "entry_id": "knowledge/best-practices/failures-after-a-restart-suspect-2026-08-28",
      "title": "Failures after a restart: suspect persistent state before code",
      "track": "knowledge",
      "category": "best-practices",
      "module": ".flow",
      "tags": [
        "fn-208",
        "debugging",
        "persistent-state",
        "state-validation"
      ],
      "date": "2026-08-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/best-practices/failures-after-a-restart-suspect-2026-08-28.md"
    },
    {
      "entry_id": "knowledge/best-practices/scb-benchmark-proof-fn-163164-2026-08-04",
      "title": "SCB benchmark proof: fn-163/164 eliminated ceremony as a cost factor",
      "track": "knowledge",
      "category": "best-practices",
      "module": "",
      "tags": [
        "fn-163",
        "fn-164",
        "fn-165",
        "slopcodebench",
        "benchmark"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/best-practices/scb-benchmark-proof-fn-163164-2026-08-04.md"
    },
    {
      "entry_id": "knowledge/best-practices/windows-path-shims-cannot-observe-2026-08-11",
      "title": "Windows PATH shims cannot observe subprocess spawns (CreateProcess skips PATHEXT",
      "track": "knowledge",
      "category": "best-practices",
      "module": "plugins/flow-next/tests",
      "tags": [
        "windows",
        "ci",
        "subprocess",
        "spawn-count",
        "git-shim"
      ],
      "date": "2026-08-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/best-practices/windows-path-shims-cannot-observe-2026-08-11.md"
    },
    {
      "entry_id": "knowledge/decisions/bugbot-pre-push-stage-wont-do-patch-id-2026-08-07",
      "title": "Bugbot pre-push stage: won't-do - patch-ID dedup falsified live",
      "track": "knowledge",
      "category": "decisions",
      "module": "review",
      "tags": [
        "bugbot",
        "cursor",
        "review-backends"
      ],
      "date": "2026-08-07",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/bugbot-pre-push-stage-wont-do-patch-id-2026-08-07.md"
    },
    {
      "entry_id": "knowledge/decisions/composed-brief-deleted-path-handoff-2026-07-19",
      "title": "Composed brief deleted: path-handoff replaces it (fn-103 eval)",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/skills/flow-next-work/references/codex-delegation.md",
      "tags": [
        "fn-103",
        "codex-delegation",
        "path-handoff",
        "eval",
        "delegation",
        "bitter-lesson"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/composed-brief-deleted-path-handoff-2026-07-19.md"
    },
    {
      "entry_id": "knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25",
      "title": "Factory Droid platform status \u2014 2026-05",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/docs/platforms.md",
      "tags": [
        "droid",
        "factory-ai",
        "cross-platform",
        "fn-48",
        "interop",
        "plugin-root",
        "hooks",
        "Execute"
      ],
      "date": "2026-05-25",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25.md"
    },
    {
      "entry_id": "knowledge/decisions/pilot-strike-recovery-is-a-cli-verb-not-2026-08-11",
      "title": "Pilot strike recovery is a CLI verb, not board-native transition detection",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/skills/flow-next-pilot",
      "tags": [
        "pilot",
        "strikes",
        "tracker-sync",
        "readyState",
        "fn-184"
      ],
      "date": "2026-08-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/pilot-strike-recovery-is-a-cli-verb-not-2026-08-11.md"
    },
    {
      "entry_id": "knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03",
      "title": "A deterministic plan-sync skip-gate is not viable \u2014 do not re-attempt",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/skills/flow-next-work/phases.md",
      "tags": [
        "plan-sync",
        "work-loop",
        "gate",
        "eval",
        "fn-83",
        "drift",
        "determinism",
        "shelved"
      ],
      "date": "2026-07-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md"
    },
    {
      "entry_id": "knowledge/decisions/ralph-guard-reverts-its-delegation-2026-08-14",
      "title": "Ralph guard reverts its delegation amendment; bridge safety is prose-only",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/scripts/hooks/ralph-guard.py",
      "tags": [
        "flow-98",
        "ralph-guard",
        "codex-delegation",
        "safety",
        "deprecation"
      ],
      "date": "2026-08-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/ralph-guard-reverts-its-delegation-2026-08-14.md"
    },
    {
      "entry_id": "knowledge/decisions/review-stall-detection-reads-resolution-2026-08-05",
      "title": "Review stall detection reads resolution; the trend heuristics are deleted (fn-168)",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-168",
        "fn-159",
        "review-convergence",
        "stall-detection",
        "ratchet-prompt",
        "findings-lineage",
        "inference-vs-evidence"
      ],
      "date": "2026-08-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/review-stall-detection-reads-resolution-2026-08-05.md"
    },
    {
      "entry_id": "knowledge/decisions/tracked-vs-runtime-durability-contract-2026-08-14",
      "title": "Tracked-vs-runtime durability contract - done crosses it, validate respects it",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "durability",
        "flow-state",
        "status-source",
        "validate",
        "fn-192"
      ],
      "date": "2026-08-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/tracked-vs-runtime-durability-contract-2026-08-14.md"
    },
    {
      "entry_id": "knowledge/decisions/tracker-sync-is-projection-not-2026-06-01",
      "title": "Tracker sync is projection, not coordination (Linear-first)",
      "track": "knowledge",
      "category": "decisions",
      "module": "strategy",
      "tags": [
        "strategy-override",
        "tracker-sync",
        "linear"
      ],
      "date": "2026-06-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/tracker-sync-is-projection-not-2026-06-01.md"
    }
  ],
  "legacy": [],
  "count": 118,
  "status": "active"
}

===== [11/11] dependencies: ids, titles, statuses, done summaries =====
- fn-74-cursor-review-backend-cursor-agent-cli.1 [done] - flowctl cursor backend foundation — registry + run_cursor_exec + check + parser tests
    Added the `cursor` review backend foundation in flowctl: the BACKEND_REGISTRY entry (model-yes / effort-no shape, default gpt-5.5-high), the require_cursor / get_cursor_version / run_cursor_exec helper trio (positional-argv prompt, resume-only session, cwd=repo_root, --mode ask --trust, no --effort, explicit prompt-too-large raise, non-zero on is_error/timeout), the `cursor check [--skip-probe]` subcommand, and unit tests (test_cursor_run_exec.py + test_backend_spec.py cursor cases). Full Python suite green at 1271 tests.

