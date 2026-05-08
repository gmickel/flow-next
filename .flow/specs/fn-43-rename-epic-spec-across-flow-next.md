# Rename epic --> spec across flow-next; release as 1.0.0 with full backward compat

## Goal & Context

flow-next is, in 2026, a spec-driven development system. The whole `prospect --> capture --> interview --> plan --> work --> impl-review --> epic-review --> make-pr` chain is built around a single load-bearing artefact -- the spec at `.flow/specs/<id>.md`. The companion JSON sidecar (`.flow/epics/<id>.json`), the CLI verb (`flowctl epic create`), the `epic-scout` subagent, and the constant "epic" references throughout skills and docs are all Agile/Jira muscle memory left over from when flow-next started life as a task tracker. A spec-driven system that calls its own central unit an "epic" confuses the very thing it is designed to teach.

Renaming `epic --> spec` across the user-facing surface is the single highest-leverage vocabulary cleanup before the project commits to a 1.0 contract. Doing it later means the deprecation surface is bigger, the muscle memory in users is deeper, and the Spec-as-PR / R-ID frozen-at-handover / handover-objects vocabulary just shipped in the teams guide stops making sense ("Spec-as-PR... but the file is in `.flow/epics/`?").

This is the right moment because:
- The teams + spec-driven-development surface just landed (0.42.0 + teams.md). The rename consolidates that vocabulary.
- v1.0.0 is a natural breaking-change window. The deprecation can stay loud and short instead of muted-and-forever.
- 287 `epic` references in `flowctl.py` and 48 doc/skill files -- the longer this waits, the more there is to rewrite.

**Non-goal:** this epic does NOT change the 1:1 spec<-->execution-graph mapping. A future epic may decompose specs from execution graphs (multi-epic specs, spec-only artefacts). That is a structural change with different risk; this rename is purely a *vocabulary + filesystem layout* change, leaving the data model intact.

## Architecture & Data Models

### Naming policy

Replace "epic" with "spec" everywhere a user sees, reads, or types it. The handover-objects framing in `docs/teams.md` already treats the spec as the load-bearing noun; this aligns the implementation with the framing.

| Old surface | New surface | Notes |
|---|---|---|
| `flowctl epic create` | `flowctl spec create` | Alias: `epic` --> `spec` with stderr deprecation |
| `flowctl epic set-plan` | `flowctl spec set-plan` | Same |
| `flowctl epic set-branch` | `flowctl spec set-branch` | Same |
| (no rename) | top-level `flowctl show <id>` | NOT renamed — already inspects both spec ids and task ids |
| `flowctl epic export-cognitive-aid` | `flowctl spec export-cognitive-aid` | Same |
| `flowctl epics` | `flowctl specs` | Same |
| `flowctl tasks --epic <id>` | `flowctl tasks --spec <id>` | `--epic` alias kept |
| `flowctl ready --epic <id>` | `flowctl ready --spec <id>` | `--epic` alias kept |
| `.flow/epics/<id>.json` | `.flow/specs/<id>.json` | Co-located with `.flow/specs/<id>.md` |
| `.flow/meta.json` `next_epic` | `next_spec` | Read both during transition |
| Task JSON `epic` field | `spec` field | Read both during transition |
| `epic-scout` agent | `spec-scout` agent | File renamed |
| `/flow-next:epic-review` skill | **Decision deferred** -- see Decision Context | Three options surfaced |
| `epic-id` argument names in commands | `spec-id` | Aliased |
| Prose mentions of "epic" in skills/docs/READMEs | "spec" | Wholesale rewrite |

The unit `<id>` itself is unchanged -- still `fn-N-<slug>`. R-IDs are unchanged. Task ids `<id>.<M>` are unchanged. Branch names allocated from spec titles are unchanged.

### Backward compatibility layers

Three layers, each with explicit deprecation timeline:

1. **CLI alias layer (mandatory).** `flowctl epic *` continues to work post-1.0. Each invocation emits a one-line stderr warning (`[flow-next] 'flowctl epic' is renamed to 'flowctl spec'; alias remains until 2.0.0. Suppress: FLOW_NO_DEPRECATION=1.`) and dispatches identically. Same for `--epic` flag. Removed in 2.0.

2. **Filesystem migration layer (consented, NEVER silent).** First non-Ralph `flowctl` invocation in a repo whose `.flow/` was created pre-1.0 detects the legacy layout (`.flow/epics/` exists, no `.flow/.flow_version` marker) and prints a loud one-time banner with the flow-swarm carrot, routing the user to two opt-in paths: (a) `/flow-next:setup` upgrade branch (interactive, AskUserQuestion-prompted); (b) `flowctl migrate-rename --yes` (deterministic). Direct `flowctl` CLI invocations get the banner + alias-mode-only -- migration runs ONLY when the user explicitly opts in. The migration itself, when triggered:
   - Backs up `.flow/` --> `.flow/.backup-pre-1.0/` (full copy with `.complete` two-phase marker).
   - Moves `.flow/epics/<id>.json` --> `.flow/specs/<id>.json` (md and json colocated).
   - Rewrites `.flow/meta.json` field names (`next_epic` --> `next_spec`).
   - Rewrites task JSON: `"epic": "..."` --> `"spec": "..."`. (Read code accepts both during transition; write code emits new only.)
   - Writes `.flow/.flow_version` = `1.0.0` LAST (sentinel-last invariant for crash recovery).
   `FLOW_NO_AUTO_MIGRATE=1` suppresses the banner entirely. **No auto-trigger; the banner offers, the user accepts.** See R5, R7, R24.

3. **JSON read-compat layer.** Python parsing accepts both `epic`/`spec` and `epic_id`/`spec_id` field names for at least 1.x. Writing always emits new field names. Same shape extends to top-level JSON output keys (e.g. `flowctl specs --json` payload key) and the cognitive-aid export payload (R31). This catches third-party tooling or mid-migration crash recovery.

### Write-location semantics (cleared up)

A 0.x user upgrading to 1.0 flowctl WITHOUT migrating yet is the load-bearing edge case. Single rule for all write paths:

- **Fresh `flowctl init` post-1.0** -> `.flow/specs/` (md + json) immediately. No `.flow/epics/` directory created.
- **Existing `.flow/.flow_version` sentinel** (migration ran) -> writes go to `.flow/specs/<id>.json`.
- **No sentinel + `.flow/epics/` exists** (alias-mode 0.x repo) -> writes continue to `.flow/epics/<id>.json` (preserves "alias mode = no migration" promise per R5). Reads probe `.flow/specs/` first then fall back to `.flow/epics/` per R33.
- **No sentinel + no `.flow/epics/`** (impossible-but-be-safe) -> writes go to `.flow/specs/`.

This rule eliminates the apparent T1/T2 contradiction: T1 ships `.flow/specs/` writes for fresh repos; T2 layers the conditional fallback for unmigrated 0.x repos so they keep working.

### Migration tool

`flowctl migrate-rename` (also runs as `flowctl migrate-rollback`):
- Idempotent. Detects current state via `.flow/.flow_version`.
- Prints a `--dry-run` plan listing every file move + every JSON field rewrite.
- Default mode requires `--yes` to commit. Auto-migration uses `--yes` implicitly.
- Rollback restores `.flow/.backup-pre-1.0/` and reverts `.flow/.flow_version`.

### Python rename (internal)

Class names, function names, and variable names follow:

| Old identifier | New identifier |
|---|---|
| `cmd_epic_create` | `cmd_spec_create` |
| `cmd_epic_set_plan` | `cmd_spec_set_plan` |
| (no rename) | `cmd_show` (top-level) |
| `cmd_epic_export_cognitive_aid` | `cmd_spec_export_cognitive_aid` |
| `cmd_epic_review` | (deferred -- see Decision Context) |
| `EpicMeta` (or similar) | `SpecMeta` |
| `epic_id` parameter names | `spec_id` |
| `EPIC_DIR` | `SPEC_JSON_DIR` (now equals `.flow/specs/`) |

### Ralph templates

`plugins/flow-next/skills/flow-next-ralph-init/templates/` references `flowctl epic *` in several places. Templates rewritten to `spec`. Existing user installs of Ralph (via `/flow-next:ralph-init` or hand-copied) continue to work via the CLI alias layer. No action required from users until they re-init.

### Codex mirror

`scripts/sync-codex.sh` does name rewrites already (`AskUserQuestion` --> `request_user_input`, etc.). The `epic --> spec` rename is canonical -- no rewrite logic needed in `sync-codex.sh`. Validation block adds a guard: the Codex mirror should not contain `flowctl epic *` references in skill prose (only in the alias-deprecation context where we explicitly mention the legacy name).

## API Contracts

### New CLI surface (canonical)

Every existing `flowctl epic *` sub-subcommand has a corresponding `flowctl spec *` form. The 11 sub-subcommands plus the top-level `flowctl specs` listing:

```
flowctl spec create --title "..." [--json]
flowctl spec set-plan <spec-id> --file - [--json] < heredoc
flowctl spec set-plan-review-status <spec-id> <status> [--json]
flowctl spec set-completion-review-status <spec-id> <status> [--json]
flowctl spec set-branch <spec-id> --branch <name> [--json]
flowctl spec set-title <spec-id> --title "..." [--json]
flowctl spec set-backend <spec-id> [--impl <spec>] [--review <spec>] [--sync <spec>] [--json]
flowctl spec add-dep <spec-id> <dep-spec-id> [--json]
flowctl spec rm-dep <spec-id> <dep-spec-id> [--json]
flowctl spec close <spec-id> [--json]
flowctl spec export-cognitive-aid <spec-id> --base <ref> [--section <name>] [--json]
flowctl specs [--json]                # top-level payload keys: "specs" (canonical) + "epics" (legacy alias) co-emitted in 1.x
flowctl task create --spec <spec-id> --title "..." [--deps ...] [--json]
flowctl tasks --spec <spec-id> [--json]
flowctl ready --spec <spec-id> [--json]
flowctl checkpoint save --spec <spec-id> [--json]
flowctl checkpoint restore --spec <spec-id> [--json]
flowctl validate --spec <spec-id> [--json]
flowctl next --specs-file <path> [--json]
```

**Note:** `flowctl show <id>` is the existing top-level inspector that resolves both spec ids and task ids by inspection -- NOT renamed (no `flowctl spec show` subcommand introduced; the top-level `show` continues to handle spec ids).

### Deprecated CLI surface (alias to canonical, removed in 2.0.0)

Each line below is a thin proxy that dispatches to the same handler as its canonical counterpart and emits a one-line stderr deprecation warning:

```
flowctl epic create     --> flowctl spec create
flowctl epic set-plan   --> flowctl spec set-plan
flowctl epic set-plan-review-status      --> flowctl spec set-plan-review-status
flowctl epic set-completion-review-status --> flowctl spec set-completion-review-status
flowctl epic set-branch --> flowctl spec set-branch
flowctl epic set-title  --> flowctl spec set-title
flowctl epic set-backend --> flowctl spec set-backend
flowctl epic add-dep    --> flowctl spec add-dep
flowctl epic rm-dep     --> flowctl spec rm-dep
flowctl epic close      --> flowctl spec close
flowctl epic export-cognitive-aid --> flowctl spec export-cognitive-aid
flowctl epics           --> flowctl specs
flowctl task create --epic <id>        --> flowctl task create --spec <id>
flowctl tasks --epic <id>              --> flowctl tasks --spec <id>
flowctl ready --epic <id>              --> flowctl ready --spec <id>
flowctl checkpoint save --epic <id>    --> flowctl checkpoint save --spec <id>
flowctl checkpoint restore --epic <id> --> flowctl checkpoint restore --spec <id>
flowctl validate --epic <id>           --> flowctl validate --spec <id>
flowctl next --epics-file <path>       --> flowctl next --specs-file <path>
flowctl <subcmd> --section epic        --> flowctl <subcmd> --section spec   (export-cognitive-aid)
```

Every alias prints stderr deprecation banner unless `FLOW_NO_DEPRECATION=1`.

### Filesystem layout (post-1.0)

```
.flow/
  .flow_version           # NEW: "1.0.0" -- sentinel for migration completion
  meta.json               # next_spec (was next_epic), other fields unchanged
  config.json             # unchanged
  specs/
    fn-1.md               # spec content (already lived here)
    fn-1.json             # spec metadata (was .flow/epics/fn-1.json)
    fn-2.md
    fn-2.json
    ...
  tasks/
    fn-1.1.json           # task metadata; "spec" field replaces "epic"
    fn-1.1.md             # task spec; frontmatter unchanged (no epic/spec field there today)
    fn-1.2.json
    fn-1.2.md
    ...
  prospects/              # unchanged
  memory/                 # unchanged
  review-receipts/        # unchanged (no epic/spec references)
  review-deferred/        # unchanged
  .backup-pre-1.0/        # NEW (only if migration ran): full copy of pre-1.0 .flow/
  bin/flowctl             # unchanged
```

### JSON schema deltas

`.flow/meta.json`: `next_epic` field renamed to `next_spec`. Read accepts both.

`.flow/specs/<id>.json` (was `.flow/epics/<id>.json`): no field name changes. The file just moved.

`.flow/tasks/<id>.<M>.json`: `epic` field renamed to `spec`. Read accepts both for the 1.x line; write emits `spec` only.

## Edge Cases & Constraints

- **In-flight Ralph runs.** A user may upgrade flow-next mid-Ralph-iteration. The alias layer guarantees running scripts continue to function. The migration banner/check is suppressed under `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` (per R5/R7/R9); migration itself is user-triggered only (never auto). Read-compat (R10) and read-path fallback (R33) handle whatever state the directory is in.
- **Multi-developer repos.** Two devs upgrade at different times. Auto-migration is idempotent; the second dev sees `.flow/.flow_version` already at 1.0.0 and skips.
- **Worktrees.** Multiple worktrees share `.flow/`. Migration runs once per repo (sentinel file shared). Concurrent migration is prevented by a `.flow/.migrating` lockfile with PID; concurrent invocation waits up to 30s then errors with a clear message.
- **CI environments.** CI typically runs on a fresh checkout; no migration needed (no pre-1.0 `.flow/`). New repos initialized at 1.0+ get the new layout from the start, no migration.
- **Crash mid-migration.** `_auto_migrate_to_v1` is transactional via the backup -- on exception, restore from `.flow/.backup-pre-1.0/` and retry on next invocation. The sentinel file is the *last* thing written.
- **Read-only filesystems / containers.** Migration that cannot write fails loudly with the rollback instruction; alias layer alone keeps reads functional.
- **User scripts grepping `.flow/epics/`.** Users with shell scripts that hardcode the old path break post-migration. Mitigation: deprecation banner explicitly mentions the path change; release notes provide a sed migration snippet.
- **Existing CLAUDE.md / AGENTS.md in user repos.** These still reference `flowctl epic *` examples. Out of our control. Banner advises a one-time `sed -i 's/flowctl epic /flowctl spec /g' CLAUDE.md` snippet for users who want to clean theirs up.
- **`flowctl epic export-cognitive-aid` JSON consumers.** External tooling parsing the JSON payload -- field names in the payload do not change (the payload's "epic" key, if any, follows the same migration). Verify in fn-43.
- **Discord/community references.** Out of scope; old aliases keep them working.
- **`epic-scout` references in plan-sync code.** Plan-sync agent dispatches `epic-scout` by name. Renaming requires updating dispatch code + agent file + Codex mirror.
- **Test fixtures under `plugins/flow-next/scripts/test_*.sh`.** Smoke tests exercise both old and new CLI paths; existing 0.x fixtures continue to validate the alias layer.

## Acceptance Criteria

- **R1:** All 11 current `flowctl epic *` sub-subcommands exist as canonical `flowctl spec *` forms with identical behavior. Full list: `create`, `set-plan`, `set-plan-review-status`, `set-completion-review-status`, `set-branch`, `set-title`, `set-backend`, `add-dep`, `rm-dep`, `close`, `export-cognitive-aid`. The corresponding alias subcommands (`flowctl epic *`) dispatch to identical handlers per R3. Top-level `flowctl show` remains unchanged (resolves both spec and task ids by inspection; not part of the rename).
- **R2:** `flowctl specs` and `flowctl tasks --spec <id>` and `flowctl ready --spec <id>` exist; the `--epic` flag is aliased.
- **R3:** All `flowctl epic *` subcommands continue to work post-1.0 and dispatch identically; each emits a one-line stderr deprecation warning unless `FLOW_NO_DEPRECATION=1`.
- **R4:** `.flow/specs/<id>.json` is the canonical location for spec metadata (md + json colocated). New repos initialized at 1.0+ get this layout immediately.
- **R5:** Pre-1.0 repos NEVER silently auto-migrate. First non-Ralph `flowctl` invocation in a pre-1.0 repo prints a loud one-time banner with the migration carrot (vocabulary alignment + future flow-swarm compatibility -- migration unlocks the layout flow-swarm will expect) and routes the user to two explicit migration paths: (a) the host-agent skill path `/flow-next:setup` (gains an "upgrade detected" branch that prompts via `AskUserQuestion` for migrate / defer / opt-out); (b) the deterministic CLI path `flowctl migrate-rename --yes`. Banner is suppressed once `.flow/.flow_version` is written. Migration itself (when triggered) is transactional via `.flow/.backup-pre-1.0/` and idempotent via `.flow/.flow_version` sentinel.
- **R6:** `flowctl migrate-rename` runs the migration on demand with `--dry-run` (default) and `--yes`; `flowctl migrate-rollback` restores from backup. Both are idempotent and print a clear plan. **Rollback safety contract:** `migrate-rename` records the migrated file set during forward migration in a top-level migration manifest at `.flow/.migration-manifest` (NOT inside `.flow/.backup-pre-1.0/` -- the backup stays immutable post-`.complete`). On rollback, it refuses to proceed if any `.flow/specs/<id>.json` file exists that was NOT in the manifest (indicates post-migration writes). Override via `flowctl migrate-rollback --yes --force-overwrite-post-migration-changes` (intentionally verbose flag name).
- **R7:** `FLOW_NO_AUTO_MIGRATE=1` suppresses the banner entirely (alias layer carries on; migration runs only when the user explicitly invokes `flowctl migrate-rename` or the `/flow-next:setup` upgrade branch).
- **R8:** Concurrent migration is prevented by `.flow/.migrating` lockfile; second invocation waits up to 30s then errors.
- **R9:** Auto-migration is skipped under `FLOW_RALPH=1` or when `REVIEW_RECEIPT_PATH` is set; alias + read-compat keeps Ralph functional.
- **R10:** Python read code accepts both `epic`/`spec` field names through 1.x; write code emits `spec` only.
- **R11:** `epic-scout` agent renamed to `spec-scout`; all dispatching skills (plan-sync, plan, etc.) updated; agent file moved + Codex mirror rebuilt.
- **R12:** All canonical skills (capture, interview, plan, work, impl-review, epic-review, make-pr, audit, prospect, strategy, sync, plan-sync, ralph-init, etc.) updated to use "spec" prose and new CLI verbs in their workflow markdown.
- **R13:** All canonical agents (worker, pr-comment-resolver, scouts, plan-sync, etc.) updated.
- **R14:** All command markdown files (`plugins/flow-next/commands/flow-next/*.md`) updated.
- **R15:** Plugin README, root README, plugin CLAUDE.md (the documentation block referenced in the plugin), and the project's CLAUDE.md updated.
- **R16:** `docs/teams.md`, `docs/ralph.md`, `docs/flowctl.md` updated.
- **R17:** `.flow/usage.md` and `plugins/flow-next/skills/flow-next-setup/templates/usage.md` updated.
- **R18:** Ralph init templates under `plugins/flow-next/skills/flow-next-ralph-init/templates/` updated; existing Ralph installs continue to work via alias layer.
- **R19:** `scripts/sync-codex.sh` regenerates the Codex mirror cleanly with new prose; validation block guards against accidental `flowctl epic` mentions in canonical (allowed only in deprecation-explanation context).
- **R20:** Smoke tests (`plugins/flow-next/scripts/smoke_test.sh`, `ralph_smoke_test.sh`) cover the new CLI surface AND verify the alias layer still works.
- **R21:** `/flow-next:epic-review` slash command and `flow-next-epic-review` skill renamed to `/flow-next:spec-completion-review` and `flow-next-spec-completion-review` respectively. Skill directory moved (`plugins/flow-next/skills/flow-next-epic-review/` --> `plugins/flow-next/skills/flow-next-spec-completion-review/`). Command markdown moved (`plugins/flow-next/commands/flow-next/epic-review.md` --> `spec-completion-review.md`). Plan-sync, work, and any other dispatching code updated to use the new skill name. A thin redirect command stays at the old path (`commands/flow-next/epic-review.md`) that surfaces a one-line "renamed to spec-completion-review" notice and dispatches; removed in 2.0.0 alongside the CLI aliases. Codex mirror regenerated.
- **R22:** CHANGELOG entry under `[flow-next 1.0.0]` describes the rename, migration, and alias deprecation timeline. Includes a "Migration guide" subsection with the user-facing sed snippet for cleaning up their CLAUDE.md / scripts.
- **R23:** Plugin version bumped to 1.0.0 via `scripts/bump.sh major flow-next`. Marketplace manifests synced. Codex mirror version synced.
- **R24:** A one-time stderr banner on first post-1.0 `flowctl` invocation in a pre-1.0 repo explains what changed (the rename + the new `.flow/specs/*.json` layout), names the carrot (vocabulary alignment + future **flow-swarm** compatibility -- migration unlocks the layout the upcoming flow-swarm will expect), and points to both migration paths: `/flow-next:setup` (interactive, recommended for human-driven sessions) or `flowctl migrate-rename --yes` (deterministic, recommended for scripts / CI). Banner is suppressed once `.flow/.flow_version` is written, OR if `FLOW_NO_AUTO_MIGRATE=1` is set, OR under Ralph (`FLOW_RALPH=1` / `REVIEW_RECEIPT_PATH`).
- **R25:** mickel.tech website (maintainer-only) updated post-merge: (a) every CLI / artefact reference renamed to the new vocabulary (`flowctl spec *`, `.flow/specs/<id>.json`), AND (b) the page lede / hero / metadata description / FAQ copy explicitly add "spec-driven development" framing -- the rename is the trigger, but landing v1.0 is the moment to teach the framing publicly, not just clean up the words. Tracked but not blocking the release.
- **R26:** Existing `.flow/` directories from 0.x line continue to function via either auto-migration or the alias layer; zero breakage for users who do nothing.
- **R27:** All existing skill workflows (interview, plan, work, capture, audit, prospect, etc.) function identically post-rename when invoked from a fresh 1.0+ repo.
- **R28:** A 1.0.0 release announcement (Discord + GitHub release notes) explicitly calls out the rename + the alias deprecation timeline (removed in 2.0.0).
- **R29:** AI-x-SDLC-Starter-Kit (`~/work/AI-x-SDLC-Starter-Kit`) cross-references audited and updated. Concrete known surface: `guides/methodology.md` (the `[8] PR-AS-COGNITIVE-AID` callout names "epic spec with R-IDs" and `flowctl epic export-cognitive-aid`); both prose phrasing and the CLI verb renamed. Other guides referencing flow-next command names (`/flow-next:plan`, `/flow-next:work`, `/flow-next:ralph-init`) are unchanged because slash-command names do not change. The `~/work/AI-x-SDLC-Starter-Kit` repo lives outside this marketplace; its update is a separate PR coordinated post-merge of the rename here. Maintainer-only (per the contributing guide -- external contributors skip this R-ID; Gordon handles).
- **R30:** Deprecation warning is hand-rolled stderr emission (matches existing `_memory_emit_deprecation` pattern at `flowctl.py:5655`), NOT Python 3.13's `argparse.add_parser(deprecated=True)`. Reason: 3.13 is too aggressive a Python floor; users on Ubuntu 22.04 default Python (3.10) and macOS system Python must continue to work. Mechanism: `cmd_epic_*` wrappers call `_emit_rename_deprecation()` then dispatch to `cmd_spec_*`. Suppress via `FLOW_NO_DEPRECATION=1` (consistent with the existing memory-deprecation env var).
- **R31:** All `flowctl --json` payload keys named `"epic"` / `"epics"` renamed to `"spec"` / `"specs"`. Through 1.x, every renamed top-level key is co-emitted alongside its legacy form (canonical first, alias-key duplicating the same value) for back-compat with `jq '.epics'` / `jq '.epic'` scripts. 2.0 drops the alias keys. The full set is determined at implementation time via `grep -n '"epic[s]\?":\|"epic_id":' plugins/flow-next/scripts/flowctl.py` over write paths -- T1 acceptance enumerates them; the known surface includes:
  - `flowctl epic export-cognitive-aid` (renamed to `flowctl spec export-cognitive-aid` per R1) section flag `--section epic` aliased to `--section spec` with stderr deprecation; payload top-level key `"epic"` renamed to `"spec"`.
  - `flowctl specs --json` (canonical) returns `{"success": true, "specs": [...], "epics": [...]}` with both arrays referencing the same data through 1.x.
  - `flowctl tasks --json`, `flowctl ready --json`, `flowctl next --json`, `flowctl validate --json` and any other output emitting `"epic":` or `"epic_id":` field names -- canonical `"spec":` / `"spec_id":` introduced; legacy form co-emitted through 1.x.
  - The make-pr skill workflow prose (`epic.spec_sections.goal_and_context`, `epic.title`, `epic.acceptance_criteria`) updates correspondingly. T7a coordinates with T1.
  - CHANGELOG migration guide explicitly flags these as breaking-when-alias-removed for external tools. Forward-compat recipes: `jq '.specs // .epics'` and `jq '.spec // .epic'` etc.
- **R32:** Migration lockfile uses cross-platform atomic primitive — `os.mkdir(".flow/.migrating")` (atomic on POSIX, NTFS, and SMB; fails with `FileExistsError` if another process holds it) with PID written inside. NOT `fcntl.flock` (POSIX-only — breaks on the Windows smoke matrix added in commit `26bba86`). 30-second wait loop with stale-lock detection (PID dead) before erroring.
- **R33:** Read-path filesystem fallback regardless of sentinel state. All read code paths (top-level `flowctl show`, `flowctl tasks --spec`, internal helpers) probe `.flow/specs/<id>.json` first, fall back to `.flow/epics/<id>.json` if not found. Decoupled from `.flow/.flow_version` sentinel — covers the case where a user manually drags `.flow/epics/` to `.flow/specs/` mid-migration, OR a sentinel exists but a JSON file got moved back, OR a 0.x repo runs 1.0+ flowctl without ever migrating. Write code emits to `.flow/specs/` only when sentinel exists; pre-sentinel writes still go to `.flow/epics/` (preserves "alias mode = no migration" semantics).
- **R34:** Forward-compat downgrade safety. If `.flow/.flow_version` parses to a value `> 1.x` (e.g., user upgrades to 2.0, then downgrades to 1.5), flowctl prints a one-line warning to stderr ("`.flow/` was migrated by a newer flow-next; some features may be unavailable") and exits 0 -- never crashes on unrecognized future sentinel values. Read-compat layer plus filesystem fallback (R33) keep operations functional.
- **R35:** Banner-fatigue suppression. The migration banner (R24) shows ONCE per `.flow/` until either (a) migration runs and `.flow/.flow_version` is written, OR (b) user explicitly acknowledges via `flowctl migrate-rename --dry-run` (which writes `.flow/.banner-acknowledged` with a timestamp), OR (c) `FLOW_NO_AUTO_MIGRATE=1` is set. Repeated invocations within a single session do not re-show the banner (process-level dedup via env-var-on-first-print).
- **R36:** Ralph plumbing rename — `EPICS_FILE` env var → `SPECS_FILE` (alias kept for back-compat); `--epics-file` flag → `--specs-file` (alias kept). `ralph.sh` template updated to write `SPECS_FILE` going forward; existing user `config.env` files with `EPICS_FILE=...` continue to work via alias resolution. Critical: this is user-observable in `scripts/ralph/config.env` files in user repos; alias is mandatory through 2.0.

## Boundaries (NOT in scope)

- Splitting the 1:1 spec<-->epic id mapping. The unit `<id>` retains today's semantics: one id = one spec = one execution graph = one branch (typically). Multi-epic-per-spec or spec-only artefacts are a separate, future epic.
- Changes to R-ID semantics, format, or propagation rules.
- Changes to the memory schema (knowledge / decisions / bug tracks).
- Changes to the prospect, glossary, or strategy artefact paths.
- Changes to `flowctl review-backend`, `flowctl rp`, `flowctl triage-skip`, or any review-subsystem CLI.
- Migration of historical CHANGELOG entries (those reference 0.x epic vocabulary correctly for that era; rewriting them would be revisionist).
- Migration of historical `.flow/specs/<id>.md` content. The spec body in fn-1 says "epic" because it was written when that was the noun. Rewriting historical specs is unbounded scope and provides no user value -- the alias layer keeps the spec readable; re-running `flowctl spec set-plan` to rewrite is a per-user choice.
- Localization of CLI strings or skill workflow text.
- Generic Agile-epic vocabulary in AI-x-SDLC-Starter-Kit guides where "epic" is being used as a generic Agile concept rather than as a flow-next artefact name. Example: `guides/coding-assistants.md` line 100's *"read the parent epic and all sibling tasks"* is a coding-assistant prompt template using "epic" generically; rewriting that to "spec" would force the SDLC starter-kit to teach flow-next vocabulary as if it were universal. Out of scope. Only flow-next-specific surfaces (CLI verbs, artefact paths, the PR-AS-COGNITIVE-AID callout) are renamed in R29.
- **Internal-but-persisted artefacts.** Checkpoint JSON schema at `.flow/.checkpoint-fn-N.json` (`flowctl.py:17880-17904`, with keys `epic_id`/`epic.data`/`epic.spec`) is by-definition transient (auto-deleted on next checkpoint) and never user-visible. Internal field names are NOT renamed in fn-43; they stay as-is. Same boundary applies to other internal-only persisted state.
- **flow-next-tui test fixtures.** `flow-next-tui/test/fixtures/{task,tasks,epic,ready}.json` use the 0.x JSON schema (`"epic": "fn-N"`, `"depends_on_epics": []`). NOT updated in fn-43 -- the read-compat layer (R10) means TUI fixtures can keep using legacy field names through the 1.x line. Updated independently when the TUI is bumped for 1.0 schema; tracked but not blocking.
- **Internal design docs in `plans/`.** Files like `plans/flow-swarm-v2-spec.md` (75 epic refs), `plans/flow-next.md` (63), `plans/ralph.md` (24), `plans/ralph-e2e-notes.md` (17), `plans/readme-polish-v0.5.7.md` (8) are repo-internal *historical design docs* (snapshots of design thinking at write-time), NOT user-shipped documentation. Same boundary as historical CHANGELOG entries (line 209). They keep their 0.x epic vocabulary because they describe what was true when written. The `flow-swarm-v2-spec.md` reference in R5/R24 is a forward-looking carrot, not a back-reference -- the upcoming flow-swarm itself will read the renamed `.flow/specs/` layout regardless of what its own design notes called it during planning.

## Quick commands

```bash
# Smoke: canonical surface works
flowctl spec create --title "Test rename" --json | jq -r '.id'
flowctl specs --json | jq '.specs | length'   # canonical key 'specs' (R31); legacy alias key 'epics' co-emitted in 1.x

# Smoke: alias surface works + emits deprecation
flowctl epic create --title "Test alias" --json 2>&1 >/dev/null | grep -q "renamed to 'flowctl spec'"

# Smoke: migration round-trip
flowctl migrate-rename --dry-run
flowctl migrate-rename --yes
test -f .flow/.flow_version && echo "sentinel written"
flowctl migrate-rollback --yes
test ! -f .flow/.flow_version && echo "rolled back"

# Full smoke + alias smoke + migration smoke
plugins/flow-next/scripts/smoke_test.sh
plugins/flow-next/scripts/alias_smoke.sh
plugins/flow-next/scripts/migration_smoke.sh
```

## Early proof point

Task fn-43.1 (canonical `flowctl spec *` subcommands + Python rename) validates that the rename pattern works without breaking existing behavior. Existing 0.x smoke tests pass against the post-T1 code via the proxy registration; both `flowctl epic *` and `flowctl spec *` dispatch to the same `cmd_spec_*` handlers. If T1 fails -- the rename surface is bigger than estimated, the proxy approach proves untenable, or hidden coupling between `epic`-named identifiers and behavior surfaces -- re-evaluate the task decomposition before continuing with T2 (alias layer) and T3 (migration). The full backward-compat story collapses if T1 cannot land cleanly.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | Canonical `flowctl spec *` subcommands | fn-43-rename-epic-spec-across-flow-next.1 | -- |
| R2  | Canonical `flowctl specs` + `--spec` flag aliases | fn-43-rename-epic-spec-across-flow-next.1 | -- |
| R3  | `flowctl epic *` aliases with stderr deprecation | fn-43-rename-epic-spec-across-flow-next.2 | -- |
| R4  | New repos initialize at `.flow/specs/` | fn-43-rename-epic-spec-across-flow-next.1 | -- |
| R5  | Consented-migrate banner + two paths | fn-43-rename-epic-spec-across-flow-next.3, .4, .10 | T3 = deterministic CLI path; T4 = banner + suppression matrix; T10 = interactive setup-skill upgrade branch |
| R6  | `flowctl migrate-rename` + `migrate-rollback` | fn-43-rename-epic-spec-across-flow-next.3 | -- |
| R7  | `FLOW_NO_AUTO_MIGRATE=1` opt-out | fn-43-rename-epic-spec-across-flow-next.4 | -- |
| R8  | `.flow/.migrating` lockfile | fn-43-rename-epic-spec-across-flow-next.3 | -- |
| R9  | Migration skipped under Ralph | fn-43-rename-epic-spec-across-flow-next.4 | -- |
| R10 | JSON read-compat (`epic`/`spec` field names) | fn-43-rename-epic-spec-across-flow-next.2 | -- |
| R11 | `epic-scout` -> `spec-scout` | fn-43-rename-epic-spec-across-flow-next.5 | -- |
| R12 | All canonical skills updated | fn-43-rename-epic-spec-across-flow-next.6, .7, .8, .9, .10 | -- |
| R13 | All canonical agents updated | fn-43-rename-epic-spec-across-flow-next.5 | -- |
| R14 | All command markdown files updated | fn-43-rename-epic-spec-across-flow-next.11 | -- |
| R15 | Plugin README + root README + CLAUDE.md | fn-43-rename-epic-spec-across-flow-next.12 | -- |
| R16 | docs/teams.md + docs/ralph.md + docs/flowctl.md | fn-43-rename-epic-spec-across-flow-next.13 | -- |
| R17 | `.flow/usage.md` (working copy) + setup templates that regenerate it | fn-43-rename-epic-spec-across-flow-next.10, .12 | T10 owns templates (in flow-next-setup); T12 owns the working `.flow/usage.md` |
| R18 | Ralph init templates updated | fn-43-rename-epic-spec-across-flow-next.9 | -- |
| R19 | sync-codex.sh + R19 validation block + Codex mirror regen | fn-43-rename-epic-spec-across-flow-next.15 | -- |
| R20 | Smoke tests cover new + alias paths | fn-43-rename-epic-spec-across-flow-next.14 | -- |
| R21 | `epic-review` -> `spec-completion-review` | fn-43-rename-epic-spec-across-flow-next.6 | -- |
| R22 | CHANGELOG `[flow-next 1.0.0]` block | fn-43-rename-epic-spec-across-flow-next.15 | -- |
| R23 | Plugin version 1.0.0 + manifest sync | fn-43-rename-epic-spec-across-flow-next.15 | -- |
| R24 | One-time stderr banner with carrot + paths | fn-43-rename-epic-spec-across-flow-next.4, .10 | T4 = the banner emission; T10 = the interactive setup-skill upgrade prompt that the banner routes users to |
| R25 | mickel.tech site (rename + spec-driven framing) | fn-43-rename-epic-spec-across-flow-next.16 | Maintainer-only |
| R26 | Zero-breakage guarantee | fn-43-rename-epic-spec-across-flow-next.1, .2, .3 | Cross-cutting; primarily covered by alias layer (T2) + read-fallback (T2) + migration safety (T3) |
| R27 | All existing skill workflows function identically | fn-43-rename-epic-spec-across-flow-next.14 | Validated via smoke tests |
| R28 | 1.0.0 release announcement (Discord + GitHub) | fn-43-rename-epic-spec-across-flow-next.15 | CHANGELOG block doubles as GH release body; Discord post is operational, not implementation |
| R29 | AI-x-SDLC-Starter-Kit cross-references | fn-43-rename-epic-spec-across-flow-next.16 | Maintainer-only; external repo |
| R30 | Hand-rolled deprecation (NOT Python 3.13's `deprecated=True`) | fn-43-rename-epic-spec-across-flow-next.2 | T1 ships silent argparse aliases; T2 layers the deprecation emission |
| R31 | Cognitive-aid `--section spec` + payload key rename | fn-43-rename-epic-spec-across-flow-next.1, .7 | T1 ships payload key; T7a updates make-pr workflow prose |
| R32 | Cross-platform lockfile (`os.mkdir`, not fcntl) | fn-43-rename-epic-spec-across-flow-next.3 | -- |
| R33 | Read-path filesystem fallback | fn-43-rename-epic-spec-across-flow-next.2 | -- |
| R34 | Forward-compat `.flow_version > 1.x` downgrade safety | fn-43-rename-epic-spec-across-flow-next.4 | -- |
| R35 | Banner-fatigue suppression via `.banner-acknowledged` | fn-43-rename-epic-spec-across-flow-next.4 | -- |
| R36 | `EPICS_FILE` -> `SPECS_FILE` Ralph plumbing rename | fn-43-rename-epic-spec-across-flow-next.2, .9 | T2 alias layer + T8 template rewrite |

## Decision Context

**Three resolved decisions (resolved via `AskUserQuestion` before plan):**

1. **`epic-review` skill name --> `spec-completion-review`.** The skill is the completion gate that runs at end-of-execution-graph (NOT a review of the spec text itself; that is `plan-review`). Renaming to `spec-completion-review` is vocab-aligned with the broader rename and semantically explicit -- "the review that runs when a spec's tasks complete". Tradeoff: longer name, but the vocabulary cost of keeping "epic-review" is higher (it would be the one place "epic" survived past 1.0). Implementation in R21.

2. **Migration trigger --> consented-migrate with carrot.** Pre-1.0 repos never silently auto-migrate. First non-Ralph `flowctl` invocation in a pre-1.0 repo prints a loud one-time banner with the **flow-swarm carrot** (migration unlocks the layout the upcoming flow-swarm will expect), and routes the user to two explicit paths: (a) `/flow-next:setup` upgrade branch (interactive, AskUserQuestion-prompted, recommended for human-driven sessions); (b) `flowctl migrate-rename --yes` (deterministic, recommended for scripts / CI). Direct CLI invocations get the banner + alias mode (no migration) until the user explicitly opts in. `FLOW_NO_AUTO_MIGRATE=1` suppresses the banner. Tradeoff: aliases linger longer than under silent auto-migrate, but the user trust cost of file moves on first invocation is higher than the vocabulary debt. The carrot framing converts a chore into an opt-in upgrade. Implementation in R5, R7, R24.

3. **Alias removal timeline --> soft deadline.** `flowctl epic *` aliases + the `epic-review` redirect command + the JSON read-compat for `epic`/`spec` field names live until 2.0.0 with no fixed schedule. Escalate to a hard deadline only if alias-usage telemetry stays high after ~6 months in 1.x. Tradeoff: 2.0.0 may never come and the aliases linger forever, but the alternative -- pressuring the ecosystem (FlowFactory, flow-next-opencode, user CLAUDE.md docs, Ralph scripts) on an arbitrary schedule -- has worse downstream cost. The deprecation banner does the work the deadline would do. Implementation in R3, R10, R11, R28.

**Data-model decisions already settled (out of scope for fn-43):**

- The `<id>` format (`fn-N-<slug>`) is unchanged. Renaming the *directory* (`epics/` --> `specs/`) is the only filesystem move.
- R-IDs continue to live in spec markdown body, format `**Rn:**`. No changes.
- The 1:1 mapping is preserved. This rename is vocabulary-only at the user-facing surface; the structural conflation discussion (multi-epic-per-spec, spec-only artefacts) is a separate, future epic.

**Cross-product context:**

- **flow-swarm.** Referenced in R5 + R24 + the migration banner copy. flow-swarm is the upcoming companion product that will read `.flow/` directly; aligning the on-disk layout to spec-centric vocabulary in 1.0 is what unlocks compatibility. The carrot framing in the migration banner is honest, not marketing -- the layout literally needs to move before flow-swarm ships against it. Coordination with flow-swarm timing is out of scope for fn-43; the rename ships independently.
