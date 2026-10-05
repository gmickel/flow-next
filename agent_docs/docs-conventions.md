# Shipped docs: consumers and conventions

Maintainer notes for `plugins/flow-next/docs/`. The shipped index
([`docs/README.md`](../plugins/flow-next/docs/README.md)) is for people and agents in other
repositories; this page records who reads each file inside flow-next and the conventions that
keep the tree small. See also [Shipped skill text](adding-skills.md#shipped-skill-text) and
[writing-docs.md](writing-docs.md).

A page that used to live in `docs/` and is now only on [flow-next.dev](https://flow-next.dev) is
not coming back; a release updates the site. A file stays in `docs/` because something at runtime
reads it: a skill, an agent, a template, a hook, the config schema, or a test that pins its
content.

## Who reads each file

| Doc | Who reads it |
|---|---|
| [`prose.md`](../plugins/flow-next/docs/prose.md) | Every emission point: 20 skills and 2 agents cite it before drafting a PR body, spec, comment, memory entry, or changelog line |
| [`flowctl.md`](../plugins/flow-next/docs/flowctl.md) | `templates/usage.md` and the qa, flow, impl-review, and spec-completion-review skills point at command sections; the surface test checks every documented leaf command exists |
| [`orchestration.md`](../plugins/flow-next/docs/orchestration.md) | `templates/usage.md` links the tiers and reach sections; the Cursor host test pins the alias-to-inherit statement |
| [`reach/README.md`](../plugins/flow-next/docs/reach/README.md) and the per-harness pages | The worker and work phases resolve the implementer tier through reach; the capture, make-pr, and setup skills read `reach/codex.md` and `reach/cursor.md`; the Codex installer test checks the tree |
| [`read-back.md`](../plugins/flow-next/docs/read-back.md) | Capture, plan, and refine read it before the first `.flow/` write |
| [`pipeline-variations.md`](../plugins/flow-next/docs/pipeline-variations.md) | The flow skill's `route-matrix.md` and capture's rewrite mode cite it; the routing test scans it as a consumer of the shared routing reference |
| [`skills.md`](../plugins/flow-next/docs/skills.md) | The resolve-pr skill and the route matrix cite the backend-split heuristic; the count test pins the 29 skills table |
| [`tracker-sync.md`](../plugins/flow-next/docs/tracker-sync.md) | Capture, make-pr, and work read the retro-fire rule; `flowctl_tracker` code and the config schema cite the dependency-projection ordering rule |
| [`memory-schema.md`](../plugins/flow-next/docs/memory-schema.md) | The qa skill maps bug categories through it |
| [`pr-cognitive-aid.md`](../plugins/flow-next/docs/pr-cognitive-aid.md) | The consumer contract for the stored PR walkthrough and its rendered briefing |
| [`review-findings.md`](../plugins/flow-next/docs/review-findings.md) | The structured findings contract; its test pins the schema fields, bounds, and identity grammar |
| [`judge.md`](../plugins/flow-next/docs/judge.md) | The setup workflow links it for key handling; the config schema descriptions point at it |
| [`running-lean.md`](../plugins/flow-next/docs/running-lean.md) | Seven config schema descriptions point at it for the cost of each optional layer |
| [`spec-template.md`](../plugins/flow-next/docs/spec-template.md) | `templates/spec.md` cites it for the scaffold rules and the auxiliary-section list |
| [`teams.md`](../plugins/flow-next/docs/teams.md) | `templates/spec.md` cites the symmetric interview pattern; the count test pins the commands table |
| [`architecture.md`](../plugins/flow-next/docs/architecture.md) | The `.flow/` layout and the review bookkeeping authority; the chart inventory and review-findings tests read it |
| [`platforms.md`](../plugins/flow-next/docs/platforms.md) | The canonical supported-platforms sentence and the platform matrix; the Cursor and tracker distribution tests pin its sections |
| [`troubleshooting.md`](../plugins/flow-next/docs/troubleshooting.md) | Landing upgrades, manual chain recovery, and bug report troubleshooting |
| [`glossary.md`](../plugins/flow-next/docs/glossary.md) | How the repo-root `GLOSSARY.md` file is shaped, resolved, and edited with `flowctl glossary`; no site page covers the file mechanics yet |
| [`ci-workflow-example.yml`](../plugins/flow-next/docs/ci-workflow-example.yml) | `flowctl.md` links it as the drop-in `flowctl validate --all` job; the mirror rewrites its link |

Codex mirror generation, formerly `docs/sync-codex.md`, is maintainer-only and lives at
[sync-codex.md](sync-codex.md).

## Conventions

- **Cross-link discipline.** Canonical sources (`templates/spec.md`, `STRATEGY.md`,
  `GLOSSARY.md`) are linked, never re-embedded.
- **Links stay inside the installed tree.** Shipped docs link relatively only to files under
  `plugins/flow-next/` (other docs, `skills/`, `templates/`, `references/`, `schema/`, `tests/`).
  Anything outside it (repo root, `STRATEGY.md`, `GLOSSARY.md`, `CONTRIBUTING.md`,
  `agent_docs/`, `scripts/`, `.flow/`) is either an absolute `https://flow-next.dev/...` or
  `https://github.com/gmickel/flow-next/...` URL, or it is maintainer material that belongs in
  `agent_docs/`. Installed plugins have no repo root, and in a consumer's repository a relative
  `GLOSSARY.md` or `STRATEGY.md` resolves to their file, not ours.
- **Codex install layout.** The mirror installs docs under `$CODEX_HOME/docs/flow-next/`.
  `sync-codex.sh` rewrites mirrored links by target class and its link-closure guard fails the
  sync on any mirrored link that neither resolves on disk nor is an absolute URL.
- **No flow-next history.** No spec or task ids, PR numbers, dated dogfood runs, or facts about
  this repository in shipped pages; those belong in the CHANGELOG, commit messages, or
  `agent_docs/` (for example [field-cases.md](field-cases.md)).
- **Tracker claims.** A change to tracker ownership or behaviour sweeps every adjacent claim,
  not only the primary section: recovery, discovery, dependency direction, idempotency,
  provenance and body-merge prose. Check each provider-fidelity bullet against
  `flowctl_tracker/relate/providers.py` and its contract tests. Grep slash-list enumerations
  (`Linear/GitHub/GitLab`) and per-provider clauses (`on GitHub`, `flat tracker`, `threaded`);
  the slash-list grep misses the second kind.
- **No mirrored pages.** A page that explains the product to a human belongs on flow-next.dev. A
  file lands in `docs/` only when something at runtime reads it, and it leaves when nothing does.
