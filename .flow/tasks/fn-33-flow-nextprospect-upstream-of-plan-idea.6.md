---
satisfies: [R8, R10, R13, R14, R17, R19]
---

## Description

End-to-end smoke test for the prospect skill + flowctl subcommands + Ralph-regression verification. Covers every acceptance criterion that's not already covered by unit tests.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/prospect_smoke_test.sh` (new — shell + bash + grep only, no LLM invocations)
- `plugins/flow-next/scripts/smoke_test.sh` (extend — add entries for prospect artifact YAML roundtrip unit hooks)

## Approach

Shell-level smoke test, pattern matches `impl-review_smoke_test.sh` (fn-32.5) — no backend LLM calls, uses synthetic artifacts + flowctl subcommand assertions.

**Test cases:**

1. **Skeleton + slash command registered.** Verify `plugins/flow-next/commands/flow-next/prospect.md` exists, invokes the skill. Verify `plugins/flow-next/skills/flow-next-prospect/SKILL.md` frontmatter is well-formed (no `context: fork`, includes `AskUserQuestion` in allowed tools).

2. **Ralph-block (R8).** Set `FLOW_RALPH=1` + invoke the skill via a dry-run harness; assert exit 2 and no artifact written. Repeat with `REVIEW_RECEIPT_PATH=/tmp/receipt.json` (with the file absent).

3. **Phase 0 resume check.** Seed `.flow/prospects/` with 3 synthetic artifacts: one fresh (<30d), one stale (>30d), one corrupt (malformed frontmatter). Run `flowctl prospect list`:
   - Default lists only the fresh one.
   - `--all` lists all three with correct `status` markers.
   - Corrupt artifact has `status: corrupt` and a reason note (task 4 formats it as `corrupt (<reason>)`; the reason string is one of the canonical values: `no frontmatter block | unparseable date | missing Grounding snapshot section | missing Survivors section | unreadable | empty | missing frontmatter field: <name>`). <!-- Updated by plan-sync: task 4 shipped the reason-string contract as module constants PROSPECT_CORRUPT_* (flowctl.py:4288-4293). Smoke assertion should grep for these literals. -->

4. **Artifact writer (R4, R13).** Call `write_prospect_artifact` + `_prospect_next_id` directly (via a thin Python harness; both ship in task 3 at flowctl.py:4106-4186) twice on the same day with the same slug. Assert: first writes `dx-2026-04-24.md`; second (via `_prospect_next_id`) suffixes to `dx-2026-04-24-2.md`. Both atomic (no `.tmp.*` leftovers). Frontmatter round-trips via `_prospect_parse_frontmatter` (task 4, flowctl.py:4296). Round-trip must preserve optional Phase 2/3 flags `floor_violation: true` and `generation_under_volume: true` when present; task 3's `PROSPECT_FIELD_ORDER` places them after `status` so the smoke test can grep for `^floor_violation: true$` deterministically. Additional shipped invariant: `date` round-trips as a quoted string (`date: "2026-04-24"`) not bare YAML date. <!-- Updated by plan-sync: task 4 shipped _prospect_parse_frontmatter; smoke test uses it directly. -->

5. **Graceful degradation (R17).** Phase 1 grounding harness run against:
   - An ungitted temp dir → snapshot includes `scanned: none (no git)` for the git section.
   - A dir with no `.flow/epics/` → snapshot includes `scanned: none (no open epics)`.
   - A dir with no CHANGELOG.md → snapshot includes `scanned: none (no changelog)`.
   - None of these error.

6. **Promote happy path (R6).** Synthetic artifact with 3 survivors → `flowctl prospect promote <id> --idea 2`. Assert:
   - New epic created (verify `.flow/epics/<new-id>.json` exists).
   - Epic spec has `## Source` section with correct `.flow/prospects/<id>.md#idea-2` link; spec is written via `_render_epic_skeleton_from_prospect` in one shot (no call to `cmd_epic_create` / `cmd_epic_set_plan`), so the first-byte state already includes prospect context. <!-- Updated by plan-sync: task 5 inlined epic allocation + spec write (flowctl.py:8034-8082) rather than calling cmd_epic_create+cmd_epic_set_plan; grep the spec for the `## Source` block directly. -->
   - Epic spec uses heading `## Acceptance` (singular, matches default `create_epic_spec`), not `## Acceptance criteria`. <!-- Updated by plan-sync: implementation uses singular `## Acceptance` to match the default epic skeleton. -->
   - `--json` payload shape is `{success, epic_id, epic_title, idea, artifact_id, source_link, spec_path, artifact_updated, [warning]}` — smoke can assert the full key set. <!-- Updated by plan-sync: task 5 returns extra fields (`epic_title`, `spec_path`, `artifact_updated`, optional `warning`) in addition to the originally-specified `{success, epic_id, idea, artifact_id, source_link}`. -->
   - Artifact frontmatter `promoted_ideas: [2]` updated.

7. **Promote idempotency (R14).** Re-run `promote --idea 2` on the same artifact. Assert exit 2 with idempotency error of the form `Idea #2 already promoted to <epic-id>. Use --force to create another epic from the same idea.` Re-run with `--force`: succeeds, artifact YAML contains `promoted_to: {2: [<id1>, <id2>]}` (bare-numeric keys in the inline-flow dict — `_format_prospect_yaml_value` renders dict keys via `_format_prospect_list_item`, which strips quotes for pure-digit strings). At the Python level the keys are strings (`str(idea_n)`) but round-trip reads them back as ints where needed. <!-- Updated by plan-sync: task 5 keys `promoted_to` with `str(idea_n)` internally; the YAML renderer emits bare-numeric tokens, so grep `promoted_to: {2: [` still works. Error message string is verbatim from flowctl.py:8018-8022. -->

8. **Promote errors.** `--idea 99` (out of range) → exit 2 with `--idea 99 out of range (artifact has <N> survivors)`. `--idea 0` → exit 2 with `--idea must be >= 1`. Non-integer `--idea foo` → exit 2 with `--idea must be a positive integer`. Corrupt artifact target → exit 3 with `[ARTIFACT CORRUPT: <reason>]` on stderr (matches `flowctl prospect read` on corrupt; task 4 shipped at flowctl.py:7489-7511). <!-- Updated by plan-sync: task 5 error strings taken verbatim from flowctl.py:7903-7977. Corrupt-branch prints to stderr (not stdout) for promote; read prints to stdout. -->

9. **list / read / archive.** Generate synthetic artifact, verify `list` shows it, `read` prints body, `read --section survivors` filters to survivors (valid `--section` values: `focus | grounding | survivors | rejected`), `archive` moves to `.flow/prospects/_archive/` and updates frontmatter `status: archived`, subsequent `list` default hides it, `list --all` shows it with status column `archived (archived)` (task 4 decorates in-archive rows with `(archived)` suffix — flowctl.py:7407-7408). Additional assertions: `read` on corrupt artifact exits 3 and prints `[ARTIFACT CORRUPT: <reason>]`; `archive` of already-archived artifact errors clearly; `read` accepts slug-only form (latest date wins). <!-- Updated by plan-sync: task 4 shipped read/list/archive with these exact behaviours. -->

10. **Numbered-options fallback (R19).** Exercise the fallback path (simulate blocking-tool unavailable). Assert the exact frozen format string is emitted. Feed `1`, `i`, `skip`, `<empty>` inputs — assert correct routing.

11. **Ralph regression sweep.** Run `ralph_smoke_test.sh` with `FLOW_RALPH=1` set; verify it still exits 0 and prospect doesn't interfere.

**Runtime target:** under 60 seconds total (no LLM calls).

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/impl-review_smoke_test.sh` (fn-32.5) — smoke-test structure template
- `plugins/flow-next/scripts/resolve-pr_smoke_test.sh` (fn-31.6) — GraphQL-free smoke pattern
- `plugins/flow-next/scripts/smoke_test.sh` — existing suite for integration
- `plugins/flow-next/tests/test_prospect_artifact.py` (task 3) — 36 unit tests already cover slug + collision + round-trip + atomic semantics; smoke test must not duplicate, focuses on shell-level + cross-subcommand integration. <!-- Updated by plan-sync: task 3 shipped comprehensive unit coverage; smoke test scope narrows to integration. -->
- `plugins/flow-next/tests/test_prospect_cli.py` (task 4) — 34 unit tests cover `_prospect_parse_frontmatter`, `_prospect_detect_corruption`, id resolution, list/read/archive, section slicer, reverse parsers. Smoke test complements at the shell integration layer. <!-- Updated by plan-sync: task 4 shipped comprehensive CLI unit coverage (34 tests); smoke test narrows to shell-level cross-subcommand integration. -->
- `plugins/flow-next/scripts/flowctl.py:4189` (`render_prospect_body`) — available as test scaffold for generating synthetic artifacts with deterministic body format. <!-- Updated by plan-sync: use render_prospect_body to build fixture artifacts instead of hand-rolling markdown. -->
- `plugins/flow-next/scripts/flowctl.py:4288-4293` — `PROSPECT_CORRUPT_*` module constants; smoke test greps these exact literals from `list --all` / `read` corrupt-branch output. <!-- Updated by plan-sync: task 4 exposed reason strings as constants for the smoke grep contract. -->

**Optional:**
- `plugins/flow-next/scripts/ralph_smoke_test.sh` — Ralph regression harness

## Acceptance

- [ ] `prospect_smoke_test.sh` exists, is executable, exits 0 on clean state.
- [ ] All 11 test cases above pass; each case prints pass/fail with specific evidence (not just checkmarks).
- [ ] Runtime under 60 seconds on a cold machine.
- [ ] Zero LLM invocations — pure shell + synthetic fixtures.
- [ ] `ralph_smoke_test.sh` continues to pass unchanged (Ralph regression verified).
- [ ] `smoke_test.sh` total count increased appropriately (prospect unit tests added).

## Done summary
Added `plugins/flow-next/scripts/prospect_smoke_test.sh` (executable, ~764 lines): an 11-case shell-level smoke test for the `/flow-next:prospect` skill and `flowctl prospect` subcommands (94 assertions; ~58s runtime; zero LLM calls). Covers skeleton + slash-command registration, Ralph-block (exit 2 under FLOW_RALPH=1 / REVIEW_RECEIPT_PATH), list classification (active/stale/corrupt/archived), atomic writer with `-N` collision suffix and frontmatter roundtrip, graceful degradation, promote happy path (full JSON shape, `## Source`, `## Acceptance`), idempotency + `--force` with `promoted_to` dict, error paths (out-of-range / 0 / non-int / corrupt → correct exit codes 2/3 + literal error strings), list/read/archive with section slicing + slug-only resolution + re-archive guard, numbered-options fallback frozen format (workflow.md grep contract + reply-routing simulator), and Ralph regression sweep verifying `ralph_smoke_test.sh` stays green under FLOW_RALPH=1.
## Evidence
- Commits: cb3fecce3e07b98fd011e2fdf775dd9bd26c25d1
- Tests: plugins/flow-next/scripts/prospect_smoke_test.sh (94 PASS / 0 FAIL, ~58s), plugins/flow-next/scripts/smoke_test.sh (125 PASS / 0 FAIL, regression check)
- PRs: