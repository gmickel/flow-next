# Changelog

All notable changes to the flow-next.

## [flow-next 1.0.1] - 2026-05-09

### Fixed
- **Bare spec id (`fn-N`) resolves to slugged spec (`fn-N-slug`) across all spec-id-accepting commands.** Pre-1.0.1, `flowctl show fn-43` failed with "Spec fn-43 missing" because the resolver did literal `<id>.json` lookup — only `flowctl show fn-43-rename-epic-spec-across-flow-next` worked. The same issue silently mis-globbed `flowctl tasks --spec fn-43` and `flowctl ready --spec fn-43` to zero results. Now: when the literal file is absent and exactly one slugged file matches `<id>-*.json`, the bare form expands automatically. Multiple matches error with a disambiguation list ("Spec id 'fn-N' is ambiguous. Matches: fn-N-foo, fn-N-bar. Use the full slug."). Single canonical helper `expand_bare_spec_id` runs at the entry of every spec-id command (`show` / `cat` / `close` / `set-plan` / `set-plan-review-status` / `set-completion-review-status` / `set-backend` / `tasks --spec` / `ready --spec` / `next --spec` / `validate --spec` / `checkpoint *`). Pre-existing limitation since 0.x — not introduced in 1.0.0; surfaced and fixed during 1.0 dogfooding. (12 unit tests in `tests/test_expand_bare_spec_id.py`.)

### Marketplace housekeeping
- **Legacy `flow` plugin removed.** The original two-step planning + execution plugin (`plugins/flow/`) has been deleted from the marketplace; `flow-next` is now the only plugin shipped here. The legacy plugin had been unmaintained for ~10 months and never tagged a release — keeping it side-by-side with `flow-next` confused new users about which to install. Marketplace metadata (`.claude-plugin/marketplace.json`), `scripts/install-codex.sh`, `scripts/bump.sh`, and `CLAUDE.md` updated to reference flow-next exclusively. To browse or restore the old code: `git show 0a45aff:plugins/flow/README.md` or `git checkout 0a45aff -- plugins/flow/` (last commit on `main` containing the plugin tree).

## [flow-next 1.0.0] - 2026-05-09

### What changed
- **`flowctl epic` renamed to `flowctl spec`; `.flow/epics/` JSON sidecars relocated under `.flow/specs/` (markdown specs already lived there in 0.x); `epic-scout` renamed to `spec-scout`; `/flow-next:epic-review` renamed to `/flow-next:spec-completion-review`.** Two years of "epic spec" prose collapsed into one word — `spec` — across the entire flow-next surface. The plugin now ships epic-free: skills, commands, agents, slash-command markdown, smoke tests, internal docs, root README + plugin README + CLAUDE.md + `.flow/usage.md`, Ralph init templates, and the Codex mirror all use spec vocabulary as canonical. Worker-prompt heredoc fields renamed `EPIC_ID → SPEC_ID`; Ralph init template variable `EPICS_FILE → SPECS_FILE`; cognitive-aid payload key `epic_id → spec_id` (both surface in dual-emit during the alias window). Why now? Two reasons: (1) "epic" overloaded "release-train epic" in user vocabulary and produced cross-team friction every time a new contributor read flow-next prose; (2) flow-swarm — the planned multi-agent orchestrator — needs the `spec` lexicon as its canonical primitive, and shipping the rename in 1.0 closes the last design ambiguity before flow-swarm's first cut.

### What still works
- **All 0.x scripts and CLAUDE.md examples keep working through 1.x.** The `flowctl epic*` CLI surface stays as a deprecation alias layer that calls into canonical `cmd_specs_*` / `cmd_spec_*` entry points. `--epic` argparse flags remain accepted (alongside new `--spec`); JSON read responses dual-emit `spec_id` *and* `epic_id` so existing pipelines see both keys; on read, `.flow/epics/` is auto-fallback when `.flow/specs/` is absent. The legacy `EPIC_ID` heredoc field is still parsed by the worker prompt; the legacy `EPICS_FILE` variable is still recognized by Ralph init. Every alias path emits a one-time stderr deprecation hint pointing at the canonical CLI; suppress with `FLOW_NO_DEPRECATION=1` (mirrors the existing `flowctl memory migrate` precedent). End result: copy-pasted CLAUDE.md examples from 0.x repos run unchanged on 1.0.0; existing `.flow/epics/` directories require zero immediate action.

### Two migration paths
- **Interactive (recommended):** `/flow-next:setup` — host agent walks the user through the migration, shows the dry-run plan, prompts for confirmation, and runs `flowctl migrate-rename --yes` on consent.
- **Deterministic (automation):** `flowctl migrate-rename --dry-run` first to preview the plan; then `flowctl migrate-rename --yes` to apply. The migration is transactional — atomic backup at `.flow/.backup-pre-1.0/`, lockfile-guarded against concurrent runs, sentinel `.flow/.migration-manifest` for idempotency, crash-recovery decision tree on every invocation. Moves the JSON sidecars `.flow/epics/<id>.json` → `.flow/specs/<id>.json` (the markdown specs already lived at `.flow/specs/<id>.md` in 0.x — only the sidecars relocate), rewrites `epic:` → `spec:` keys in `meta.json` and per-task JSON state files, removes the now-empty `.flow/epics/` directory, and stamps the post-migration sentinel `.flow/.flow_version`. End state: spec JSON + spec markdown colocated under `.flow/specs/`.

### Optional cleanup
- **Refresh your CLAUDE.md / AGENTS.md prose.** Aliases keep examples working through 1.x (see Alias removal timeline below), but the deprecation banner stops nagging once your prose uses `flowctl spec` everywhere. Quick `sed` snippet:
  ```bash
  # In-place rewrite (BSD sed — macOS); GNU sed users drop the empty -i argument.
  sed -i '' \
    -e 's|flowctl epic create|flowctl spec create|g' \
    -e 's|flowctl epic set-plan|flowctl spec set-plan|g' \
    -e 's|flowctl epics|flowctl specs|g' \
    -e 's|flowctl epic |flowctl spec |g' \
    -e 's|--epic |--spec |g' \
    -e 's|\.flow/epics/|.flow/specs/|g' \
    CLAUDE.md AGENTS.md
  ```
  Always commit your CLAUDE.md / AGENTS.md before running this; review the diff and tweak edge cases (deprecation context, fenced-code examples that intentionally show the legacy form). A future `flowctl migrate-docs --dry-run` helper will automate this with diff-preview semantics — deferred from 1.0.0 to keep the release surface tight.

### Alias removal timeline
- **Aliases are not deprecated forever.** The current contract: aliases keep working through all of 1.x, with stderr deprecation hints (suppressible via `FLOW_NO_DEPRECATION=1`). Soft removal target is 2.0.0 — telemetry-driven, NOT calendar-driven. We'll watch the deprecation-hint stderr counts (and direct user feedback) for the duration of 1.x; if real-world `flowctl epic` invocations have effectively zeroed out, 2.0.0 drops the alias layer. If usage stays high, the alias layer stays. R28 explicitly forbids hard-coded sunset dates — a flag day with no escape hatch is a footgun on a tool that runs in production loops.

### Rollback
- **`flowctl migrate-rollback --yes` restores the pre-1.0 layout.** The migration writes a transactional backup to `.flow/.backup-pre-1.0/` before touching anything; rollback restores from that backup, deletes `.flow/specs/` + `.flow/.migration-manifest`, and re-asserts `.flow/epics/`. Post-migration writes (new specs / task updates / done summaries authored after migrate-rename) are detected and rollback refuses by default — pass `--force-overwrite-post-migration-changes` to discard them explicitly. Lockfile-guarded so a peer migrate-rename + migrate-rollback can't race.

### Auto-managed `.flow/.gitignore`
- **`flowctl init` and `flowctl migrate-rename` now write `.flow/.gitignore`** with patterns that exclude transient migration + per-run state from version control. Auto-managed block:
  ```gitignore
  # Auto-managed by flowctl — do not edit above this marker.
  .checkpoint-*.json
  receipts/
  tmp/
  .backup-pre-1.0/
  .banner-acknowledged
  .migrating
  .migration-manifest
  # End of auto-managed block. User patterns below this line are preserved.
  ```
  Idempotent on subsequent invocations; user-added patterns below the footer are preserved on update. **Why this matters:** without it, the first `git add -A` after running `flowctl migrate-rename` would commit a multi-megabyte `.flow/.backup-pre-1.0/` directory, the per-developer `.flow/.banner-acknowledged` timestamp, and the stale `.flow/.migrating` lockfile. `.flow/.flow_version` is intentionally NOT in the auto-managed block — that's the schema sentinel and should be tracked per repo so multiple devs share the migrated state (semantics like `Cargo.lock`).

### Known issue (anthropics/claude-code#52218)
- **Claude Code's plugin auto-update may stale on bundled hook changes.** When a flow-next release ships hook-file changes (Ralph guard hooks, PreToolUse matchers), Claude Code's plugin auto-update path occasionally serves the cached pre-update hook bundle even after the manifest version bumps. Symptom: `flowctl` CLI reports 1.0.0 but Ralph guard hooks behave like 0.42.0. Workaround: run `/plugin update flow-next` manually once after upgrading; this forces a hot-reload of the bundled hook bundle. Tracking upstream: anthropics/claude-code#52218. Codex (`scripts/install-codex.sh flow-next`) and Factory Droid plugin paths are unaffected — only the Claude Code marketplace auto-update path exhibits this behavior.

### Notes
- **Why `spec` and not `epic-spec` / `feature-spec` / `plan`?** Single-word primitives compose better in CLI grammar. `flowctl spec create` reads cleanly; `flowctl epic-spec create` reads as if there's an unspoken `epic` parent. The shorter form also matches GitHub's `gh pr create` / `gh issue create` cadence — the rename brings flow-next in line with the existing CLI lexicon users already have in muscle memory.
- **Why a major bump?** Renaming the canonical CLI surface and the on-disk directory layout is a breaking-change-shaped event even when aliases preserve every behavior. Semver says: don't surprise people. 1.0.0 is also a deliberate signal — flow-next has been production-stable since the 0.30.0 era; the version number was holding the ecosystem back from treating it as a 1.x dependency. Both motivations align.
- **Why dual-emit JSON instead of a hard cutover?** Dual-emit lets downstream tooling (the future flow-swarm orchestrator, third-party integrators reading flowctl JSON output) migrate at their own cadence inside the 1.x window. JSON consumers reading `epic_id` keep working; consumers reading `spec_id` see the new canonical key from day one. The dual-emit overhead is two extra dictionary entries per response — measured cost, not theoretical.

## [flow-next 0.42.0] - 2026-05-07

### Added
- **`/flow-next:make-pr` — PR-as-cognitive-aid skill.** New eighteenth slash command closes the gap between "all tasks done" and "human reviews the PR." Five phases (pre-flight → gather → build body → mermaid → push + create) render a reviewable PR body from rich flow-next state: epic spec with R-IDs, per-task `done_summary` + evidence commits, `decisions` / bug / `architecture-patterns` memory, glossary changes, strategy alignment, deferred review findings, and the diff itself. Body sections include TL;DR, R-ID coverage table (R# → satisfying task → evidence commit), Critical changes (high-churn / cross-module / public-interface / security-sensitive / behavior-visible), Decisions, Memory references, Glossary/strategy deltas, Open items, and Where to look (reviewer-focus list). Default `--draft` if open items > 0 or under Ralph; `--ready` overrides. Uses `gh pr create --body-file` (NOT heredoc — LLM-generated markdown frequently contains characters that break heredocs and shell interpolation). NOT Ralph-blocked — PR creation is the autonomous-loop terminus, and Ralph defaults to `--draft` for human review. NO cross-model review of the PR body — each harness's own model identifies critical changes from the structured input; `/flow-next:impl-review` already covers the *code itself*, so reviewing the description too is double-counting.
- **Mermaid codefences when diff crosses module boundaries.** Skill emits up to 3 diagrams × 12 nodes (hard caps) when changes touch ≥2 modules. Markdown codefences only — GitHub / GitLab / Gitea render natively, no external rendering pipeline. `mermaid-rules.md` ref file documents reserved words, escape patterns, shape selection, and the pre-emission validation checklist. Disable via `--no-mermaid`.
- **`flowctl epic export-cognitive-aid <epic-id> --base <ref> --json` plumbing.** New deterministic flowctl subcommand aggregates 9 input streams (epic spec, tasks + done summaries + evidence, R-ID coverage, decisions / bug / architecture-patterns memory, glossary deltas, strategy alignment, deferred review findings, diff stats) into a single structured JSON payload. Reusable from skills + scripts; the skill consumes it as the single source of truth for body rendering.
- **Smoke test `plugins/flow-next/scripts/make-pr_smoke_test.sh`** covering `export-cognitive-aid` JSON shape + body-rendering invariants + `--dry-run` (no push, no `gh pr create`).
- **Codex sync regenerated.** New `flow-next-make-pr` `openai.yaml` entry (workflow tier, brand color `#3B82F6`); `REQUIRED_OPENAI_YAML_SKILLS` array updated. Canonical skill files use Claude-native `AskUserQuestion`; `sync-codex.sh` rewrites to `request_user_input` for the Codex mirror per repo convention.

### Notes
- **Why PR-as-cognitive-aid?** The framing comes from a simple observation: don't ask a human to skim a 10K-line diff — ask the agent to make those 10K lines reviewable. The PR body itself is the artefact that lets a reviewer decide *where to focus* before opening any file. flow-next already collects every input that body needs — this skill stitches them.
- **Why no cross-model review of the body?** Each harness (Claude Code, Codex, Droid) is competent at "what looks important here?" given the rich structured input. `/flow-next:impl-review` already covers the *code itself*; running a second review on the description would be double-counting and inflate latency for no gain.
- **Why NOT Ralph-blocked?** PR creation is the natural autonomous-loop terminus — Ralph just opened a draft PR for human review. Ralph defaults to `--draft` (human reviews on their cadence; `/flow-next:resolve-pr` handles the response loop after).
- **Why `--body-file` not heredoc?** LLM-generated markdown frequently contains backticks, `$`, dollar-paren, and other shell-interpolation characters that mangle heredoc-passed strings. `gh pr create --body-file <path>` reads bytes verbatim from disk.

## [flow-next 0.41.1] - 2026-05-07

### Changed
- **Codex subagent default model bumped `gpt-5.4` → `gpt-5.5`.** The 11 intelligent subagents (opus-tier + smart-sonnet-tier in the Claude Code mapping) now use `gpt-5.5` in their pre-built tomls. The 8 fast scouts stay on `gpt-5.4-mini` (mini doesn't support reasoning tiers; no value in bumping). `worker` and `pr-comment-resolver` continue inheriting from parent. `flowctl.py`'s review-backend default was already `gpt-5.5:high` (lines 2632 / 2661) — this change closes the gap between subagent and review-backend defaults.
- **Per-agent reasoning effort split: `quality-auditor` stays at `high`; all other intelligent subagents drop to `medium`.** `quality-auditor` is review-shaped (a second pair of eyes on uncommitted changes) — undershooting risks missed regressions. Scout / editorial agents (10 of them) run efficiently at `medium`. New env vars `CODEX_REASONING_EFFORT` (default `medium`) and `CODEX_REASONING_EFFORT_AUDITOR` (default `high`) override per tier; new helper `reasoning_effort_for(<agent>)` in `sync-codex.sh` dispatches per-agent. The actual review backend (`flowctl impl-review` / `plan-review` / `completion-review`) is configured separately and unaffected — it remains at `gpt-5.5:high` via `flowctl.py`.
- **Doc updates.** `CLAUDE.md` model-mapping table reformatted to a 5-row tier with explicit per-agent reasoning column; example `codex:gpt-5.4:xhigh` spec-form examples updated to `codex:gpt-5.5:xhigh`. `plugins/flow-next/README.md` model-mapping section updated to match. Registry catalog rows (`gpt-5.5`, `gpt-5.4`, `gpt-5.2`, ...) preserved — `gpt-5.4` remains a valid catalog model, just not the subagent default.

## [flow-next 0.41.0] - 2026-05-02

### Changed
- **CI smoke matrix expanded to 7 suites on ubuntu / macos / windows.** Beyond `ci_test.sh` (already in matrix), the workflow now runs `resolve-pr_smoke_test.sh`, `strategy_smoke_test.sh`, `audit_smoke_test.sh`, `glossary_smoke_test.sh`, `prospect_smoke_test.sh`, `impl-review_smoke_test.sh`, and `smoke_test.sh` on each OS leg. ~596 assertions per leg, ~260s runtime, matrix wall time ~4 min. `fail-fast: false` so one OS failure no longer cancels the others; `defaults.run.shell: bash` unifies the matrix; `if: always()` on each smoke step ensures full diagnostic in one run. Skipped: `ralph_smoke_test.sh`, `ralph_smoke_rp.sh`, `plan_review_prompt_smoke.sh` — need external CLIs (claude / codex / rp-cli) not on hosted runners.

### Fixed
- **`atomic_write` no longer silently translates LF → CRLF on Windows.** Python's text-mode default `newline=None` on the `os.fdopen` inside `atomic_write` translates `\n` to `os.linesep` (`\r\n` on Windows). Every flowctl-written file (memory entries, glossary entries, prospect artifacts, `STRATEGY.md`, epic/task specs) ended up with CRLF on Windows checkouts, causing phantom "modified" diffs in cross-OS git checkouts and round-trip byte-comparison failures. Fix: pass `newline=""` so on-disk content matches the LF line endings flow-next writes everywhere.
- **`flowctl glossary add --definition-file -` normalizes CRLF/CR to LF on stdin.** Bash on Windows (Git Bash / MSYS) writes CRLF to pipes by default; Python's text-mode stdin universal-newlines didn't always fire when the parent opened the pipe in binary mode. Result: glossary `--definition-file -` stored multi-line definitions with CRLF instead of LF on Windows, breaking byte-equal round-trip comparisons. Defensive `.replace('\r\n', '\n').replace('\r', '\n')` runs immediately after `sys.stdin.read()`.
- **`_prospect_parse_frontmatter` coerces typed booleans in the no-PyYAML fallback path.** `_parse_inline_yaml` deliberately keeps booleans as strings (memory entries don't need typed scalars), but prospect frontmatter ships typed booleans (`floor_violation`, `generation_under_volume`) that `validate_prospect_frontmatter` and downstream consumers expect as `bool`. Without PyYAML installed, `parsed["floor_violation"] is True` evaluated `False` even when the serialized value was `floor_violation: true`. Fallback now post-coerces those two prospect-specific keys.
- **Multiple Windows-portability fixes across smoke tests.** `TEST_DIR` now honors `$TEST_DIR` env override, falls back through `$RUNNER_TEMP` → `$TMPDIR` → `/tmp`; backslashes are normalized to forward slashes after expansion (Python on Windows accepts forward-slash paths and is corrupted when bash interpolates `D:\a\_temp` into Python source — `\a` is bell). `SCRIPT_DIR` and `PLUGIN_ROOT` get `cygpath -m` conversion on Windows so `import flowctl` from inline Python resolves. `assert_grep` rewritten to use here-strings (no `printf | grep` SIGPIPE under `pipefail` when `grep -q` exits early on a found match in a large haystack). `json_get` strips `\r` from output (Python's `print()` text-mode stdout translates internal `\n` in JSON values to `\r\n` on Windows). Em-dashes in strategy fixtures replaced with `--` (Git Bash + cp1252 locale wrote em-dashes as cp1252 single-byte). Strategy T10 subprocess calls use `[sys.executable, FLOWCTL_PY, ...]` instead of `[FLOWCTL]` (the bash wrapper isn't a valid Win32 exe). Ralph-regression sweeps in prospect Case 11 + impl-review skip on `$RUNNER_OS=Windows` (ralph_smoke embeds POSIX patterns; the regression check tests prospect/impl-review env-var handling, unrelated to ralph's Windows portability).

### CI workflow
- `core.autocrlf=false` step before `actions/checkout@v4` so heredoc and fixture line endings are preserved as LF on Windows runners (default Windows-runner config converts LF → CRLF, mangling content compared byte-identically by smokes).
- `git config --global user.email/name` before tests (smoke_test.sh exercises `git commit` flows; runners ship git without identity → "fatal: empty ident name").

## [flow-next 0.40.0] - 2026-05-01

### Added
- **`/flow-next:strategy [optional: section to revisit]` — agent-native repo strategy anchor.** New skill that writes/maintains a repo-root `STRATEGY.md` (peer of `GLOSSARY.md` / `README.md`, never under `.flow/`) so strategic intent survives `rm -rf .flow/` (R1 / R22 — survives uninstall by design, mirrors the glossary R18 invariant). Section structure derived from Richard Rumelt's strategy kernel (*Good Strategy Bad Strategy*: diagnosis / guiding policy / coherent action), extended with persona + metrics for repo-doc utility: 5 required sections (`Target problem` / `Our approach` / `Who it's for` / `Key metrics` / `Tracks`) plus 2 optional (`Milestones` / `Not working on`). A `Marketing` section was considered and dropped — over-rotated for OSS-tools repos. Atomic per-section writes; `last_updated` bumps on every save. No draft state file. Re-invocation reads existing sections via `flowctl strategy status` and asks which section to revisit. Pushback discipline: 2 rounds maximum per section, then captures what user gave with a `<!-- worth revisiting -->` comment. Anti-pattern labels (vanity / fluff / feature-list) NOT leaked to user — only used internally to formulate sharper follow-up questions; quote user's own words back when challenging.
- **Repo-root `STRATEGY.md` artifact.** Frontmatter holds 3 keys only: `name`, `last_updated`, `generator: flow-next-strategy`. Foreign-file refusal — without the `generator: flow-next-strategy` sentinel the skill prompts the user (migrate / keep / rewrite?). Multi-format migration (CE-format / hand-written) explicitly deferred to v2; v1 ships the sentinel + refusal. Plain GFM markdown only; no MDX / admonitions / `:::tip` blocks.
- **`flowctl strategy status / read / list` plumbing.** `flowctl strategy status [--json]` returns `{exists, husk, sections_filled, total_sections, last_updated, file_path}`. Husk definition: file exists but `sections_filled == 0`. `flowctl strategy read [--section <name>] [--json]` resolves the repo root via `git rev-parse --show-toplevel` and checks for `STRATEGY.md` ONLY at that root — single-root resolution, no upward walk, no cascade. An `apps/web/STRATEGY.md` is always ignored; downstream skills consume the repo-root file regardless of cwd. Strategy is repo-wide by Rumelt's definition (NOT nearest-ancestor like glossary). `flowctl strategy list [--json]` parallels `flowctl glossary list` for symmetric downstream iteration. NO `flowctl strategy add/edit/remove` — strategy is too prose-heavy for atomic field-set CLI; the skill IS the editor.
- **Doc-aware autodetect — third condition.** Doc-aware mode now activates when ANY of three signals: `glossary.total_terms > 0` OR `knowledge/decisions/` has entries OR `strategy.sections_filled >= 1`. Override flags follow a cascade-with-explicit-override rule: `--docs` / `--no-docs` cascade to all three categories (glossary + decisions + strategy); explicit `--strategy` / `--no-strategy` always wins over the cascade for the strategy slot. 5-row matrix: `(default)` autodetect all three; `--docs` on for all three; `--no-docs` off for all three; `--no-docs --strategy` strategy on / glossary+decisions off; `--docs --no-strategy` glossary+decisions on / strategy off. Husk semantics on autodetect: branches on `flowctl strategy status --json | jq '.sections_filled >= 1'`, NOT on `[[ -f STRATEGY.md ]]` — same trap glossary fell into.
- **Strategy-doc fluff guard (R19).** New guard block in `plugins/flow-next/scripts/ci_test.sh` (separate from R17 DDD section 5c — comment specifies "strategy-doc fluff guard, NOT R17"). Tier 1 jargon only (Rumelt's "fluff" hallmarks): `synergy / pivot / disrupt / thought-leadership / best-in-class / world-class / 10x`. Scoped to `plugins/flow-next/skills/flow-next-strategy/SKILL.md` + `cmd_strategy_*` regions in `flowctl.py` + `plugins/flow-next/commands/flow-next/strategy.md`. The `references/interview.md` file is excluded — must describe anti-patterns to push back on them (same exemption as glossary references). Mirrored in `scripts/sync-codex.sh` validation block for the Codex mirror at `plugins/flow-next/codex/skills/flow-next-strategy/`. Two-tier guard (canonical + mirror) catches violations at either source path.
- **Smoke test `plugins/flow-next/scripts/strategy_smoke_test.sh` (T1-T12).** Cases: T1 first-run create-from-scratch; T2 targeted section re-run preserves rest byte-identically; T3 subdirectory invocation walks up; T4 husk detected via `sections_filled == 0`; T5 foreign-file refusal (no `generator` sentinel); T6 mid-flow abandonment + resume; T7 forbidden-vocab pushback; T8 strategy-glossary conflict surfaces in interview spec; T9 capture `--override-strategy` writes decision record; T10 prospect grounding emits verbatim approach + tracks; T11 plan-sync drift surfacing read-only; T12 Ralph-block exit-2.

### Changed
- **`/flow-next:prospect` Phase 0 grounding scan reads `STRATEGY.md`** when `sections_filled >= 1`. Injects approach + active tracks verbatim into candidate-generation prompt (mirrors CE-ideate's "emit approach and active tracks verbatim" pattern). Adds `out-of-scope-vs-strategy` to the rejection taxonomy. Surfaced as advisory at prospect phase — never auto-rejects.
- **`/flow-next:plan` research scan reads `STRATEGY.md`.** Plan emits a `## Strategy Alignment` spec section listing which active tracks the plan serves. Drift surfaced as a `## Strategy drift flagged for review` block (read-only — never auto-supersedes; mirrors decision-record convention).
- **`/flow-next:interview` doc-aware mode reads `STRATEGY.md`** before terminology questions. Surfaces conflicts in a `## Strategy Conflicts` spec section parallel to existing `## Glossary Conflicts`. Throttle: ≤1 strategy-conflict question per interview turn (parallel to the existing glossary-question throttle). Behavior (e) added — code-versus-strategy contradiction.
- **`/flow-next:capture` Phase 0 reads `STRATEGY.md` as input.** Source-tags strategy-derived acceptance criteria as `[strategy:<track-name>]` (joins existing `[user]` / `[paraphrase]` / `[inferred]` tags). Refuses to write spec contradicting an active track without `--override-strategy` flag. On flag fire: prompts user via `AskUserQuestion` to record a decision via `flowctl memory add --track knowledge --category decisions ...` (recommendation: yes; user can decline). Audit trail captured to stderr for future review.
- **`/flow-next:sync` (plan-sync agent) Step 5 reads `STRATEGY.md`.** Surfaces drift in a `## Strategy drift flagged for review` spec heading parallel to existing "Decision overrides flagged for review". NEVER auto-supersedes — read-only surface only. Track renames replace inline with a `<!-- Updated by plan-sync: track rename ... -->` breadcrumb mirroring the existing glossary rename pattern.
- **Codex sync regenerated.** New `flow-next-strategy` openai.yaml entry (`Flow Strategy`, brand color `#3B82F6`); `REQUIRED_OPENAI_YAML_SKILLS` array updated to include the new skill. Canonical skill files use Claude-native `AskUserQuestion`; `sync-codex.sh` rewrites to `request_user_input` for the Codex mirror per repo convention.

### Constraints
- **R1 — `STRATEGY.md` lives at the repo root.** Peer of `GLOSSARY.md` / `README.md`, never under `.flow/`. Survives a wipe of `.flow/` (R22 / R18 invariant). Frontmatter contains `name`, `last_updated`, `generator: flow-next-strategy` only.
- **R2 — Section structure locked.** 5 required + 2 optional, in CE 3.4's verbatim order. Optional sections deleted entirely if unused; never left as empty headers. Last-section deletion leaves a husk (H1 + frontmatter) — file never deleted (R23).
- **R7 — Single-root walk.** `flowctl strategy *` walks UP from cwd to first `STRATEGY.md` found, capped at repo root. NOT nearest-ancestor like glossary. Subdirectory invocation surfaces "Using repo-root STRATEGY.md at <path>" before any interview question (R16).
- **R15 — Foreign-file refusal.** STRATEGY.md without `generator: flow-next-strategy` frontmatter routes via `AskUserQuestion` (migrate / keep / rewrite?). On "keep" — exits without writing. v1 explicitly defers automatic migration.
- **R17 — Ralph-block.** `/flow-next:strategy` exits 2 with stderr `[STRATEGY: user-triggered only — Ralph cannot run /flow-next:strategy]` when `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` is set. Mirrors the `/flow-next:prospect` and `/flow-next:capture` precedent.
- **R19 — Tier 1 forbidden-vocab guard.** Separate from R17 DDD guard. `references/interview.md` excluded so it can describe anti-patterns. Two-tier (canonical + Codex mirror).

### Smoke coverage
- `strategy_smoke_test.sh` (T1-T12) covers happy path + corner cases listed above.
- `ci_test.sh` (R19 canonical) gates `SKILL.md` + `commands/flow-next/strategy.md` + `cmd_strategy_*` regions of `flowctl.py`.
- `scripts/sync-codex.sh` validation block (R19 mirror) gates `plugins/flow-next/codex/skills/flow-next-strategy/`.
- Glossary smoke (`glossary_smoke_test.sh`) and `smoke_test.sh` stay green; `audit_smoke_test.sh` and `prospect_smoke_test.sh` unchanged.

### Notes
- **Why repo-root STRATEGY.md, not `.flow/strategy.md`?** Survives a wipe of `.flow/`; peer of `README.md` / `CHANGELOG.md` / `GLOSSARY.md`; generic markdown tooling reads it. R18 invariant established by 0.39.0 glossary epic; the same rationale applies — strategic intent belongs to the project, not to flow-next.
- **Why single-root, NOT nearest-ancestor walk like glossary?** Strategy is repo-wide by Rumelt's definition (one diagnosis, one guiding policy, coherent action). Cascading per-subdirectory STRATEGY.md files re-introduce the "is for everyone, is for no one" problem the skill exists to prevent. Glossary cascades because vocabulary is local; strategy is global.
- **Why drop CE's `Marketing` section?** Over-rotated for OSS-tools repos — the marketplace manifest IS the distribution surface. Adding sections has cost; CE's principle 3 ("Short is a feature") supports the cut.
- **Why no `flowctl strategy add` plumbing?** Strategy is too prose-heavy for atomic field-set CLI. The skill running the interview IS the LLM that should write the file (per CLAUDE.md "agentic vs deterministic" architecture rule). Atomic CLI plumbing fits term-list / decision-record / memory shape but not prose-heavy strategy shape.
- **Why Tier 1 fluff vocab only (drop the `leverage` verb)?** Rumelt's source uses "leverage" as a noun in *Good Strategy Bad Strategy* — false-positive risk too high for `references/learn-more.md` prose. Tier 1 list is unambiguous.
- **Why foreign-file refusal in v1 (no migration)?** CE-format and hand-written `STRATEGY.md` files have ambiguous section mappings. Multi-format migration is a v2 problem; v1 ships the sentinel + refusal pattern, documents the limitation, lets early adopters delete-or-rename to bootstrap.

## [flow-next 0.39.0] - 2026-04-30

### Added
- **`GLOSSARY.md` artifact + `flowctl glossary` subcommands.** New first-class human-readable glossary that lives at the repo root (and optional subdirectories) so the project's canonical names + term-conflict resolutions survive `rm -rf .flow/` (R18). H2-per-term markdown format aligns with `open-gitops/documents` and `glossarify-md`. Resolution is nearest-ancestor-walk from cwd up to repo root (first match wins; same shape as `tsconfig.json` / EditorConfig discovery), capped at 32 levels with cycle detection. Subcommands: `flowctl glossary add <term> [--definition ... | --definition-file FILE | -] [--avoid a,b,c] [--relates-to x,y] [--json]` upserts case-insensitively; `glossary list [--json]` returns `{groups: [{path, entries, count}], file_count, total_terms}` grouped by file (nearest first); `glossary read <term> [--json]` walks ancestors and returns `{path, term, definition, avoid, relates_to}`; `glossary remove <term> [--json]` removes from the file that defines it. Last-term `remove` leaves a `# Glossary` H1 husk on disk — never deletes the file (R18). New helper functions `find_nearest_glossary` / `find_all_glossaries` / `parse_glossary_file` / `render_glossary_file` / `validate_glossary_entry` / `_glossary_term_matches` / `_glossary_strip_fenced_code` and constants `GLOSSARY_FILE` / `GLOSSARY_WALK_MAX_DEPTH` are reusable from downstream skills via the subcommands rather than direct imports.
- **`knowledge/decisions/` memory category + decision-specific frontmatter fields.** New category alongside `architecture-patterns`, `conventions`, `tooling-decisions`, `workflow`, `best-practices`. Three optional frontmatter fields permitted on any knowledge entry but specifically intended for `decisions/` entries: `decision_status` (enum: `proposed | accepted | superseded`), `superseded_by` (id reference), `alternatives_considered` (free-form prose). Schema constants exposed: `MEMORY_DECISION_FIELDS` (frozenset) and `MEMORY_DECISION_STATUSES` (enum tuple) live alongside the existing `MEMORY_KNOWLEDGE_FIELDS` / `MEMORY_STATUS` constants. Body convention: 1–3 sentence floor describing trade-offs, irreversibility, and surprise factor. Validator picks up additions automatically via the allowed-fields union.
- **`/flow-next:interview` doc-aware mode.** New autodetect: if `GLOSSARY.md` exists at any ancestor (with at least one term — husks are skipped) or `knowledge/decisions/` has at least one entry, the interview enters doc-aware mode. Override via `--docs` (force on) / `--no-docs` (force off). Four behaviors when active: (a) **glossary lookup before terminology questions** — fetch nearest-ancestor canonical wording via `flowctl glossary read`; surface conflicts as a `## Glossary Conflicts` section in the refined spec when user wording diverges from canonical, with resolution outcome (use-canonical / update-glossary / accept-divergence); (b) **inline glossary write on resolution** — `flowctl glossary add` invoked when the user picks update-glossary, recording the new canonical term; (c) **decision-record awareness** — when a load-bearing architectural choice is made during interview, prompt to write a `knowledge/decisions/` entry with the three-criteria gate (hard-to-reverse / surprising / load-bearing trade-off) and read-back loop before write; (d) **code/spec contradiction surfaced** — when an interview answer conflicts with an active decision record, the contradiction is surfaced in the refined spec rather than silently overwriting either side. The new `## Glossary Conflicts` template section sits alongside the existing `## Resolved via Codebase` section as the audit trail for canonical-vs-user wording resolutions; both are written by `NEW-IDEA` and `EXISTING-EPIC` interview templates.

### Changed
- **`docs-gap-scout` extends planning-phase scan.** Scout now reads `GLOSSARY.md` at repo root (and walked ancestors when planning a subdirectory feature) plus `.flow/memory/knowledge/decisions/` to surface canonical terminology and prior load-bearing choices in the planning context. Planning-phase output flags terminology mismatches between the proposed feature description and the glossary, and lists relevant decision records the plan should respect. No new acceptance criteria are auto-added — surfaced findings flow into `/flow-next:plan` for human / planner judgment.
- **`/flow-next:audit` walks glossary terms + decision entries.** Phase 0.5 (new) reads every `GLOSSARY.md` on the ancestor chain and audits each term against the current code (any references intact? renamed? gone?). Phase 0.1 (extended) auto-walks `knowledge/decisions/` alongside other categories. Replace outcomes for decision entries are **supersede-not-delete** — the audit writes a new entry with `decision_status: accepted` and sets the old entry's `decision_status: superseded` + `superseded_by: <new-id>`, preserving the historical trail. Other categories keep the existing Replace semantics.
- **`/flow-next:sync` detects glossary renames + flags decision overrides.** Phase 3b extends the drift sweep: **3b.1** glossary renames replace `_Avoid_` aliases with the canonical term across downstream task specs (additive — old wording is replaced inline with a `<!-- Updated by plan-sync: glossary rename ... -->` breadcrumb); **3b.2** decision overrides surface read-only under a "Decision overrides flagged for review" heading in the affected task specs. Sync **never auto-supersedes** decision records — superseding is a human-judgment / audit-driven action. Husk and superseded entries are skipped (no work to do; the file_count == 0 OR total_terms == 0 short-circuit prevents false positives). The read-only contract on decisions matches the broader principle that automated drift sweeps should not silently rewrite explicit historical choices.
- **Two-tier R17 + R4 grep guard added to CI.** Canonical scan in `plugins/flow-next/scripts/ci_test.sh` section 5c covers `skills/`, `agents/`, `commands/`, and `flowctl.py`; matches print `file:line` for fast remediation. Mirror scan in `scripts/sync-codex.sh` validation block covers `plugins/flow-next/codex/`; matches print a count plus a remediation hint pointing back at the canonical guard. R17 enforces the forbidden-vocabulary list (intentionally only listed inline inside the grep pattern itself; documentation refers to "the R17 forbidden list" without enumeration); R4 forbids early-design meta-file names (`GLOSSARY-MAP.md`, `CONTEXT-MAP.md`) leaking into canonical or mirrored prose.

### Notes
- **Foundations.** Builds on closed epics fn-30 (categorized memory schema), fn-34 (`/flow-next:audit`), fn-36 (capture + interview grill-me patterns), and the fn-15-96t plan-sync infrastructure. The `decisions/` category extends fn-30's schema additively; the doc-aware interview mode threads through fn-36's lead-with-recommendation + codebase-before-asking patterns; audit + sync extensions reuse fn-34's walk-and-decide framing.
- **R18 — survives uninstall by design.** `GLOSSARY.md` lives at the repo root, NOT inside `.flow/`. Deleting `.flow/` removes task tracking + memory + prospects, but the project's canonical wording stays put. This is a tenet, not an accident: terminology is the project's, not flow-next's.
- **Read-only sync contract.** Plan-sync's decision-override flagging is deliberately read-only. Auto-supersede would be a footgun: the agent might supersede an active decision based on a single conflicting task spec, losing the historical trail. Surface and let the human decide.
- **Smoke coverage:** `glossary_smoke_test.sh` (T2) covers parse / round-trip / nearest-ancestor walk / husk-on-last-remove / 80 assertions. `ci_test.sh` section 5c (R17 + R4 canonical) and `scripts/sync-codex.sh` validation block (R17 + R4 mirror) gate canonical and Codex-mirror prose hygiene.

## [flow-next 0.38.3] - 2026-04-28

### Changed
- **`plugins/flow-next/docs/flowctl.md` refreshed.** Authoritative CLI reference (linked from `.flow/usage.md`) had drifted since 0.33.0 — missing entire subcommand families introduced across 0.33–0.38. Added sections: `review-backend` (0.31.0+ spec grammar), `prospect` family (`list` / `read` / `promote` / `archive`, 0.36.0), `triage-skip` (0.35.0), `ralph` run control (`pause` / `resume` / `stop` / `status`), `copilot` review backend (parallel to `codex`), `codex deep-pass` + `codex validate` (fn-32.1/2), `review-deep-auto`, `review-walkthrough-defer`, `review-walkthrough-record` (fn-32.3 helpers). Memory section rewritten for the categorized YAML schema (0.33.0+): `--track bug|knowledge --category C` syntax, track-specific fields, `--status active|stale|all` filter, plus new subcommands `mark-stale`, `mark-fresh`, `migrate` (with deprecation pointer to `/flow-next:memory-migrate`), `list-legacy`, `discoverability-patch`. Updated available-commands list at the top of the file. Pure docs — no behavior change.

## [flow-next 0.38.2] - 2026-04-27

### Fixed
- **`flowctl.py` subprocess calls now pin `encoding="utf-8"` instead of defaulting to the system locale.** On Windows, `subprocess.run(input=prompt, text=True, ...)` decodes through `locale.getencoding()` — which is **cp1252** by default — so any prompt containing characters outside the cp1252 range (Unicode in git diffs, prototype/documentation files, non-ASCII commit messages) raised `UnicodeEncodeError: 'charmap' codec can't encode characters ...`. Setting `PYTHONIOENCODING=utf-8` did not help because `subprocess.run` ignores stdio encoding env vars. Fixed by adding `encoding="utf-8"` to all 25 `text=True` subprocess invocations in `flowctl.py`, covering `run_codex_exec()`, `run_copilot_exec()`, `run_rp_cli()`, every git plumbing call (`git diff`, `git rev-parse`, `git config`), and review-backend dispatch. No-op on macOS/Linux (already UTF-8 by default); fixes Windows. Smoke (129) green.

### Notes
- Thanks to @evansmith-everag (Evan Smith) for the detailed report ([#123](https://github.com/gmickel/flow-next/issues/123)) — root-caused, reproducer, fix, AND flagged the broader class of issue ("other subprocess calls in the file may have the same issue if they ever receive Unicode input") in one shot.

## [flow-next 0.38.1] - 2026-04-25

### Fixed
- **`scripts/install-codex.sh` no longer writes a duplicate `[features]` TOML table.** Pre-fix versions appended a standalone `[features]\ncodex_hooks = true` block to `~/.codex/config.toml` even when an existing `[features]` table was already present (Codex's own defaults ship one). TOML disallows duplicate tables — Codex 0.125.0 hard-errors on parse with `duplicate key`, breaking every Codex invocation post-install. Script now uses a portable awk merge: detects existing `[features]` block, inserts `codex_hooks = true  # flow-next` after the header (idempotent — skipped if already present); falls back to creating a fresh block when none exists. Migration: legacy `# --- flow-next features ---` markers are still cleaned before the merge, so re-running the new script over a previously-broken config heals it in one pass.

### Changed
- **Codex install: single documented path is now `git clone + ./scripts/install-codex.sh flow-next`.** The native `/plugins` install (both `cd flow-next && codex` → `/plugins` and `codex plugin marketplace add gmickel/flow-next` → `/plugins`) is no longer documented because Codex's plugin manifest schema (as of April 2026) supports `skills`, `mcpServers`, `apps` but not `agents`, `hooks`, or `commands`. Both `/plugins` paths register the slash commands but skip the bundled 21 `.toml` agents and `hooks.json` — breaking subagent isolation (worker model tier, `disallowed_tools` enforcement) and Ralph hooks. The script merges everything into `~/.codex/config.toml` directly. Idempotent — re-run after every `git pull` to update.
- **README.md (root, plugin), CLAUDE.md** rewritten to reflect single-path Codex install with rationale paragraph. Recheck note in `CLAUDE.md` ties the docs decision to a concrete trigger: revisit when Codex changelog mentions plugin manifest fields or app-server plugin management; once `agents` + `hooks` land in the schema, drop the script and document `codex plugin marketplace add gmickel/flow-next` instead.

### Notes
- No skill, agent, command, or flowctl behavior changes. Pure install-path + script-bug fix.

## [flow-next 0.38.0] - 2026-04-25

### Added
- **`/flow-next:capture [mode:autofix] [--rewrite <id>] [--from-compacted-ok] [--yes]` — agent-native conversation → epic spec.** New skill that synthesizes the current conversation context into a flow-next epic spec at `.flow/specs/<epic-id>.md` via existing `flowctl epic create + epic set-plan` plumbing. No new flowctl subcommands. Sits between free-form discussion (or `/flow-next:prospect` artifact promotion) and the formal `/flow-next:plan` task breakout, replacing the manual `flowctl epic create + set-plan` heredoc documented in `CLAUDE.md` for any spec emerging from conversation. Adapted from upstream `to-prd`; flow-next-shaped (output to `.flow/specs/`, not GitHub issue). Host agent does the synthesis directly — no Python synthesizer, no codex / copilot subprocess.
- **Hard guardrails:** source-tagged acceptance criteria (`[user]` = verbatim from conversation, `[paraphrase]` = user intent restated, `[inferred]` = agent fill-in, most-scrutinized at read-back); mandatory read-back loop (full draft + `[inferred]` count via `AskUserQuestion`, even in autofix mode where `--yes` is required to commit); duplicate-epic detection (Phase 0 scans `.flow/epics/` + runs `flowctl memory search` on extracted keywords); compaction detection (refuses without `--from-compacted-ok` when conversation has truncation markers); idempotency-via-`--rewrite` (refuses to overwrite an existing spec without explicit opt-in); must-ask cases (ambiguous title / untestable acceptance / scope-conflict are hard-error conditions, not soft preferences); "consider splitting?" suggestion at 8+ acceptance criteria (never auto-splits — user decides). CLAUDE.md richer template (`Goal & Context` / `Architecture` / `API Contracts` / `Edge Cases` / `Acceptance Criteria` / `Boundaries` / `Decision Context`); R-IDs allocated sequentially from R1.
- **Workflow position:** capture is **upstream of** `interview` and `plan`, **downstream of** free-form discussion or `/flow-next:prospect` promotion. The `/flow-next:prospect` direct-to-`plan` path (via `flowctl prospect promote`) still works unchanged. New pathways supported: `free-form → capture → plan`, `free-form → capture → interview → plan`, `prospect → capture → plan`, `prospect → capture → interview → plan`. All terminate at `work`.

### Changed
- **`/flow-next:interview` enhanced with three patterns from upstream `grill-me`.** (a) **Lead-with-recommendation** — every `AskUserQuestion` body now includes options summary, recommended option, one-sentence rationale, and a confidence tier (`[high]` / `[judgment-call]` / `[your-call]`). The third tier breaks the always-recommend habit when the agent has no signal. (b) **Pre-question taxonomy** — codebase-answerable questions ("what exists / how wired / what conventions") are investigated via Read/Grep/Glob and logged to a new `## Resolved via Codebase` spec section; user-judgment-required questions ("what should / what tradeoff / what priority") go to `AskUserQuestion`. Eliminates wasteful "should we use PostgreSQL?" questions when grep can answer "is there already a DB layer?". (c) **Dependency-ordered branch walk** — depth cap of 4, discover-as-you-go (not pre-compute), abandoned branches are surfaced ("Skipping persistence questions — you said no DB"). One-question-per-turn invariant reaffirmed.
- **Workflow ladder docs (root README + plugin README + CLAUDE.md + website FAQ)** updated to reflect all spec-diagram pathways: `prospect → plan` (direct via promote), `prospect → capture → interview/plan`, `free-form → capture → interview/plan`, plus the existing `interview-first` / `plan-first` / `work-direct` rows.
- **Plugin README mermaid lifecycle diagram** extended with a capture node showing all three entry points (prospect-promote, free-form, direct) and both downstream branches (interview, plan).
- **Plugin README "Prospect vs Spec vs Interview vs Plan" explainer** extended with a Capture entry positioning it as the automated alternative to manual `flowctl epic create + epic set-plan`, with read-back guarantees.

### Notes
- **Capture is Ralph-blocked by default.** Requires conversation context + user confirmation; both unavailable in autonomous loops. Hard-errors with exit 2 under `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` (matches `/flow-next:prospect` and `/flow-next:resolve-pr`).
- **Capture is the automated alternative** to the manual `flowctl epic create + epic set-plan` heredoc documented in `CLAUDE.md`. Both paths supported. Capture is recommended for any spec emerging from conversation; the manual path is still useful for scripted callers.
- **Why a new skill instead of extending `/flow-next:plan`?** Plan takes a feature description and produces tasks. Capture's input is *conversation history* (a fundamentally different shape) and output is a *spec, not tasks*. Forcing both into one skill would conflate distinct phases. Cleaner: capture is a separate phase, output feeds plan.
- **Why source-tag every acceptance criterion?** Practice-scout F1.1 found ~30% of intended requirements get missed by LLM elicitation, and bots fabricate confident answers. Distinguishing `[user]` / `[paraphrase]` / `[inferred]` makes the failure mode visible at read-back. User can reject `[inferred]` items they didn't actually agree to.
- **Why fold grill-me into existing interview skill, not separate skill?** Three small enhancements (~80 lines of skill text total) don't warrant a new top-level command. Folding keeps the user-facing surface stable: `/flow-next:interview` does what it always did, just better.
- Codex sync extended: new `flow-next-capture` openai.yaml entry (`Flow Capture`, brand color `#3B82F6`, default prompt `Capture this as a spec: `); `REQUIRED_OPENAI_YAML_SKILLS` array updated. Canonical skill files use Claude-native `AskUserQuestion`; `sync-codex.sh` rewrites to `request_user_input` for the Codex mirror per repo convention.
- Smoke suites stay green: `audit_smoke_test.sh` (13/41), `smoke_test.sh` (127), `prospect_smoke_test.sh` (94), `ralph_smoke_test.sh` (15). Capture has no flowctl plumbing (zero new subcommands), so no new smoke is required — the skill is exercised manually.

## [flow-next 0.37.1] - 2026-04-25

### Fixed
- **Codex `openai.yaml` UI metadata backfilled for 4 user-facing skills.** Since 0.34.0, every new slash-command skill (`/flow-next:resolve-pr`, `/flow-next:prospect`, `/flow-next:audit`, `/flow-next:memory-migrate`) silently shipped to Codex without UI metadata — raw slug names in the desktop UI, no display name / brand color / default prompt. `scripts/sync-codex.sh` now generates `agents/openai.yaml` for all 13 user-facing skills and uses an explicit `REQUIRED_OPENAI_YAML_SKILLS` array as validation; CI fails when a future skill is added without the matching call.
- **Cross-platform tool-name handling moved into the sync script.** Canonical skill files now use Claude-native tool names (`AskUserQuestion`); `sync-codex.sh` rewrites them to `request_user_input` in the Codex mirror and strips Claude-only `ToolSearch` schema-load fallbacks. Several skills (audit, prospect, memory-migrate, resolve-pr, impl-review walkthrough, prime, setup) had previously documented all platform variants inline (`AskUserQuestion / request_user_input / ask_user`), which polluted the agent's context with abstraction noise. Cleaner: each platform's mirror sees only its native tool name.
- **`flow-next-prime` and `flow-next-setup`** previously had bare `AskUserQuestion` mandates with no Codex / Droid path documented. Now use the canonical pattern (Claude-native tool name, sync-rewritten for Codex mirror) along with the rest of the skills.

### Changed
- **`scripts/sync-codex.sh`** validation block extended: required-skills list (instead of a `>= 9` count threshold) catches missing entries by name; new check that no `AskUserQuestion` or `ToolSearch` references remain in the Codex skill prose post-rewrite.
- **Gemini removed from supported-platform documentation.** flow-next supports Claude Code, Codex, and Factory Droid as first-class targets. Gemini was incidental documentation that crept in.

### Notes
- `CLAUDE.md` `## Cross-platform patterns` section rewritten: explicit architectural rule that canonical files use Claude-native tool names and the sync script handles platform-specific rewrites. New `### Adding a new user-facing skill` checklist documents every step required when shipping a new `/flow-next:<name>` skill (canonical content, slash command, `generate_openai_yaml` call, `REQUIRED_OPENAI_YAML_SKILLS` entry, sync-codex.sh re-run, commands list updates, CHANGELOG, smoke). Captures the lessons from the 0.34.0 → 0.37.0 silent-degradation era.
- Droid mirror infrastructure (similar to Codex) is a future hotfix; for now Droid users see canonical Claude-native names.

## [flow-next 0.37.0] - 2026-04-25

### Added
- **`/flow-next:audit [mode:autofix] [scope hint]` — agent-native memory staleness review.** New skill that walks `.flow/memory/`, reviews each entry against the current codebase using the host agent's own Read/Grep/Glob tools, and decides per entry whether to **Keep / Update / Consolidate / Replace / Delete**. Adapted to the categorized memory schema shipped in 0.33.0. The audit IS the agent: no Python audit engine, no codex/copilot subprocess dispatch, no deterministic scorer. The host agent reads the workflow markdown and executes it directly. Subagent dispatch documented for Claude Code (`Agent` + Explore), Codex (`spawn_agent` + explorer), and Droid; orchestrator falls back to main-thread investigation when subagent primitives are unavailable.
- **Two modes:** **Interactive** (default) — agent asks decisions per entry via the platform's blocking-question tool (`AskUserQuestion` / `request_user_input` / `ask_user`). **Autofix** (`mode:autofix` token) — applies unambiguous Keep/Update/Consolidate/Replace/Delete actions and marks ambiguous entries as stale via `flowctl memory mark-stale`; this is the Ralph-safe path. Scope hint follows the mode token (`/flow-next:audit mode:autofix runtime-errors`).
- **`flowctl memory mark-stale <id> --reason "..." [--audited-by "..."] [--json]`** — sets `status: stale`, stamps `last_audited` (UTC date), records `audit_notes` from `--reason`. Atomic via existing `write_memory_entry`; body untouched. Idempotent: re-mark replaces `audit_notes` and re-stamps `last_audited`. Used by `/flow-next:audit`, also callable directly. JSON shape: `{success, id, path, status, last_audited, audit_notes}`.
- **`flowctl memory mark-fresh <id> [--audited-by "..."] [--json]`** — clears stale flag (drops `status`, `audit_notes`), stamps `last_audited`. Idempotent on already-active entries.
- **`flowctl memory search --status active|stale|all`** — mirrors `memory list`'s `--status` flag (default `active`). Stale entries are excluded from default search results so audit-flagged advice stops polluting `memory-scout` output. Existing `memory list --status` behavior unchanged.
- **Schema extension:** `MEMORY_OPTIONAL_FIELDS` extended with `last_audited` and `audit_notes`. `MEMORY_FIELD_ORDER` updated; `_MEMORY_QUOTED_STRING_FIELDS` includes `last_audited` (date string survives PyYAML date coercion). Validator picks up additions automatically via the allowed-fields union.
- **`/flow-next:memory-migrate [mode:autofix] [scope hint]` — agent-native legacy migration.** Same architectural fix applied to legacy migration as `/flow-next:audit` applied to staleness review. The host agent reads each legacy entry from `.flow/memory/{pitfalls,conventions,decisions}.md`, classifies it into the right `(track, category)` pair using its own intelligence + repo context, and writes a categorized entry via `flowctl memory add`. Interactive (asks via the platform's blocking-question tool on ambiguous entries) or autofix (accepts mechanical default + logs as `needs-review` in the report). Inline skill (no `context: fork`) so question tools stay reachable across phases. Optional scope hint after the mode token narrows the run to a single legacy file (e.g. `pitfalls.md`). Phase 4 cleanup writes a self-ignoring `.flow/memory/_migrated/.gitignore` (`*`) and renames originals on user consent (autofix declines by default; never auto-deletes).
- **`flowctl memory list-legacy [--json]`** — emits parsed legacy entries with mechanical default `(track, category)` per entry. Used by `/flow-next:memory-migrate` skill; also useful for ad-hoc inspection. JSON shape: `{files: [{filename, entry_count, entries: [{title, body, tags, date, mechanical_track, mechanical_category}]}]}`. Returns `{files: []}` (rc=0) when no legacy files exist.

### Changed
- README + website lifecycle text now mentions `/flow-next:audit` and `/flow-next:memory-migrate` alongside the categorized memory schema. CLAUDE.md memory-system block adds audit + mark-stale + mark-fresh + search-status + memory-migrate bullets.
- `smoke_test.sh` memory section: `memory search 'stale example'` now passes `--status all` (default-active is the new contract); a complementary assertion verifies the default-active behavior. New `memory list-legacy` smoke (4 cases: empty dir, two-entry parse, mechanical defaults present, text mode) appended after the migrate block.
- **`flowctl memory migrate` is now deterministic-only.** The codex/copilot subprocess classification chain has been removed (~225 LoC across six functions: `_memory_classify_run_codex`, `_memory_classify_run_copilot`, `_memory_classify_select_backend`, `_memory_classify_build_prompt`, `_memory_classify_parse_response`, `_memory_classify_entry`). Mechanical filename → `(track, category)` heuristic (`_memory_classify_mechanical`) is the only path. For accurate per-entry classification, use the new `/flow-next:memory-migrate` skill — host agent classifies in-context. JSON receipt shape preserved (`method` always `"mechanical"`, `model` always `null`) for backcompat with pre-fn-35 callers. `--no-llm` flag accepted-but-noop (avoids breaking scripted callers).
- `flowctl memory migrate` now emits a one-time stderr deprecation hint (TTY only; suppressible via `FLOW_NO_DEPRECATION=1`) pointing at `/flow-next:memory-migrate` for accurate classification. Stderr-only — `--json` pipelines stay clean.

### Removed
- **`FLOW_MEMORY_CLASSIFIER_BACKEND`, `FLOW_MEMORY_CLASSIFIER_MODEL`, `FLOW_MEMORY_CLASSIFIER_EFFORT` env vars** are no longer consumed (subprocess classifier dispatch was removed). Setting them now triggers a one-time stderr warning so users with leftover env vars notice they're now dead. Suppressible via `FLOW_NO_DEPRECATION=1`.

### Notes
- **Legacy entries skipped.** Pre-fn-30 flat files (`pitfalls.md`, `conventions.md`, `decisions.md`) have no per-entry frontmatter to mutate, so `/flow-next:audit` skips them with a warning recommending `/flow-next:memory-migrate` first. The skipped count surfaces in the audit report.
- **No silent deletes.** The `Delete` outcome is reserved for unambiguous cases (code gone AND problem domain gone). Ambiguous cases default to mark-stale; the entry stays on disk and shows up under `--status stale` until a future audit confirms removal.
- **Why agent-native, not flowctl Python?** flow-next runs inside an agentic environment (Claude Code / Codex / Droid). The host agent already reads files, runs grep, judges relevance, and writes updates with its own tools. Spawning a second LLM via subprocess is wasteful (cost + latency) and adds machinery — subprocess timeouts, structured-verdict parsers, drift guards — that disappears in the agent-native architecture. **fn-34 (audit) and fn-35 (memory-migrate) ship together as 0.37.0 — the same architectural correction applied to two parallel features.** Future Ralph hooks / receipts / triage-skip stay subprocess-based per the agentic-vs-deterministic guidance in CLAUDE.md (those run from non-agent contexts).
- **Why thin flowctl plumbing instead of skill-only?** The skills need deterministic atomic frontmatter writes (`mark-stale` / `mark-fresh` for audit; `memory add` + `memory list-legacy` for migrate), schema-validated round-trip, and consistent search filtering. Those are pure persistence concerns where flowctl shines. Split rule: flowctl owns "set this field on this entry" / "parse these legacy segments"; skill owns "should this entry be flagged" / "which (track, category) does this belong in."
- Smoke suite: dedicated `plugins/flow-next/scripts/audit_smoke_test.sh` (13 cases, 41 assertions, ~5s runtime, zero LLM calls — covers Task 2 plumbing only since skills aren't unit-testable). `smoke_test.sh` (127, +1 for `list-legacy`), `prospect_smoke_test.sh` (94), `ralph_smoke_test.sh` (15) all stay green. Unit tests: 341 passing.

## [flow-next 0.36.0] - 2026-04-24

### Added
- **`/flow-next:prospect [focus hint]` — upstream-of-plan idea generation.** New user-triggered command that fills the "what should I build?" gap above `/flow-next:interview` and `/flow-next:plan`. Generates many candidate ideas grounded in the repo, critiques every one with explicit rejection reasons, and surfaces only the survivors bucketed by leverage. Output is a ranked artifact under `.flow/prospects/<slug>-<date>.md` that feeds directly into `interview` or `plan` via `flowctl prospect promote`. Lifecycle is now `prospect → interview → plan → work` for unformed targets; existing users with clear targets skip `prospect` and go straight to `interview` / `plan`.
- **Phase order:** Phase 0 resume check (artifacts <30 days old) → Phase 1 grounding (recent files, open epics, memory, audit, CHANGELOG) → Phase 2 persona-seeded divergent generate (`senior-maintainer` / `first-time-user` / `adversarial-reviewer`, ≥2 personas) → Phase 3 second-pass critique (separate prompt; rejection taxonomy: `duplicates-open-epic | out-of-scope | insufficient-signal | too-large | backward-incompat | other`) → Phase 4 bucketed rank (`High leverage 1-3` / `Worth considering 4-7` / `If you have the time 8+`; prose-only, no numeric scores) → Phase 5 atomic artifact write → Phase 6 frozen-format handoff prompt (`1`|`2`|`...`|`skip`|`interview`).
- **Volume semantics:** `top N` = exactly N survivors; `N ideas` = generate ≥N candidates; `raise the bar` = 60-70% rejection target; default = 15-25 candidates → 5-8 survivors.
- **Rejection floor (R12):** critique must reject ≥40% (or 60-70% under `raise the bar`); on floor violation the skill asks whether to regenerate, loosen, or ship anyway — no silent pass-through.
- **`flowctl prospect list / read / archive / promote` subcommands.** `list` defaults to <30-day artifacts (`--all` shows everything including archived and stale; columns: id, date, focus, survivor count, promoted count, status). `read` accepts full id, slug+date, slug-only (latest wins) and supports `--section focus|grounding|survivors|rejected`. `archive` moves to `.flow/prospects/_archive/`. `promote <id> --idea <N> [--epic-title "..."] [--force] [--json]` reads survivor #N's title/summary/leverage, allocates an epic via the same scan-based logic as `cmd_epic_create`, and writes the spec skeleton in one shot (mirrors `cmd_epic_create` allocation, but inlines the spec write so the prospect-context spec is on disk from the first byte). Success output: `Promoted idea #N ("<title>") to <epic-id>. Next: /flow-next:interview <epic-id>`.
- **Idempotency guard (R14, R20):** promote refuses if the artifact's `promoted_to` frontmatter already contains the target idea; `--force` overrides. Successful promote atomically appends to the artifact's `promoted_to` map (inline-flow YAML dict `{N: [epic-A, epic-B]}` with bare-numeric keys), so subsequent `list` shows `<promoted>/<survivors>` counts.
- **Ralph-out (R8):** `/flow-next:prospect` is exploratory and human-in-the-loop. Hard-errors with exit 2 when `REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` is set (matches fn-32 `--interactive` treatment). No env-var opt-in.
- **Atomic artifact writes (R4):** `.flow/prospects/<slug>-<date>.md` written via write-then-rename before the Phase 6 handoff prompt — Ctrl-C at handoff preserves the artifact. Same-day slug collision suffixes with `-2`, `-3` (R13). YAML frontmatter shape: `title`, `date` (quoted-string round-trip), `focus_hint`, `volume`, `survivor_count`, `rejected_count`, `rejection_rate`, `artifact_id`, `promoted_to` (omitted when empty), `status` (`active` | `corrupt` | `stale` | `archived`); optional `floor_violation` and `generation_under_volume` flags omitted when unset.
- **Malformed-artifact detection (R16):** resume check validates frontmatter parses and required sections exist; corrupt artifacts surface in `list --all` with `corrupt (<reason>)` in the status column and are never offered for extension. `flowctl prospect read` on a corrupt artifact exits **3** (distinct from Ralph-block exit 2). `flowctl prospect promote` on a corrupt artifact also exits **3** (stderr marker `[ARTIFACT CORRUPT: <reason>]`); `promote` on a duplicate idea without `--force` exits **2** with a message referencing the prior epic-id.
- **Graceful degradation (R17):** grounding records `scanned: none (reason)` when git/CHANGELOG/memory/audit is absent — no fatal errors on minimal repos.
- **flowctl helper surface (Phase 5/6 + write/list/read/archive/promote):**
  - Phase 3 (artifact writer): `write_prospect_artifact`, `render_prospect_body`, `validate_prospect_frontmatter`, `_prospect_slug`, `_prospect_next_id`, `PROSPECT_REQUIRED_FIELDS` / `PROSPECT_OPTIONAL_FIELDS` / `PROSPECT_FIELD_ORDER`.
  - Phase 4 (CLI + parsing): `_prospect_parse_frontmatter`, `_prospect_detect_corruption`, `_prospect_artifact_status`, `_prospect_resolve_id`, `_prospect_iter_artifacts`, `_prospect_extract_section`, `_prospect_extract_survivors`, `_prospect_extract_rejected`, `get_prospects_dir`, plus the `PROSPECT_CORRUPT_*` module constants that own the R16 reason-string contract.
  - Phase 5 (promote): `_render_epic_skeleton_from_prospect`, `_prospect_rewrite_in_place` (shared atomic in-place rewrite, used by both `cmd_prospect_archive` and `cmd_prospect_promote`), and the inline-flow dict branch added to `_format_prospect_yaml_value` for the `promoted_to` field. Survivor lookup is inlined via `next((s for s in _prospect_extract_survivors(body) if s["position"] == N), None)` — no standalone `_extract_survivor` helper. Promote inlines epic allocation + spec write rather than calling `cmd_epic_create` + `cmd_epic_set_plan`, so the prospect-context spec lands on disk from the first byte.

### Changed
- README/website lifecycle diagrams updated: prospect → interview → plan → work for the unformed-target path; existing flows (Spec → Interview/Plan → Work, Plan → Work, etc.) unchanged. Prospect is purely additive — no existing surface modified.

### Notes
- **User-triggered only.** Ralph autonomous loop is unaffected — no automatic invocation, no receipt writes, no shared state. Autonomous loops have no business deciding what a repo should tackle next.
- **Inline skill (no `context: fork`)** keeps `AskUserQuestion` available throughout. Subagents can't call blocking question tools (Claude Code issues #12890, #34592), and Phases 0 + 6 both require user choice.
- **Numbered-options fallback (R19)** frozen string format `1`|`2`|`...`|`skip`|`interview`; tested under cross-backend smoke for backends without a blocking question tool.
- **Persona seeding (R18):** post-RLHF LLMs exhibit pronounced mode collapse. Persona-seeded divergent generation converges on distinct semantic regions, measurably increasing idea diversity. ≥2 personas; spec names three to choose from.
- **Why bucketed ranking (3/4/∞) instead of flat?** Prose-only ranking is robust for top-3 but near-random past position 5 across reruns. Bucketing stabilizes the top-3 while preserving prose reasoning within each bucket.
- **Why two-pass generate-then-critique?** Single-pass prompts soft-reject — everything is kept, just ordered. Two passes with separate system prompts force explicit rejection with a taxonomy; the critique pass doesn't see its own generation prompt, avoiding rationalization.
- Smoke suite: dedicated `plugins/flow-next/scripts/prospect_smoke_test.sh` (11 cases, 94 assertions, ~58s runtime, zero LLM calls — pattern matches `impl-review_smoke_test.sh` from fn-32). Existing `smoke_test.sh` unchanged (regression-checked only). Unit tests: 308 passing.

## [flow-next 0.35.1] - 2026-04-24

### Changed
- **`/flow-next:resolve-pr` now parallel-dispatches on Codex.** Codex 0.102.0+ ships native multi-agent role support and `pr-comment-resolver.toml` installs into `~/.codex/agents/` via `scripts/install-codex.sh` — the skill and workflow now instruct parallel spawn on Codex using the same file-overlap wave pattern used on Claude Code. Copilot and Droid stay serial (no native parallel dispatch). Previous docs were stale — the machinery was already in place via fn-24 but the resolve-pr skill defaulted Codex to serial.

## [flow-next 0.35.0] - 2026-04-24

### Added
- **`--validate` flag on `/flow-next:impl-review`.** After a `NEEDS_WORK` verdict, dispatches a validator pass (same backend session, receipt-driven session resume) that independently re-checks each finding against the current code and drops false-positives with logged reasons. If all findings drop, the verdict upgrades `NEEDS_WORK → SHIP` (never downgrades from `SHIP` or `MAJOR_RETHINK`); `verdict_before_validate` is recorded on upgrade. Receipt carries `validator: {dispatched, dropped, kept, reasons}` plus `validator_timestamp`. Env opt-in: `FLOW_VALIDATE_REVIEW=1` (works in Ralph). Conservative bias — "only drop if clearly wrong; when uncertain, keep" (findings missing from validator output default to kept). New `flowctl codex validate` / `flowctl copilot validate` subcommands invoke the pass in the same chat session.
- **`--deep` flag on `/flow-next:impl-review`.** Layers specialized deep-dive passes on top of the primary Carmack-level review in the same backend session: adversarial (always), security + performance (auto-enabled based on changed-file globs via `flowctl review-deep-auto`). Findings tagged `pass: <name>`; merged with primary via fingerprint dedup (primary wins on collision); primary+deep cross-pass agreement promotes the primary finding's confidence one anchor step (0→25→50→75→100, ceiling 100). Cross-deep collisions dedup without promotion (avoids double-counting correlated passes). Explicit pass selection: `--deep=adversarial,security`. Env opt-in: `FLOW_REVIEW_DEEP=1` (works in Ralph). Receipt carries `deep_passes` array, `deep_findings_count` per-pass dict, `cross_pass_promotions` list of `{id, from, to, pass}`, and `deep_timestamp`. Deep may upgrade verdict `SHIP → NEEDS_WORK` when it surfaces new blocking `introduced` findings (records `verdict_before_deep`); deep never downgrades. New `flowctl codex deep-pass` / `flowctl copilot deep-pass` subcommands; new `flowctl review-deep-auto` helper reads changed files from stdin and emits the auto-enabled pass list.
- **`--interactive` flag on `/flow-next:impl-review`.** Per-finding walkthrough via the platform's blocking question tool (AskUserQuestion / request_user_input / ask_user). Four actions per finding: Apply / Defer / Skip / Acknowledge. "LFG the rest" escape hatch auto-classifies the remainder: `P0/P1` at confidence ≥ 75 → Apply; otherwise → Defer (mirrors the primary-review suppression gate). Deferred findings append to `.flow/review-deferred/<branch-slug>.md` (append-only; each review session gets a new `## <timestamp> — review session <receipt-id>` section; branch slug allows `a-zA-Z0-9-_.`). **Ralph-incompatible by design** — hard-errors when `REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` is set. Receipt carries `walkthrough: {applied, deferred, skipped, acknowledged, lfg_rest}` + `walkthrough_timestamp`. Walkthrough never flips the verdict. New helpers: `flowctl review-walkthrough-defer` (appends to the sink atomically) and `flowctl review-walkthrough-record` (stamps walkthrough counts + timestamp into the receipt).

### Changed
- Review workflow documents the phase ordering for flag combinations: **primary → deep → validate → interactive → verdict**.
- Receipt schema gains optional fields: `validator`, `validator_timestamp`, `verdict_before_validate` (validate); `deep_passes`, `deep_findings_count`, `cross_pass_promotions`, `verdict_before_deep`, `deep_timestamp` (deep); `walkthrough` (with `lfg_rest`), `walkthrough_timestamp` (interactive). All additive — existing Ralph scripts read by key and ignore unknowns.
- **Copilot backend model catalog + defaults refreshed.** Added `claude-opus-4.7`, `claude-opus-4.6`, `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.3-codex` to the registered model set (verified live against copilot CLI 1.0.36 via `copilot -p "/model"`). Default bumped `gpt-5.2` → `gpt-5.5`; `high` effort retained (confirmed `gpt-5.5` honors `--effort {low,medium,high,xhigh}`). Older rows stay listed — copilot itself still accepts them. Use `flowctl config set review.backend copilot:<model>:<effort>` to pin a different model.

### Notes
- **Default review is unchanged.** These flags are opt-in. The Carmack-level single-chat primary review remains the baseline and the primary. Flags add structure, validation, and deep-dives **on top** — they do not replace.
- `--deep` in same backend session means context carry-over (cheaper per pass); parallel multi-agent dispatch intentionally not adopted to preserve rp/codex/copilot parity.
- `--interactive` has no env var; per-invocation only to prevent accidental Ralph engagement.
- Depends on flow-next 0.32.1+ (confidence anchors, pre-existing classification) for flag semantics.
- Smoke suite: 217 unit tests pass; `impl-review_smoke_test.sh` covers the 7-case flag-combination matrix (74 assertions, ~58s wall-clock including 4-config parallel Ralph sweep).

## [flow-next 0.34.0] - 2026-04-24

### Added
- **`/flow-next:resolve-pr` — PR feedback resolver.** New user-triggered command for resolving GitHub PR review threads. Fetches unresolved threads, triages new vs pending-decision, dispatches parallel (Claude Code) or serial (Codex/Copilot/Droid) resolver agents, validates combined state, commits + pushes fixes, replies and resolves via GraphQL.
- **Handles all three feedback surfaces:** inline review threads, top-level PR comments, and review submission bodies. GraphQL resolves threads; PR-comment replies via `gh pr comment`.
- **Cross-invocation cluster analysis.** When multiple review rounds reveal recurring patterns in the same file/subtree, dispatches a cluster-aware resolver that investigates the broader area before making targeted fixes. Gated on both: prior-resolved threads exist AND spatial-overlap with new threads.
- **Targeted mode:** pass a comment URL to resolve a single thread only.
- **`--dry-run` flag:** fetch + plan, no edits/commits/replies.
- **`--no-cluster` flag:** skip cluster analysis, all items individual.
- **`pr-comment-resolver` agent:** single-thread resolver subagent with read-only investigation (git/gh) + Edit/Write for fixes; never commits/pushes (orchestrator owns that).
- **GraphQL scripts bundled:** `get-pr-comments`, `get-thread-for-comment`, `reply-to-pr-thread`, `resolve-pr-thread`. Zero runtime deps beyond `gh` + `jq`.

### Notes
- User-triggered only. Ralph autonomous loop is unaffected — no automatic invocation, no receipt writes, no shared state.
- Safety: comment text is untrusted input; resolvers never execute shell commands from comment bodies.
- Verify loop bounded at 2 fix-verify cycles; 3rd attempt escalates pattern to user.
- Smoke test: `plugins/flow-next/scripts/resolve-pr_smoke_test.sh`.

## [flow-next 0.33.0] - 2026-04-24

### Added
- **Categorized memory schema.** `.flow/memory/` is now a tree under `bug/` (build-errors, test-failures, runtime-errors, performance, security, integration, data, ui) and `knowledge/` (architecture-patterns, conventions, tooling-decisions, workflow, best-practices). Each entry is a single file with YAML frontmatter (`title`, `date`, `track`, `category`, `module`, `tags`, plus track-specific fields: `problem_type` / `root_cause` / `resolution_type` for bug; `applies_when` for knowledge). Entry IDs are `<track>/<category>/<slug>-<date>` matching filepath.
- **Overlap detection on `memory add`.** Scans existing entries in the target category. High overlap updates the existing entry in place; moderate overlap creates a new entry with `related_to: [existing-id]` in its frontmatter. Prevents silent duplication drift.
- **`flowctl memory migrate`.** Converts legacy `.flow/memory/pitfalls.md` / `conventions.md` / `decisions.md` into categorized entries via fast-model classification. `--dry-run` prints plan; `--yes` applies; `--no-llm` uses mechanical defaults. Classifier auto-selects `codex` (default `gpt-5.4-mini`) or `copilot` (default `claude-haiku-4.5`); override via `FLOW_MEMORY_CLASSIFIER_BACKEND=codex|copilot|none`, `FLOW_MEMORY_CLASSIFIER_MODEL`, `FLOW_MEMORY_CLASSIFIER_EFFORT`. Idempotent (re-run reports "No legacy files to migrate."). JSON mode refuses writes without `--yes` as a safety guard. Per-entry JSON shape: `{source, source_entry, target, target_path, method, model}`; top-level adds `moved_legacy`, `count`, `dry_run`, `legacy_moved_to`.
- **`flowctl memory discoverability-patch`.** Optional command that adds a `.flow/memory/` reference to the project's AGENTS.md / CLAUDE.md so agents without flow-next loaded can discover the store. Two strategies: `listing` (injects into an existing `.flow/` fenced code block) and `append` (adds a `## Memory / Learnings` section). Auto-target detection prefers AGENTS.md when both are substantive; handles `@AGENTS.md` / `@CLAUDE.md` shims and symlinks. JSON shape: `{target, action, reason, notes, strategy, diff, message}` where `action ∈ {exists, applied, dry-run, skipped}`. `--apply` and `--dry-run` are mutually exclusive (exit 2). JSON callers must pass `--apply` explicitly — the command refuses destructive auto-writes.
- **Ralph auto-capture rewrite.** Worker agent writes structured bug-track entries via `memory add --track bug --category <c>` on NEEDS_WORK → SHIP. Overlap detection handles duplicates automatically.
- **Category-aware memory-scout.** Scout returns track/category-tagged results, prioritizing module-matched entries.

### Changed
- `memory list` / `read` / `search` gain `--track` and `--category` filter flags; still read legacy flat files until migration runs.
- `memory list` also gains `--status active|stale|all` (default: `active`) — stale entries hidden unless asked.
- `memory search` also gains `--module <m>`, `--tags "a,b"`, `--limit <N>` filters plus weighted token-overlap scoring (title 5×, tags 3×, body 1.5×, misc 1×).
- `memory read` accepts three id forms — full (`bug/runtime-errors/slug-YYYY-MM-DD`), slug+date (unique lookup), and slug-only (latest date wins) — plus legacy forms (`legacy/pitfalls.md`, `legacy/pitfalls#N`).
- Legacy hits in `search` surface as synthetic entries with `track: "legacy"` and `entry_id` like `legacy/pitfalls#3` (1-based).
- JSON output shapes: `list` returns `{entries, legacy, count, status}`; `search` returns `{query, matches, count}`; `read` returns `{entry_id, path, frontmatter, body}` (categorized) or `{entry_id, path, legacy: true, body, index?}` (legacy).

### Deprecated
- `memory add --type pitfall|convention|decision` maps to new `--track/--category` flags with a deprecation warning. Will be removed in 0.36.0.

### Notes
- Backward compatible: legacy `.flow/memory/*.md` flat files continue to work until `memory migrate` runs; `list` / `read` / `search` read both.
- Opt-in remains the default — `flowctl init` does not create memory; run `flowctl config set memory.enabled true` and `flowctl memory init` to opt in.
- Smoke suite: 99 tests pass (adds memory migrate + discoverability-patch coverage).

## [flow-next 0.32.1] - 2026-04-24

### Added
- **Requirement-ID traceability (R-IDs).** Epic specs emit numbered acceptance criteria (`- **R1:**`, `- **R2:**`, ...). Task specs support optional `satisfies: [R1, R3]` frontmatter. Impl-review and epic-review produce per-R-ID coverage tables (met / partial / not-addressed / deferred). Any unaddressed R-ID flips verdict to `NEEDS_WORK`; receipt carries an `unaddressed` array. Renumber-forbidden after first review cycle — deletions leave gaps, new criteria take the next unused number. Plan skill writes R-IDs on creation; plan-sync preserves them during drift updates.
- **Confidence anchors (0 / 25 / 50 / 75 / 100) + suppression gate.** Reviewers score each finding on exactly five discrete anchors. Findings below 75 are suppressed except P0 @ 50+. Reviews report `suppressed_count` by anchor; receipt optionally carries a `suppressed_count` dict. Prose rubric tells the reviewer to treat scores as integers, not a continuous scale.
- **Introduced vs pre-existing classification.** Reviewers mark each finding `introduced: true` (caused by this branch's diff) or `pre_existing: true` (broken on the base branch). Verdict gate considers only `introduced`. Pre-existing findings surface in a separate non-blocking "Pre-existing issues" section. Receipt carries `introduced_count` and `pre_existing_count`.
- **Protected artifacts list in review prompts.** Hardcoded never-flag paths (`.flow/*`, `.flow/bin/*`, `.flow/memory/*`, `docs/plans/*`, `docs/solutions/*`, `scripts/ralph/*`). Review synthesis discards findings recommending their deletion or gitignore. Prevents cross-model reviewers unfamiliar with flow-next conventions from proposing destructive cleanups.
- **Trivial-diff skip (`flowctl triage-skip`).** Deterministic whitelist pre-check (lockfile-only / docs-only / release-chore / generated-file-only) returns `VERDICT=SHIP` with receipt `mode: triage_skip` and `source: deterministic`. Optional fast-model LLM judge (`gpt-5-mini` / `claude-haiku-4.5`) gated behind `FLOW_TRIAGE_LLM=1`; deterministic layer is conservative (ambiguous → REVIEW). On by default in Ralph mode; opt-out via `--no-triage` or `FLOW_RALPH_NO_TRIAGE=1`. Saves rp / codex / copilot calls on trivial commits.

### Changed
- Impl-review and epic-review workflows now emit structured per-finding metadata (severity, confidence, introduced/pre_existing) instead of free-form prose.
- Receipt schema gains optional fields: `unaddressed`, `suppressed_count`, `introduced_count`, `pre_existing_count`, plus new receipt `mode: triage_skip`. All additive — existing Ralph scripts read by key and ignore unknowns.

### Notes
- Zero breaking changes. Specs without R-IDs continue to work. Ralph's autonomous loop is unchanged in shape; review inputs and outputs are sharper.
- Carmack-level review remains the default and baseline. This release adds structure; it does not change the review style.
- Smoke suite: 71 tests pass (unchanged — rollup is prompt + docs only).

## [flow-next 0.32.0] - 2026-04-24

### Added
- **Codex default model: `gpt-5.5 + high`.** GPT-5.5 is now the codex backend default for cross-model reviews. Live-probed: codex CLI 0.124.0 accepts `--model gpt-5.5` with `-c 'model_reasoning_effort="high"'` (verdict=SHIP returned cleanly). Added to `BACKEND_REGISTRY["codex"]["models"]`; previous `gpt-5.4` still valid for anyone who wants to pin explicitly via `--review=codex:gpt-5.4:high` or `FLOW_CODEX_MODEL=gpt-5.4`. Registry default flipped from `gpt-5.4` → `gpt-5.5`. All docs (README catalog table, skill `(default ...)` prose, workflow spec-form examples) updated to match.

### Changed
- **Codex-only: `@browser` → `@agent-browser`** to avoid collision with OpenAI's bundled **Browser Use** plugin (Codex desktop v0.124+). The two tools have non-overlapping scope:
  - **Browser Use** (OpenAI bundled, Codex desktop only) — in-app browser widget for `localhost`, `127.0.0.1`, `::1`, `file://`, or the current in-app tab. No cookies, no auth, no extensions, no production sites, no Electron apps.
  - **`@agent-browser`** (this skill, Codex + CLI + all hosts) — full Chrome-via-CDP browser. Cookies, saved sessions, production sites, authenticated flows, Electron desktop apps (VS Code / Slack / Figma / etc), iOS Simulator, proxies, video recording, visual diff.

  Claude Code and Factory Droid continue to expose the skill as `@browser` (no OpenAI collision there, no muscle-memory break). The rename is Codex-mirror-only — performed by `scripts/sync-codex.sh` during regeneration.
- Codex version of the skill now carries a **prose-based delegation preface** explaining when to hand off to Browser Use vs use this skill. Written for the model, not the user — prose invocation ("Use the Browser Use plugin to open http://localhost:3000") rather than `@`-autocomplete (LLMs can't interactively pick from menus). Explicit CLI fallback: Browser Use doesn't exist in Codex CLI, so always use this skill there.

### Notes
- 112 unit tests pass (6 updated to expect `gpt-5.5` as the codex default).
- 67 smoke tests pass.
- No changes to Claude Code / Droid skill source — only the Codex mirror is renamed.

## [flow-next 0.31.0] - 2026-04-22

### Added
- **Unified review backend spec parser** — `backend[:model[:effort]]` grammar accepted at every surface (env, config, per-task, per-epic, CLI flag). `parse_backend_spec()` + `BackendSpec` dataclass + `BACKEND_REGISTRY` (rp/codex/copilot/none) validate specs on store; invalid values rejected with helpful errors listing valid models/efforts. Legacy bare-backend values (`codex`, `copilot`, `rp`) still work unchanged. Unparseable strings on disk degrade to bare backend with a stderr warning — never crash.
- Backend registry (static dict in `flowctl.py`):
  - `codex`: models `gpt-5.4`, `gpt-5.2`, `gpt-5`, `gpt-5-mini`, `gpt-5-codex`; efforts `none|minimal|low|medium|high|xhigh`; defaults `gpt-5.4` / `high`.
  - `copilot`: models `claude-sonnet-4.5`, `claude-haiku-4.5`, `claude-opus-4.5`, `claude-sonnet-4`, `gpt-5.2`, `gpt-5.2-codex`, `gpt-5-mini`, `gpt-4.1`; efforts `low|medium|high|xhigh`; defaults `gpt-5.2` / `high`. `claude-*` models drop `--effort` at runtime.
  - `rp` and `none`: bare-only (no model/effort).
- **Resolution precedence** (first match wins): `--spec` CLI flag > per-task `review` > per-epic `default_review` > `FLOW_REVIEW_BACKEND` env > `.flow/config.json` `review.backend` > backend-specific env (`FLOW_CODEX_MODEL` / `FLOW_CODEX_EFFORT` / `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT`) > registry default. Env fills **missing** fields only — explicit spec values always win.
- `--spec backend:model:effort` flag on all six review commands: `flowctl {codex,copilot} {impl,plan,completion}-review`. Parses + resolves + threads `model` + `effort` into `run_codex_exec` / `run_copilot_exec`.
- `flowctl review-backend --json` now returns `{backend, spec, model, effort, source}` — full resolved spec + field-level source tag (`env` / `config` / `none`). Text mode still prints bare backend for skill grep back-compat.
- `flowctl task show-backend --json` / `flowctl epic show-backend --json` expose raw stored spec + resolved spec + per-field source (`task` / `epic` / `env` / `default`).
- `parse_backend_spec_lenient()` + `resolve_review_spec()` helpers centralise spec parsing for skills and Ralph.
- Ralph integration: `scripts/ralph/config.env` accepts spec form on `PLAN_REVIEW` / `WORK_REVIEW` / `COMPLETION_REVIEW` (e.g. `WORK_REVIEW=codex:gpt-5.4:xhigh`). `ralph.sh` exports the full spec via `FLOW_REVIEW_BACKEND` and derives `PLAN_REVIEW_BACKEND` / `WORK_REVIEW_BACKEND` / `COMPLETION_REVIEW_BACKEND` (bare backend, via `${VAR%%:*}`) so existing prompt-level branching keeps working unchanged.
- Review skills (`flow-next-impl-review`, `flow-next-plan-review`, `flow-next-epic-review`) document the `--spec` flag + spec grammar + precedence in both SKILL.md and workflow.md. `flow-next-setup` workflow now offers spec-form defaults.
- Receipts include a new `spec` field alongside `model` + `effort`: `{"mode": "codex", "model": "gpt-5.4", "effort": "high", "spec": "codex:gpt-5.4:high"}`. `spec` is the canonical round-trippable form (via `str(resolved_spec)`); older readers that only look at `model` + `effort` stay correct.
- Smoke suite: 60 → 67 tests (backend spec validation, set-backend rejection paths, show-backend field sources, legacy fallback). Unit tests: 56 → 112 (parser edges, registry integrity, precedence resolution, Ralph bare-backend extraction, `cmd_review_backend` JSON shape).

### Changed
- Aspirational `--review=codex:gpt-5.4-high` help text (never implemented) replaced with real `backend:model:effort` grammar. No migration needed; old stored bare-backend values continue to parse.
- `run_codex_exec` and `run_copilot_exec` now take a resolved `BackendSpec` argument instead of ad-hoc `model=` / `effort=` kwargs. Env-var fallback moved up into `BackendSpec.resolve()`.

## [flow-next 0.30.0] - 2026-04-22

### Added
- **GitHub Copilot CLI review backend** — third cross-platform option alongside RepoPrompt and Codex. New `flowctl copilot` command group (`check`, `impl-review`, `plan-review`, `completion-review`) with same receipt schema as Codex. Session continuity via client-generated UUIDs (`copilot --resume=<uuid>` creates-or-resumes; flowctl stores the UUID, reuses it on re-review). Text mode output with `<verdict>` tag extraction. Temp-file prompt delivery handles >100KB prompts and dodges Windows `ARG_MAX`.
- `flowctl copilot check` does a live auth probe (trivial `-p "ok"` with `gpt-5-mini` + `effort=low`) instead of only checking binary presence — auth failures surface here, not at first review. GPT model chosen because Claude-family models reject `--effort`.
- Review skills (`flow-next-impl-review`, `flow-next-plan-review`, `flow-next-epic-review`) branch on `copilot` backend.
- `/flow-next:setup` auto-detects `copilot` on `PATH` and offers it as a review backend option.
- Ralph integration: `ralph-guard.py` bumped to `0.14.0` — blocks direct `copilot` calls outside `flowctl copilot …` wrappers and blocks `--continue` (conflicts with parallel sessions / multiple projects). New `copilot_review_succeeded` state key. `ralph-init` templates (`config.env`, `ralph.sh`, `prompt_{plan,work,completion}.md`) carry the `copilot` review branch.
- Runtime knobs (env-only, no CLI flags): `FLOW_COPILOT_MODEL` (default `gpt-5.2`; matches Codex's GPT-5.x + high philosophy), `FLOW_COPILOT_EFFORT` (default `high`; `low|medium|high|xhigh`), `FLOW_COPILOT_EMBED_MAX_BYTES` (default `512000`). Resolved via `env > arg > default` cascade in `_resolve_copilot_model_effort()` and stamped into every receipt (`model` + `effort` keys) for reproducibility. `ralph.sh` conditionally exports each var only when set, so empty values in `config.env` fall back to flowctl defaults instead of clobbering them. Claude-family models reject `--effort`; flowctl omits the flag automatically for them.
- Model catalog: `claude-sonnet-4.5`, `claude-haiku-4.5`, `claude-opus-4.5`, `claude-sonnet-4`, `gpt-5.2`, `gpt-5.2-codex`, `gpt-5-mini`, `gpt-4.1`.
- Smoke suite grew 52 → 59 tests (4 copilot command-help checks + 3 live copilot e2e: `plan-review`, `plan-review` re-resume asserting stable `session_id`, `impl-review`). Live e2e uses `gpt-5-mini` + `FLOW_COPILOT_EFFORT=low` to minimise premium-request cost.
- README `Cross-Model Reviews` section documents Copilot on equal footing with RP and Codex (setup, usage, verify, env vars, which-to-choose table). `CLAUDE.md` project guide lists Copilot as a valid review backend. All `--review=` flag tables now enumerate `rp|codex|copilot|export|none`.

### Changed
- RepoPrompt remains the recommended (best-context) backend. Codex and Copilot are both listed as cross-platform alternatives for Linux / Windows / CI / headless.
- Inline `backend:model:effort` spec parsing is intentionally out of scope here — that unification ships in a follow-up epic so RP, Codex and Copilot can all be retrofitted in one pass.

## [flow-next 0.29.4] - 2026-04-12

### Fixed
- **rp-cli 2.1.6: builder output missing tab/context ID** — `cmd_rp_builder` and `cmd_rp_setup_review` now always pass `--raw-json` to builder (was conditional on `--response-type`). RP 2.1.6 removed the `Tab:`/`Context:` text line from plain-text output; IDs are only in JSON mode. JSON parse tried first, regex fallback for older RP versions. Closes #109. Thanks @berhanbero
- **Python 3.12+ `datetime.utcnow()` deprecation** — replaced with `datetime.now(timezone.utc)` in `now_iso()` and `cmd_memory_add`. Eliminates `DeprecationWarning` on Python 3.12+.

### Changed
- README recommends RepoPrompt v2.1.6+ and documents update path (`brew upgrade --cask repoprompt`)

## [flow-next 0.29.3] - 2026-04-12

### Fixed
- **RepoPrompt 2.x `oracle_send` support** — `flowctl rp chat-send` now prefers RP 2.x `oracle_send` over legacy `chat_send`, falling back only on missing-tool errors. Strips `chat_name` and `selected_paths` fields that RP 2.1.x rejects. Real errors propagate immediately instead of being masked by fallback. Thanks @clairernovotny — [#107](https://github.com/gmickel/flow-next/pull/107)
- **Ralph receipt gate hardened** — review receipts now require `type`, `id`, and `verdict` (SHIP/NEEDS_WORK/MAJOR_RETHINK). Catches variable-based receipt writes (`printf ... > "$RECEIPT_PATH"`) that previously bypassed the guard. Defense in depth: pre-tool-use checks command text, Stop handler validates actual file on disk.
- **Ralph prompt templates** — all three templates (`prompt_plan.md`, `prompt_work.md`, `prompt_completion.md`) now include `"verdict":"SHIP"` in receipt JSON. Review workflows capture response and extract verdict from `<verdict>` tags.

### Added
- `run_rp_cli_unchecked` — graceful rp-cli runner for oracle_send fallback detection
- `ralph-receipt-guard.sh` — shell-level receipt validation with verdict + type/id cross-checking
- CI test coverage: oracle_send modern/legacy/error paths, receipt bypass patterns, receipt validation

## [flow-next 0.29.2] - 2026-04-09

### Fixed
- **RepoPrompt 2.1.4 `Context:` builder output** — `flowctl rp builder` / `flowctl rp setup-review` now accept the new `Context: <uuid>` text format and `context_id`/`context`/`contextId` JSON keys alongside the legacy `Tab:` / `tab_id` shapes. Downstream `--tab` flag unchanged; legacy paths still tried first for backward compat. CI regression coverage added. Thanks @clairernovotny — [#106](https://github.com/gmickel/flow-next/pull/106)

## [flow-next 0.29.1] - 2026-04-08

### Fixed
- **RepoPrompt workspace leak in setup-review** — Ralph sessions with `WORK_REVIEW=rp` could accumulate dozens of duplicate RepoPrompt workspaces/windows for the same repo when window matching fell through to `workspace create --new-window` on every retry. Now falls back through three layers: `bind_context` (RP's native repo-path matching, newest API) → workspace inventory lookup by repo path → last-resort creation. Hidden workspaces are reopened via `manage_workspaces switch` instead of duplicated. Thanks @clairernovotny — [#104](https://github.com/gmickel/flow-next/pull/104)
- **`parse_builder_tab` tolerates JSON-shaped responses** — now tries regex patterns (`Tab:`, `T=`, `"tab_id"`, `"tab"`) then falls back to recursive JSON walking before failing. No more fatal errors on newer RP response shapes.
- **`parse_manage_workspaces` unwraps nested result objects** — handles `{"result": {"workspaces": [...]}}` JSON-RPC style payloads with bounded recursive unwrapping. String workspace names are preserved as `{"name": item}` dicts instead of dropped.
- **Windows: ralph-guard state file uses `tempfile.gettempdir()`** — hardcoded `/tmp` path resolved to `\tmp\` on Windows and failed. Pre-existing bug exposed by new regression tests.

### Added
- `try_run_rp_cli` — graceful-failure variant of `run_rp_cli` for optional capability probing (e.g. newer RepoPrompt features)
- `bind_context_window` helper — prefers RepoPrompt's native repo-path binding when available, falls back to legacy window/workspace matching
- Regression test coverage for RepoPrompt setup-review: bind_context fast path, visible workspace reuse, hidden workspace reopen, nested result unwrap, string workspace names

## [flow-next 0.29.0] - 2026-04-05

### Added
- **DESIGN.md awareness** — conditional design system integration when Google Stitch DESIGN.md exists
- repo-scout detects and validates DESIGN.md (section headings + hex color heuristic)
- Plan skill writes `## Design context` in frontend task specs with relevant tokens
- Worker reads DESIGN.md sections in Phase 1.5 when design context present
- Prime Pillar 4 DC7 criterion: DESIGN.md exists (informational)
- docs-gap-scout scans for DESIGN.md and .stitch/DESIGN.md
- Quality-auditor checks design token conformance in frontend diffs (advisory)
- Flow-gap-analyst checks design system alignment for UI features (advisory)

### Changed
- Frontend task detection heuristic documented (file extensions, directories, keywords)

## [flow-next 0.28.0] - 2026-04-05

### Added
- **Investigation targets** in task specs — plan writes file paths (Required/Optional) workers must read before coding, reducing hallucination and ensuring pattern conformance
- **Requirement coverage** traceability table in epic specs — maps each requirement to covering task(s) with gap justification, maintained by plan-sync on drift
- **Early proof point** in epic specs — identifies which task validates the core approach and what to reconsider if it fails
- **Bidirectional epic-review** — adds code→spec reverse coverage check detecting scope creep (UNDOCUMENTED_ADDITION, LEGITIMATE_SUPPORT, UNRELATED_CHANGE classifications)
- **Pre-implementation search** — worker greps for similar functionality before coding, applies reuse > extend > new decision tree
- **Typed escalation** — structured block messages with 6 categories (SPEC_UNCLEAR, DEPENDENCY_BLOCKED, DESIGN_CONFLICT, SCOPE_EXCEEDED, TOOLING_FAILURE, EXTERNAL_BLOCKED)
- **Confidence qualifiers** — repo-scout and context-scout tag findings as `[VERIFIED]` (tool-confirmed) or `[INFERRED]` (derived from naming/structure)
- **Test budget awareness** — quality-auditor flags disproportionate test generation (>2:1 ratio) and existing test modifications as advisory

### Changed
- **Plan-sync scope** widened to also update `## Requirement coverage` table in epic specs when drift is detected
- **Epic-review prompt** upgraded from two-phase to three-phase (extract requirements → verify implementation → reverse coverage)
- Codex plugin update instructions documented (uninstall → reinstall from repo)

## [flow-next 0.27.0] - 2026-04-05

### Added
- **Native Codex plugin support** (`.codex-plugin/plugin.json`) — Flow-Next is now a first-class Codex plugin discoverable via `/plugins`
- **Codex marketplace discovery** (`.agents/plugins/marketplace.json`) — repo works as a Codex marketplace source
- **Pre-built Codex agents** as `.toml` files with subagent optimizations (`sandbox_mode`, `nickname_candidates`)
- **Pre-built Codex skills** with platform-specific invocation patterns (`$flow-next-plan` instead of `/flow-next:plan`)
- **Codex-compatible hooks** for Ralph mode — Bash tool guard + Stop hook (experimental)
- **`openai.yaml` UI metadata** for Codex app display (brand color, descriptions, default prompts)
- **`scripts/sync-codex.sh`** — build script generates `codex/` directory from canonical Claude Code sources
- **SessionStart hook** for Codex (flow context loading)

### Changed
- **`install-codex.sh` simplified** — 785 → 257 lines; uses pre-built `codex/` files instead of runtime conversion
- **Model mapping updated** — `gpt-5.4-mini` replaces `gpt-5.3-codex-spark` for scanning scouts
- **flowctl path** — installed to `~/.codex/scripts/` (was `~/.codex/bin/`) for consistency
- **`bump.sh`** updates both `.claude-plugin/` and `.codex-plugin/` manifests
- **Setup skill** detects Codex platform and configures project-scoped agents/hooks
- Plugin README updated with native Codex install instructions and skill invocation guide
- **Repo renamed** `gmickel-claude-marketplace` → `flow-next` (GitHub auto-redirects old URLs)

## [flow-next 0.26.0] - 2026-03-06

### Changed

- **Codex model defaults: gpt-5.4 across the board** — review/oracle model upgraded from `gpt-5.2` to `gpt-5.4` (high reasoning). Agent intelligent tier upgraded from `gpt-5.3-codex` to `gpt-5.4` (high reasoning). Fast scouts remain on `gpt-5.3-codex-spark`.

### Fixed

- **Codex docs: removed incorrect Ralph support claim** — "What works" section incorrectly listed Ralph autonomous mode. Ralph requires plugin hooks (guard hooks, receipt gating) which Codex doesn't support. Expanded caveats to clarify.

## [flow-next 0.25.0] - 2026-03-01

### Fixed

- **Codex reviews: embed files on all platforms** — removed `os.name == "nt"` gate that restricted file embedding to Windows only. On Unix/macOS, Codex wasted its entire turn budget reading files via `sed`/`rg` before producing a verdict (observed 114 shell commands, 3.68M tokens, no verdict on complex epics). Now always embeds changed files with budget-aware fallback: disk reads allowed when embed budget is exceeded. Default `FLOW_CODEX_EMBED_MAX_BYTES` raised from 100KB to 500KB. (Thanks @acebytes — [#93](https://github.com/gmickel/flow-next/pull/93))

## [flow-next 0.24.0] - 2026-02-21

### Added

- **Spec-driven workflow** — "create a spec for X" now has guidance in the CLAUDE.md/AGENTS.md snippet installed by `/flow-next:setup`. Creates an epic with structured spec template (Goal & Context, Architecture & Data Models, API Contracts, Edge Cases & Constraints, Acceptance Criteria, Boundaries, Decision Context). Then choose `/flow-next:plan` (task breakdown) or `/flow-next:interview` (refine spec).
- **README: spec-driven entry point** — new "Spec-driven" workflow section in "When to Use What", updated summary table, clarified Spec vs Interview vs Plan boundaries.

> Re-run `/flow-next:setup` to update your project's CLAUDE.md/AGENTS.md with the new spec guidance.

## [flow-next 0.23.0] - 2026-02-20

### Added

- **Browser skill: comprehensive update from upstream agent-browser** — synced with latest `vercel-labs/agent-browser` skill. New features: version check on use, command chaining guidance, `snapshot -i -C` (cursor-interactive), `click --new-tab`, diff commands (snapshot/screenshot/url comparison), annotated screenshots (`--annotate` vision mode), safe JS eval (`--stdin`/`-b`), config file support, session persistence with encryption (`--session-name`), `--auto-connect` for existing Chrome, `--allow-file-access` for local files, iOS Simulator (`-p ios`), timeouts section, `get box`/`get styles`, `drag`/`upload`, video recording, Chrome DevTools profiling.
- **Browser skill: new reference files** — `commands.md` (full command reference), `snapshot-refs.md` (ref lifecycle/notation), `session-management.md` (auto-persistence/encryption/concurrency), `proxy.md` (proxy config/geo-testing/rotating proxies).
- **Browser skill: updated references** — `auth.md` (OAuth/SSO, 2FA, token refresh, security best practices), `debugging.md` (video recording, profiling), `advanced.md` (auto-connect, extensions, env vars, eval stdin/base64).

## [flow-next 0.22.3] - 2026-02-19

### Fixed

- **RP `--create` fails on empty default window** — when only an empty RP window exists (no folder loaded), `setup-review --create` reused it instead of creating a workspace with the repo folder, causing "No workspace open" from the builder. Now falls through to workspace creation.

## [flow-next 0.22.2] - 2026-02-19

### Fixed

- **Codex: ensure `multi_agent` at TOML root** — `generate_config_entries` appended `multi_agent = true` at end of config.toml, which landed inside a preceding table instead of at root scope. Now prepended before any `[table]` header.
- **Codex: deduplicate `[agents]` table** — installer always emitted a fresh `[agents]` declaration; if user already had one, the resulting file was invalid TOML. Now checks before declaring.
- **Codex: patch prime workflow for multi-agent** — `Task flow-next:<scout>` references in prime's workflow.md were not converted to Codex role names, causing "Scout availability partial" (only 4/9 scouts resolved). All 9 scouts now patched.
- **Codex: escape backslashes in TOML agent configs** — agent markdown containing regex patterns (`\.env`, `\[test\]`) broke TOML `"""` strings. Backslashes now auto-escaped.

### Added

- **RP auto-create workspace** — all `setup-review` calls now pass `--create`, so RepoPrompt auto-opens a workspace + window if none matches the repo root (RP 1.5.68+).
- **Codex multi-agent roles** — complete rewrite of `install-codex.sh` for Codex 0.102.0+: `.md` agents → `.toml` role configs, 3-tier model mapping (intelligent/smart scouts/fast scouts), `agents-md-scout` rename, prime/plan/work skill patching.
- **Codex install docs** — clone instructions, 3-tier model mapping table, override examples.

## [flow-next 0.22.0] - 2026-02-17

### Fixed

- **Fix receipt-reset false positive on codex reviews** — PostToolUse receipt-write detection matched codex commands containing `--receipt` path + `>` chars in stdout (from `<verdict>` tags), causing `chat_send_succeeded` and `codex_review_succeeded` to reset immediately after being set. Receipt-write detection now uses proper shell redirect pattern matching (same regexes as PreToolUse) instead of naive substring checks. (thanks @clairernovotny for reporting)

### Added

- **Block self-modification of workflow files** — Ralph can no longer Edit/Write to `ralph-guard.py`, `flowctl.py`, `flowctl`, or `hooks.json` during a run. Hooks config now registers `Edit|Write` matcher in addition to `Bash|Execute`. Prevents agents from bypassing guards by editing their own tooling. (ralph-guard v0.13.0)

## [flow-next 0.21.0] - 2026-02-17

### Changed

- **Upgrade scout agents from Haiku to Sonnet 4.6** — All 11 lightweight scout agents (build, claude-md, docs-gap, env, epic, memory, observability, security, testing, tooling, workflow) now use `claude-sonnet-4-6` (pinned) instead of `haiku`. Sonnet 4.6 brings improved reasoning, instruction following, and a training data cutoff of Jan 2026. Requires Claude Code 2.1.45+.

## [flow-next 0.20.21] - 2026-02-10

### Changed

- **github-scout now opt-in** — Disabled by default (`scouts.github: false`). Enable via `/flow-next:setup` or `flowctl config set scouts.github true`. Reduces planning cost and removes `gh` CLI requirement for users who don't need cross-repo search.

## [flow-next 0.20.20] - 2026-02-07

### Fixed

- **Review skills: prevent double context build** — Reordered RP workflow in impl-review, plan-review, and epic-review to run context-gathering before setup-review. Builder now runs once with a real summary instead of a placeholder. Added guardrails against re-running setup-review.

## [flow-next 0.20.19] - 2026-02-03

### Fixed

- **Project-local ralph-guard for cross-platform hooks** — Hooks now reference `scripts/ralph/hooks/ralph-guard.py` (project-local) instead of plugin root variables. ralph-init copies the guard script during setup. Existence check ensures silent exit if ralph not initialized. Works on both Claude Code and Factory Droid without any plugin root variables.

## [flow-next 0.20.18] - 2026-02-03

### Fixed

- **Hooks: shell check for cross-platform** — Hook commands now use `[ -n "${VAR}" ] && ...` to skip execution when the platform's variable isn't set. Eliminates noisy "file not found" errors from the other platform's unexpanded variable.

> **Note:** v0.20.10–0.20.18 added Factory Droid compatibility. If you experience issues on Claude Code, downgrade to v0.20.9: `claude plugins install flow-next@0.20.9`

## [flow-next 0.20.17] - 2026-02-03

### Fixed

- **Hooks: duplicate entries for cross-platform** — Droid doesn't support bash fallback syntax in hook commands. Now uses separate entries for `${CLAUDE_PLUGIN_ROOT}` and `${DROID_PLUGIN_ROOT}`. Each platform expands its own variable; the other fails silently.

## [flow-next 0.20.16] - 2026-02-03

### Fixed

- **Full cross-platform variable support** — Hooks and skills now use `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` bash fallback pattern. Works on both Claude Code and Factory Droid without duplication. Hook matchers use `Bash|Execute` regex for both platforms.

## [flow-next 0.20.15] - 2026-02-03

### Fixed

- **Restore read-only scout permissions** — v0.20.14 inadvertently gave all agents Edit/Write access. Now scouts use `disallowedTools: Edit, Write, Task` to maintain read-only restrictions while staying cross-platform compatible (no whitelist of tool names that differ between Claude Code and Droid).

## [flow-next 0.20.14] - 2026-02-03

### Fixed

- **Full Droid compatibility** — Removed explicit `tools:` field from all agents. Both platforms now inherit their native tools automatically. Fixes "partially loaded" issue on Factory Droid caused by unknown tool names (`WebFetch`/`FetchUrl`, `Bash`/`Execute`).

## [flow-next 0.20.13] - 2026-02-03

### Fixed

- **Droid Bash/Execute compatibility** — Added `Execute` alongside `Bash` in 18 agents. Droid uses `Execute`, Claude Code uses `Bash` — now both work.

## [flow-next 0.20.12] - 2026-02-03

### Fixed

- **Droid agent tool compatibility** — Added `FetchUrl` alongside `WebFetch` in 7 agents (context-scout, docs-scout, flow-gap-analyst, github-scout, practice-scout, quality-auditor, repo-scout). Droid uses `FetchUrl`, Claude Code uses `WebFetch` — now both work.

## [flow-next 0.20.11] - 2026-02-03

### Changed

- **Marketplace reorder** — flow-next now listed first (Droid auto-installs first plugin when adding marketplace)

## [flow-next 0.20.10] - 2026-02-03

### Fixed

- **Factory Droid compatibility** — Plugin version checks now work on both Claude Code (`.claude-plugin/`) and Factory Droid (`.factory-plugin/`). Skills gracefully handle either directory structure.

## [flow-next 0.20.9] - 2026-02-03

### Fixed

- **Cleaner Ralph branch names** — Branch format changed from `ralph-20260203T143000Z-hostname-email-pid-rand` to `ralph-20260203-143000-rand`. Removes PII (hostname, email) and noise (PID) from git history. Full verbose ID preserved in logs for debugging. Thanks to [@aleparreira](https://github.com/aleparreira) for the report! (#90)

### Added

- **ZSH-safe file truncation helper** — Added `truncate_file()` function using `: > "$file"` pattern for portable file truncation across bash/zsh/sh. Prevents potential hangs on macOS (ZSH default since Catalina).

## [flow-next 0.20.8] - 2026-02-03

### Fixed

- **Double context builder in reviews** — SKILL.md files for epic-review, impl-review, and plan-review no longer contain duplicate executable code. Now explicitly direct agent to workflow.md as single source of truth. Fixes issue where agent would run setup-review and chat-send twice.

### Changed

- **Codex install script improvements**:
  - Agents now installed to `~/.codex/agents/` with frontmatter converted to Codex format (`profile`, `approval_policy`, `sandbox_mode`)
  - `flow-next-work` skill patched to inline worker phases (Codex lacks Task tool for subagents)
  - Added timeout warnings for `setup-review` (5-10 min) and `chat-send` (2-5 min) commands

## [flow-next 0.20.7] - 2026-02-02

### Fixed

- **Epic ID collision prevention** — `scan_max_epic_id` now scans both `epics/*.json` and `specs/*.md` to catch orphaned specs created outside flowctl. Prevents reusing numeric IDs when specs exist without matching epic JSON.
- **Collision detection in validate** — `flowctl validate --all` now detects and reports epic ID collisions (multiple epics with same `fn-N` prefix) as errors.
- **Orphaned spec warnings** — `flowctl validate --all` warns about specs without matching epic JSON files.

## [flow-next 0.20.5] - 2026-02-01

### Fixed

- **Duplicate skill/command listings** — Skills that have command stubs now set `user-invocable: false` to hide from `/` menu. Commands remain the user-facing entry points; skills still work when Claude invokes them.

## [flow-next 0.20.4] - 2026-02-01

### Added

- **`epic set-title` command** — Rename epics by updating title and slug: `flowctl epic set-title fn-1-old --title "New Title"`. Renames all related files, updates task references and `depends_on_epics` in other epics.

## [flow-next 0.20.3] - 2026-01-31

### Changed

- **Readable epic IDs** — Epic IDs now use slugified titles instead of random suffixes. `fn-23-zgk` → `fn-23-readable-epic-ids`. Random 3-char suffix only used as fallback for empty/special-char titles. Existing IDs remain fully compatible.

### Updated

- All error messages and CLI help strings to show new slug format examples
- TUI regex patterns to accept slug-based IDs
- Skill docs with new ID format examples

## [flow-next 0.20.2] - 2026-01-31

### Added

- **`task set-deps` command** — Set multiple task dependencies in one call: `flowctl task set-deps fn-1.3 --deps fn-1.1,fn-1.2`. Convenience wrapper for `dep add` that matches the `--deps` syntax from `task create`.

## [flow-next 0.20.1] - 2026-01-30

### Added

- **Epic dependency visualization skill** — New `flow-next-deps` skill shows epic dependency graphs, blocking chains, and execution phases. Triggers on "what's blocking", "execution order", "critical path", "which epics can run in parallel". Uses flowctl for data access with jq-based phase computation. Thanks [@clairernovotny](https://github.com/clairernovotny)! (PR #85)

### Fixed

- **Skill count sync** — Updated manifest descriptions to reflect actual counts (20 subagents, 11 commands, 16 skills).

## [flow-next 0.20.0] - 2026-01-30

### Added

- **Epic-completion review gate** — New `/flow-next:epic-review` skill runs when all epic tasks complete, before epic closes. Two-phase review (extract requirements → verify coverage) catches gaps that per-task impl-review misses: decomposition gaps, cross-task requirements, scope drift. Supports RepoPrompt and Codex backends. Closes #83.

- **flowctl commands** — `codex completion-review` for LLM-driven epic review, `epic set-completion-review-status` for manual status control, `--require-completion-review` selector flag.

- **Ralph integration** — `COMPLETION_REVIEW` config (rp/codex/none), gating in `maybe_close_epics()`, `status=completion_review` handler, `prompt_completion.md` template.

- **ralph-guard support** — Parses `completion-fn-N.json` receipt pattern, tracks `flowctl codex completion-review` calls, routes stop-hook to `/flow-next:epic-review`.

- **Work skill update** — `/flow-next:work` now handles `completion_review` status after all tasks complete.

### Changed

- **README callouts** — Replaced `/flow-next:prime` callout with `/flow-next:epic-review`. Removed "Stable features" line (now baseline).

## [flow-next 0.19.1] - 2026-01-30

### Fixed

- **Plan skill scout enforcement** — Added CRITICAL block requiring ALL scouts to run in parallel during planning. Previously, agents would skip scouts "because they seem most relevant", causing incomplete plans missing external docs, epic dependencies, and practice pitfalls.

- **Task dependency guidance** — Updated steps.md to document existing `--deps` flag on `task create`. Removes incorrect guidance that said flag didn't exist. Shows preferred inline dependency declaration vs separate `dep add` calls.

## [flow-next 0.19.0] - 2026-01-28

### Changed

- **Worker review enforcement** — Phase 4 header now reads "MANDATORY if REVIEW_MODE != none" with clearer instruction that worker must invoke `/flow-next:impl-review` and receive SHIP verdict before proceeding to Phase 5. Addresses issue where worker would skip review phase entirely.

- **Stop hook guidance improved** — When worker tries to stop without completing review, the ralph-guard hook now tells the worker to invoke the review skill (`/flow-next:impl-review` or `/flow-next:plan-review`) instead of providing a command to manually write the receipt. This prevents bypassing the actual review and allows the worker to correct in-context without a full retry.

### Fixed

- **Worker skipping impl-review** — Fixed issue where worker subagent would complete implementation, run `flowctl done`, and return without invoking `/flow-next:impl-review` when `REVIEW_MODE` was `rp` or `codex`. This caused Ralph to block on missing receipt, force retries, and eventually auto-block tasks after 5 attempts. Thanks [@tiagoefreitas](https://github.com/tiagoefreitas)! (PR #81)

### Migration

This release modifies ralph-guard hook behavior. If you encounter issues:
1. Report at https://github.com/gmickel/flow-next/issues
2. Downgrade: `claude plugins uninstall flow-next && claude plugins add https://github.com/gmickel/flow-next && claude plugins install flow-next@0.18.27`

## [flow-next 0.18.27] - 2026-01-28

### Added

- **`--config` flag for Ralph** — Specify alternate config file: `ralph.sh --config my-codex-config.env`. Enables different configs for different platforms/review backends without editing config.env. Closes #82.

## [flow-next 0.18.26] - 2026-01-28

### Added

- **Version check warning in Ralph** — Ralph now checks if local setup version differs from plugin version at startup. Shows warning: "Plugin updated to vX.Y.Z. Run /flow-next:setup to refresh local scripts (current: vA.B.C)." Non-blocking, warn only.

## [flow-next 0.18.25] - 2026-01-27

### Fixed

- **Block Explore auto-delegation in Ralph mode** — Worker subagent has `disallowedTools: Task` but enforcement is inconsistent (known Claude Code bugs #21295, #21296). When Explore was auto-spawned, it failed with READ-ONLY constraint and couldn't write receipts, causing infinite retry loops. Now explicitly block `Task(Explore)` at CLI level in ralph.sh (precedence 2 beats agent frontmatter precedence 6). Interactive mode unaffected - fix only applies to Ralph autonomous sessions.

## [flow-next 0.18.24] - 2026-01-26

### Fixed

- **Epic dependency race condition** — Move `maybe_close_epics()` before selector in Ralph loop. Previously, dependent epics remained blocked when parent epic completed because closing happened after selector returned `NO_WORK`. Now epics close at iteration start, unblocking dependents immediately. Thanks [@tiagoefreitas](https://github.com/tiagoefreitas)! (#79)

## [flow-next 0.18.23] - 2026-01-26

### Added

- **Plan Review Gate documentation** — Comprehensive docs for Ralph's plan review gate: how it works, configuration matrix, review cycle, checkpoint recovery, status inspection, and comparison with impl review. Added troubleshooting for common issues: plan review never starts, blocked forever, dependent epics not starting.

## [flow-next 0.18.22] - 2026-01-26

### Fixed

- **Ralph plan prompt aligned with skill** — Added checkpoint save before plan review, task spec sync mention, and checkpoint restore on context compaction. Ensures Ralph plan gate has same recovery capabilities as interactive `/flow-next:plan-review`.

## [flow-next 0.18.21] - 2026-01-26

### Added

- **Backend spec fields for tasks and epics** — New optional `impl`, `review`, `sync` fields on tasks and `default_impl`, `default_review`, `default_sync` on epics. These fields store preferred AI backend + model specs (e.g., `codex:gpt-5.2-high`, `claude:opus`). Pure storage - flowctl doesn't interpret them; orchestration products like flow-swarm use them to route different tasks to different backends.

- **`flowctl task set-backend`** — Set backend specs on a task: `flowctl task set-backend fn-1.1 --impl codex:gpt-5.2-high --review claude:opus`

- **`flowctl epic set-backend`** — Set default backend specs on an epic: `flowctl epic set-backend fn-1 --impl codex:gpt-5.2-codex`

- **`flowctl task show-backend`** — Query effective backend specs for a task (task + epic levels): `flowctl task show-backend fn-1.1 --json`

**Note:** These fields have no effect on current flow-next/Ralph usage. They enable an upcoming orchestration product where different tasks can use different backends (complex refactors → expensive reasoning models, simple fixes → fast cheap models).

## [flow-next 0.18.20] - 2026-01-26

### Changed

- **Task sizing: M is the sweet spot** — Updated plan skill to prefer M-sized tasks over many S tasks. Sequential S tasks should be combined into M tasks. Added "7+ tasks = look for tasks to combine" heuristic.

- **OAuth example: 4 tasks → 2 tasks** — Task breakdown example now shows combining sequential backend work into one M task + separate frontend S task. Added "over-split" anti-pattern example.

- **Plan review checks for over-splitting** — Added "Task sizing" as review criterion #8: flags 7+ tasks or sequential S tasks that should be combined.

- **Interview balances split vs combine** — Architecture questions now probe both: "can tasks touch disjoint files?" AND "can sequential steps be combined into M-sized tasks?"

## [flow-next 0.18.19] - 2026-01-26

### Changed

- **Memory and Plan-Sync enabled by default** — New projects now have `memory.enabled: true` and `planSync.enabled: true` out of the box. Cross-epic sync remains disabled by default to avoid long Ralph loops. Disable with `flowctl config set memory.enabled false` or `flowctl config set planSync.enabled false`.

## [flow-next 0.18.18] - 2026-01-25

### Fixed

- **Preserve GH-73 COMPLETE handling fix** — PR #74 inadvertently reverted the fix for premature completion in Ralph. Workers should NEVER output `<promise>COMPLETE</promise>` (prompts forbid it); completion is detected via selector returning `status=none`. Restored the ignore-and-log behavior.

### Documentation

- **Improved `--files` guidance in plan-review skills** — Added explanation of how to identify which files to pass (read epic spec, find affected paths) instead of just a hardcoded example.

## [flow-next 0.18.17] - 2026-01-25

### Fixed

- **Filter artifact files using is_task_id() validation** — Replaced weak `"." not in task_id` check with proper `is_task_id()` regex validation. Fixes `KeyError: 'title'` crash when `.flow/tasks/` contains artifact files like `fn-1.2-review.json`. Works with both legacy (`fn-3.1`) and new (`fn-3-sds.1`) ID formats. Thanks to @kirillzh for the contribution!

## [flow-next 0.18.16] - 2026-01-24

### Added

- **Parallelization guidance for task splitting** — Plan skill now includes guidance to minimize file overlap when splitting tasks. Tasks touching disjoint files can be worked in parallel without merge conflicts.

- **Plan-review parallelizability criterion** — Added "Parallelizability" as review criterion #3: flags independent tasks that touch overlapping files.

- **Interview probe for parallel work** — Architecture questions now include "Can this be split so tasks touch disjoint files?"

## [flow-next 0.18.15] - 2026-01-24

### Fixed

- **Restored manual prompt building for RP reviews** — Reverted from the flaky two-step chat approach (`--response-type review` + follow-up) back to the reliable single-chat approach with custom review prompts.

  **Why this was necessary:**
  - The `--response-type review` mode introduced in 0.14.0 delegates prompt construction to RepoPrompt's builder, giving us no control over the exact prompt sent to the reviewer model
  - RP returns its own verdict format (`request-changes`, `approve`, etc.) instead of our `<verdict>SHIP|NEEDS_WORK|MAJOR_RETHINK</verdict>` tags
  - This required a follow-up message just to get the verdict in the correct format, making the flow fragile
  - Versions 0.18.5 through 0.18.12 were all attempts to patch this two-step flow, adding warnings, stronger instructions, and format reminders — none fully resolved the flakiness
  - In autonomous operation (Ralph), this unreliability breaks the review loop entirely when the model skips the follow-up or misparses the builder's verdict

  **What changed:**
  - Removed `--response-type review` from `setup-review` calls
  - Restored Phase 2 manual file selection (explicitly add changed files)
  - Restored Phase 3 `prompt-get` + custom review prompt with full Carmack criteria and verdict requirement baked in
  - Single `chat-send --new-chat` returns verdict directly — no follow-up needed

  **What was preserved:**
  - MAX_REVIEW_ITERATIONS=3 (reduced from 5)
  - Checkpoint save/restore for context compaction recovery
  - Task spec inclusion and syncing in plan-review
  - All flowctl.py improvements (`--chat-id`, `--mode`, etc. remain available)

## [flow-next 0.18.14] - 2026-01-24

### Fixed

- **Codex sandbox on Windows blocking all reads** — Codex CLI's `read-only` sandbox uses Windows AppContainer which blocks ALL shell commands, including file reads. Added `--sandbox` flag to `flowctl codex impl-review` and `flowctl codex plan-review` with `auto` mode that resolves to `danger-full-access` on Windows and `read-only` on Unix. Added `CODEX_SANDBOX` config option for Ralph. Full file contents are now embedded in review prompts to work around sandbox limitations.

### ⚠️ Breaking Change: `--files` required for `flowctl codex plan-review`

`flowctl codex plan-review` now requires `--files` (comma-separated **code** file paths) so the reviewer has concrete repository context (and so Windows can embed file contents when the Codex sandbox blocks reads).

Migration: update any scripts to pass `--files`, e.g. `--files "src/auth.ts,src/config.ts"`.

### Added

- **`--sandbox` flag for codex commands** — Supports `read-only`, `workspace-write`, `danger-full-access`, and `auto` modes
- **`CODEX_SANDBOX` config option for Ralph** — Configure sandbox mode in `scripts/ralph/config.env` (default: `auto`)
- **Exit code 3 for sandbox errors** — flowctl returns exit code 3 for sandbox configuration issues

### Documentation

- flowctl.md: Added `--sandbox` flag documentation for both impl-review and plan-review
- flowctl.md: Documented `--files` requirement for plan-review
- ralph.md: Added `CODEX_SANDBOX` config option with valid values
- ralph.md: Added troubleshooting section for "blocked by policy" errors
- CLAUDE.md: Added Windows sandbox note in Codex section

**Note:** Re-run `/flow-next:setup` or `/flow-next:ralph-init` after plugin update to get sandbox fixes.

## [flow-next 0.18.13] - 2026-01-23

### Fixed

- **Ralph exits early on NEEDS_WORK despite force_retry** — Worker returns `<promise>COMPLETE</promise>` after marking task done. Ralph checked for COMPLETE *after* setting `force_retry=1` for NEEDS_WORK, causing premature exit. Now skips COMPLETE exit when `force_retry=1`.

## [flow-next 0.18.12] - 2026-01-23

### Fixed

- **Agent skipping verdict follow-up** — Added ⚠️ WARNING block after Step 2 explicitly stating RP's verdict is INVALID and Step 4 is MANDATORY. Agent was seeing builder's `request-changes` verdict and jumping to fix loop without sending the follow-up to get our verdict format.

## [flow-next 0.18.11] - 2026-01-23

### Fixed

- **RP uses its own verdict format** — Builder's `response_type=review` returns RP's verdict format (`request-changes`, `approve`, etc.) not ours. Updated instructions to explicitly IGNORE builder verdict and extract verdict ONLY from the follow-up chat response. Added clearer verdict tag requirements with "Do NOT use any other verdict format."

## [flow-next 0.18.10] - 2026-01-23

### Changed

- **Stronger workflow.md references** — Changed "Read workflow.md" to "⚠️ MANDATORY: Read workflow.md BEFORE executing RP backend steps" and "⚠️ STOP: Read workflow.md NOW" to ensure agents follow the link. SKILL.md is a summary; workflow.md has the complete flow.

## [flow-next 0.18.9] - 2026-01-23

### Fixed

- **Missing verdict follow-up step in SKILL.md** — Builder returns review findings but NOT a verdict tag. Added explicit follow-up chat step to request verdict in both impl-review and plan-review SKILL.md files. Without this, Ralph breaks waiting for a verdict that never comes.

## [flow-next 0.18.8] - 2026-01-23

### Fixed

- **plan-review also missing --response-type review** — Same fix as 0.18.7 but for plan-review skill. Updated SKILL.md, workflow.md, and flowctl-reference.md.

## [flow-next 0.18.7] - 2026-01-23

### Fixed

- **impl-review SKILL.md missing --response-type review** — The actual bug was in SKILL.md which agents read. The example setup-review call was missing `--response-type review`, causing RP to use default "clarify" mode instead of "review" mode.

## [flow-next 0.18.6] - 2026-01-23

### Fixed

- **rp-cli builder --type flag** — Use `--type review` (shorthand flag) instead of `response_type=review` (key=value). Turns out both work, but the real issue was SKILL.md - see 0.18.7.

## [flow-next 0.18.5] - 2026-01-23

### Fixed

- **rp-cli builder response_type format** — Changed from invalid `--response-type review` to `response_type=review`. Still didn't work - see 0.18.6.

- **Added verdict requirement to review instructions** — The builder review instructions now explicitly request a verdict tag (`<verdict>SHIP|NEEDS_WORK|MAJOR_RETHINK</verdict>`), ensuring consistent verdict output from RP reviews.

- **Fixed cli-reference.md** — Updated rp-cli example to use `--type` shorthand instead of invalid `--response-type` flag.

## [flow-next 0.18.4] - 2026-01-23

### Fixed

- **Ralph now auto-closes epics in unscoped runs** — Previously `maybe_close_epics()` only ran when `EPICS=...` was specified, meaning unscoped Ralph runs would never auto-close epics even when all tasks were done. This blocked downstream epics that depended on them. Now Ralph checks all open epics and closes any with all tasks completed. Thanks to [@VexyCats](https://github.com/VexyCats) for the report!

- **Added `list_open_epics()` helper** — New function to get all non-done epic IDs from flowctl for unscoped runs.

## [flow-next 0.18.3] - 2026-01-23

### Fixed

- **Ralph now enforces receipt verdict** — Previously Ralph only checked that impl-review receipts existed but ignored the `verdict` field. Now Ralph reads the verdict from the receipt file and forces a retry if `NEEDS_WORK`, even if the worker marked the task as done. This fixes issue #70 where NEEDS_WORK verdicts from Codex reviews were being ignored. Thanks to [@VexyCats](https://github.com/VexyCats) for the detailed report!

- **Added `read_receipt_verdict()` helper** — New function in ralph.sh to read the verdict field from receipt JSON files.

## [flow-next 0.18.2] - 2026-01-23

### Changed

- **Expanded `/flow-next:prime` to 8 pillars (48 criteria)** — Now matches Factory.ai's comprehensive assessment:
  - Agent Readiness (Pillars 1-5): Style & Validation, Build System, Testing, Documentation, Dev Environment
  - Production Readiness (Pillars 6-8): Observability, Security, Workflow & Process

- **Two-tier scoring** — Agent Readiness score (determines maturity level, fixes offered) + Production Readiness score (reported only, no fixes). Gives full visibility while keeping remediation focused.

- **3 new scouts** for production readiness:
  - `observability-scout` — Structured logging, tracing, metrics, error tracking, health endpoints
  - `security-scout` — Branch protection, secret scanning, CODEOWNERS, Dependabot (via GitHub API)
  - `workflow-scout` — CI/CD pipelines, PR templates, issue templates, release automation

- **Test verification** — Now runs `pytest --collect-only` (or equivalent) to verify tests actually work, not just that files exist.

- **GitHub API integration** — Uses `gh` CLI to check branch protection, secret scanning status, and repository settings.

## [flow-next 0.18.0] - 2026-01-23

### Added

- **`/flow-next:prime` command** — Agent readiness assessment inspired by Factory.ai's framework. Analyzes your codebase and proposes non-destructive improvements.

- **6 haiku scouts** for fast parallel assessment:
  - `tooling-scout` — Scans linters, formatters, pre-commit hooks, type checking
  - `claude-md-scout` — Analyzes CLAUDE.md/AGENTS.md quality and completeness
  - `env-scout` — Checks .env.example, Docker, devcontainer, setup scripts
  - `testing-scout` — Evaluates test framework, coverage config, test commands
  - `build-scout` — Reviews build system, scripts, CI configuration
  - `docs-gap-scout` — README, ADRs, architecture docs

- **Maturity levels 1-5** — Repositories scored from Minimal (1) to Autonomous (5). Level 3 (Standardized) is the recommended target for most teams.

- **Interactive remediation** — After assessment, offers to fix gaps with user consent via AskUserQuestion. Supports `--report-only` (skip fixes) and `--fix-all` (apply all without asking).

- **Remediation templates** — Built-in templates for common fixes: CLAUDE.md, .env.example, pre-commit hooks, and more.

### Technical Details

The prime workflow:
1. Runs scouts in parallel (fast, ~15-20 seconds)
2. Synthesizes findings into a readiness report with pillar scores
3. Uses AskUserQuestion for each category of improvements
4. Applies approved fixes non-destructively (never overwrites without consent)
5. Offers re-assessment to show improvement

Works for both greenfield and brownfield projects.

## [flow-next 0.17.4] - 2026-01-22

### Fixed

- **Bash `!=` operator in skill markdown** — Version check in `/flow-next:plan` and `/flow-next:interview` was failing with syntax error when Claude Code parsed the bash code blocks. The `!` character was being escaped to `\!` during processing. Rewrote conditionals to avoid `!=` operator. Thanks @clairedotcom for reporting (#68).

## [flow-next 0.17.2] - 2026-01-21

### Fixed

- **Windows compatibility** — `fcntl` import now conditional; was causing `ModuleNotFoundError` on Windows since 0.17.0. File locking gracefully degrades to no-op on Windows (acceptable for single-machine use).

## [flow-next 0.17.1] - 2026-01-21

### Fixed

- **Plan review now includes task specs** — `/flow-next:plan-review` previously reviewed only the epic spec, leaving task specs stale when epic changes occurred during the fix loop. Now both RP and Codex backends include task specs in the review. Reviewers can flag inconsistencies between epic and task specs, and the fix loop instructs the agent to sync affected task specs.

### Added

- **`task set-spec --file`** — Full spec replacement mode for task specs (like `epic set-plan --file`). Supports both file paths and stdin (`-`). Use in plan-review fix loops to sync task specs after epic changes.
- **Consistency checking in review criteria** — Both plan review backends now explicitly check for epic/task consistency: contradicting requirements, misaligned acceptance criteria, stale state/enum references.
- **Task sync instructions in re-review preamble** — When re-reviewing, Codex backend now instructs the agent to sync task specs if epic changes affected them.

### Changed

- **Review prompt expanded** — Plan review now includes `<task_specs>` section with all task spec content (Codex backend). RP backend adds task spec files to selection.
- **Fix loop steps updated** — Both SKILL.md and workflow.md now include task spec sync as explicit step (step 3 in SKILL.md, step 4 in workflow.md) before re-review.
- **Anti-pattern added** — "Updating epic spec without syncing affected task specs" documented as anti-pattern in workflow.md.

### Technical Details

Task specs need syncing when epic changes affect:
- State/enum values referenced in tasks
- Acceptance criteria that tasks implement
- Approach/design decisions tasks depend on
- Lock/retry/error handling semantics
- API signatures or type definitions

## [flow-next 0.17.0] - 2026-01-21

### Added

- **Shared runtime state for parallel worktree execution** — Task runtime state (status, assignee, claim info, evidence) now lives in `.git/flow-state/` instead of the tracked definition files. This enables multiple git worktrees to share task state, unlocking parallel orchestration workflows where different agents work on different tasks simultaneously.

- **StateStore abstraction** — New `LocalFileStateStore` with per-task `fcntl` locking prevents race conditions when multiple processes claim or update tasks concurrently.

- **New commands**:
  - `flowctl state-path` — Shows resolved state directory (useful for debugging)
  - `flowctl migrate-state [--clean]` — Migrates existing repos to the new state model. `--clean` removes runtime fields from tracked JSON files after migration.

- **Checkpoint schema v2** — Checkpoints now include runtime state, enabling full restore across worktrees.

### Changed

- **Merged read path** — All task reads now merge definition + runtime state.
- **Atomic task claiming** — `flowctl start` validates and writes under the same lock, eliminating TOCTOU race conditions.
- **Reset semantics** — `flowctl task reset` now properly clears runtime state (overwrite, not merge).

### Backward Compatibility

**No action required.** Existing repos work without any migration. The merged read path automatically falls back to reading runtime fields from definition files when no state file exists. Migration is only needed if you want to:
- Use parallel worktree orchestration
- Stop tracking runtime state in git (cleaner diffs)

### Technical Details

State directory resolution order:
1. `FLOW_STATE_DIR` environment variable (explicit override)
2. `git --git-common-dir` + `/flow-state` (worktree-aware, shared)
3. `.flow/state` fallback (non-git or old git)

Runtime fields moved to state: `status`, `updated_at`, `assignee`, `claimed_at`, `claim_note`, `evidence`, `blocked_reason`

## [flow-next 0.16.0] - 2026-01-21

### Added

- **Epic-aware planning** — New `epic-scout` subagent runs during `/flow-next:plan` research phase (parallel with other scouts). Scans open epics for dependency relationships and auto-sets `depends_on_epics` when found. No user prompts needed — findings reported at end of planning.
- **Docs-gap detection** — New `docs-gap-scout` subagent identifies documentation that may need updates (README, API docs, ADRs, CHANGELOG, etc.). Adds acceptance criteria to relevant tasks — implementer decides actual content.
- **Cross-epic plan-sync** — Optional mode for plan-sync agent. When `planSync.crossEpic: true`, also checks other open epics for stale references after task completion. **Default: false** (avoids long Ralph loops).
- **New config option** — `planSync.crossEpic` (boolean, default false). Enable via `/flow-next:setup` or `flowctl config set planSync.crossEpic true`.

### Changed

- Plan-sync agent now accepts `CROSS_EPIC` input and has new Phase 4b for cross-epic checking
- Setup workflow shows new cross-epic config option (only asked if plan-sync is enabled)
- `memory-scout` model changed from opus to haiku (task is mechanical grep/read, doesn't need reasoning)

### Notes

- **Re-run `/flow-next:setup`** to get the new config option and update local flowctl
- Cross-epic sync is conservative — only flags clear API/pattern references, not general topic overlap

## [flow-next 0.15.0] - 2026-01-21

### Changed

- **WORKER_TIMEOUT default** — 45min → 1hr (3600s). Timeout is now a safety guard against runaway workers, not flow control. Properly sized tasks shouldn't hit it ([#59](https://github.com/gmickel/flow-next/issues/59))
- **MAX_REVIEW_ITERATIONS default** — 5 → 3. Tighter cap; if 3 fix cycles don't pass review, task/spec is likely too big or ambiguous. Let next Ralph iteration start fresh
- **Timeout philosophy** — Docs and comments now clarify: time is arbitrary, `MAX_REVIEW_ITERATIONS` is the real control. One Ralph iteration = impl + review, should complete within single context window

## [flow-next 0.14.4] - 2026-01-21

### Added

- **Version mismatch warning** — `/flow-next:plan` and `/flow-next:interview` now check if local setup is outdated. If `.flow/meta.json` has older `setup_version` than plugin, prints: "Plugin updated to vX.Y.Z. Run /flow-next:setup to refresh local scripts." Non-blocking, continues normally.

## [flow-next 0.14.3] - 2026-01-21

### Changed

- **Setup skips already-configured options** — Re-running `/flow-next:setup` now detects existing config (memory, planSync, review.backend) and skips those questions. Shows current config with `flowctl config set` commands for changing values.
- **Review backend descriptions improved** — RepoPrompt now highlights auto-scoped diffs and ~65% fewer tokens; Codex notes cross-platform + GPT 5.2 High. No "(Recommended)" — user decides based on platform/needs.

## [flow-next 0.14.2] - 2026-01-21

### Fixed

- **Task-level interview guard** — When interviewing a task (fn-N.M) that already has planning content (file refs, sizing, approach), interview now preserves that detail instead of overwriting. Only acceptance criteria can be appended, or user is directed to interview the epic instead.

## [flow-next 0.14.1] - 2026-01-21

### Fixed

- **Interview skill boundary ambiguity** — Interview was creating full implementation plans with tasks, conflicting with `/flow-next:plan`. Now:
  - Interview creates epic with refined requirements only (problem, decisions, edge cases)
  - Interview does NOT create tasks — that's plan's job
  - When interviewing an epic that already has tasks, only the epic spec is updated
  - Clear "NOT in scope" section lists what belongs in plan vs interview

### Changed

- **Epic spec template** — Renamed "Approach" → "Key Decisions" + added "Open Questions" section to clarify interview captures requirements, not implementation approach
- **Input-type routing** — Interview now handles different inputs differently:
  - New idea → create epic stub, suggest `/flow-next:plan`
  - Existing epic with tasks → update epic spec only, don't touch tasks
  - Task ID → update task requirements only
  - File path → rewrite file, suggest `/flow-next:plan <file>`
- **README clarification** — Added explicit "Interview vs Plan boundary" note in "When to Use What" section

Thanks to @tiagoefreitas for the detailed issue report ([#62](https://github.com/gmickel/flow-next/issues/62)).

## [flow-next 0.14.0] - 2026-01-21

### ⚠️ Breaking Change: RepoPrompt 1.6.0+ Required

The RepoPrompt (rp) backend for `/flow-next:impl-review` now uses the new **builder review mode** introduced in RepoPrompt 1.6.0. This provides better context discovery and more focused reviews.

**Before upgrading**: Check your RepoPrompt version with `rp-cli --version`. If you're on an older version, update RepoPrompt first or use `--review=codex` as an alternative.

### Changed

- **RP impl-review uses builder review mode** — Instead of manually building review prompts and selecting files, the builder's discovery agent now:
  - Automatically includes git diffs for the commits being reviewed
  - Selects relevant context files with full codebase awareness
  - Produces structured review findings before verdict
  - Lower token usage (~26K vs ~71K) with better coverage

- **New flowctl rp commands**:
  - `--response-type review` on `rp builder` and `rp setup-review`
  - `--chat-id` on `rp chat-send` for conversation continuity
  - `--mode` on `rp chat-send` (chat/review/plan/edit)

- **Simplified RP workflow** — Removed manual file selection (Phase 2) and elaborate prompt building (Phase 3). Builder handles context discovery; follow-up chat requests verdict.

- **Fix loop uses `--chat-id`** — Re-reviews now use explicit chat ID for session continuity instead of relying on tab state.

### Added

- RP 1.6.0 requirement notice in SKILL.md and workflow.md

### Unchanged

- Codex backend — No changes, works as before
- Plan-review — No changes, only impl-review affected
- Receipt format — Compatible with Ralph

## [flow-next 0.13.0] - 2026-01-19

### ⚠️ Significant Planning Workflow Changes

**The Problem:** Plans were doing implementation work. Epic and task specs contained complete function bodies, full interface definitions, and copy-paste ready code blocks. This caused:

1. **Wasted tokens in planning** — Writing code that won't ship
2. **Wasted tokens in review** — Reviewing code that won't ship
3. **Wasted tokens in implementation** — Re-writing essentially the same code
4. **Plan-sync drift** — Implementer does it slightly differently, specs and reality diverge

Real examples from production plans showed 28KB epic specs with complete TypeScript implementations, and task specs that were literally the code to write — nothing left for `/flow-next:work` to do.

**The Solution:** Plans describe WHAT to build and WHERE to look — not HOW to implement.

### Added

- **"The Golden Rule" in SKILL.md** — Explicit guidance on what code belongs in plans vs. what doesn't
  - ✅ Allowed: Signatures, file:line refs, recent/surprising APIs, non-obvious gotchas
  - ❌ Forbidden: Complete implementations, full class bodies, copy-paste snippets (>10 lines)

- **Task sizing with T-shirt sizes** — Observable metrics instead of token estimates

  | Size | Files | Acceptance | Pattern | Action |
  |------|-------|------------|---------|--------|
  | S | 1-2 | 1-3 | Follows existing | ✅ Good |
  | M | 3-5 | 3-5 | Adapts existing | ✅ Good |
  | L | 5+ | 5+ | New/novel | ⚠️ Split |

  - Anchor examples for calibration (S = fix bug, M = new endpoint with tests, L = split it)
  - Good/bad breakdown examples (e.g., "Implement OAuth" → 4 S/M tasks)

- **Plan depth selection** — Users can now choose detail level upfront
  - `--depth=short` | `--depth=standard` (default) | `--depth=deep`
  - Or answer "1a/1b/1c" in setup questions

- **Follow-up options in Step 7** — After plan creation:
  - Go deeper on specific tasks
  - Simplify (reduce detail)
  - Loop until user chooses work/interview/review

- **Expanded examples.md** — Complete rewrite with:
  - Good vs. bad epic spec examples (side by side)
  - Good vs. bad task spec examples
  - Task breakdown examples
  - When code IS appropriate (with specific triggers)

- **"Current year is 2026" note** — Added to docs-scout, practice-scout, github-scout
  - Ensures web searches target recent documentation

- **Stakeholder analysis step** — New Step 2 asks who's affected (end users, developers, operations)
  - Shapes what the plan needs to cover
  - Pure backend refactor needs different detail than user-facing feature

- **Mermaid diagram guidance** — For data model and architecture changes
  - ERD for new tables/schema changes
  - Flowchart for service architecture
  - Examples in examples.md

### Changed

- **Subagent output rules** — All research scouts now have explicit guidance:
  - Show signatures, not full implementations
  - Keep snippets to <10 lines illustrating the pattern shape
  - Focus on "where to look" not "what to write"

- **"When to include code" heuristic** — Instead of asking models to know their knowledge cutoff (they can't), we use observable signals:
  - Docs say "new in version X" or "changed in version Y"
  - API differs from common/expected patterns
  - Recent releases (2025+) with breaking changes
  - Deprecation warnings or migration guides
  - **Anything that surprised you or contradicted expectations**

  This "surprised you" heuristic works because models CAN notice "this is different from what I'd expect" even if they can't reliably say "this is beyond my training data."

- **Default depth is STANDARD** — Balanced detail; short/deep on request

### Technical Notes

This is a behavior change in planning output. Existing `.flow/` data is fully compatible — only new plans will follow the tighter guidelines.

The changes affect:
- `skills/flow-next-plan/SKILL.md` — Golden Rule, depth selection
- `skills/flow-next-plan/steps.md` — Task sizing, complexity, Step 7 options
- `skills/flow-next-plan/examples.md` — Complete rewrite
- `agents/repo-scout.md` — Output rules
- `agents/context-scout.md` — Output rules
- `agents/practice-scout.md` — Output rules, year note
- `agents/docs-scout.md` — Output rules, year note
- `agents/github-scout.md` — Year note

### Feedback Welcome

This is a significant change to the planning philosophy. If you find plans are now too sparse, or the "surprised you" heuristic isn't working well, please open an issue at https://github.com/gmickel/flow-next/issues

We'd rather iterate based on real usage than guess at the right balance.

---

### Implementation Review Improvements

**Scenario exploration checklist** — Reviewers now systematically walk through failure scenarios for changed code:

- Happy path (normal operation)
- Invalid inputs (null, empty, malformed)
- Boundary conditions (min/max, empty collections)
- Concurrent access (race conditions, deadlocks)
- Network issues (timeouts, partial failures)
- Resource exhaustion (memory, disk, connections)
- Security attacks (injection, overflow, DoS)
- Data corruption (partial writes, inconsistency)
- Cascading failures (downstream service issues)

**Scope guardrail:** Checklist explicitly scoped to "changed code only" — reviewers flag issues in the changeset, not pre-existing patterns. Reinforces the verdict scope rules added in 0.12.10.

Affects:
- `skills/flow-next-impl-review/workflow.md` (RP backend)
- `scripts/flowctl.py` — `build_review_prompt()` and `build_standalone_review_prompt()` (Codex backend)

## [flow-next 0.12.10] - 2026-01-19

### Changed
- **WORKER_TIMEOUT default increased** - 30min → 45min (2700s) to accommodate complex impl-review loops (#59)
- **Review verdict scope tightened** - Codex impl/plan reviews now focus on issues introduced by the changeset, not pre-existing codebase issues
  - Reviewers may mention tangential issues as "FYI" without affecting verdict
  - Prevents review loops from drifting to unrelated improvements

### Added
- **Iteration tracking in receipts** - Receipts now include `"iteration": N` for debugging timeout/failure patterns
- **Enhanced timeout logging** - Timeouts now log phase, task/epic ID, iteration, and suggest increasing `WORKER_TIMEOUT`

## [flow-next 0.12.9] - 2026-01-18

### Fixed
- **Task jumping on timeout** - Prevent tasks from being skipped when worker times out after `flowctl done` but before receipt write (#57)
  - Reset `done→todo` if receipt missing (ensures `flowctl next` picks it up)
  - Fatal abort if reset fails (prevents silent skipping)
  - Delete corrupted/partial receipts on verification failure
- **Timeout retry handling** - Don't count timeouts against `MAX_ATTEMPTS_PER_TASK` (infrastructure ≠ code failure)
- **Unnecessary retry on proven completion** - Clear `force_retry` when task done + receipt valid

Thanks to @VexyCats for the detailed analysis and logs that identified the root cause.

## [flow-next 0.12.8] - 2026-01-18

### Added
- **MAX_REVIEW_ITERATIONS env var** - Cap fix+re-review cycles within impl-review (default 5) (#57)
- **WORKER_TIMEOUT documentation** - Now documented in config.env template and ralph.md

### Fixed
- **plan command description** - Removed "clear" to avoid collision with /clear command (#56)

## [flow-next 0.12.7] - 2026-01-18

### Fixed
- **Review fix loop no longer prompts user** - plan-review and impl-review now automatically fix all valid issues without asking for confirmation (#55)
  - Goal: production-grade world-class software and architecture
  - Added explicit "Never use AskUserQuestion in this loop" to SKILL.md and workflow.md

## [flow-next 0.12.6] - 2026-01-17

### Added
- **github-scout agent** - Cross-repo code search via `gh` CLI
  - Search public + private GitHub repos
  - Quality tiers: Authoritative (★5k+) → Established (★1k+) → Reference (★100+) → Examples
  - Signals: stars, recency, official repos, fork status
- **Enhanced docs-scout** - Source diving when docs fall short
  - Fetch library source via `gh api`
  - Search GitHub issues for known problems
- **Enhanced practice-scout** - Real-world examples from GitHub
  - Quality heuristics table (stars, recency, official = High weight)
  - Cross-reference pattern (2-3 repos = higher confidence)

### Changed
- Research phase now runs `github-scout` in parallel with other scouts
- Subagent count: 7 → 10

### Docs
- Force update tip in README (issue #54)

## [flow-next 0.12.1] - 2026-01-16

### Fixed
- **Single-task mode respects input** - `/flow-next:work fn-N.M` now stops after completing that task
  - Previously looped to next task after plan-sync (bug in Phase 3f)
  - Phase 1 now tracks SINGLE_TASK_MODE vs EPIC_MODE
  - Phase 3f only loops in EPIC_MODE; SINGLE_TASK_MODE goes to quality phase

## [flow-next 0.12.0] - 2026-01-16

### ⚠️ Migration Required

**Review backend no longer auto-detects.** Users who relied on automatic `which rp-cli` / `which codex` detection will see behavior changes:

**Why this change:**
- LLMs deviated from instructions, checking wrong binaries (`rp`, `repoprompt` instead of `rp-cli`)
- 12+ redundant subprocess calls per session (same detection in every skill)
- Ralph mode already handled this correctly via config—now all skills do too

| Command | Old behavior | New behavior |
|---------|--------------|--------------|
| `/flow-next:plan`, `/flow-next:work` | Auto-detect, pick first available | Asks which backend to use (discovery flow) |
| `/flow-next:impl-review`, `/flow-next:plan-review` | Auto-detect, pick first available | Error if no backend configured |

**To migrate:** Run `/flow-next:setup` once per repo, or pass `--review=rp|codex|none` explicitly.

**Backwards compatible:** All existing `.flow/` data works unchanged. Only review invocation behavior changed.

### Added
- **`flowctl review-backend` command** - Returns explicit `ASK` or configured backend (`rp`/`codex`/`none`)
  - Skills use this instead of complex jq checks
  - LLMs handle explicit string matching better than empty/non-empty checks
  - Reduces LLM deviation on conditional logic

### Changed
- **Remove runtime `which` detection from skills** - Skills no longer auto-detect review backends
  - Removed `which rp-cli` / `which codex` from impl-review, plan-review, work, plan skills
  - Priority order: `--review=X` flag > `FLOW_REVIEW_BACKEND` env > `.flow/config.json` > error
  - Run `/flow-next:setup` to configure preferred backend (one-time)
  - Reduces LLM deviation (agents checking wrong binary names)
  - Reduces subprocess overhead (12+ calls per session)
- **Simplified skill conditionals** - All skills now use `$FLOWCTL review-backend`
  - Check for `ASK` (not configured) vs actual value (configured)
  - No more jq parsing or empty string checks
- **Setup asks review backend** - `/flow-next:setup` now prompts for RepoPrompt/Codex/None
  - Writes to `.flow/config.json` under `review.backend`
  - Shows detection status (detected / not detected) for each option
- **README updated** - Removed "auto-detect" from priority documentation

## [flow-next 0.11.9] - 2026-01-16

### Fixed
- **Task-scoped impl-review** - Reviews now only cover current task's changes, not entire branch
  - Worker captures `BASE_COMMIT` before implementing
  - Passes `--base $BASE_COMMIT` to `/flow-next:impl-review`
  - Diff is `BASE_COMMIT..HEAD` instead of `main..HEAD`
  - Prevents re-reviewing already-shipped code from previous tasks
  - Critical for Ralph mode where all tasks share one branch

## [flow-next 0.11.8] - 2026-01-16

### Added
- **`/flow-next:sync` command** - Manual plan-sync trigger ([#43](https://github.com/gmickel/flow-next/issues/43))
  - Sync from task: `/flow-next:sync fn-1.2`
  - Scan whole epic: `/flow-next:sync fn-1`
  - Preview mode: `/flow-next:sync fn-1.2 --dry-run`
  - Ignores `planSync.enabled` config (manual = always run)
  - Works with any source task status (not just done)
- **Dry-run support in plan-sync agent** - Shows proposed changes without writing

### Fixed
- **flowctl tasks/list KeyError** - Task JSON uses `epic` field, not `epic_id`
  - Fixes `flowctl tasks --epic` crash
  - Fixes TUI task fetching on repos with collision-resistant IDs

## [flow-next 0.11.5] - 2026-01-16

### Fixed
- **Ralph hooks check removed** - Remove blocking local hooks check from `ralph.sh` ([#45](https://github.com/gmickel/flow-next/issues/45))
  - Plugin hooks work via `hooks/hooks.json` when installed normally
  - The check was blocking ALL users, not just `--plugin-dir` users
  - Test scripts handle the `--plugin-dir` workaround for bug #14410
- **Ralph upgrade support** - `/flow-next:ralph-init` now offers to update existing setup
  - Detects existing `scripts/ralph/` and asks to update
  - Preserves `config.env` and `runs/` during update
  - Existing users: re-run `/flow-next:ralph-init` to get the fix

### Changed
- **Dev guidance** - CLAUDE.md now recommends local marketplace install over `--plugin-dir`
  - `/plugin marketplace add ./` then `/plugin install flow-next@flow-next`
  - Hooks work correctly this way (no workaround needed)
- **Setup notes** - `/flow-next:setup` now mentions `/flow-next:ralph-init` for autonomous mode

## [flow-next 0.11.4] - 2026-01-16

### Added
- **Plan-sync agent** - Synchronizes downstream task specs when implementation drifts
  - Opt-in via `flowctl config set planSync.enabled true`
  - Runs after each task completes, compares spec vs actual implementation
  - Updates downstream tasks with accurate names, APIs, data structures
  - Skip conditions: disabled (default), task failed, no downstream tasks
  - Agent uses `disallowedTools: Task, Write, Bash` + prompt-based Edit restriction
- New phase 3e in `/flow-next:work` phases.md (between verify and loop)
- `planSync.enabled` config key in flowctl.py
- Smoke test for planSync config
- **Idempotent `flowctl init`** - Safe to re-run, handles upgrades
  - Creates missing dirs/files without destroying existing data
  - Merges new config keys into existing config.json (deep merge)
  - Old configs without `planSync` now work correctly
- **Config deep merge** - `load_flow_config()` merges with defaults
  - Missing keys automatically get default values
  - Existing user values preserved
- `/flow-next:setup` now uses `AskUserQuestion` for all options at once
  - Memory, Plan-Sync, Docs, Star questions in single UI interaction

## [flow-next 0.11.1] - 2026-01-15

### Fixed
- **flowctl tasks/list commands** - Added guard to skip artifact files lacking required fields (GH-21)

## [flow-next 0.11.0] - 2026-01-15

### Added
- **Worker subagent model** - Each task spawns isolated worker for implementation
  - Prevents context bleed between tasks during `/flow-next:work`
  - Re-anchor info stays with implementation (survives compaction)
  - Worker handles: re-anchor → implement → commit → review → complete
  - Main conversation handles task selection and looping only
  - `disallowedTools: Task` prevents infinite subagent nesting
- **Agent colors** - Visual identification in Claude Code UI
  - worker: blue (#3B82F6), repo-scout: green (#22C55E)
  - context-scout: cyan (#06B6D4), practice-scout: yellow (#EAB308)
  - docs-scout: orange (#F97316), memory-scout: purple (#A855F7)
  - flow-gap-analyst: red (#EF4444), quality-auditor: pink (#EC4899)

### Fixed
- **ralph-init efficiency** - Uses `cp -R` instead of read/Write per file
  - Single bash command copies all templates (including dotfiles)
  - Only edits `config.env` for review backend setting
- **Legacy `deps` key migration** - flowctl now handles both `deps` and `depends_on`
  - `normalize_task()` auto-migrates legacy `deps` to `depends_on`
  - Backwards compatible with older task files

## [flow-next 0.10.0] - 2026-01-15

### Added
- **Stdin support** (`--file -`) for flowctl commands
  - `epic set-plan`, `task set-description`, `task set-acceptance` now accept `-` to read from stdin
  - Enables heredoc usage: `flowctl epic set-plan fn-1 --file - <<'EOF'`
  - Eliminates temp file creation, solves shell escaping issues
- **Combined task set-spec command**
  - `flowctl task set-spec <id> --description <file> --acceptance <file>`
  - Sets both sections in single call (2 atomic writes vs 4)
- **Checkpoint commands** for compaction recovery
  - `flowctl checkpoint save --epic <id>` - Snapshots epic + all tasks to `.flow/.checkpoint-<id>.json`
  - `flowctl checkpoint restore --epic <id>` - Restores from checkpoint
  - `flowctl checkpoint delete --epic <id>` - Removes checkpoint file

### Changed
- Updated skill files to use stdin heredocs and `task set-spec` where applicable
- Plan-review workflow now saves checkpoint before review (recovery point)
- Added smoke tests for stdin, set-spec, and checkpoint commands

## [flow-next 0.9.0] - 2026-01-15

### Added
- **Browser automation skill** - Web testing, form filling, screenshots, scraping via agent-browser CLI
  - Core workflow: snapshot → ref-based interaction (@e1, @e2)
  - Progressive disclosure: main skill + debugging/auth/advanced references
  - Triggers on UI verification, doc lookup, baseline capture, e2e testing
- **Bundled Skills** section in README documenting utility skills

### Fixed
- `install-codex.sh` now auto-discovers all skills (was hardcoded, missing 7 skills)

## [flow-next-tui 0.1.2] - 2026-01-14

### Added
- Support for collision-resistant epic IDs (`fn-N-xxx` format)
  - Updated runs.ts receipt/block/epic parsing
  - Added tests for new ID format

### Fixed
- Resolved oxlint warnings (useless escapes, control-regex disable comments)

## [flow-next 0.8.0] - 2026-01-15

### Added
- **Ralph async control** (GH-14)
  - `flowctl status [--json]` - Show epic/task counts + active Ralph runs
  - `flowctl ralph pause/resume/stop/status [--run <id>]` - Control Ralph runs externally
  - Sentinel file mechanism in ralph.sh (PAUSE/STOP files at iteration boundaries)
  - All exit paths in ralph.sh now write `promise=COMPLETE` marker
- **Task reset command**
  - `flowctl task reset <id> [--cascade]` - Reset done/blocked tasks to todo
  - Clears evidence, claim fields, blocked_reason
  - `--cascade` resets dependent tasks in same epic
- **Epic dependency CLI**
  - `flowctl epic add-dep <epic> <dep>` - Add epic-level dependency
  - `flowctl epic rm-dep <epic> <dep>` - Remove epic-level dependency
- **CI tests** for all new async control commands (40 total, +9 new)

### Fixed
- README Troubleshooting: replaced nonexistent `task set` with `task reset`

## [flow-next 0.7.2] - 2026-01-14

### Added
- **Windows/Git Bash support** (GH-35, thanks @VexyCats)
  - Python detection: prefer `python3`, fallback to `python` (common on Windows)
  - Windows platform detection (`IS_WINDOWS` flag in ralph.sh)
  - Auto-generated flowctl wrapper for NTFS exec bit issues
  - Codex stdin-based prompt passing to avoid Windows CLI length limits (~8191 chars)
- **CI workflow** for cross-platform testing (Linux, macOS, Windows)
  - flowctl.py syntax and basic command tests
  - ralph.sh syntax and Python detection tests

### Changed
- `smoke_test.sh` and `ralph_smoke_test.sh` now use dynamic Python detection

## [flow-next 0.7.1] - 2026-01-14

### Added
- **C# symbol support** in flowctl.py (GH-36, thanks @clairernovotny)
  - Symbol extraction for `.cs` files: classes, interfaces, structs, enums, records, methods
  - Added `*.cs` to git grep reference search patterns

## [flow-next 0.7.0] - 2026-01-14

### Added
- **Collision-resistant epic IDs**: New epics use `fn-N-xxx` format with 3-char alphanumeric suffix
  - Prevents ID collisions when team members create epics simultaneously
  - Cryptographically secure suffix using Python `secrets` module
  - Legacy `fn-N` format still supported (backwards compatible)
  - Example: `fn-1-abc`, `fn-42-z9k`, tasks: `fn-1-abc.1`

### Changed
- Updated TUI to parse new ID format in run discovery
- Updated Ralph receipt parsing for new format
- Updated all error messages to mention both `fn-N` and `fn-N-xxx` formats

### Fixed
- **Codex reviews from `/tmp` dirs**: Added `--skip-git-repo-check` to `codex exec` (GH-33)
  - Fixes "not a git repo" errors when reviewing cloned/temp repos
  - Safe: reviews run with read-only sandbox
- **Ralph Ctrl+C handling**: Signal now properly terminates entire process tree
  - Added cleanup trap for SIGINT/SIGTERM in all modes
  - Fixed `timeout --foreground` detection for proper signal propagation

## [flow-next 0.6.3] - 2026-01-13

### Added
- **Spec file input for `/flow-next:work`**: Pass `.md` files directly to create epic and start work
  - `/flow-next:work docs/my-spec.md` creates epic from file, sets plan, creates task, executes
  - Detection order: task ID > epic ID > .md file > idea text
  - No changes to Ralph or existing workflows

## [flow-next-tui 0.1.1] - 2026-01-13

### Added
- **CI/CD workflow**: `.github/workflows/publish-tui.yml`
  - Triggers on push to main (flow-next-tui/**) or workflow_dispatch
  - Test matrix: ubuntu + macos, lint, test, pack-test
  - npm publish with OIDC trusted publishing (no NPM_TOKEN needed)
  - Version detection: only publishes when version differs from npm
- **Bump script**: `scripts/bump.sh` for semver version management
- Screenshot in README (replaces ASCII layout diagram)

### Changed
- README intro now explains what Flow-Next and Ralph are

## [flow-next 0.6.2] - 2026-01-13

### Added
- **TUI documentation**: Ralph docs now include TUI quickstart with screenshot
- TUI links in README and ralph.md

## [flow-next 0.6.1] - 2026-01-12

### Changed
- Ralph now always outputs stream-json to logs (TUI compatibility)
  - `--watch` flag only controls terminal display, not log format
  - Logs always parseable by TUI regardless of watch mode

### Fixed
- Add `--verbose` to quiet mode (required by Claude CLI for `stream-json` + `--print`)
  - Without this, quiet mode errored: "output-format=stream-json requires --verbose"
- Skip artifact files in `.flow/tasks/` that don't have `id` field (GH-21)
  - Prevents `KeyError` crash when Claude writes temp files like `fn-1.1-evidence.json`
  - Affects: `next`, `list`, `ready`, `show`, `validate` commands
- Ralph now exports `FLOW_REVIEW_BACKEND` based on `PLAN_REVIEW`/`WORK_REVIEW`
  - Skills inside Claude now see consistent backend config
  - Previously skills would re-detect and potentially choose different backend

## [flow-next 0.6.0] - 2026-01-12

### Added
- **Watch mode**: `--watch` flag streams tool calls in real-time with TUI styling (icons, colors)
- **Watch verbose**: `--watch verbose` also streams model text responses
- `watch-filter.py` for stream-json parsing (fail-open pattern, drains stdin on error)
- **Review feedback in receipts**: Codex plan/impl review receipts now include `review` field with full feedback (enables fix loops)
- `FLOW_RALPH_CLAUDE_PLUGIN_DIR` env var for testing with local dev plugin

### Changed
- Codex exec timeout increased 300s → 600s (matches RP timeout)
- Stream-json text extraction for reliable tag parsing in watch mode
- Conditional signal trap (only in watch mode)

### Fixed
- Improved Ctrl+C signal handling in watch mode

## [flow-next 0.5.9] - 2026-01-11

### Fixed
- Worker timeout now triggers retry instead of failing entire Ralph run
- macOS compatibility: detect `timeout`/`gtimeout`, warn if missing
- Python 3.9 compat: use `Optional[int]` not `int|None`

### Changed
- RP timeout configurable via `FLOW_RP_TIMEOUT` env (default 1200s/20min)
- Increased default timeout from 600s to 1200s for large repo context builders

## [flow-next 0.5.8] - 2026-01-11

### Added
- Context gathering prompt for Codex reviews (cross-boundary checks, related patterns)
- Rust, C/C++, Java symbol extraction in `gather_context_hints`
- Extended `find_references` to search `.rs`, `.c`, `.h`, `.cpp`, `.hpp`, `.java` files

### Changed
- Mark flow plugin as legacy with clearer messaging
- Wrap `extract_symbols_from_file` in try/except for graceful failure

## [flow-next 0.5.7] - 2026-01-11

### Changed
- Removed "Experimental" label - flow-next is production-ready
- Updated callouts to show feature maturity (not "New" on old features)
- Moved YOLO warning before Ralph setup section
- Improved safety warning format (bullet points)

### Added
- "vs Anthropic's ralph-wiggum" comparison section explaining architectural differences
- Plain-English re-anchoring explanation in "Why It Works"
- "How to Start" recommended workflow (spec -> interview -> plan -> work)
- Use-case matrix for choosing workflow (manual, review, autonomous)
- "Auto-blocks stuck tasks" feature to features list
- Troubleshooting section with common issues and fixes
- `ralph_once.sh` test step in Ralph Quick Start
- Verdict format documentation (SHIP, NEEDS_WORK, MAJOR_RETHINK)
- Partial run handling in morning review workflow
- Review criteria summary table (plan vs implementation)

### Fixed
- Clarified `/flow-next:setup` benefits with concrete examples
- Removed duplicate "Agents that finish what they start" tagline
- Updated repo description and topics via `gh repo edit`

## [flow-next 0.5.6] - 2026-01-11

### Fixed
- `ralph-init` now detects Codex CLI as fallback (was rp-cli only, defaulted to `none`)
- `ralph-init` asks user to choose if both RepoPrompt and Codex available
- Replace `--mode` with `--review` in all review prompts for consistency
- Review skills (plan-review, impl-review) now parse `--review` argument

### Changed
- Backend selection priority: `--review` arg > env > config > auto-detect

## [flow-next 0.5.5] - 2026-01-11

### Fixed
- Ralph no longer fails on non-zero exit code when task actually succeeded (#11)
- Checks both `task_status=done` and `verdict=SHIP` before treating exit code as failure
- Prevents false failures from transient errors (telemetry, model fallback, etc.)

### Added
- Smoke tests for non-zero exit code handling

### Chores
- ruff format on Python files

## [flow-next 0.5.4] - 2026-01-11

### Fixed
- Remove hardcoded `model: claude-opus-4-5-20251101` from review skills (#9)
- Skills now inherit session's default model, fixing 404 on limited API endpoints

## [flow-next 0.5.3] - 2026-01-11

### Fixed
- plan/work skills skip review question when backend already configured or in Ralph mode
- Checks `FLOW_REVIEW_BACKEND` env and `.flow/config.json` before prompting

## [flow-next 0.5.2] - 2026-01-11

### Fixed
- plan-review and impl-review skills now ask which backend when both available (interactive mode)
- Only prompts when not in Ralph mode (`FLOW_RALPH` not set)

## [flow-next 0.5.1] - 2026-01-11

### Added
- Codex option in plan/work skill setup questions (was missing from interactive flow)

### Fixed
- Plan and work skills now ask about Codex backend when available (not just RepoPrompt)
- Backend detection checks for both `codex` and `rp-cli` availability

## [flow-next 0.5.0] - 2026-01-11

### Added
- **Codex review backend** — cross-platform alternative to RepoPrompt (#5)
  - `flowctl codex plan-review` and `flowctl codex impl-review` commands
  - Uses GPT 5.2 High by default (no user config needed)
  - Session continuity via thread IDs in receipts
  - Context hints from changed files (symbols + references)
  - Same Carmack-level review criteria as RepoPrompt (7 plan + 7 impl)
- Backend selection: `flowctl config set review.backend codex` or `FLOW_REVIEW_BACKEND` env
- Comprehensive smoke tests for codex commands and context hints

### Changed
- Plan review prompts now use plan-specific criteria (was using impl-style criteria)
- Docs recommend RepoPrompt when available, codex as cross-platform alternative

## [flow-next 0.4.3] - 2026-01-11

### Fixed
- Stop hook no longer blocks when `PLAN_REVIEW=none` and `WORK_REVIEW=none` (#8)
- `REVIEW_RECEIPT_PATH` only exported when review is enabled
- Smoke test `write_config()` now properly updates PLAN_REVIEW/WORK_REVIEW on subsequent calls

## [flow-next 0.4.2] - 2026-01-11

### Fixed
- `flowctl done` now stores evidence in task JSON metadata (was only in markdown spec)
- Evidence accessible via `flowctl show <task> --json | jq '.evidence'`

## [flow-next 0.4.1] - 2026-01-11

### Added
- Hook enforcement: `flowctl done` now requires `--evidence-json` and `--summary-file` flags
- Morning review workflow guide in ralph.md

### Fixed
- Evidence field was empty because Claude drifted and skipped --evidence-json flag

## [flow-next 0.4.0] - 2026-01-11

### Changed
- **BREAKING**: `BRANCH_MODE=new` now creates a single run branch (`ralph-<run-id>`) instead of per-epic branches
- All epics work on the same run branch, making cherry-pick/revert of individual epics easy
- branches.json format simplified: `{base_branch, run_branch}` instead of epic mappings

### Fixed
- Fixed duplicate plan reviews when working on multiple epics (stale `.flow/` state across branches)

## [flow-next 0.3.22] - 2026-01-11

### Fixed
- Hook now tracks `flowctl done` with path/variable invocations ($FLOWCTL, .flow/bin/flowctl)

## [flow-next 0.3.21] - 2026-01-11

### Fixed
- ralph-init skill now explicitly tells user to run scripts from terminal

## [flow-next 0.3.20] - 2026-01-11

### Fixed
- Clarified Ralph docs: run scripts from terminal, not inside Claude Code

## [flow-next 0.3.19] - 2026-01-11

### Changed
- Removed verdict display from Ralph UI (too brittle, interfered with prompting)

### Fixed
- Added important notice to e2e notes about uninstalling marketplace plugins before dev testing

## [flow-next 0.3.18] - 2026-01-10

### Added
- `/flow-next:uninstall` command - removes flow-next from project with option to keep tasks
- Ralph UI improvements: elapsed time, progress counters, task titles, git stats, review stats
- `/flow-next:setup` now asks about GitHub starring

### Changed
- Quick start docs now promote `/flow-next:setup` as recommended step

## [flow-next 0.3.17] - 2026-01-10

### Added
- Memory system for persistent learning (opt-in via `flowctl config set memory.enabled true`)
- `flowctl config get/set` commands for project settings
- `flowctl memory init/add/list/search` commands for memory management
- `memory-scout` subagent for retrieving relevant memories during plan/work
- Auto-capture of review feedback to pitfalls.md (Ralph mode only)

### Fixed
- Re-review prompt now instructs reviewer to verify actual code, not just trust summary

## [flow 0.8.4] - 2026-01-10

### Fixed
- Removed incorrect `selected_paths` requirement for re-reviews (files auto-refresh)
- Re-review prompt now instructs reviewer to verify actual code, not just trust summary

## [flow-next 0.3.16] - 2026-01-10

### Changed
- `flowctl epic create` now defaults `branch_name` to epic ID if not specified

## [flow-next 0.3.15] - 2026-01-09

### Changed
- `/flow-next:setup` now detects doc status (missing/current/outdated) before asking
- Only prompts for files that actually need updates

## [flow-next 0.3.14] - 2026-01-09

### Added
- `flowctl list` command - shows all epics with tasks grouped, human-readable + JSON

## [flow-next 0.3.13] - 2026-01-09

### Added
- `flowctl epics` command - list all epics with task counts/progress
- `flowctl tasks` command - list tasks with `--epic` and `--status` filters

### Changed
- Removed misleading `list`/`ls` aliases from `show` command
- Updated all docs to reference new `epics`/`tasks` commands
- Added cross-references between human docs (flowctl.md) and agent docs (usage.md)
- File structure in docs now shows optional `/flow-next:setup` files

## [flow-next 0.3.12] - 2026-01-09

### Changed
- Optimized `/flow-next:setup` to minimize context footprint
  - CLAUDE.md snippet now minimal (~20 lines) with rules + quick commands
  - Full reference moved to `.flow/usage.md` (loaded on demand)
  - Added `<!-- BEGIN/END FLOW-NEXT -->` delimiters for idempotent updates

## [flow-next 0.3.11] - 2026-01-09

### Changed
- Expanded CLAUDE.md/AGENTS.md template with file structure, workflow, and rules
- Improved `flow-next` skill trigger phrases ("show me my tasks", "list epics", etc.)

## [flow-next 0.3.10] - 2026-01-09

### Fixed
- Clarified `/flow-next:setup` idempotency for existing `.flow/` directories
  - Safe to re-run; preserves existing epics/tasks
  - Clear version comparison logic for updates

## [flow-next 0.3.9] - 2026-01-09

### Added
- **`flow-next` skill**: General task management skill for quick operations
  - Triggers on: "add task", "show tasks", "what's ready", etc.
  - Provides flowctl path setup and CLI quick reference
  - Prevents agents from struggling to find/use flowctl
- **`/flow-next:setup` command**: Optional local install for power users
  - Copies flowctl scripts to `.flow/bin/` for CLI access
  - Adds flow-next instructions to CLAUDE.md or AGENTS.md
  - Enables use in non-Claude-Code environments (Codex, Cursor, etc.)
  - Tracks setup version for update detection
  - **Fully optional** - standard plugin usage works without this

### Notes
- Setup is opt-in only; flow-next continues to work via plugin as before
- Re-run `/flow-next:setup` after plugin updates to refresh local scripts

## [flow-next 0.3.7] - 2026-01-09

### Ralph: Autonomous Coding with Multi-Model Review Gates

This release introduces **Ralph**, a production-ready autonomous coding loop that goes beyond simple "code until tests pass" agents. Ralph implements **multi-model review gates** using [RepoPrompt](https://repoprompt.com/?atp=KJbuL4) to send your plans and implementations to a different AI model for review.

**Why Ralph is different:**

- **Two-model review**: Your code is reviewed by a separate model (we recommend GPT-5.2 High), catching blind spots that self-review misses
- **Review loops until SHIP**: No "LGTM with nits" that get ignored—reviews block progress until the reviewer returns `<verdict>SHIP</verdict>`
- **Receipt-based gating**: Every review must produce a receipt proving it ran. No receipt = no progress. This prevents the agent from skipping steps
- **Guard hooks**: Deterministic enforcement of workflow rules—the agent can't drift from the prescribed flow

**Getting started:**

```bash
/flow-next:ralph-init    # Set up Ralph in your repo
scripts/ralph/ralph.sh   # Run the autonomous loop
```

See the [Ralph documentation](plugins/flow-next/docs/ralph.md) for the full guide.

### Technical Details

**Guard hooks** (only active when `FLOW_RALPH=1`):
- Block impl receipts unless `flowctl done` was called
- Block receipts missing required `id` field
- Warn on informal approvals without verdict tags
- Zero impact for non-Ralph users

**Autonomous mode system prompt** ensures the agent follows instructions precisely when running unattended.

---

### Internal changes (0.2.1 → 0.3.7)

<details>
<summary>Click to expand development history</summary>

#### 0.2.8 - Unreleased
- Enforce numeric RepoPrompt window selection + validation before builder
- Clarify builder requires `--window` + `--summary`; no names/ids
- Update plan/impl review rp-cli references + workflow guidance

#### 0.2.7 - Unreleased
- Add epic `branch_name` field + `flowctl epic set-branch` command
- Ralph now writes run-local `progress.txt` per iteration
- Plan guidance enforces one-iteration task sizing and sets epic branch_name
- Work flow requires tests/Quick commands green before impl review

#### 0.2.6 - Unreleased
- Add flowctl rp wrappers; remove direct rp-cli usage in review workflows
- Add skill-scoped Ralph hooks (guard + receipt + optional verbose log)
- Update review skills/commands/docs to use wrappers + Claude Code 2.1.0+ note

#### 0.2.5 - Unreleased
- Align rp-cli refs + option text to `call chat_send` (no rp-cli chat)
- Ralph work prompt no longer double-calls impl review; receipts always any verdict
- Window switch uses git root + explicit -w; add jq + tab rebind guidance
- Docs clarify receipt gating + Ralph mode bans rp-cli chat/codemap/slice

#### 0.2.4 - Unreleased
- Added Ralph-mode rule blocks to plan/impl review + work skills
- Ralph prompts now restate anti-drift rules
- Ralph sets `RALPH_MODE=1` for stricter skill behavior

#### 0.2.3 - Unreleased
- /flow-next:work now hard-requires flowctl done + task status check before commit
- Work workflow requires git add -A (no file lists) to include .flow + ralph artifacts
- Review skills now RETRY if rp-cli chat/codemap/slice are used (enforce call chat_send)
- Ralph forces retry if task status is not done after work iteration

#### 0.2.2 - Unreleased
- Plan/impl review skills now mandate receipt write when `REVIEW_RECEIPT_PATH` is set
- Plan-review guidance now pins correct flowctl command for status updates
- Ralph loop logs per-iteration status, mode, receipt checks
- Flow-next docs add Ralph deep dive and receipt notes

#### 0.2.1 - Unreleased
- Plan/impl review workflows now auto-select RepoPrompt window by repo root
- Review workflows write receipts only when `REVIEW_RECEIPT_PATH` is set
- `plan-review` and `impl-review` command stubs trimmed to route to skills

</details>

## [flow-next 0.2.0] - 2026-01-07

### Added
- **Autonomous mode flags**: All commands now accept flags to bypass interactive questions
  ```bash
  # Interactive (asks questions)
  /flow-next:plan Add caching
  /flow-next:work fn-1

  # Autonomous (flags)
  /flow-next:plan Add caching --research=grep --no-review
  /flow-next:work fn-1 --branch=current --no-review

  # Autonomous (natural language)
  /flow-next:plan Add caching, use context-scout, skip review
  /flow-next:work fn-1 current branch, no review
  ```
  - `/flow-next:plan`: `--research=rp|grep`, `--review=rp|export|none`, `--no-review`
  - `/flow-next:work`: `--branch=current|new|worktree`, `--review=rp|export|none`, `--no-review`
  - `/flow-next:plan-review`: `--mode=rp|export`
  - `/flow-next:impl-review`: `--mode=rp|export`
- Natural language parsing also works ("use context-scout", "skip review", "current branch")
- First step toward fully autonomous Flow-Next operation

### Fixed
- Homepage URL now points to `/apps/flow-next` instead of `/apps/flow`

## [0.8.2] - 2026-01-06

### Changed
- **Re-review messages now require detailed fix explanations**
  - Template includes: what was wrong → what changed → why that approach
  - Plan reviews: section changes summary, trade-offs acknowledged
  - Impl reviews: file-by-file changes summary, architectural decisions
  - Helps reviewer understand HOW fixes were made, not just "trust me"
- **Fixed linebreak escaping in re-review messages**
  - Use raw `call chat_send` with JSON for multi-line messages
  - Bash single quotes don't interpret `\n` - now documented
- Added "Why detailed re-review messages?" explanation to both workflows

## [0.8.1] - 2026-01-06

### Changed
- **RepoPrompt v1.5.62+ now required** for review features
  - New `-t` flag for direct tab targeting (cleaner than `workspace tab` chaining)
  - Progress notifications during builder/chat execution
  - Updated all rp-cli references and examples
- **Re-review loop clarified**: Skip builder on re-reviews—discovery is done
  - Chat already has full context from initial review
  - Just augment selection with any files touched during fixes
  - Continue existing chat, don't start fresh
- Added "Why skip builder on re-reviews?" explanation to both workflows
- Downgrade path: `flow@0.8.0` for users on older RepoPrompt versions

## [0.8.0] - 2026-01-05

### Changed
- **Review workflows now use "Context Over Convenience" approach**
  - Builder prompt simplified to intent only (e.g., "Review implementation of OAuth on current branch")
  - No longer stuffs builder with file lists or module details—let Builder discover context
  - Builder's handoff prompt becomes foundation; review criteria added on top (not replaced)
  - Explicit step to capture and reuse Builder's handoff prompt via `prompt get`
- **New philosophy section** at top of both workflow files
  - Introduces "RepoPrompt's Context Builder" once, then refers to it as "Builder"
- **New anti-patterns**: "Stuffing builder prompt", "Ignoring builder's handoff prompt"
- Phase 1 now composes concise summary (flexible: 1-2 sentences for simple, paragraph for complex epics)
- Phase 2/3 renamed to "Context Discovery & Selection" with clearer 4-step process:
  1. Run builder with intent
  2. Capture handoff prompt
  3. Review and augment selection
  4. Verify final selection
- Builder wait warning now explicitly says "do NOT send another builder command"
- Review criteria condensed (same content, fewer tokens)

### Why This Change
Builder is AI-powered—its strength is discovering related patterns, architectural context, and dependencies the reviewer needs. We already know the changed files/plan file; Builder's job is finding surrounding context. Previous approach was too prescriptive.

## [0.7.7] - 2026-01-04

### Changed
- Renamed `interview` skill to `flow-interview` (pattern consistency)
- Extracted question categories to `questions.md` (like `flow-work` has `phases.md`)
- SKILL.md now references `questions.md` for interview guidelines

## [0.7.6] - 2026-01-03

### Fixed
- Stronger AskUserQuestion requirement with anti-pattern example

## [0.7.5] - 2026-01-03

### Fixed
- Interview skill now explicitly requires AskUserQuestion tool (was outputting questions as text)

## [0.7.4] - 2026-01-03

### Added
- `/flow:interview` command + `interview` skill
  - Deep interview about a spec/bead (40+ questions for complex features)
  - Accepts beads ID or file path
  - Writes refined spec back to source
  - Optional step before `/flow:plan` for thorough requirements gathering

## [0.7.3] - 2026-01-02

### Added
- Codex CLI install script (`scripts/install-codex.sh`)
  - Copies skills and prompts to `~/.codex/`
  - Note: subagents won't run (Codex limitation), core flow still works

## [0.7.2] - 2026-01-02

### Changed
- Review skills now check conversation context before asking mode question
  - If mode already chosen in `/flow:plan` or `/flow:work` setup → use it, don't ask again
  - Only asks when invoked directly without prior context

## [0.7.1] - 2026-01-02

### Changed
- Clarified review mode question: both modes use RepoPrompt for context building, difference is where review happens

## [0.7.0] - 2026-01-01

### Added
- **Export for external review**: Review skills now offer export mode for ChatGPT Pro, Claude web, etc.
  - `/flow:plan` and `/flow:work` setup questions now have 3 review options:
    - `a) Yes, RepoPrompt chat` (default)
    - `b) Yes, export for external LLM`
    - `c) No`
  - Direct `/flow:impl-review` and `/flow:plan-review` ask upfront which mode to use
  - Export mode: same context building, exports to `~/Desktop/` and opens file
  - Uses new RepoPrompt 1.5.61 `prompt export` command

### Changed
- Updated rp-cli references for RepoPrompt 1.5.61:
  - `workspace tabs` shorthand (replaces verbose `call manage_workspaces`)
  - `workspace tab "name"` shorthand for tab selection
  - `prompt export /path.md` for full context export
  - Workflow shorthand flags (`--export-prompt`, `--export-context`)
  - Note: chats are now bound to compose tabs

## [0.6.5] - 2025-12-31

### Fixed
- Remove "Top 3 changes" from review output format
  - Agents were only fixing top 3 instead of ALL Critical/Major/Minor issues
  - Added explicit instruction: list ALL issues, agent will fix all of them
  - Applies to both plan-review and impl-review workflows

## [0.6.4] - 2025-12-31

### Fixed
- Clarified valid reasons to skip a fix in reviews:
  - Reviewer lacked context (missed constraint/related code)
  - Reviewer misunderstood requirement/intent
  - Fix would break something else
  - Conflicts with established patterns
  - Must explain reasoning in re-review message

## [0.6.3] - 2025-12-30

### Fixed
- Strengthened fix-and-re-review loop to require fixing Minor issues
  - Explicit: Critical/Major/Minor MUST be fixed, only Nitpick is optional
  - Added anti-pattern: "Skipping Minor issues"
  - Updated both plan-review and impl-review workflows

## [0.6.2] - 2025-12-30

### Fixed
- Clarified JSON escaping for chat_send in review workflows
  - Message must use `\n` for newlines, not literal line breaks
  - Removed broken heredoc pattern that caused JSON parse errors
  - Added note to keep message concise (chat sees selected files)

## [0.6.1] - 2025-12-30

### Fixed
- Added fix-and-re-review loop to plan/impl review workflows
  - Agents were documenting issues instead of fixing them during re-review
  - Now explicitly instructs to implement all fixes directly
  - Escape hatch for genuine disagreements preserved
  - Updated anti-patterns to flag "documenting instead of fixing"

## [0.6.1] - 2025-12-30

### Added
- Tab isolation docs for parallel agents using rp-cli (#3)
  - `builder` auto-creates isolated compose tabs
  - Chain commands to maintain tab context: `builder "..." && select add && chat`
  - Rebind by tab name for separate invocations
  - Updated: flow-plan-review, flow-impl-review workflows
  - Updated: context-scout agent, rp-explorer skill

## [0.5.16] - 2025-12-29

### Fixed
- Fixed new chat creation in reviews (shorthand `--new-chat` is broken in rp-cli)
  - Initial review now uses `call chat_send {"new_chat": true, ...}` (works)
  - Re-review uses shorthand `chat "..." --mode chat` (continues existing)
  - Updated both workflow.md and rp-cli-reference.md files

## [0.5.15] - 2025-12-29

### Fixed
- Made review-fix-review loop fully automated (no human gates)
  - flow-work Phase 7: explicit "do NOT ask for confirmation"
  - flow-plan Step 5: same fix
  - Removed "ask before closing final tasks" ambiguity
  - Reviews now auto-fix and re-run until "Ship"

## [0.5.14] - 2025-12-29

### Fixed
- Removed redundant "Go ahead to start?" confirmation in flow-work
  - User already consented via setup questions
  - Only ask if something is actually unclear or blocking

## [0.5.13] - 2025-12-29

### Changed
- Replaced AskUserQuestion with text-based questions in flow-plan and flow-work
  - Better for voice dictation users
  - Supports terse replies ("1a 2b") and natural language rambling
  - All questions visible at once
  - Explicit "do NOT use AskUserQuestion tool" instruction

## [0.5.12] - 2025-12-29

### Added
- Issue quality guidelines in review prompts (inspired by OpenAI Codex)
  - impl-review: only flag issues **introduced by this change**
  - Both: cite **actual affected code** (no speculation)
  - Both: specify **trigger conditions** (inputs, edge cases)

## [0.5.11] - 2025-12-29

### Fixed
- Restructured chat command examples so `--new-chat` flags aren't buried

## [0.6.1] - 2025-12-29

### Added
- Chat session targeting for re-reviews
  - `chats list` → get chat IDs and names
  - `--chat-id <id>` → continue specific chat

## [0.5.9] - 2025-12-29

### Fixed
- Clarified new-chat behavior in review workflows

## [0.5.8] - 2025-12-29

### Fixed
- Added prominent "CRITICAL" instruction for chat management in review workflows

## [0.5.7] - 2025-12-29

### Changed
- Merged redundant verify phases in review workflows
  - `flow-plan-review`: Phase 2+3 → "Build Context & Verify Selection"
  - `flow-impl-review`: Phase 3+4 → "Build Context & Verify Selection"
  - Agent now adds all supporting docs found in earlier phases after builder runs
  - Eliminates duplicate "check for PRD" instructions

## [0.5.6] - 2025-12-29

### Changed
- Improved skill descriptions to explicitly mention Beads issue ID support
  - `flow-plan`: now triggers on issue IDs (e.g., bd-123, gno-45)
  - `flow-work`: now triggers on epic/issue IDs for execution

## [0.5.4] - 2025-12-28

### Added
- **New skill: `rp-explorer`** - Token-efficient codebase exploration via rp-cli
  - Deliberate activation: triggers on "use rp", "use repoprompt", explicit requests
  - Includes full rp-cli command reference (progressive disclosure)

### Changed
- `/flow:plan` now asks two setup questions when rp-cli detected:
  - Q1: Research approach (context-scout vs repo-scout)
  - Q2: Auto-review preference
- Updated README with comparison table and SETUP phase diagram

## [0.5.3] - 2025-12-28

### Changed
- Documented cross-model review benefit (GPT-5.2 High, o3 for validation)

## [0.5.2] - 2025-12-28

### Added
- **New agent: `context-scout`** - Token-efficient codebase exploration using RepoPrompt's rp-cli
  - Uses `structure` for code signatures (10x fewer tokens than full files)
  - Uses `builder` for AI-powered file discovery
  - Comprehensive workflow: window setup → explore → summarize

### Changed
- **Improved all 6 agents** with proper configuration and detailed prompts:
  - Added `tools` field - each agent now has only the tools it needs
  - Added `model` field - scouts use `haiku` (fast), analysts use `sonnet` (reasoning)
  - Detailed search/analysis methodologies
  - Structured output formats for consistent, actionable results
  - Clear rules on what to focus on and what to skip

### Technical
- All 6 agents use opus model with full research toolkit: Read/Grep/Glob/Bash/WebSearch/WebFetch
- Explicitly excludes Edit/Write (read-only), Task (no sub-agents), TodoWrite/AskUserQuestion (parent manages)

## [0.5.0] - 2025-12-28

### Added
- **Auto-offer review**: Both `flow-plan` and `flow-work` now detect if rp-cli is installed and offer Carmack-level review
  - `flow-plan`: After writing plan, offers `/flow:plan-review` before next steps
  - `flow-work`: After shipping, offers `/flow:impl-review` with fix-and-iterate loop
- Eliminates need for manual chaining like "then review with /flow:impl-review"

### Changed
- `flow-work`: Branch setup question now in SKILL.md (first thing shown, cannot be skipped)
- Explicit examples of chained instructions in skill inputs

### Fixed
- Review commands now have explicit wait instructions for rp-cli chat responses (1-5+ min timeout)

## [0.4.0] - 2025-12-27

### Added
- **Beads integration**: Optional Beads (`bd`) support for flow skills
  - `flow-plan`: Can create Beads epics/tasks instead of markdown plans
  - `flow-work`: Can accept Beads IDs/titles, track via `bd ready`/`bd update`/`bd close`
  - `flow-plan-review`: Can accept Beads IDs/titles as input
  - `flow-impl-review`: Looks for Beads context during code review
- Graceful fallback to markdown/TodoWrite when `bd` unavailable
- Context recovery guidance per Anthropic's long-running agent best practices

### Technical
- Agent-first design: no rigid detection gates, uses judgment based on context
- Validated against bd v0.38.0
- CLI behavior documented in plan (ID formats, parent linking, scoped ready)

## [0.3.7] - 2024-12-27

### Added
- `/flow:plan-review` command: Carmack-level plan review via rp-cli context builder + chat
- `/flow:impl-review` command: Carmack-level implementation review of current branch changes
- `flow-plan-review` skill: progressive disclosure with workflow.md + rp-cli-reference.md
- `flow-impl-review` skill: progressive disclosure with workflow.md + rp-cli-reference.md

### Technical
- Both review skills use rp-cli for context building and chat-based review
- Shared rp-cli-reference.md for CLI command reference
- Commands are thin wrappers (~15 lines) invoking skills

## [0.2.3] - 2024-12-27

### Fixed
- Use "subagent" terminology consistently (official Claude Code term)

## [0.2.2] - 2024-12-27

### Fixed
- Use namespaced agent names (`flow:repo-scout`, `flow:practice-scout`, etc.) in skill reference files
- Make workflow file references directive ("Read and follow" instead of passive links)

## [0.2.1] - 2024-12-27

### Changed
- **Progressive disclosure for Skills**: SKILL.md files now contain only overview + links to reference files
- `flow-plan`: 117 → 30 lines in SKILL.md, detailed steps moved to `steps.md` and `examples.md`
- `flow-work`: 95 → 27 lines in SKILL.md, phases moved to `phases.md`
- Context usage reduced: ~100-150 tokens per skill at startup instead of 400-700

## [0.2.0] - 2024-12-27

### Added
- `flow-plan` skill: planning workflow logic extracted from command
- `flow-work` skill: execution workflow logic extracted from command

### Changed
- **Commands → Skills refactor**: `/flow:plan` and `/flow:work` are now thin wrappers (~15 lines each) that invoke Skills
- Skills enable auto-triggering based on description matching (e.g., "plan out adding OAuth" triggers `flow-plan`)
- Updated manifests: 1 skill → 3 skills

### Technical
- Commands reduced from ~2.1k and ~2.4k tokens to ~36 and ~38 tokens
- Full logic loads on-demand when skill is triggered

## [0.1.1] - 2024-12-26

### Changed
- Moved commands to `commands/flow/` subdirectory for prefixed naming (`/flow:plan`, `/flow:work`)
- Renamed commands for clarity
- Updated argument hints

### Added
- Semver bump script for version management

## [0.1.0] - 2024-12-26

### Added
- Initial release of Flow plugin
- `/flow:plan` command: research + produce `plans/<slug>.md`
- `/flow:work` command: execute a plan end-to-end
- 5 agents: `repo-scout`, `practice-scout`, `docs-scout`, `flow-gap-analyst`, `quality-auditor`
- `worktree-kit` skill for safe parallel git workspaces
- Issue creation integration (GitHub, Linear, Beads)
- Marketplace structure with plugin manifest
