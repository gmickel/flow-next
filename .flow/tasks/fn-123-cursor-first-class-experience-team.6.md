---
satisfies: [R7, R8]
---
# fn-123-cursor-first-class-experience-team.6 Cursor-host orchestration docs + tier-degrade documentation

## Description
Document Cursor-host orchestration + model-tier degradation. Update `plugins/flow-next/templates/usage.md` (+ byte-identical `.flow/usage.md`): dedicated Cursor-host section - caller-side pin grammar (Cursor slugs, bracket params), slug volatility + enumeration (`cursor-agent --list-models` / host catalog), cross-family pairing rule, `review.backend host`, recipes reframed for a Cursor host; clearly distinguish host-native `host` from the headless `cursor` CLI backend. Update `plugins/flow-next/docs/orchestration.md` and `docs/flowctl.md` (`host` = model-less selection sentinel; grammar/precedence table). State the tiering degrade: canonical `agents/*.md` family aliases resolve to inherit (session model) on Cursor; caller-side pins are the escape hatch; no alias-to-slug rewrite exists or is planned. Add `test_cursor_host_docs.py`.

## Acceptance
- usage.md Cursor-host section complete (pin grammar, volatility/enumeration, pairing rule, host backend, recipes); template and `.flow/usage.md` byte-identical.
- host-native `host` vs headless `cursor` CLI backend distinction unambiguous.
- Alias degrade documented (inherit on Cursor; pins as escape hatch); no rewrite pass suggested.
- flowctl.md documents `host` sentinel; existing backend grammar/precedence retained.
- Focused suites green (`test_cmd_usage`, `test_dogfood_template_parity`, `test_cursor_host_docs`).


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
