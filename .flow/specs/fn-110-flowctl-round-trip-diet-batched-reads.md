# fn-110 flowctl round-trip diet: batched reads and writes for hot skills

> Planned 2026-07-20 (autonomous pipeline run; review backend codex). Refined from the fn-101 audit census with a fresh 4-scout re-verification against 2.20.0 (fn-102/103/116 changed skills and gates; fn-117 rewrote docs). Two scope corrections from scouting are baked in below.

## Overview

Each skill Bash fence costs an agent round-trip plus ~0.4s flowctl startup; hot skills spend 10-20 per run. The fn-101 census identified the offenders; scouts re-verified them at 2.20.0: land's `cfg()` helper makes 7 sequential `config get` startups (land/workflow.md:53), plan scatters 5 single-key config reads across its run (steps.md L97/127-128/536/599) and pays avoidable write round-trips per spec and per task, pilot re-reads config per tick, make-pr runs 8 read-only Phase-0 fences, impl-review fragments argument parsing into 3 fences (SKILL.md L155/175/219), and plan-review duplicates its per-backend block across SKILL.md and workflow.md.

SCOPE CORRECTIONS (scout-verified 2026-07-20):
- `spec create --branch` ALREADY EXISTS in flowctl (flowctl.py:13586, parser :32617) and is documented in flowctl.md - the plan skill simply does not use it (steps.md:279 create, :286 separate set-branch). That item is a skill-callsite fix, not a flowctl feature.
- `task set-spec` already combines description+acceptance in ONE call (plan uses create + set-spec = 2 calls per task, not 3). The remaining win is create-time file flags on `task create` (saves 1 call per task, N per plan).
- Review handlers self-writing `plan_review_status` (the original item 3) is DEFERRED to fn-112: it edits the exact 9 review-command clones fn-112 collapses into a registry, a region the fn-112/113/114/115 workstream owns right now. Recorded in Boundaries.

## Quick commands

```bash
python3 -m unittest discover -s plugins/flow-next/tests -q
(cd "$(mktemp -d)" && bash /Users/gordon/work/flow-next/.claude/worktrees/flow-next-optimization-0e3145/plugins/flow-next/scripts/smoke_test.sh)   # guard refuses repo-root invocation
./scripts/sync-codex.sh && ./scripts/sync-codex.sh   # x2 idempotency
cmp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py
cd ~/work/flow-next.dev && pnpm build   # docs-site gate (task .3)
```

## Approach

1. **Subtree/multi-key `config get`** (the one new flowctl feature). `flowctl config get land --json` returns the whole merged `land.*` subtree when the key resolves to a dict; scalar keys behave exactly as today (back-compat absolute). Include `--raw` parity (subtree of set-only values). Reuse `resolve_config_key_for_read` (flowctl.py:1466) per leaf inside one config parse per invocation - do NOT fork a second resolver (fn-111 deletes the alias machinery next door; land this first, fn-111 rebases). JSON shape: `{"key": "land", "value": {...}}` mirroring the scalar shape.
2. **`task create --description-file <p> --acceptance-file <p>`** (new flags): create-time equivalents of `task set-spec`'s file flags, same normalization pipeline (reuse the set-spec section-writing helpers; H2-layering rules per fn-79 apply). `-` stdin NOT supported for two files - files only, matching set-spec.
3. **Skill callsite updates** (single-emission discipline, fn-81):
   - land workflow.md Phase 0: `cfg()` 7 calls -> ONE `config get land --json` + jq lookups from the captured subtree.
   - plan steps.md: batch the 5 scattered config reads into at most 2 (one `config get` subtree/multi-read early; tracker leaf stays where sync gating needs it if ordering demands); use `spec create --branch` (drop the set-branch call); use `task create --description-file/--acceptance-file` (drop per-task set-spec where no satisfies-frontmatter is needed - set-spec REMAINS the path when frontmatter is required, per its --file mode).
   - pilot: consolidate its config reads into one subtree read per tick. ANCHOR WARNING: pilot was restructured since fn-101 (backlog-mode extracted to references/backlog-mode.md) - the worker MUST re-scout pilot's current fence structure first and consolidate only what still duplicates (hard-guard dup SKILL.md-vs-workflow.md if still present; Phase-4 re-reads if still present). Respect the split file; do not inline backlog-mode.md.
   - make-pr workflow.md Phase 0: collapse the 8 read-only fences to <=3; the tasks-done validation (§0.5) keeps its semantics - the earlier validation-only `show >/dev/null` folds into it.
   - impl-review SKILL.md: merge the 3 `for arg in $ARGUMENTS` fences (L155/175/219) into one.
   - plan-review: single-source the per-backend blocks (SKILL.md L60-138 vs workflow.md) - one canonical location, the other references it. PRESERVE VERBATIM: the Foreground rule (SKILL.md:124) and the fn-90 deterministic-cap prose (L263); never reintroduce agent-side iteration counting.
4. **Cross-platform**: sync-codex.sh x2 + commit mirror; canonical files stay Claude-native; no new Claude-only constructs without portable-host clauses. Dual-copy flowctl invariant (both copies, same commit).
5. **Docs** (task .3) - honoring the POST-fn-117 register (Messaging Library rules: mechanical precision, NO speed/process brags, role labels, plain imperative tone):
   - flowctl.md: `config get` subtree subsection; `task create` flag list + one interaction sentence (file flags vs set-spec); `spec create` paragraph notes create-time branch replaces the create-then-set-branch two-step (set-branch = renames).
   - CHANGELOG: new `## Unreleased` above 2.20.0, established bold-lead + fn-id style, "Dual-copy flowctl mirrored." No version bump.
   - .flow/usage.md: the two canonical example lines gain the new flags inline (one-line diffs, keep terse).
   - flow-next.dev: cli-reference.mdx L27-29 two-call pattern collapsed to create-time `--branch` (mention rename path); configuration.mdx gains a subtree-read subsection after the single-key examples; cookbook.mdx scanned for stale two-call recipes; pnpm build green.

## Boundaries / non-goals

- Review-handler self-write status: DEFERRED to fn-112 (same call sites as the registry collapse; the fn-112/113/114/115 agent owns that region). rp review-rounds folding goes with it.
- Work skill (phases.md/worker.md) untouched - and note for fn-118's planner: fn-118's Boundaries line claiming fn-110 touches phases.md is stale; fn-110 never did.
- No behavior changes to config semantics (merged-vs-raw precedence identical; scalar reads byte-compatible). No new config leaves.
- Coordination: fn-111 (config-alias removal) rebases on this; fn-114's RALPH_ITERATION dedupe is not touched here.
- fn-83's decision boundary not implicated (no gate/receipt code touched).

## Decision context

- Subtree read over `--keys a,b,c`: one mental model (key prefix = subtree), no new list-parsing grammar, and land/plan/pilot all want whole namespaces. Scalar behavior unchanged keeps every existing caller safe.
- create-time task file flags over stdin: matches set-spec's existing file-flag surface; stdin multiplexing two documents needs a delimiter grammar nobody wants.
- Deferral of the review-handler item: spec-scout verdict - landing it first forces fn-112 to re-derive or revert it mid-collapse; wasted work in a region another agent actively holds.
- Docs register: fn-117 shipped the copy rules; a CLI-mechanics change documents itself in plain imperative style, no "fewer round-trips!" marketing.

## Acceptance Criteria

- **R1:** `flowctl config get <prefix> --json` returns the merged subtree for dict-valued keys (and `--raw` returns set-only subtree); scalar key reads are byte-identical to 2.20.0; exactly one config.json parse per invocation; unit tests cover subtree/scalar/raw/missing-key/alias-seam.
- **R2:** `task create --description-file/--acceptance-file` writes both sections at create time via the same normalization as `task set-spec` (H2-layering safe); tests cover create-with-files, create-without (unchanged), malformed-file error.
- **R3:** land Phase 0 makes exactly 1 `config get` invocation (was 7), captured-subtree lookups replacing `cfg()`.
- **R4:** plan happy path: config reads <=2; `spec create --branch` used (no set-branch call on the create path); tasks created with file flags where frontmatter is not required (set-spec remains for satisfies-frontmatter); scripted count shows >=40% fewer flowctl invocations on a 4-task plan.
- **R5:** pilot tick: one config subtree read; remaining duplication consolidated per fresh re-scout; references/backlog-mode.md split respected; no repeated `show` of the same id within a tick where state has not changed.
- **R6:** make-pr Phase 0 has <=3 read fences with §0.5 semantics intact; impl-review has one argument-parse fence; plan-review per-backend block single-sourced with Foreground rule + fn-90 cap prose preserved verbatim (diff-checked).
- **R7:** sync-codex.sh x2 idempotent with mirror committed; dual-copy parity (cmp); full unittest + smoke (temp-dir) green.
- **R8:** Docs updated per the post-fn-117 register (no speed-brag framing): flowctl.md sections, CHANGELOG `## Unreleased` entry, usage.md example lines, flow-next.dev cli-reference + configuration (+ cookbook scan) with `pnpm build` green.

## Early proof point

Task fn-110.1 validates the core mechanism (subtree config get with byte-compatible scalar behavior + create-time task files). If subtree semantics cannot preserve scalar byte-compatibility cleanly, re-evaluate toward an explicit `--subtree` flag before touching any skill callsites in fn-110.2.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | subtree config get | fn-110.1 | - |
| R2  | task create file flags | fn-110.1 | - |
| R3  | land 7->1 | fn-110.2 | - |
| R4  | plan read/write diet | fn-110.2 | - |
| R5  | pilot consolidation (fresh re-scout) | fn-110.2 | - |
| R6  | make-pr/impl-review/plan-review fences | fn-110.2 | - |
| R7  | cross-platform + gates | fn-110.1, fn-110.2 | - |
| R8  | docs per new register | fn-110.3 | - |

## References

- fn-101 audit plan section 4 (round-trip census) + the 2026-07-20 scout re-verification (current anchors inline above).
- flowctl.py:1466 (resolve_config_key_for_read - reuse), :7243 (cmd_config_get), :13586 (spec create with --branch), :13712 (task create - flags gap), :17355 (task set-spec helpers to reuse), :14391 (set-plan-review-status - NOT touched, deferred).
- Memory: skill-prose-must-match-real-flowctl-2026-06-10 (verify JSON emitters before review); rename-smoke-rewire-variable-form-cli-2026-05-09 (smoke discipline); fn-81 single-emission discipline.
- land/workflow.md:53 (cfg), plan/steps.md:97/127/279/286/414/427, impl-review/SKILL.md:155/175/219, plan-review/SKILL.md:60-138/124/263.
