# Flow-Next docs

Reference material for flow-next. Each file is self-contained, terse, and offline-readable. Cross-links use relative repo paths — fork-survivable, no external URLs.

> For the plugin overview, install path, and the 6-step workflow narrative see [`../README.md`](../README.md). For the repo's strategic intent see [`../../../STRATEGY.md`](../../../STRATEGY.md). For canonical vocabulary see [`../../../GLOSSARY.md`](../../../GLOSSARY.md).

## Subsystem references

| Doc | What's in it |
|-----|--------------|
| [`architecture.md`](architecture.md) | `.flow/` directory layout, spec-first task model, ID format, separation of concerns, task completion shape |
| [`spec-template.md`](spec-template.md) | Canonical scaffold cross-link, R-ID rules, confidence anchors, introduced-vs-pre-existing, protected artifacts, trivial-diff skip, receipt schema |
| [`memory-schema.md`](memory-schema.md) | Categorized memory tree (bug / knowledge tracks), frontmatter schemas, decisions subtree, audit lifecycle, legacy migration |
| [`tracker-sync.md`](tracker-sync.md) | `/flow-next:tracker-sync` bridge — projection-not-coordination, discovery ceremony, hybrid id model, sync-state schema, transport ladder (Linear/GitHub), lifecycle touchpoints, Ralph-safe conflict queueing; distinct from `/flow-next:sync` (plan-sync) |
| [`glossary.md`](glossary.md) | Repo-root `GLOSSARY.md` shape, resolution walk, subcommands, R17 forbidden-vocabulary guard |
| [`strategy.md`](strategy.md) | Repo-root `STRATEGY.md` shape, Rumelt sections, foreign-file refusal, R19 fluff guard, how downstream skills consume it |
| [`self-improving.md`](self-improving.md) | How the system compounds through normal work — memory, glossary, decision records, strategy loops (seeded / grown / read / pruned); the no-manual-ceremony principle |
| [`platforms.md`](platforms.md) | Install matrix (Claude Code / Codex / Droid / OpenCode), cross-platform patterns, Codex model mapping, community ports, optional skill requirements (`/flow-next:map` Node 22+ + `clawpatch`) |
| [`sync-codex.md`](sync-codex.md) | `scripts/sync-codex.sh` pipeline shape, validation guards, plain-text transform (fn-45), R17 cross-link discipline |
| [`troubleshooting.md`](troubleshooting.md) | Reset stuck tasks, `.flow/` cleanup, Ralph debugging, receipt validation, rp-cli conflict resolution, `/flow-next:map` clawpatch failure modes, uninstall |

## Workflow references

| Doc | What's in it |
|-----|--------------|
| [`flowctl.md`](flowctl.md) | Full `flowctl` CLI reference — every command, every flag, JSON shapes, exit codes (including the [`repo-map`](flowctl.md#repo-map) readers consumed by the `/flow-next:map` opt-in skill) |
| [`../skills/flow-next-qa/SKILL.md`](../skills/flow-next-qa/SKILL.md) | `/flow-next:qa` — live-app real-user QA pass. Derives scenarios from the spec (AC / R-IDs / boundaries), drives the running app via [`flow-next-drive`](../skills/flow-next-drive/SKILL.md), files structured P0/P1/P2 findings with evidence, ends with a YES/NO ship verdict receipt (`type: qa_verdict`). FORBIDDEN from marking PASS by reading source. Opt-in; requires a live deploy + a driver. |
| [`../skills/flow-next-pilot/SKILL.md`](../skills/flow-next-pilot/SKILL.md) | `/flow-next:pilot` — single-tick conductor for plan / plan-review / work / make-pr. Covers `PILOT_VERDICT` grammar, `mode:autonomous` signal, strikes ledger, driver recipes, and Ralph as the alternative driver — never nested. |
| [`../skills/flow-next-land/SKILL.md`](../skills/flow-next-land/SKILL.md) | `/flow-next:land` — cadence-tick ship loop babysitting build-loop-authored PRs. Covers the `LAND_VERDICT` grammar, dual authorship signals, CI tri-state + fix budget, patience window, `land.reviewSignal`, the confined auto-merge override, post-merge tail (spec close → tracker → release-follow), and `--dry-run`. Opt-in. |
| [`ralph.md`](ralph.md) | Ralph autonomous mode internals — hooks, receipts, iteration cap, DCG setup, sandbox options |
| [`../skills/flow-next-work/references/codex-delegation.md`](../skills/flow-next-work/references/codex-delegation.md) | `/flow-next:work` opt-in Codex implementation-delegation — host pre-flight gates + one-time consent, `codex exec` invocation + result schema, orchestration split / batching / classification / safety, circuit breaker + Ralph-safe + ralph-guard amendment + receipts + attribution. OFF by default. |
| [`teams.md`](teams.md) | Spec-driven team workflow — handover objects, Spec-as-PR, parallel work from one spec, symmetric interview, adoption ladder |
| [`ci-workflow-example.yml`](ci-workflow-example.yml) | Drop-in GitHub Actions example running `flowctl validate --all` |

## Conventions

- **R17 cross-link discipline.** Each doc here is a self-contained reference. Canonical sources (`templates/spec.md`, `scripts/sync-codex.sh`, `STRATEGY.md`, `GLOSSARY.md`) are linked, never re-embedded.
- **Relative paths only.** No absolute `github.com/...` URLs anywhere in this tree — fork-survivable + offline-readable.
- **Length discipline.** Reference shape (tables, lists, schemas first; narrative second). Brevity beats completeness.

## See also

- [`../README.md`](../README.md) — plugin overview, install, workflow narrative.
- [`../../../STRATEGY.md`](../../../STRATEGY.md) — flow-next's strategic intent + active tracks.
- [`../../../GLOSSARY.md`](../../../GLOSSARY.md) — canonical vocabulary (Spec, Task, R-ID, ...).
- [`../../../CLAUDE.md`](../../../CLAUDE.md) — repo-level guide for working in this codebase.
