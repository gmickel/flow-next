# fn-26-designmd-aware-orchestration.5 Docs, CHANGELOG, version bump, codex sync

## Description
Update documentation, CHANGELOG, version bump, and regenerate codex/ directory.

**Size:** M
**Files:** `plugins/flow-next/README.md`, `CHANGELOG.md`, codex/ (generated)

## Flow-Next README

Add a new Features subsection (after existing features like "Investigation Targets", "Typed Escalation"):

```markdown
### DESIGN.md Awareness

When a project has a [DESIGN.md](https://stitch.withgoogle.com/docs/design-md/overview/) file (Google Stitch format), flow-next detects it and injects design context at each pipeline stage:

- **Planning**: repo-scout reads DESIGN.md, plan writes `## Design context` in frontend task specs with relevant color/component/typography tokens
- **Implementation**: worker reads referenced DESIGN.md sections before coding, uses design tokens over hard-coded values
- **Readiness**: `/flow-next:prime` checks for DESIGN.md in Pillar 4 (Documentation) as informational criterion
- **Quality audit**: quality-auditor flags hard-coded colors/spacing in frontend files when design tokens exist (advisory)

Backend tasks are not affected — design injection only applies to tasks touching frontend files.

No DESIGN.md? No change in behavior. The feature is entirely opt-in.
```

## CHANGELOG

Add `[flow-next 0.29.0]` entry:

```markdown
## [flow-next 0.29.0] - 2026-04-XX

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
```

## Version bump + codex sync

```bash
scripts/bump.sh minor flow-next
scripts/sync-codex.sh
plugins/flow-next/scripts/smoke_test.sh
```

## Investigation targets
**Required:**
- `plugins/flow-next/README.md:820-840` — Features section (investigation targets, etc.)
- `CHANGELOG.md:0-20` — recent entries for style reference

## Key context
- Minor bump (0.29.0) — new agent behaviors warrant minor, not patch
- Root README doesn't need updating — the "Why It Works" table doesn't have a design-specific row
- Don't add badges or visual elements — just prose
## Acceptance
- [ ] Flow-next README Features section documents DESIGN.md awareness
- [ ] CHANGELOG has [flow-next 0.29.0] entry
- [ ] `scripts/bump.sh minor flow-next` run successfully
- [ ] `scripts/sync-codex.sh` run clean
- [ ] `plugins/flow-next/scripts/smoke_test.sh` passes
- [ ] No changes to flowctl, .flow/ JSON, or hooks
## Done summary
Updated flow-next README with DESIGN.md Awareness feature section. Added [flow-next 0.29.0] CHANGELOG entry. Ran `scripts/bump.sh minor flow-next` (0.28.0 → 0.29.0, updates marketplace + plugin manifests + codex manifests). Codex sync regenerated 16 skills + 20 agents. Smoke test: 52/52 passed. No changes to flowctl, .flow/ JSON, or hooks.
## Evidence
- Commits:
- Tests:
- PRs: