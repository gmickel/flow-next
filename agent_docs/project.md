# Flow-Next development policy

Read this policy when working in this repository. `AGENTS.md` and `CLAUDE.md`
are separate host entry points; maintain shared rules here. Both roots link
here explicitly. Their Flow-Next marker blocks are repo-customized; keep
maintainer policy outside those blocks and preserve each file's ownership.

This repository develops Flow-Next, a spec-driven agentic SDLC plugin with a
pure-stdlib Python CLI. The canonical supported-host roster is in
[platforms.md](../plugins/flow-next/docs/platforms.md). Preserve all supported
consumers when changing shared product behavior.

## Architecture

The host agent owns contextual judgment, investigation, planning, and composing
multi-step workflows. Skills express those workflows. Deterministic `flowctl`
helpers own schema validation, atomic writes, receipts, git plumbing, and
mechanical operations that must work without an agent in the loop.

Choose by the operation's responsibility. Do not substitute word lists, scoring
heuristics, or subprocess LLM calls for a judgment the host can make. Review
backend dispatch and the triage-skip judge are licensed subprocess-judgment
exceptions for independent review. Implementation offload is host-orchestrated:
the child implements while the host retains git, scope, and verdict authority.
Read [orchestration.md](../plugins/flow-next/docs/orchestration.md) and
`flowctl usage` before changing or using model steering or bridge routes.

Pass resolvable artifact paths and commit ranges instead of embedding evidence
bodies in prompts. Preserve the no-embed dispatch contract; prompt payload
fitters and truncators are not a remedy. Genuine transport limits stay explicit.
[STRATEGY.md](../STRATEGY.md) holds the rationale and active product boundaries;
[GLOSSARY.md](../GLOSSARY.md) owns vocabulary.

## Sources and ownership

- Canonical product sources live under `plugins/flow-next/`. Never hand-edit
  `plugins/flow-next/codex/`; `scripts/sync-codex.sh` generates that mirror.
- Canonical skills use Claude-native tool names. Codex transforms and portable
  host fallbacks belong to the existing platform machinery. Read the
  [cross-platform checklist](adding-skills.md#cross-platform-patterns) when
  changing a skill, agent, command, hook, transform, or installer.
- For those changes, run `./scripts/sync-codex.sh` twice to verify idempotency
  and commit generated changes with their source. Preserve transform/guard
  pairs and validate the installed consumer layout, not just the source tree.
- Read [setup.md](setup.md) before changing setup, snippets, artifact resolution,
  or their transforms. Setup-block rejects symlink targets deliberately.
- Avoid feature flags and compatibility scaffolding without a demonstrated
  requirement. Do not add commands, agents, or skills unless requested.
- Preserve user-authored specs and recorded decisions. A settled design choice
  may be discussed as FYI; do not re-litigate it as a merge gate. Missing
  checklist ceremony or dogfood records are not merge gates.

## Verification

Python is 3.11+ and pure stdlib for flowctl. `jq` and `gh` support the review and
PR plumbing. Component-specific tooling belongs in its component guide.

Use focused suites in task Quick commands. Run the full suite once at the final
handoff gate, including for root docs, `agent_docs/**`, and plugin docs changes:

```bash
python3 scripts/run_tests_parallel.py
uvx ruff@0.16.0 check .
```

`--serial` is the test runner's fallback. Docs-only classification does not
waive this repository's unit gate: content and contract tests cover these
surfaces. Re-run affected checks after fixes; a prior green is not evidence for
a changed tree.

Keep the Ruff pin aligned with `.github/workflows/test-flow-next.yml`. Its
correctness-only rules are explained in `ruff.toml`. Do not add or remove a
rule merely to make a diff pass; document evidence for a policy change there.
Do not use unsafe fixes or lint fixes on generated `.flow/` and `codex/` copies.
Never enable lint rules that rewrite prompt strings (ISC, Q, UP032, COM, W291,
D). Intentional prompt changes update `test_prompt_text_pinned.py` in the same
commit with a wording-change rationale; lint/refactor work must not alter them.

The four extracted review prompt fallbacks are byte-identical template mirrors.
`VALIDATOR_TEMPLATE_FALLBACK` and `DEEP_PASSES_FALLBACK` are intentional
condensations, not drift. Preserve that distinction.

[Standing criteria G1/G2](../.flow/criteria.md) govern prose growth and test
shape. Never reintroduce frozen char/token ceilings, live-skill hash freezes,
or sentence-level prose assertions. Use the real no-embed dispatch test as the
behavioral model. Conduct checklists are conditional review rubrics; read the
[conduct index](conduct/README.md) when reviewing skill prose, not on every task.

Conditional generated-artifact checks:

- `flowctl.py` or `flowctl_tracker/`: run `python3 scripts/gen_tracker_manifest.py`
  and `./scripts/sync-codex.sh` twice; include required generated updates.
- Config key added, renamed, or retyped: update the table in
  `scripts/gen_flow_config_schema.py` (or its machine-written-key allowlist),
  regenerate the committed schema, and keep its drift test green.

## Repository work and delivery

Flow-Next owns repository implementation specs/tasks. This does not replace a
maintainer's personal reminder system. Use `flowctl` for Flow state, not
TodoWrite or markdown TODO lists. When task-state orientation is needed, run
`flowctl brief` once, then inspect the relevant spec/task. For unfamiliar syntax
use `flowctl <command> --help`; `flowctl usage` supplies broader examples.
For local CLI work use `plugins/flow-next/scripts/flowctl` if PATH lacks it.

Use the canonical [spec template](../plugins/flow-next/templates/spec.md), with
`SPEC.md` then `spec.md` taking precedence when present. Plan accepts understood
feature requests or existing Flow items; capture synthesizes conversation
requirements. Use the established skill contract for the selected operation.
Reference applicable G-IDs; never duplicate standing criteria as R-IDs.

`flowctl done` writes a receipt into the tracked task file after implementation
commits. Stage and commit its reported `modified_paths`; verify status and
preserve other work. Bulk creation uses `flowctl task create --spec <id>
--from-json tasks.json --json` when needed.

When a PR is requested for a Flow spec, use make-pr. For a chore without a spec,
write a concise summary, changes, validation, and version note. Use resolve-pr
for requested review-feedback resolution. Only the opt-in land skill has a
standing skill-level merge license, bounded by its gates; otherwise merging
needs the user's explicit instruction. A requested direct commit/push does not
require opening a PR.

Version bumps are batched. Implementation goes under `## Unreleased` when a
user-facing changelog entry is warranted; never run `scripts/bump.sh` or touch
version manifests merely because a spec names a target version. Pure developer
guidance changes need no version bump. Read [releasing.md](releasing.md) only
when preparing a release or writing a changelog entry.

Update affected public docs and flow-next.dev for user-facing product changes.
The maintainer's private downstream policy owns additional local properties;
do not copy private paths into public guidance. Developer-only instruction
maintenance does not require a customer release announcement.

## Conditional references

| Task | Read |
|---|---|
| Product direction or a new architecture boundary | [STRATEGY.md](../STRATEGY.md), [GLOSSARY.md](../GLOSSARY.md) |
| Add/change skills or platform behavior | [adding-skills.md](adding-skills.md) |
| Setup, instruction snippets, artifact resolution | [setup.md](setup.md) |
| Local plugin loading or integration testing | [local-dev.md](local-dev.md) |
| Prompt optimization or an evaluation | [optimizing-skills.md](optimizing-skills.md) |
| Documentation or changelog prose | [writing-docs.md](writing-docs.md), [releasing.md](releasing.md#changelog-writing-gate) |
| Subsystem reference | [documentation index](../plugins/flow-next/docs/README.md) |

For performance/evaluation work, also read the maintainer-local notes in
`.claude/CLAUDE.md` if present, on any host. They point to private research;
keep that material local. Use later dated outcomes over earlier proposals.
