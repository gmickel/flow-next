---
satisfies: [R1, R2, R3, R6, R7, R9]
---

## Description

Replace `scripts/sync-codex.sh` Stage 3 (lines 510-514: the 3-line sed block that rewrites `` `AskUserQuestion` `` → `` `request_user_input` ``) with a Python heredoc that rewrites canonical `AskUserQuestion` invocations into a plain-text numbered-prompt instruction in the Codex mirror. Add validation guards that fail if `request_user_input` survives into the mirror. Update Stage 3 comment block at line 386 to document the new transform contract.

**Size:** M

**Files:**
- `scripts/sync-codex.sh` (Stage 3 sed → Python heredoc; validation block; comment block)
- `plugins/flow-next/codex/skills/**` (regenerated mirror — should byte-roundtrip on second sync run)

## Approach

- Follow the Python-heredoc precedent established by Stage 1 (`scripts/sync-codex.sh:396-418` — breadcrumb strip) and Stage 2 (`:423-507` — ToolSearch strip). Sed cannot reliably insert multi-line replacement text across macOS BSD + GNU; Python `re.sub` is the established pattern.
- Keep Stage 1 + Stage 2 unchanged — they expect the canonical `AskUserQuestion` token and run before the new transform.
- Process longest-most-specific patterns first so the bare-token rule doesn't eat structured ones (precedent: existing line 510-513 order).
- Use `re.MULTILINE` only when anchoring `^`/`$`; default `.` to single-line (no `re.DOTALL`).
- Follow the validation-guard pattern at `:818-885` exactly: `var_refs=$( { grep -rE 'pattern' "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | wc -l | tr -d ' ')`; `if [ "$var_refs" != "0" ]; then errors=$((errors + 1)); fi`. Wrap `grep` in `{ ... || true; }` to neutralize the no-match exit code under `set -euo pipefail`.

## Investigation targets

**Required** (read before coding):
- `scripts/sync-codex.sh:386-517` — current 3-stage transform pipeline; Stage 3 is the swap target
- `scripts/sync-codex.sh:818-885` — validation-guard pattern precedent (`task_refs`, `ddd_refs`, `alias_refs`, `askq_refs`)
- `plugins/flow-next/skills/flow-next-capture/workflow.md:135-160` — canonical `AskUserQuestion` options-list shape (one of the four surface forms)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:217-235` — hard mandate ("MUST use") + ONLY-via mandate + existing fallback prose (verify transform handles all three)
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md:1056` + `plan-review/workflow.md:379` + `spec-completion-review/workflow.md:574` — "Never use AskUserQuestion in this loop" auto-fix mandates that must survive semantically

**Optional**:
- `plugins/flow-next/skills/flow-next-plan/SKILL.md:117` — anti-mandate (`do NOT use AskUserQuestion tool`) — verify transform produces sensible output
- `plugins/flow-next/skills/flow-next-ralph-init/SKILL.md:37` — same anti-mandate pattern
- `plugins/flow-next/skills/flow-next-prime/pillars.md:219` + `SKILL.md:97` — table cells (`✅ Fixes offered via AskUserQuestion`) — verify transform doesn't break tables
- `plugins/flow-next/skills/flow-next-ralph-init/templates/watch-filter.py:47` — `"AskUserQuestion": "❓"` (dict key, intentional) — already excluded by `/templates/` guard

## Key context

- **Canonical surface forms to rewrite:**
  1. `` Use `AskUserQuestion` with [questions array] `` — workflow blocks
  2. `` Use `AskUserQuestion`. Call `ToolSearch` with `select:AskUserQuestion` first... `` — SKILL.md prose (note: ToolSearch strip in Stage 2 may already handle this — verify)
  3. `**CRITICAL**: You MUST use the `` `AskUserQuestion` `` tool — hard mandates (R3)
  4. `Ask **one question at a time** via ` `` `AskUserQuestion` `` — grouped-prompt prose
- **Substituted instruction phrasing (R2 verbatim target):**
  > **Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.
- **For hard mandates (R3):** rewrite the mandate clause to `MUST ask via the plain-text numbered prompt described above` rather than mentioning `request_user_input`.
- **For auto-fix-loop "Never use" mandates:** rewrite token only (`Never use the plain-text numbered prompt in this loop`) — preserves the "do not interrupt the loop" intent.
- **R6 grep guards:** join forbidden patterns with `|` in one `grep -rE`. Always exclude `/templates/` (precedent at `:833,845,866,879`).
- **Pitfall:** keep `sed -i.bak ... && rm -f *.bak` shape if any sed survives; macOS BSD vs GNU sed `-i` quirk.
- **Pitfall:** the existing askq guard at `:833` is a positive check that the transform fired (no bare `AskUserQuestion` left over). Keep it. R6 adds the inverse `request_user_input` guards alongside.
- **Frontmatter `allowed-tools: request_user_input` lines** in Codex SKILL.md files (e.g. `codex/skills/flow-next-capture/SKILL.md:5`) are harmless residue (Codex reads `agents/openai.yaml`, not SKILL.md frontmatter). Not in this task's scope.
- **Verify idempotency:** run sync twice; `git diff --stat plugins/flow-next/codex/` should be empty between runs.

## Acceptance

- [ ] `scripts/sync-codex.sh` Stage 3 sed block (lines 510-514) replaced with a Python heredoc handling four surface forms via distinct `re.sub` calls.
- [ ] Substituted instruction text matches R2 phrasing substantively.
- [ ] Hard mandates → softened mandate ("MUST ask via the plain-text numbered prompt described above"); auto-fix-loop "Never use" mandates preserve intent.
- [ ] Stage 3 comment block at line 386 updated: replace "`# --- TOOL NAMES: AskUserQuestion → request_user_input (Codex native) ---`" with a comment documenting the plain-text numbered-prompt transform contract + linking to fn-45.
- [ ] New validation guards added in the validation block (around `:840`, after the existing `askq_refs` guard) that fail when the Codex mirror contains: `` `request_user_input` ``, `request_user_input tool`, `request_user_input(`, "MUST use `request_user_input`", "ONLY ask via `request_user_input`". Guards follow the established pattern; print offending file:line on failure.
- [ ] `./scripts/sync-codex.sh` runs cleanly (exit 0) with the new transform + new guards on a clean working tree.
- [ ] Re-running `./scripts/sync-codex.sh` produces byte-identical mirror (`git diff --stat plugins/flow-next/codex/` is empty between runs).
- [ ] Existing smoke scripts stay green: `bash plugins/flow-next/scripts/smoke_test.sh`, `audit_smoke_test.sh`, `prospect_smoke_test.sh`, `ralph_smoke_test.sh`.
- [ ] Standalone grep guard: `grep -rE '`request_user_input`|request_user_input tool|request_user_input\(|MUST use `request_user_input`|ONLY ask via `request_user_input`' plugins/flow-next/codex/skills/ | grep -v '/templates/'` returns no output.

## Done summary

Replaced `scripts/sync-codex.sh` Stage 3 sed block (canonical `AskUserQuestion` → `request_user_input`) with a Python heredoc that rewrites canonical Claude `AskUserQuestion` invocations into a plain-text numbered-prompt instruction for the Codex mirror. The mirror never calls `request_user_input` (Plan-mode-only per openai/codex #10384/#11536/#12694). Added R6 validation guards (`rui_refs`) that fail sync if forbidden `request_user_input` patterns survive into the mirror. Stage 1 breadcrumb-strip regex was widened to tolerate multi-line parentheticals; ToolSearch stripper ordering was corrected so Stage 3 sees a clean canonical input. Codex mirror regenerated for all 24 skills; byte-identical idempotency confirmed across two consecutive sync runs.

## Evidence

- Commits: 8c286f0 (initial transform), 063b06e (skip neg ctx + table rows + UI prose), 128030c (active-ask anchors + ToolSearch ordering), f584da9 (structured-tool prose rewrites: multiSelect, blocking-question), 05a6ce6 (drop interview anti-pattern contradicting plain-text), 096a325 (capture memory entry)
- Tests:
  - `./scripts/sync-codex.sh` exits 0; all validation guards pass
  - `bash plugins/flow-next/scripts/smoke_test.sh` — 130/130 pass
  - `bash plugins/flow-next/scripts/audit_smoke_test.sh` — 41/41 pass
  - `bash plugins/flow-next/scripts/prospect_smoke_test.sh` — 94/94 pass
  - `bash plugins/flow-next/scripts/ralph_smoke_test.sh` — 15/15 pass
  - Idempotency: `find codex -type f -name '*.md' -exec md5sum {} + | sort | md5sum` identical across two consecutive sync runs
  - Standalone R6 guard: `grep -rE '\`request_user_input\`|request_user_input tool|request_user_input\(|MUST use \`request_user_input\`|ONLY ask via \`request_user_input\`' plugins/flow-next/codex/skills/ | grep -v '/templates/'` returns empty
  - Codex impl-review verdict SHIP (after 4 NEEDS_WORK iterations + fixes)
- PRs: —