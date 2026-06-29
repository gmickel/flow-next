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
- **Oversized prompts — VERIFIED on POSIX (60KB argv).** Reuse copilot's argv-vs-temp threshold. **Windows is the one open risk:** cursor-agent stdin support is unconfirmed and there is no `CreateProcessW`-safe path yet → during impl either confirm/implement a stdin path OR explicitly document Windows large-prompt as unsupported (don't silently hardcode argv).
- **Triage precision** — see Architecture §8: deterministic by default; opt-in LLM judge stays codex/copilot and is a documented dependency for cursor users who enable it.
- **Auth not configured** → `check` and runners surface a clear error pointing at `cursor-agent` login / `CURSOR_API_KEY` (never a silent empty review).
- **`.result` empty / `is_error:true`** → backend failure (non-zero exit + stderr), never a false SHIP.
- **Effort must not leak** — copying copilot receipt code literally risks writing `effort:"high"`; cursor receipts must omit `effort` (assert in tests).
- **Model-list drift** — Cursor ships model strings without changelog (and auto-updates the CLI); document "keep synced with `cursor-agent --list-models`", copilot-style note.
- **Not the host driver.** Independent of the `CURSOR_AGENT` host-platform path; works on any host with `cursor-agent` installed.

## Acceptance Criteria

- **R1:** `cursor` is in `BACKEND_REGISTRY` and `VALID_BACKENDS`; `flowctl review-backend` resolves/reports `cursor` from `.flow/config.json`, `FLOW_REVIEW_BACKEND`, per-task stored review, and `--spec`.
- **R2:** `BackendSpec.parse("cursor")` / `parse("cursor:gpt-5.5-high")` succeed; `parse("cursor:gpt-5.5-high:high")` raises (effort rejected); `parse("cursor:bogus")` raises listing valid models; `.resolve()` fills `gpt-5.5-high`, effort `None`.
- **R3:** `run_cursor_exec` shells `cursor-agent -p --output-format json --trust --mode ask --model <m>` with `cwd=repo_root`; on a first call it omits `--resume` and returns Cursor's generated `session_id`; on continuation it passes `--resume <session_id>`; parses `.result`/`.session_id`/`.is_error`; returns non-zero on a 600s timeout.
- **R4:** `flowctl cursor check [--skip-probe]` reports availability + version + auth (`authed`) in text and `--json`, schema-aligned to copilot's `check`.
- **R5:** `flowctl cursor impl-review <task> --base <b> --receipt <r>` writes a `mode:"cursor"` receipt (no `effort` key) and prints `VERDICT=...`.
- **R6:** `cursor plan-review`, `completion-review`, `validate`, `deep-pass` dispatch through `run_cursor_exec` and write the same additive receipt shapes as codex/copilot (`mode:"cursor"`).
- **R7:** Re-review with an existing `mode=="cursor"` receipt resumes via `--resume <session_id>` (using the persisted returned id); a cross-backend receipt starts fresh.
- **R8:** A cursor review leaves the working tree unchanged (`git status` identical before/after).
- **R9:** `/flow-next:impl-review` routes `BACKEND=="cursor"` to `workflow-cursor.md`; `/flow-next:plan-review` and `/flow-next:spec-completion-review` handle `cursor`; every user-facing `--review=rp|codex|copilot|none` string includes `cursor`.
- **R10:** `flow-next-setup` `review.backend` config accepts `cursor` and spec form `cursor:gpt-5.5-high`.
- **R11:** Tests: `test_cursor_run_exec.py` (mock subprocess: success / `is_error` / timeout / **first-call-omits-resume** / **resume-passes-id** / **cwd=repo_root** / **no-effort-in-receipt**), `test_backend_spec.py` cursor cases (model-yes/effort-no), receipt-schema `mode:"cursor"`. Full Python suite passes.
- **R12:** `scripts/sync-codex.sh` regenerated; `cursor` surfaces in the codex mirror; install/sync parity tests pass.
- **R13:** Docs chain updated at the concrete targets below; **no version bump** (batched), entries under `## Unreleased`:
  - **Repo:** `plugins/flow-next/docs/flowctl.md` (cmd list L14 + new cursor backend section), `README.md` (L44 / L253 / L290 backend lists), `GLOSSARY.md` (L29 "Backends:" list), root `CHANGELOG.md` `## Unreleased`.
  - **flow-next.dev:** `src/content/docs/review/workflow.mdx` + `review/receipts.mdx` + `install.mdx` backend enumeration, `releases/changelog.mdx`, bump `src/lib/site.ts` `FLOW_NEXT_VERSION` + `package.json`. No new page → navbars unchanged. Run `pnpm build`.
  - **AI-x-SDLC:** `guides/flow-next.md` (L65 "(RepoPrompt, OpenAI Codex, GitHub Copilot)" → add Cursor), `guides/code-review-tools-changelog.md`.
  - **GrowthFactors:** `spec/05-cross-model-review.md` (claim already lists Cursor — verify/tighten), re-render `dist/gf.html` (+ `shd`/`shopfully`/`flooid`) and the bundled `~/work/AI-x-SDLC-Starter-Kit/resources/assets/code-factory-onboarding.html`.
  - **Obsidian vault:** the cross-model-review / Skills Catalog / Release Timeline note(s).
- **R14:** Cursor `impl-review` / `completion-review` receipts carry the **same rigor fields as copilot** — confidence-rubric anchors, suppressed-finding counts, introduced-vs-pre_existing classification, unaddressed-R-ID surfacing, and protected-path filtering — asserted by a receipt-parity test against the copilot field set.

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
