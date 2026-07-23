---
satisfies: [R16]
---
# fn-118-work-skill-sanctioned-parallel-worker.2 Align parallel-work documentation

## Description
Align the public repository and flow-next.dev documentation with prompt-guided parallel waves. Explain that the planner exposes parallel candidates and the work conductor chooses a safe isolation arrangement or serializes. Remove wording that implies atomic task claims make shared-checkout Git/file mutation safe.

**Size:** M

**Files:** `README.md`, `plugins/flow-next/docs/teams.md`, `GLOSSARY.md`, `CHANGELOG.md`, `/Users/gordon/work/flow-next.dev/src/content/docs/skills/work.mdx`, `/Users/gordon/work/flow-next.dev/src/content/docs/tasks/concurrency.mdx`, `/Users/gordon/work/flow-next.dev/src/content/docs/cookbook.mdx`, `/Users/gordon/work/flow-next.dev/src/content/docs/releases/changelog.mdx`

### Approach

- Keep documentation proportional: no scheduler internals because none are being added.
- Describe the task DAG as execution waves and parallelism as a host-agent orchestration choice.
- Distinguish atomic task claims from filesystem/Git isolation.
- Preserve natural-language invocation as the primary UX; add no new flag.
- Record the user-visible behavior under `## Unreleased` in both changelogs.

### Investigation targets

**Required** (read before editing):

- `README.md:143-151` — current prompted-parallel example.
- `plugins/flow-next/docs/teams.md:280-292` — parallel work guidance.
- `GLOSSARY.md` — Task and Worker subagent definitions.
- `/Users/gordon/work/flow-next.dev/src/content/docs/skills/work.mdx` — work-skill behavior.
- `/Users/gordon/work/flow-next.dev/src/content/docs/tasks/concurrency.mdx` — concurrency truth surface.

**Optional** (reference as needed):

- `/Users/gordon/work/flow-next.dev/src/content/docs/cookbook.mdx` — parallel recipes.
- `CHANGELOG.md` and flow-next.dev changelog — Unreleased format.

### Key context

Atomic task claims protect task ownership only. Concurrent implementation also requires isolated mutable workspaces and a safe integration arrangement chosen by the host. Keep platform-specific claims out unless verified.

## Acceptance
- [ ] README and teams guidance show planner-produced execution waves and agent-chosen safe parallel work.
- [ ] GLOSSARY distinguishes fresh-context workers, task claims, and mutable-workspace isolation.
- [ ] flow-next.dev work, concurrency, and cookbook surfaces tell the same concise story.
- [ ] No document claims that atomic task claims alone make shared-checkout work race-safe.
- [ ] Repository and docs-site changelogs contain concise `## Unreleased` entries; no version bump.
- [ ] `cd /Users/gordon/work/flow-next.dev && pnpm build` passes.
- [ ] The exact offline Lychee command from `.github/workflows/docs-linkcheck.yml` passes for repository markdown.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
