$ flowctl show fn-74-cursor-review-backend-cursor-agent-cli.2 --json
{
  "success": true,
  "assignee": "gordon.mickel@gmail.com",
  "claim_note": "",
  "claimed_at": "2026-06-29T12:48:36.668946Z",
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
  "updated_at": "2026-06-29T13:22:26.030348Z",
  "evidence": {
    "acceptance": [
      "R5",
      "R6",
      "R7",
      "R8",
      "R11",
      "R14"
    ],
    "commits": [
      "d5c58042"
    ],
    "note": "recovered from lost-worker truncation; host re-ran suite + codex review and finalized",
    "review": {
      "backend": "codex",
      "base": "c9834827",
      "verdict": "SHIP"
    },
    "tests": "python3 -m unittest discover -s plugins/flow-next/tests \u2192 1286 passed, 2 skipped"
  },
  "impl": null,
  "review": null,
  "sync": null,
  "epic": "fn-74-cursor-review-backend-cursor-agent-cli"
}

$ flowctl cat fn-74-cursor-review-backend-cursor-agent-cli.2
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

$ flowctl show fn-74-cursor-review-backend-cursor-agent-cli --json
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
  "status": "open",
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
  "updated_at": "2026-06-29T22:05:58.479486Z",
  "tasks": [
    {
      "id": "fn-74-cursor-review-backend-cursor-agent-cli.1",
      "title": "flowctl cursor backend foundation \u2014 registry + run_cursor_exec + check + parser tests",
      "status": "done",
      "priority": null,
      "depends_on": []
    },
    {
      "id": "fn-74-cursor-review-backend-cursor-agent-cli.2",
      "title": "cursor review commands \u2014 impl/plan/completion/validate/deep handlers + dispatch + mode:cursor receipts",
      "status": "done",
      "priority": null,
      "depends_on": [
        "fn-74-cursor-review-backend-cursor-agent-cli.1"
      ]
    },
    {
      "id": "fn-74-cursor-review-backend-cursor-agent-cli.3",
      "title": "skill + setup wiring + codex mirror \u2014 workflow-cursor.md x2, --review literals, review.backend, sync-codex",
      "status": "done",
      "priority": null,
      "depends_on": [
        "fn-74-cursor-review-backend-cursor-agent-cli.2"
      ]
    },
    {
      "id": "fn-74-cursor-review-backend-cursor-agent-cli.4",
      "title": "docs + downstream chain \u2014 flowctl.md/README/GLOSSARY/CHANGELOG + flow-next.dev + AI-x-SDLC + GF + vault",
      "status": "done",
      "priority": null,
      "depends_on": [
        "fn-74-cursor-review-backend-cursor-agent-cli.3"
      ]
    }
  ],
  "ready": false
}

$ flowctl cat fn-74-cursor-review-backend-cursor-agent-cli
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


$ git status
On branch fn-83-work-loop-speed-conservative-plan-sync
You are in a sparse checkout with 100% of tracked files present.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   .flow/specs/fn-83-work-loop-speed-conservative-plan-sync.json
	modified:   .flow/specs/fn-83-work-loop-speed-conservative-plan-sync.md
	modified:   .flow/tasks/fn-83-work-loop-speed-conservative-plan-sync.4.json
	modified:   .flow/tasks/fn-83-work-loop-speed-conservative-plan-sync.4.md
	modified:   plugins/flow-next/scripts/flowctl.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	.flow/tasks/fn-83-work-loop-speed-conservative-plan-sync.6.json
	.flow/tasks/fn-83-work-loop-speed-conservative-plan-sync.6.md
	optimization/worker-anchor/
	plugins/flow-next/tests/test_anchor_bundle.py

no changes added to commit (use "git add" and/or "git commit -a")

$ git log -5 --oneline
7d628564 chore(flow): close fn-83.2 — done summary + evidence
c0477c32 feat(eval): plan-sync gate corpus — frozen real-agent answer key + zero-false-skip CI check (fn-83.2)
43264e13 chore(flow): close fn-83.1 — done summary + evidence
5993c446 feat(flowctl): plan-sync-probe — fail-open drift lattice, planSync.gate config, gate ledger
23ab917d chore(flow): plan fn-83 (5 tasks, plan-review SHIP r3) + FLOW-29 link

$ flowctl config get memory.enabled --json
{
  "success": true,
  "key": "memory.enabled",
  "value": true
}

$ flowctl memory list --json
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27.md"
    },
    {
      "entry_id": "bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05",
      "title": "Codex mirror audit must verify R2 block lands before a COMPLETE sentence, not ju",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-qa/references/qa-discipline.md",
      "tags": [
        "sync-codex",
        "codex",
        "mirror",
        "fn-53",
        "AskUserQuestion",
        "plain-text-numbered-prompt",
        "mid-sentence-injection",
        "multi-line-ask",
        "tool-rewrites",
        "audit",
        "review-feedback"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/docs-activation-command-for-string-enum-2026-06-05.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/env-marker-gate-must-scan-the-namespace-2026-06-04.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/fn-44-review-cycle-lessons-2026-05-21.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03.md"
    },
    {
      "entry_id": "bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12",
      "title": "Lavish interactive-only gate must check MODE var AND env markers in-snippet",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-capture/workflow.md",
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11.md"
    },
    {
      "entry_id": "bug/build-errors/optional-side-effect-snippets-need-2026-06-12",
      "title": "Optional side-effect snippets need guarded git steps; check-ignore the exact fil",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-make-pr/workflow.md",
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/optional-side-effect-snippets-need-2026-06-12.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/policy-claim-inversion-sweep-all-2026-06-18.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27.md"
    },
    {
      "entry_id": "bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10",
      "title": "R2 ask-block must never anchor in autonomous hard-error prose; mode-rename sweep",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-make-pr/workflow.md",
      "tags": [
        "fn-59",
        "sync-codex",
        "codex-mirror",
        "R2-injection",
        "is_negative_context",
        "autonomous",
        "FLOW_AUTONOMOUS",
        "make-pr",
        "review-feedback"
      ],
      "date": "2026-06-10",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26.md"
    },
    {
      "entry_id": "bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10",
      "title": "Skill prose must match real flowctl surfaces (fields, status enums, subcommands)",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-pilot/workflow.md",
      "tags": [
        "fn-59",
        "pilot",
        "skill-authoring",
        "flowctl-json",
        "task-status",
        "rp-review",
        "fn-68",
        "backlog-mode",
        "safety-gates",
        "dry-run",
        "review-feedback",
        "fn-82",
        "skill-prose",
        "dedupe",
        "progressive-disclosure"
      ],
      "date": "2026-06-10",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/status-policy-map-needs-a-matching-2026-06-18.md"
    },
    {
      "entry_id": "bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18",
      "title": "sync-codex.sh tool-substitution needs prose surgery + context-aware injection",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh",
      "tags": [
        "sync-codex",
        "codex",
        "mirror",
        "fn-45",
        "AskUserQuestion",
        "tool-rewrites",
        "injection",
        "markdown-tables",
        "fenced-code-blocks",
        "fn-50",
        "FLOWCTL",
        "prelude",
        "agents",
        "scouts",
        "symmetry-gap",
        "R2-injection",
        "is_negative_context",
        "fn-55",
        "plain-text-numbered-prompt",
        "reference-doc"
      ],
      "date": "2026-05-18",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/template-rewrite-env-var-cascade-2026-05-09.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/archaeology-fn-strip-can-over-strip-a-2026-07-02.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/final-gate-grep-for-a-forbidden-token-2026-07-02.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/test-fixtures-must-mirror-upstream-zod-2026-05-26.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/test-production-path-not-parallel-construction-2026-05-21.md"
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
        "review-feedback"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/runtime-errors/who-wins-ladder-must-check-the-2026-06-03.md"
    },
    {
      "entry_id": "bug/performance/linear-graphql-every-nodes-connection-2026-06-03",
      "title": "Linear GraphQL: every {nodes} connection needs first: \u2014 incl. workflowStates/tea",
      "track": "bug",
      "category": "performance",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/linear-graphql.md",
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/performance/linear-graphql-every-nodes-connection-2026-06-03.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/security/rollback-path-sanitizer-must-not-2026-06-05.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/security/shell-command-allowlist-gates-must-2026-06-05.md"
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
        "fn-74"
      ],
      "date": "2026-06-29",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/adding-a-review-backend-sweep-all-2026-06-29.md"
    },
    {
      "entry_id": "bug/integration/adding-a-tracker-to-tracker-sync-sweep-2026-06-28",
      "title": "Adding a tracker to tracker-sync: sweep WHOLE tree + read adapter ref for dep-pr",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync",
      "tags": [
        "tracker-sync",
        "gitlab",
        "fn-69",
        "doc-sweep",
        "flow:deps",
        "dependency-projection",
        "impl-review",
        "jira",
        "fn-70",
        "per-adapter-fidelity",
        "adapter-ref-crosscheck"
      ],
      "date": "2026-06-28",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/adding-a-tracker-to-tracker-sync-sweep-2026-06-28.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/byte-for-byte-spec-contract-branch-2026-07-01.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/ceremony-validation-must-read-persisted-2026-06-28.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/drop-receipt-to-break-codex-2026-05-09.md"
    },
    {
      "entry_id": "bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17",
      "title": "gh api -f stringifies numeric body fields (issue_id) \u2192 GitHub 422; use -F",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/github.md",
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/heredoc-built-json-breaks-on-free-form-2026-06-05.md"
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
        "cross-model-review"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/markerstruct-field-semantics-must-2026-06-27.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/rp-builder-file-slices-cause-false-2026-06-10.md"
    },
    {
      "entry_id": "bug/integration/set-tracker-id-rejected-github-n-2026-06-03",
      "title": "set-tracker-id rejected GitHub",
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/set-tracker-id-rejected-github-n-2026-06-03.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/skill-bash-blocks-re-declare-every-2026-07-02.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/trackers-auto-linkify-issue-key-2026-06-03.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/data/fence-preserving-writer-needs-fence-2026-07-02.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/data/migrationrollback-cli-10-review-cycle-2026-05-08.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/data/paired-snapshot-setter-must-write-both-2026-06-03.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/ui/flow-nextdev-docs-page-needs-2026-06-03.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/knowledge/workflow/final-integration-tasks-need-wider-impl-2026-05-26.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/knowledge/decisions/tracker-sync-is-projection-not-2026-06-01.md"
    }
  ],
  "legacy": [],
  "count": 55,
  "status": "active"
}

$ flowctl glossary list --json
{
  "success": true,
  "groups": [
    {
      "path": "/Users/gordon/work/flow-next/GLOSSARY.md",
      "entries": [
        {
          "term": "Spec",
          "definition": "The central artefact of flow-next: a specification at `.flow/specs/<id>.md` (markdown body) plus `.flow/specs/<id>.json` (metadata sidecar, post-1.0). Reviewable on its own; cross-model-reviewed; verifiable against prior handovers; frozen at handover. Replaces the term *epic* from the 0.x line.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Ready",
          "definition": "A human-owned boolean on the spec record (default `false`, toggled via `flowctl spec ready` / `spec unready`) marking a spec complete enough to hand to an agent \u2014 the entry gate autonomous loops consume. Orthogonal to `status` (`open|done`): a ready spec stays `open` through planning and work. Human-owned or tracker-projected (`tracker.readyState` pulls the configured tracker state onto the local flag, one-way), never agent-inferred. Opt-in and invisible until adopted: the flag is written lazily, non-adopters see no badge, prompts, or warnings anywhere.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Task",
          "definition": "An execution unit under a spec, sized to fit one `/flow-next:work` iteration (~100k tokens fresh context). Tasks declare dependencies (`requires:`) and may declare which spec acceptance criteria they advance (`satisfies: [R1, R3]`). Implemented by a worker subagent with re-anchored context.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "R-ID",
          "definition": "A numbered acceptance criterion in a spec, format `**R1:** ...`, `**R2:** ...`. Renumber-forbidden after the first review cycle: deletions leave gaps, new criteria take the next unused number. R-IDs are the load-bearing identity of a requirement across the spec, the tasks that satisfy it, the commits that reference it, and the PR body coverage table.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Handover object",
          "definition": "A named, reviewable artefact that carries context across a step in the agentic SDLC. flow-next defines six handover states: the spec at business-layer completion (#1) and at full completion (#2) \u2014 both the **same** `.flow/specs/<spec-id>.md` file at successive layers, NOT two separate specs \u2014 then the implementation plan (#3), the working implementation (#4), the cross-model code review (#5), and the PR-as-cognitive-aid (#6). Each is reviewable on its own, cross-model-verified, and frozen at handover. The chain of handovers replaces the standups / refinement / design-review touchpoints that pre-agentic Agile relied on.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Re-anchoring",
          "definition": "Re-reading the spec, the task, and `git log` since branch base before each task starts. Counters context drift in long-running agent sessions per Anthropic guidance. Worker subagents re-anchor on every iteration; `/flow-next:work` re-anchors every loop turn.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Cross-model review",
          "definition": "A different model reviews the artefact produced by the first model. Applied at every handover. Backends: RepoPrompt (rp), Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor `cursor-agent` CLI (cursor). The disagreement surface between writing model and reviewing model is where the gaps live.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Feature map",
          "definition": "The `.clawpatch/features/*.json` index produced by `clawpatch map` and consumed by flow-next scouts via `flowctl repo-map`. Semantic feature slices across ~20 languages/frameworks (Zod-validated upstream, `schemaVersion: 1`). Wrapped by the opt-in `/flow-next:map` skill; flow-next core (flowctl) never imports or requires clawpatch \u2014 when `.clawpatch/` is absent, scouts gracefully fall back to grep/glob.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "features_anchored",
          "definition": "Optional scout output field listing feature slices from the feature map that overlap the current scope. Emitted by `repo-scout` and `context-scout` when `.clawpatch/features/*.json` is present; omitted when absent. Each entry carries a `last_mapped` timestamp so downstream skills can flag staleness (informational signal, not a block).",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Receipt",
          "definition": "A JSON artefact that gates Ralph state transitions. `flowctl impl-review` writes a receipt at `.flow/review-receipts/<branch>.json` with verdict (`SHIP` / `NEEDS_WORK` / `MAJOR_RETHINK`), confidence anchors, introduced vs pre-existing finding counts, and the deferred / suppressed counts. Ralph reads receipts to decide loop progression.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Worker subagent",
          "definition": "A subagent dispatched by `/flow-next:work` to implement a single task with fresh context. Re-anchors the spec + task + git state, implements the task, records evidence (commits + tests + done summary), and exits. The fresh context per task is what enables N tasks to run in parallel without context-bleed.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Carmack-level review",
          "definition": "The strict cross-model review tier flow-next runs by default. References John Carmack review standard. Five confidence anchors (0/25/50/75/100) gate findings; `<75` suppressed except P0 @ 50+; introduced vs pre-existing classification means only introduced findings count toward the verdict.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Triage skip",
          "definition": "A deterministic whitelist pre-check that returns `SHIP` without invoking a review backend, for trivial diffs: lockfile-only / docs-only / release-chore / generated-file-only. `flowctl triage-skip` is the helper. On by default in Ralph mode; opt-out via `--no-triage` or `FLOW_RALPH_NO_TRIAGE=1`.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "PR-as-cognitive-aid",
          "definition": "A structured PR body synthesizing nine flow-next state streams (spec with R-IDs, per-task done summary + evidence commits, decisions / bug / architecture-patterns memory, glossary changes, strategy alignment, deferred review findings, the diff itself) into a reviewable artefact. Body sections: TL;DR, R-ID coverage table, Critical changes, Decisions, Memory, Glossary/strategy deltas, Open items, Where to look. Produced by `/flow-next:make-pr`.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Ralph",
          "definition": "The flow-next hardened autonomous harness. External shell loop drives fresh Claude / Codex sessions per task with cross-model review gates, hook-enforced guardrails (ralph-guard / DCG), and receipt-based proof-of-work. Consumes **fully planned** specs only \u2014 it iterates plan-review -> work -> impl-review -> spec-completion-review until the spec ships or the iteration cap is hit; it never runs the planning fan-out (planning stays with the human or pilot). Differentiator from `ralph-wiggum`-style open-loop autonomous agents. The default autonomy path is the pilot + land pipeline; reach for Ralph when a run outlasts a session or prose guardrails aren't enough \u2014 Ralph owns the loop in a shell script, pilot hands the loop to the host's `/loop` / `/goal` primitives.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Pilot",
          "definition": "The single-tick build-loop conductor (`/flow-next:pilot`): one tick advances one ready spec by one pipeline stage (plan / plan-review / work / `[optional qa]` / make-pr \u2014 see [QA stage](#qa-stage-pipelineqa)) and ends with a terminal `PILOT_VERDICT` line; the host's `/loop` or `/goal` owns iteration. Signals autonomy to sub-skills via the `mode:autonomous` token + `FLOW_AUTONOMOUS=1` env (distinct from `FLOW_RALPH`; never activates ralph-guard). Selection consumes the fn-58 `ready` gate; two healthy no-advance ticks clear the spec's `ready` flag (don't-thrash). The default `ready` mode selects only already-ready specs; the opt-in [backlog mode](#backlog-mode-pilotautonomy) widens it to the whole open backlog.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Backlog mode (`pilot.autonomy`)",
          "definition": "Pilot's opt-in wide-autonomy behavior (fn-68), gated by config `pilot.autonomy \u2208 {ready (default), backlog}` (per-run override `--backlog` / `--auto`; with the gate off, pilot is byte-for-byte unchanged and `references/backlog-mode.md` is never even read). A backlog tick **enumerates the full open set** \u2014 flow specs (`flowctl ready --all`) **plus** tracker issues at the promoted lane (`listOpenIssues`, unioned in by the skill) \u2014 selects the top **dep-ordered** actionable item, runs the [triage stage](#triage-stage-backlog-mode) in front of pilot's existing pipeline, and either advances it one stage (`plan \u2192 plan-review \u2192 work \u2192 [qa] \u2192 make-pr`) or parks it behind an [async question](#ask-stage--question-valve). It is a **leftward extension of the same single-tick conductor**, not a new skill or altitude: one `/loop`/`/goal` target, one verdict grammar, one mental model; the host primitive still owns repetition. The consent boundary moves from *before* the loop to *inside the loop, on block* \u2014 but the load-bearing boundaries hold: it **never authors a spec** (a thin/missing spec is surfaced as a \"run `/flow-next:capture` or `/flow-next:interview`\" gap, never auto-written), **never sets the `ready` flag** (promotion is the human's board act), and **never merges** (land stays human-gated). Readiness is the human's **explicit signal** (the fn-58 ready gate set OR tracker status exactly at `tracker.readyState`), never an agent-inferred completeness score \u2014 un-promoted backlog items are skipped silently.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Triage stage (backlog mode)",
          "definition": "The classify-and-route stage backlog mode runs **in front of** pilot's existing `classify`, on the selected item only. It reads the spec **agentically** (the host's judgment, never a flowctl-computed `triageClass`) and routes by *explicit state first*: **workable** (ready signal + complete spec) \u2192 select-and-advance (pilot's existing path); **ready-but-thin / ready-but-ambiguous** (signal present, spec missing or too thin to act on) \u2192 [`ask`](#ask-stage--question-valve) (kick back with the gap, never build, never auto-author); **dep-unsatisfied** \u2192 `BLOCKED <id> by <dep>` (a state-changing surface of the dep wait); **needs a human decision** \u2192 `ask`. A *live* triage always lands on a **state-changing terminal** (`ADVANCED` / `ASKED` / `BLOCKED` / `NEEDS_HUMAN`) so an item can never re-select forever; `TRIAGED <id> <class>` is **diagnostic / `--dry-run` only**. `needs-spec` is always a *promoted* item missing a workable spec \u2014 never an un-promoted idea, which is simply skipped.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Ask stage / question valve",
          "definition": "Backlog mode's **async human-in-the-loop valve** \u2014 \"stuck\" becomes a question, not a stall, and never an interactive `AskUserQuestion`. When it cannot safely proceed, the `ask` stage writes each Open Question behind a **stable anchor** `<!-- flow-next:question id=<hash> status=open -->` (`id` hashes **stable fields only** \u2014 `subjectId` + blocked-stage + reason code + question slug; the free-prose reason is *outside* the hash so rephrasing never duplicates) and surfaces it where the item lives: a **spec-backed** item parks via the spec's `## Open Questions` section **and** a projected tracker comment; a **tracker-only** item (no spec) parks in the tracker comment alone. Projection is transport-blind across GitHub / GitLab / Jira / Linear via tracker-sync's adapter; no transport \u21d2 spec-only (when a spec exists) + a one-line \"enable X to mirror\" note, never a block. Selection **skips any item carrying a `status=open` parked question**, so it is never re-picked. A human answer (flipping the spec anchor to `status=answered`, or a tracker reply carrying `<!-- flow-next:answer id=<hash> -->` matched by `id`) makes the next tick re-triage and proceed. Terminal verdict: `ASKED <id> (<n>)` \u2014 a durable park.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Decision log (`pilot-log`)",
          "definition": "The per-tick **factory-metrics substrate** backlog mode writes (fn-68) via `flowctl pilot-log append --id <id> --action <triaged|advanced|asked|blocked|needs-human> --stage <stage|-> [--cost-tokens <n>]`, summarized by `flowctl pilot-log summary --json` \u2192 `{tick, id, action, stage, costTokens}` rows. The action enum is **aligned to the verdict grammar**; token cost is **host-reported** (omitted/null when unavailable) \u2014 flowctl only stores the row, never measures cost. Rows yield the efficiency readout (% moved with no question / one async answer / parked, and cost per change) and are the substrate a future self-improvement-synthesis spec mines. Stored under `.flow/pilot-runs/` (a sync-runs-style dir, auto-gitignored) \u2014 deliberately **NOT** any `receipts/` path the ralph-guard validates.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Land",
          "definition": "The cadence-tick ship loop (`/flow-next:land`): one tick discovers the open PRs the build loop authored (spec `branch_name` match AND the make-pr breadcrumb \u2014 both signals required), walks each through the gate tree (CI tri-state over ALL checks, patience window anchored to the last push, resolve-pr convergence, `land.reviewSignal`), and takes at most one action class per PR \u2014 CI fix, resolve dispatch, mechanical rebase, or the gated explicit merge (`gh pr merge --squash --match-head-commit`, never `--auto`) plus the post-merge tail (spec close \u2192 tracker touchpoint \u2192 release-follow). The one confined exception to the no-auto-merge rule; `/loop`-shaped where pilot is `/goal`-shaped. Ends with a terminal `LAND_VERDICT` line.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "QA stage (`pipeline.qa`)",
          "definition": "The optional live-app QA pass `/flow-next:qa`, graduated into a config-gated pilot stage (`pipeline.qa`, default **off**). When on, pilot runs one live pass over the complete build at all-tasks-done \u2014 `plan -> plan-review -> work -> **qa** -> make-pr` \u2014 driving the app the dev already has running during `work`. **Evidence-aware** (subtracts only AC a deterministic re-runnable check already proved; always live-runs every runtime / UI / integration criterion because the worker's self-report is narration, not captured evidence), **surfaced not blocking** (routes on `qa_outcome`, NOT the Ralph-guard `verdict` projection \u2014 `SHIP`/`NA`/`BLOCKED` advance, `NEEDS_WORK` still advances to the **draft** PR with findings in a `## Live QA` section + the bug-memory track + a tracker comment), and **augments, never replaces** CI / staging / manual QA. Net-new is one config-key default plus additive `qa_verdict` receipt fields (`head_sha` / `rid_coverage` / `open_p0p1`) \u2014 no new flowctl subcommand, no persisted test-case artefact. Idempotent per branch head via the receipt's `head_sha`. See `skills/flow-next-qa/SKILL.md` (fn-72).",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Verdict",
          "definition": "The structured tick outcome a loop skill prints for transcript-blind drivers, always the last line of a tick. Pilot: `PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason=\"<one line>\"`; [backlog mode](#backlog-mode-pilotautonomy) **adds `ASKED <id> (<n>)`** (a durable park) and keeps every existing terminal verbatim (drivers grep `DEFERRED_TO_LAND` for the land hand-off, stop on `NO_WORK`); `TRIAGED <id> <class>` is diagnostic / `--dry-run` only, never a live terminal. Land: `LAND_VERDICT=<MERGED|RELEASED|FIXING_CI|AWAITING_REVIEW|RESOLVING|BLOCKED|NEEDS_HUMAN|NO_WORK> prs=<n> pr=<deciding-pr-url|-> reason=\"<one line>\"` (tick verdict = worst severity across PRs). Autonomous resolve-pr runs end with `RESOLVE_PR_VERDICT=<RESOLVED|PENDING|NEEDS_HUMAN> threads=<n> fixed=<n> needs_human=<n>`, which land gates on. Distinct from a review receipt (Ralph's file-based proof-of-work): a verdict lives in the conversation output because `/goal` validators read the transcript, never the filesystem.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Spec-as-PR",
          "definition": "A team workflow where the spec is opened as a draft PR for review BEFORE any code lands. Reviewing a 50-line spec is higher-leverage than reviewing a 500-line implementation. Once merged, the spec is frozen on main; implementation PRs reference the merged spec.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Frozen-at-handover",
          "definition": "The R-ID invariant. Once a spec has been reviewed once, R5 means the same thing forever. A reviewer reading R5 in a six-month-old commit, a new team member reading R5 in the spec, and `/flow-next:make-pr` emitting R5 coverage all refer to the same acceptance criterion. Renumber-forbidden after first review cycle.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "flow-swarm",
          "definition": "An in-progress companion product to flow-next that reads `.flow/specs/` directly to coordinate parallel agents across worktrees and consume `/flow-next:make-pr` output. The on-disk layout flow-swarm expects is what fn-43 (epic->spec rename) produces. Reference target for the v1.0 migration carrot.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Tracker",
          "definition": "An external issue tracker (Linear, GitHub Issues, GitLab, or Jira) that flow-next *projects* a spec to via `/flow-next:tracker-sync`. The tracker is a **co-editable mirror** \u2014 body, status, and comments sync two-way \u2014 but it is **projection, not coordination**: the `.flow/specs/<id>.md` spec stays the source of truth and the quality layer, and the tracker never drives flow state or spawns agents. Distinct from `/flow-next:sync` (plan-sync). Contrast OpenAI Symphony, where the tracker *is* the control plane.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "merge-base snapshot",
          "definition": "The common-ancestor body the tracker-sync 3-way merge compares against \u2014 a **paired** snapshot taken at the last sync point: both a flow-form body and a tracker-form body, plus content hashes (the echo fence). Stored in the spec-JSON `tracker` block (`mergeBaseFlow` / `mergeBaseTracker` / `baseHashFlow` / `baseHashTracker`) and written atomically as a unit (a one-sided update is rejected, so neither half pins to a stale sync point). Advances with `lastSyncedAt` on a real reconcile, never on a no-op echo.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "discovery ceremony",
          "definition": "The detect \u2192 surface \u2192 ask \u2192 never-assume flow `/flow-next:tracker-sync` runs before enabling the bridge. It probes six signals (Linear MCP, `LINEAR_API_KEY`, GitHub auth, GitLab auth/`GITLAB_TOKEN`, Jira REST + token \u2014 `JIRA_BASE_URL` plus Cloud `JIRA_EMAIL`+`JIRA_API_TOKEN` or DC/Server `JIRA_PAT`), surfaces what is present *and* absent, asks the user, and writes `tracker.*` config **only on confirmation**, with provenance. No signal \u21d2 nothing written; the bridge stays off. Resolution model is env > config > ask (mirrors `flowctl review-backend`).",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "tracker-key handle",
          "definition": "A tracker identifier (e.g. `WOR-17`) used as a **resolvable flow id**, the hybrid id model. **Tracker-first** specs are canonically `wor-17-slug` (tasks `wor-17-slug.M`); bare `wor-17` / `wor-17.M` resolve as aliases. **Flow-first** specs keep `fn-NN-slug` and store `WOR-17` in `tracker.identifier` as a resolvable display alias. Resolution is case-insensitive (`show wor-17`, `work wor-17` resolve); the native `fn-` scheme is reserved (`fn-N` allocation counts `fn-*` only); one tracker team per repo; **ids never rename** on link.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "dependency projection",
          "definition": "Tracker-sync's projection of a spec's local `depends_on_epics` edges into **tracker issue relations** (fn-64) \u2014 a `depends_on_epics` edge between two linked specs becomes a **blocked-by** relation between their issues (Linear native relations / GitHub native dependencies / GitLab native `is_blocked_by` issue links / Jira native \"is blocked by\" issue links \u2014 directional and universally available, no licence gate, no `flow:deps` block \u2014 else, for GitHub's reduced rung and GitLab on every tier, a provenance-fenced `<!-- flow:deps -->` body block). The relations counterpart to body/status/comments sync: projection, not coordination \u2014 flow stays authoritative, the tracker never declares deps back. Runs through the transport-blind `projectDepRelations` hook + the normalized `setIssueRelation` / `listIssueRelations` adapter pair; idempotent via read-before-write. No transitive/graph expansion \u2014 only direct edges project.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "provenance ledger",
          "definition": "The per-spec `depRelations` list (in the `.flow/specs/<id>.json` `tracker` block, atomic write) that records **which** dependency relations tracker-sync created \u2014 so projection is idempotent and removals are provably-ours-only. Each entry is `{key, dep_spec, from_tracker_id, to_tracker_id, type, source, updatedAt}`, where `key` is an opaque hash of the directed issue pair (never a raw issue key inline \u2014 trackers auto-linkify keys even inside HTML comments). A relation **not** in the ledger (native trackers) / **outside** the `<!-- flow:deps -->` fenced block (GitHub's fenced fallback; GitLab's block on every tier) is never removed: a human's manual relation is safe by construction. Mirrors the merge-base hash-provenance shape, minus its paired-snapshot constraint.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "completed-blocker rule",
          "definition": "The tracker-sync semantics for a dependency whose **local** dep spec is `done` (\u2192 its issue Done/Closed): the projected blocked-by relation stays **visible** on the tracker (preserving the real historical ordering on the board) but does **NOT** feed back into Flow `ready=true` gating \u2014 readiness already treats done deps as satisfied, and dependency projection must not regress that. Keys off the *local* dep-spec status (flow is authoritative), never a remote fetch.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "render lens",
          "definition": "A regenerable human-review artifact (HTML) derived from a markdown source of truth; never the storage format, always re-derivable. flow-next ships two: the spec artifact and the PR artifact, both living at fixed deterministic paths under `.flow/artifacts/<spec-id>/` (never timestamped \u2014 Lavish keys annotation sessions on the absolute path). Every lens is self-contained single-file HTML (inline CSS/JS, zero external requests), carries a staleness stamp in its footer, and is never parsed back as state \u2014 regeneration always overwrites the same file.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "HTML artifact mode",
          "definition": "The opt-in feature (2.0.0+) that makes participating skills (capture, plan, make-pr) emit render lenses alongside their markdown output. Activated via `flowctl config set artifacts.html.enabled true` (OFF by default, offered once by `/flow-next:setup`); when active, skills load the shared disclosure reference at `plugins/flow-next/references/html-artifacts.md` \u2014 the single carrier of all generation rules and the anti-slop design contract. With the mode off, skills load nothing extra: zero token cost, zero behavior change. Markdown and tracker-sync remain the sole source of truth.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "spec artifact",
          "definition": "The spec's render lens at `.flow/artifacts/<spec-id>/spec.html`. ONE generation pathway with state-dependent rendering: spec-only view before tasks exist (capture workflow \u00a75.10 \u2014 the business-review surface) and the added plan layer (task dependency DAG with critical path, R-ID \u2192 task coverage matrix) once tasks exist (plan Step 8.5 \u2014 after the refinement loop exits). Links back from the spec markdown via the idempotent `<!-- flow-next:artifact-link -->` marker line (replaced in place, repo-relative target). The only artifact that enters the Lavish annotate loop.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "PR artifact",
          "definition": "The PR's render lens at `.flow/artifacts/<spec-id>/pr.html`, emitted by `/flow-next:make-pr` Phase 1.5. A **read-only review instrument**: diff-derived (never from commit messages), verified against the spec's R-ID export before publishing \u2014 mismatches render as visibly flagged rows, warn-in-artifact, never blocking. Committed narrowly (`chore(flow): pr artifact <spec-id>`, artifact file only) so the PR body's SHA-pinned blob link resolves; never enters the annotate loop \u2014 review conversation belongs to the code host.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Lavish (lavish-axi)",
          "definition": "An optional detect-on-PATH companion (npm: `lavish-axi`) for annotating spec artifacts in the browser \u2014 never wrapped, bundled, or required (same shape as clawpatch/`/flow-next:map`). Feedback is pull-only and session-spanning: annotations queue in the global `~/.lavish-axi/state.json` (not per-workspace), survive agent death, and any later agent session drains them via the `lavish-axi poll` CLI, mapping each annotation to a markdown-source edit followed by lens regeneration. Sessions key on the absolute artifact path (different worktrees = separate sessions); the local server idle-stops after ~30 min and `lavish-axi <file>` resumes it \u2014 absence or idle-stop is invisible because the artifact is a self-contained static page. Autonomous contexts never open a session and never poll.",
          "avoid": [],
          "relates_to": []
        }
      ],
      "count": 38
    }
  ],
  "file_count": 1,
  "total_terms": 38
}
