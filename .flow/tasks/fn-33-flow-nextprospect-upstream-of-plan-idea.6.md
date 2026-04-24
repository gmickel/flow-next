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
   - Corrupt artifact has `status: corrupt` and a reason note.

4. **Artifact writer (R4, R13).** Call `write_prospect_artifact` directly (via a thin Python harness) twice on the same day with the same slug. Assert: first writes `dx-2026-04-24.md`; second suffixes to `dx-2026-04-24-2.md`. Both atomic (no `.tmp.*` leftovers). Frontmatter round-trips via `_prospect_parse_frontmatter`.

5. **Graceful degradation (R17).** Phase 1 grounding harness run against:
   - An ungitted temp dir → snapshot includes `scanned: none (no git)` for the git section.
   - A dir with no `.flow/epics/` → snapshot includes `scanned: none (no open epics)`.
   - A dir with no CHANGELOG.md → snapshot includes `scanned: none (no changelog)`.
   - None of these error.

6. **Promote happy path (R6).** Synthetic artifact with 3 survivors → `flowctl prospect promote <id> --idea 2`. Assert:
   - New epic created (verify `.flow/epics/<new-id>.json` exists).
   - Epic spec has `## Source` section with correct `.flow/prospects/<id>.md#idea-2` link.
   - Artifact frontmatter `promoted_ideas: [2]` updated.

7. **Promote idempotency (R14).** Re-run `promote --idea 2` on the same artifact. Assert exit 2 with idempotency error mentioning the prior epic-id. Re-run with `--force`: succeeds, `promoted_to: {2: [<id1>, <id2>]}` tracks both.

8. **Promote errors.** `--idea 99` (out of range) → exit 2. `--idea 0` → exit 2. Corrupt artifact target → exit 3.

9. **list / read / archive.** Generate synthetic artifact, verify `list` shows it, `read` prints body, `read --section survivors` filters to survivors, `archive` moves to `_archive/` and updates `status: archived`, subsequent `list` default hides it, `list --all` shows it with `status: archived`.

10. **Numbered-options fallback (R19).** Exercise the fallback path (simulate blocking-tool unavailable). Assert the exact frozen format string is emitted. Feed `1`, `i`, `skip`, `<empty>` inputs — assert correct routing.

11. **Ralph regression sweep.** Run `ralph_smoke_test.sh` with `FLOW_RALPH=1` set; verify it still exits 0 and prospect doesn't interfere.

**Runtime target:** under 60 seconds total (no LLM calls).

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/impl-review_smoke_test.sh` (fn-32.5) — smoke-test structure template
- `plugins/flow-next/scripts/resolve-pr_smoke_test.sh` (fn-31.6) — GraphQL-free smoke pattern
- `plugins/flow-next/scripts/smoke_test.sh` — existing suite for integration

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
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
