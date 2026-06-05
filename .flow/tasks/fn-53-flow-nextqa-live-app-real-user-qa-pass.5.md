---
satisfies: [R10]
---

## Description
Register the new skill on the Codex side and regenerate the mirror, then smoke-test the skill's flowctl plumbing. Runs after .4 so the canonical skill (all `AskUserQuestion` / `Task` invocations) is complete before the mirror is generated.

**Size:** M
**Files:** `scripts/sync-codex.sh`, `plugins/flow-next/codex/**` (regenerated), `plugins/flow-next/tests/test_qa_smoke.py`

## Approach
- **Codex registration (R10):** add a `generate_openai_yaml "flow-next-qa" "Flow QA" "<one-line desc>" "<color>" false "<arg-hint>"` call in `scripts/sync-codex.sh`, and add `"flow-next-qa"` to `REQUIRED_OPENAI_YAML_SKILLS` (the sync VALIDATION fails otherwise).
- Run `./scripts/sync-codex.sh`; commit the regenerated `plugins/flow-next/codex/` mirror.
- **Audit the `AskUserQuestion`→numbered-prompt rewrite** in the generated mirror (memory gotcha — verify the transform output for the QA skill's prompts, not just that sync ran). Confirm `Task`/`Explore` → `spawn_agent` rewrite is clean too.
- **Skill smoke (R10):** a hermetic smoke (`"$FLOWCTL"`, Windows-portable, production `cmd_*` path) asserting the skill's flowctl touchpoints resolve (`spec export-cognitive-aid`, the `tracker.perEvent.qa` leaf from .4, the receipt write path) — not a live drive.

## Investigation targets
**Required:**
- `scripts/sync-codex.sh:1227-1246` (`REQUIRED_OPENAI_YAML_SKILLS`), `:1164` (generate_openai_yaml call sites), `:406+` (AskUserQuestion rewrite)
- `agent_docs/adding-skills.md:1-24` — registration steps 4-6
- existing `plugins/flow-next/tests/test_*smoke*.py` — smoke pattern

## Key context
- DEPENDS on .4 (transitively .1-.3): the mirror must reflect the COMPLETE canonical skill, so registration/sync run last among the build tasks (docs in .6 follow).
- `REQUIRED_OPENAI_YAML_SKILLS` omission FAILS the sync build — easy to forget.

## Acceptance
- [ ] `flow-next-qa` added to sync-codex (generate_openai_yaml + REQUIRED list); `./scripts/sync-codex.sh` runs clean and the mirror is committed
- [ ] AskUserQuestion→numbered-prompt + Task→spawn_agent rewrites audited in the QA mirror output (not just "sync ran")
- [ ] Hermetic skill smoke passes via the production `cmd_*` path (Windows-portable, `"$FLOWCTL"`)

## Done summary
Registered the flow-next-qa skill on the Codex side: added the `generate_openai_yaml` call + `REQUIRED_OPENAI_YAML_SKILLS` entry in `scripts/sync-codex.sh`, regenerated and committed the `plugins/flow-next/codex/` mirror, audited the AskUserQuestion→numbered-prompt rewrites (fixing two mirror-prose artifacts caught in review: a mid-sentence R2 injection in qa-discipline.md and a wrong-article rewrite in SKILL.md), and added a hermetic production-cmd-path smoke (`test_qa_smoke.py`) for the skill's three flowctl touchpoints. RP impl-review: SHIP (R10).
## Evidence
- Commits: e16cc7e, eb05e8a, 538b20e
- Tests: python3 -m unittest plugins.flow-next.tests.test_qa_smoke, python3 -m unittest plugins.flow-next.tests.test_qa_receipt plugins.flow-next.tests.test_qa_tracker_event, python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (996 tests OK, skipped=2), ./scripts/sync-codex.sh (clean, byte-idempotent)
- PRs: