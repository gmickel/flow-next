---
satisfies: [R10, R14]
---

## Description
Repo-side documentation for the feature (docs part of R14; the release mechanics are fn-62.6).

**Size:** M
**Files:** plugins/flow-next/docs/html-artifacts.md (new), plugins/flow-next/docs/README.md, README.md, plugins/flow-next/docs/teams.md, plugins/flow-next/docs/ralph.md, GLOSSARY.md, CLAUDE.md

## Approach
- NEW plugins/flow-next/docs/html-artifacts.md (mirror ralph.md's feature-reference shape): activation, disclosure-file location, spec-lens state-dependent pathway, PR-lens instrument, Lavish integration (detect-on-PATH, session-spanning pull-only model, ~30min idle-stop + resume, global ~/.lavish-axi/state.json reality — NOT the README's misleading workspace wording), GitHub display limitation + local-open + optional raw.githack mention, `.flow/artifacts/` layout + commit-vs-gitignore tradeoff, conversational regeneration, autonomous discipline.
- README.md: feature paragraph in the overview + happy-path note after make-pr (no skill-count change — no new skill added).
- teams.md: "review surfaces" note — spec/diff review gain a render-lens companion; link the new doc.
- ralph.md: one paragraph — autonomous runs generate artifacts, never poll.
- GLOSSARY.md: expand `render lens`; add `HTML artifact mode`, `spec artifact`, `PR artifact`, `Lavish (lavish-axi)`.
- CLAUDE.md "Where to look": one row → docs/html-artifacts.md. docs/README.md index: one row.

## Investigation targets
**Required:**
- plugins/flow-next/docs/ralph.md — feature-doc shape to mirror
- plugins/flow-next/docs/README.md — index format
- GLOSSARY.md:95-110 — render-lens stub to expand
**Optional:**
- docs-gap-scout checklist in the spec's planning research

## Acceptance
- [ ] html-artifacts.md covers all listed topics incl. the global-state-file reality and the worktree session caveat
- [ ] README/teams/ralph/GLOSSARY/CLAUDE.md/doc-index edits all land; no stale skill counts introduced
- [ ] Every flowctl invocation cited in docs matches real surfaces (memory: skill-prose-must-match-real-flowctl)
- [ ] Glossary terms match the spec's vocabulary exactly (no synonyms drift)

## Done summary
Repo-side docs for HTML artifact mode: new feature reference at plugins/flow-next/docs/html-artifacts.md (activation, disclosure file, spec/PR lens hooks as implemented in fn-62.1-.4, GitHub display limitation + raw.githack note, commit-vs-gitignore, conversational regen, Lavish global-state/pull-only/idle-stop reality incl. worktree session caveat, autonomous generate-only discipline), plus surfaces in docs/README.md index, root README (overview bullet + make-pr note), teams.md (render-lens companion on review surfaces), ralph.md (generate-only-never-poll subsection), GLOSSARY.md (render lens expanded; HTML artifact mode, spec artifact, PR artifact, Lavish (lavish-axi) added), and CLAUDE.md Where-to-look. Review: triage-skip SHIP (docs-only).
## Evidence
- Commits: a2478b0290da692b1beb4bab45ed43eeabb6ff5e
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (1071 tests, OK, 2 skipped), flowctl glossary list --json parses 30 terms incl. 4 new, flowctl config get artifacts.html.enabled --json verified against real CLI
- PRs: