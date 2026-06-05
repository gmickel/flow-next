---
satisfies: [R9, R11, R13]
---

## Description
Make the skill run interactively AND autonomously (not a hard Ralph-block), degrade gracefully when no live deploy/driver is available, and add the one additive flowctl change: the opt-in `tracker.perEvent.qa` verdict-post leaf.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-qa/references/autonomy.md` (new), `plugins/flow-next/skills/flow-next-qa/workflow.md` (*execute/autonomy* section anchor only — disjoint from 53.3's *prepare*), `plugins/flow-next/scripts/flowctl.py` + `.flow/bin/flowctl.py` (dual-copy), `plugins/flow-next/tests/test_qa_tracker_event.py`

## Approach
- **Ralph-aware-but-not-blocked (R11):** copy make-pr's §0.0 detect-once — detect `REVIEW_RECEIPT_PATH`/`FLOW_RALPH` ONCE, then route deterministically. `AskUserQuestion` is **info-only** (target URL / accounts), never a confirm gate. **Do NOT add a top-of-skill `FLOW_RALPH` exit-2 guard** (make-pr forbids this explicitly). Autonomous when URL + accounts configured (emit the verdict receipt, no prompts); interactive ask only when undocumented.
- **Graceful degradation (R13):** no live deploy or fn-51 degraded to the manual rung → surface the limitation as a **BLOCKED** verdict, add nothing to the base flow, exit clean. Inherit fn-51's degradation table — don't re-derive it.
- **Opt-in tracker post (R9):** add a `"qa"` leaf to `perEvent` in `get_default_tracker_config()` accepting **`off|comment`** (default `off`). `comment` is the only sensible verb for a QA verdict — posting it as a tracker comment; treat any other non-`off` value as `comment` (or reject with a one-line warning), never `push`/`pull`/`reconcile`. **Dual-copy invariant** — edit BOTH `plugins/flow-next/scripts/flowctl.py` AND `.flow/bin/flowctl.py` (byte-identical), or `cp` canonical→bin. When `tracker.perEvent.qa == comment` AND the bridge is active, post the verdict as a structured tracker comment via the existing flow-next-tracker-sync skill (follow fn-52's perEvent pattern; best-effort, never blocks).
- **Merge-safety + serial after 53.3:** this task is serialized after 53.3 and writes its own `references/autonomy.md`; it edits ONLY the *execute/autonomy* section anchor in `workflow.md` (53.3 owns *prepare*) — no shared-region conflict.

## Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:24-41` — the §0.0 detect-once Ralph pattern to copy
- `plugins/flow-next/skills/flow-next-make-pr/SKILL.md:96` — the "do NOT add a Ralph exit guard" rule
- `plugins/flow-next/scripts/flowctl.py` (`get_default_tracker_config`, ~`:1045`) — the `perEvent` nested dict to extend
- `plugins/flow-next/skills/flow-next-drive/SKILL.md:70-78` — fn-51 graceful-degradation contract

**Optional:**
- `plugins/flow-next/skills/flow-next-work/SKILL.md` (tracker `perEvent` gate prose) — fn-52 opt-in event pattern

## Key context
- **Dual-copy invariant** (MEMORY): `.flow/bin/flowctl.py` must stay byte-identical to `plugins/flow-next/scripts/flowctl.py` or the bundled CLI runs stale code — the smoke test must hit the production `cmd_*` path.
- Receipt-prefix decision (v1): a `qa-*.json` receipt parses to the `parse_receipt_path` fallback but still validates via the verdict enum; do NOT extend `parse_receipt_path` in v1 (QA is not a hard Ralph-gate).

## Acceptance
- [ ] Detect-once routing (info-only AskUserQuestion; no top-of-skill Ralph exit guard); autonomous when URL+accounts set, interactive when undocumented
- [ ] No live deploy / no driver → clean BLOCKED surface, zero base-flow impact (R13)
- [ ] `tracker.perEvent.qa` default `off` added to BOTH flowctl copies (byte-identical); opt-in verdict-post wired via flow-next-tracker-sync, best-effort
- [ ] `test_qa_tracker_event.py` proves the new leaf round-trips via the production `cmd_config_*` path (hermetic, `"$FLOWCTL"`, Windows-portable)

## Done summary
Made /flow-next:qa Ralph-aware-but-not-blocked: filled Phase A (detect-once routing with info-only AskUserQuestion and no exit guard, graceful BLOCKED degradation inheriting fn-51, opt-in tracker verdict post) plus a new references/autonomy.md, and added the additive tracker.perEvent.qa config leaf (default off, comment-only verb) to both byte-identical flowctl copies with a subprocess CLI round-trip test.
## Evidence
- Commits: 19261e94ace4281e37d80a98fb2a4fc8a56d01e2
- Tests: python3 -m unittest plugins.flow-next.tests.test_qa_tracker_event -v (6 passed), python3 -m unittest discover -s plugins/flow-next/tests (992 passed, 2 skipped), cmp scripts/flowctl.py .flow/bin/flowctl.py (byte-identical), rp impl-review --base f35081e -> SHIP (R9/R11/R13 met, 0 findings)
- PRs: