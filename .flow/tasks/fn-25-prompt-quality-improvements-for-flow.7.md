# fn-25-prompt-quality-improvements-for-flow.7 Docs, CHANGELOG, version bump, codex sync

## Description
Update documentation, CHANGELOG, version bump, and regenerate codex/ directory after all prompt changes land.

**Size:** M
**Files:** `plugins/flow-next/README.md`, `README.md`, `CHANGELOG.md`, codex/ (generated)

## Flow-Next README updates

In the Features section (line 700+), add a subsection documenting the new agent behaviors:

### Investigation targets
Brief description: plan writes investigation targets per task, worker reads them before coding. Reduces hallucination, ensures pattern conformance.

### Requirement traceability
Brief description: plan outputs a requirement coverage table in epic specs. Plan-sync maintains it. Epic-review uses it for bidirectional coverage checking.

### Pre-implementation search
Brief description: worker searches for similar functionality before implementing. Reuse > extend > new.

### Typed escalation
Brief description: structured block messages with categories (SPEC_UNCLEAR, DEPENDENCY_BLOCKED, etc.) for faster triage.

Keep descriptions concise — 2-3 sentences each, consistent with existing feature descriptions in that section.

## Root README updates

Root README is minimal (142 lines). Add one line to the "Why It Works" table:

| Problem | Solution |
|---------|----------|
| Duplicate implementations | **Pre-implementation search** — worker checks for similar code before writing new |

Or similar — keep it one row, consistent with existing table style.

## CHANGELOG

Add `[flow-next 0.27.1]` entry (patch bump for prompt-only changes):

```markdown
## [flow-next 0.27.1] - 2026-04-XX

### Added
- **Investigation targets** in task specs — plan writes file paths workers must read before coding
- **Requirement coverage** traceability table in epic specs — tracks spec-to-task mapping
- **Early proof point** in epic specs — identifies which task validates the core approach
- **Bidirectional epic-review** — checks code→spec direction (scope creep detection)
- **Pre-implementation search** — worker greps for similar functionality before coding
- **Typed escalation** — structured block messages (SPEC_UNCLEAR, DEPENDENCY_BLOCKED, etc.)
- **Confidence qualifiers** — scouts tag findings as [VERIFIED] or [INFERRED]
- **Test budget awareness** — quality-auditor flags disproportionate test generation (advisory)
```

## Version bump + codex sync

```bash
scripts/bump.sh patch flow-next
scripts/sync-codex.sh
```

Verify sync is clean — no errors, all agents regenerated.

## Investigation targets
**Required** (read before coding):
- `plugins/flow-next/README.md:700-800` — Features section
- `README.md` — root README (full file, short)
- `CHANGELOG.md:0-30` — recent entries for style reference

## Key context

- Root README was cleaned up in v0.27.0 — keep it minimal
- Flow-next README Features section has subsections like "Re-anchoring", "Multi-user Safe", etc. — new features follow same pattern
- CHANGELOG uses `[flow-next X.Y.Z]` format with `### Added` / `### Changed` subsections
- bump.sh + sync-codex.sh are the standard release pipeline per CLAUDE.md
- Don't add badges or visual elements — just prose descriptions
## Acceptance
- [ ] Flow-next README Features section documents investigation targets, traceability, pre-impl search, typed escalation
- [ ] Root README "Why It Works" table updated (one row)
- [ ] CHANGELOG has [flow-next 0.27.1] entry listing all 8 improvements
- [ ] `scripts/bump.sh patch flow-next` run successfully
- [ ] `scripts/sync-codex.sh` run clean — codex/ regenerated with updated agents
- [ ] `plugins/flow-next/scripts/smoke_test.sh` passes
- [ ] No changes to flowctl, .flow/ JSON, or hooks (doc task only)
## Done summary
Updated flow-next README Features section (5 new subsections), root README Why It Works table (+1 row), CHANGELOG with [flow-next 0.27.1] entry, version bump via bump.sh, codex sync via sync-codex.sh. Smoke test 52/52 green.
## Evidence
- Commits: 3191d387b60fe5f94b6fd9463932bf6635317090
- Tests: plugins/flow-next/scripts/smoke_test.sh (52/52 passed)
- PRs: