# Flow-Next docs

Reference material for flow-next. Each file is self-contained, terse, and offline-readable. Cross-links use relative repo paths — fork-survivable, no external URLs.

> For the plugin overview, install path, and the 6-step workflow narrative see [`../README.md`](../README.md). For the repo's strategic intent see [`../../STRATEGY.md`](../../STRATEGY.md). For canonical vocabulary see [`../../GLOSSARY.md`](../../GLOSSARY.md).

## Subsystem references

| Doc | What's in it |
|-----|--------------|
| [`architecture.md`](architecture.md) | `.flow/` directory layout, spec-first task model, ID format, separation of concerns, task completion shape |
| [`spec-template.md`](spec-template.md) | Canonical scaffold cross-link, R-ID rules, confidence anchors, introduced-vs-pre-existing, protected artifacts, trivial-diff skip, receipt schema |
| [`memory-schema.md`](memory-schema.md) | Categorized memory tree (bug / knowledge tracks), frontmatter schemas, decisions subtree, audit lifecycle, legacy migration |
| [`glossary.md`](glossary.md) | Repo-root `GLOSSARY.md` shape, resolution walk, subcommands, R17 forbidden-vocabulary guard |
| [`strategy.md`](strategy.md) | Repo-root `STRATEGY.md` shape, Rumelt sections, foreign-file refusal, R19 fluff guard, how downstream skills consume it |
| [`platforms.md`](platforms.md) | Install matrix (Claude Code / Codex / Droid / OpenCode), cross-platform patterns, Codex model mapping, community ports |
| [`sync-codex.md`](sync-codex.md) | `scripts/sync-codex.sh` pipeline shape, validation guards, plain-text transform (fn-45), R17 cross-link discipline |
| [`troubleshooting.md`](troubleshooting.md) | Reset stuck tasks, `.flow/` cleanup, Ralph debugging, receipt validation, rp-cli conflict resolution, uninstall |

## Workflow references

| Doc | What's in it |
|-----|--------------|
| [`flowctl.md`](flowctl.md) | Full `flowctl` CLI reference — every command, every flag, JSON shapes, exit codes |
| [`ralph.md`](ralph.md) | Ralph autonomous mode internals — hooks, receipts, iteration cap, DCG setup, sandbox options |
| [`teams.md`](teams.md) | Spec-driven team workflow — handover objects, Spec-as-PR, parallel work from one spec, symmetric interview, adoption ladder |
| [`ci-workflow-example.yml`](ci-workflow-example.yml) | Drop-in GitHub Actions example running `flowctl validate --all` |

## Conventions

- **R17 cross-link discipline.** Each doc here is a self-contained reference. Canonical sources (`templates/spec.md`, `scripts/sync-codex.sh`, `STRATEGY.md`, `GLOSSARY.md`) are linked, never re-embedded.
- **Relative paths only.** No absolute `github.com/...` URLs anywhere in this tree — fork-survivable + offline-readable.
- **Length discipline.** Reference shape (tables, lists, schemas first; narrative second). Brevity beats completeness.

## See also

- [`../README.md`](../README.md) — plugin overview, install, workflow narrative.
- [`../../STRATEGY.md`](../../STRATEGY.md) — flow-next's strategic intent + active tracks.
- [`../../GLOSSARY.md`](../../GLOSSARY.md) — canonical vocabulary (Spec, Task, R-ID, ...).
- [`../../CLAUDE.md`](../../CLAUDE.md) — repo-level guide for working in this codebase.
