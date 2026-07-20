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

1. **Snapshot-based `config get`** (the one new flowctl feature; design revised per review round 1). Two read forms, one mechanism:
   - `flowctl config get --json` (NO key): the ROOT snapshot - the entire merged config as `{"key": null, "value": {...}}` (`--raw`: set-only values, absent leaves omitted, not defaulted). This is what plan (tracker+memory+scouts+artifacts namespaces) and pilot (pilot+pipeline) consume in ONE call - no common prefix exists for them, so prefix reads alone cannot meet R4/R5.
   - `flowctl config get <prefix> --json`: subtree when the resolved key maps to a dict (`{"key": "land", "value": {...}}`); scalars byte-identical to 2.20.0.
   Mechanism: a COMMAND-SCOPED config snapshot - read config.json raw at most once, derive the merged view once, and pass the snapshot into `resolve_config_key_for_read` via a new optional parameter (default None preserves current behavior for every other caller). Parse contract: AT MOST one parse; exactly one when config.json exists. No cache outliving the command (no staleness after `config set`). Alias-seam contract (map currently empty): subtree/root output always emits CANONICAL keys; a persisted legacy leaf is surfaced under its canonical name with the existing read-warning behavior; raw mode mirrors the same canonicalization. Do NOT fork a second resolver (fn-111 deletes the alias machinery next door; land this first, fn-111 rebases).
2. **`task create` create-time completeness** (scope corrected: `--acceptance-file` ALREADY EXISTS on task create - only description and frontmatter are missing):
   - NEW `--description-file <p>`: same normalization pipeline as set-spec's description path (H2-layering per fn-79).
   - NEW `--satisfies R1,R3` (comma list): writes the `satisfies:` YAML frontmatter block at create time. MECHANISM (no existing writer - `set-spec --file` accepts a pre-rendered document; the only current satisfies code is a reader): a new small zero-dependency task-frontmatter renderer used by task creation, emitting the frontmatter block above the document body. Grammar: comma-separated tokens, whitespace-trimmed; empty tokens rejected; duplicates rejected (error, not dedupe); input order preserved; each token must match the CANONICAL R-ID grammar `R[1-9][0-9]*[a-z]?` (the spec template supports sibling ids like R4a/R4b; R0, uppercase suffixes, and multi-letter suffixes are invalid); tests cover R1, R10, R4a, invalid R0, invalid R4A/R4ab, duplicates, ordering; any malformed value errors BEFORE either output file is written. Equivalence test: `task create --satisfies` output parses identically (via the existing reader) to an equivalent create + `set-spec --file` with a frontmatter-bearing document. This removes the last reason a freshly planned task needs a follow-up set-spec call.
   - Regression guard: existing `--acceptance-file`-only invocations must stay byte-compatible (explicit test).
   - Input handling: all file reads complete BEFORE any task JSON/markdown is written; explicit cases for missing file, unreadable file, directory-as-path, and partial flag combinations. Files only, no stdin.
3. **Skill callsite updates** (single-emission discipline, fn-81):
   - land workflow.md Phase 0: `cfg()` 7 calls -> ONE `config get land --json` + jq lookups from the captured subtree.
   - plan steps.md: ONE root-snapshot `config get --json` early replaces the 5 scattered reads (<=2 total if sync-gating order forces a late leaf read); use `spec create --branch` (drop the set-branch call); use `task create --description-file --acceptance-file --satisfies ...` - ONE call per task, no follow-up set-spec on the plan path at all (set-spec remains for later edits/interview write-backs).
   - pilot: SKILL.md is the snapshot OWNER (control flow: SKILL.md resolves PILOT_AUTONOMY from config BEFORE workflow.md loads, so workflow-owned capture would leave mode detection configless or force a second call). SKILL.md captures the root snapshot once during mode detection and derives/exports PILOT_AUTONOMY; workflow.md and references/backlog-mode.md derive gateClasses and pipeline.qa from the captured snapshot - EXACTLY ONE config call across all three pilot files, located in SKILL.md. ANCHOR WARNING: pilot was restructured since fn-101 - the worker MUST re-scout current fence structure first. Respect the split file; do not inline backlog-mode.md.
   - make-pr workflow.md Phase 0: collapse the 8 read-only fences to <=3; the tasks-done validation (§0.5) keeps its semantics - the earlier validation-only `show >/dev/null` folds into it.
   - impl-review SKILL.md: merge the 3 `for arg in $ARGUMENTS` fences (L155/175/219) into one.
   - plan-review: single-source the per-backend blocks (SKILL.md L60-138 vs workflow.md) - one canonical location, the other references it. PRESERVE VERBATIM: the Foreground rule (SKILL.md:124) and the deterministic-cap SENTENCE (flowctl-owned counter, ESCALATE + exit 4). The verbatim guarantee is deliberately NARROW: if adjacent prose still describes an agent-context iteration counter, that prose is stale (fn-90 moved the cap into flowctl) and MAY be removed/reworded - the invariant is "no agent-side counting is (re)introduced", not "every old sentence survives".
4. **Durable prose tests** (review round 1): a new structural test file pins the diet invariants so they survive future edits - per-skill assertions on the markdown itself: land has exactly one `config get` invocation in Phase 0; plan contains no `spec set-branch` on the create path and no `task set-spec` on the create path; impl-review has one `for arg in $ARGUMENTS` fence; plan-review's per-backend block exists in exactly one file; exactly one config call across pilot's three files (SKILL.md + workflow.md + references/backlog-mode.md), located in SKILL.md - zero in the other two; protected prose (Foreground rule, cap sentence) present byte-exact. Plus a reproducible before/after plan fixture measuring flowctl invocation counts.
5. **Cross-platform**: sync-codex.sh x2 + commit mirror; canonical files stay Claude-native; no new Claude-only constructs without portable-host clauses. Dual-copy flowctl invariant (both copies, same commit).
6. **Docs** (task .3) - honoring the POST-fn-117 register (Messaging Library rules: mechanical precision, NO speed/process brags, role labels, plain imperative tone):
   - flowctl.md: `config get` documents ALL THREE read forms (keyed scalar, keyed subtree, keyless root) incl. `--raw` behavior and exact JSON shapes per form; `task create` flag list gains `--description-file` AND `--satisfies` (comma-list grammar, R-ID token rule, error-before-write, relationship to later set-spec edits); `spec create` paragraph notes create-time branch replaces the create-then-set-branch two-step (set-branch = renames).
   - CHANGELOG: new `## Unreleased` above 2.20.0, established bold-lead + fn-id style, "Dual-copy flowctl mirrored." No version bump.
   - .flow/usage.md: the two canonical example lines gain the new flags inline incl. `--satisfies` (one-line diffs, keep terse).
   - flow-next.dev: cli-reference.mdx L27-29 two-call pattern collapsed to create-time `--branch` (mention rename path); configuration.mdx documents all three read forms (scalar/subtree/root) with JSON shapes after the single-key examples; cookbook.mdx scanned for stale two-call recipes; pnpm build green.

## Boundaries / non-goals

- Review-handler self-write status: DEFERRED to fn-112 (same call sites as the registry collapse; the fn-112/113/114/115 agent owns that region). rp review-rounds folding goes with it.
- Work skill (phases.md/worker.md) untouched - and note for fn-118's planner: fn-118's Boundaries line claiming fn-110 touches phases.md is stale; fn-110 never did.
- No behavior changes to config semantics (merged-vs-raw precedence identical; scalar reads byte-compatible). No new config leaves.
- Coordination: fn-111 (config-alias removal) rebases on this; fn-114's RALPH_ITERATION dedupe is not touched here.
- fn-83's decision boundary not implicated (no gate/receipt code touched).

## Decision context

- Root snapshot + prefix subtree over `--keys a,b,c`: plan and pilot span namespaces with no common prefix, so the keyless root read is the primary consumer surface; prefix subtree serves single-namespace consumers (land); scalar behavior unchanged keeps every existing caller safe. One mechanism (the command-scoped snapshot) backs all three forms.
- create-time completion over post-create set-spec: `--description-file` matches the existing acceptance-file surface, and `--satisfies` (a new tiny frontmatter renderer with a strict R-ID grammar) removes the final reason for a follow-up call - the plan path becomes one call per task. Files only, no stdin (two-document stdin needs a delimiter grammar nobody wants).
- Deferral of the review-handler item: spec-scout verdict - landing it first forces fn-112 to re-derive or revert it mid-collapse; wasted work in a region another agent actively holds.
- Docs register: fn-117 shipped the copy rules; a CLI-mechanics change documents itself in plain imperative style, no "fewer round-trips!" marketing.

## Acceptance Criteria

- **R1:** `config get` snapshot mechanism: keyless root read returns the full merged config (raw parity: set-only); prefix reads return dict subtrees; scalar reads byte-identical to 2.20.0; AT MOST one config.json parse per invocation (exactly one when the file exists), snapshot passed into the existing resolver via optional parameter; subtree/root output emits canonical keys with existing alias warning semantics. Tests cover root/subtree/scalar/raw/missing-key/alias-seam/parse-count.
- **R2:** `task create` gains `--description-file` + `--satisfies` (acceptance-file pre-exists and stays byte-compatible, regression-tested); sections + frontmatter identical to an equivalent create+set-spec; all input files read before any write; tests cover missing/unreadable/directory-as-path/partial-flag cases and acceptance-only back-compat.
- **R3:** land Phase 0 makes exactly 1 `config get` invocation (was 7), captured-subtree lookups replacing `cfg()`.
- **R4:** plan happy path: config reads <=2 (one root snapshot + at most one ordering-forced leaf); `spec create --branch` used (no set-branch on the create path); every task created in ONE call (`--description-file --acceptance-file --satisfies`) with zero follow-up set-spec on the plan path; the committed before/after fixture (a standard 4-task, all-frontmatter plan) shows >=40% fewer flowctl invocations.
- **R5:** pilot tick: EXACTLY ONE config call across SKILL.md + workflow.md + references/backlog-mode.md, located in SKILL.md (mode detection captures the root snapshot; the other files derive from it); remaining duplication consolidated per fresh re-scout; no repeated `show` of the same id within a tick where state has not changed.
- **R6:** make-pr Phase 0 has <=3 read fences with §0.5 semantics intact; impl-review has one argument-parse fence; plan-review per-backend block single-sourced; Foreground rule + the deterministic-cap sentence byte-preserved while stale agent-counter prose (if any) is removed - the structural test suite (R7b) pins all of these.
- **R7:** sync-codex.sh x2 idempotent with mirror committed; dual-copy parity (cmp); full unittest + smoke (temp-dir) green.
- **R7b:** durable structural prose tests exist and are green: per-skill invariants (fence counts, prohibited old calls, single-sourced backend block, protected prose byte-exact, backlog-mode.md config-call-free) + the reproducible before/after plan fixture.
- **R8:** Docs updated per the post-fn-117 register (no speed-brag framing): flowctl.md sections, CHANGELOG `## Unreleased` entry, usage.md example lines, flow-next.dev cli-reference + configuration (+ cookbook scan) with `pnpm build` green.

## Early proof point

Task fn-110.1 validates the core mechanism (the command-scoped snapshot backing root/subtree/scalar reads with byte-compatible scalar behavior, plus the create-time frontmatter renderer). If snapshot threading through the resolver cannot preserve scalar byte-compatibility cleanly, re-evaluate toward explicit `--root`/`--subtree` flags before touching any skill callsites in fn-110.2.

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
| R7b | durable structural prose tests | fn-110.2 | - |
| R8  | docs per new register | fn-110.3 | - |

## References

- fn-101 audit plan section 4 (round-trip census) + the 2026-07-20 scout re-verification (current anchors inline above).
- flowctl.py:1466 (resolve_config_key_for_read - reuse), :7243 (cmd_config_get), :13586 (spec create with --branch), :13712 (task create - flags gap), :17355 (task set-spec helpers to reuse), :14391 (set-plan-review-status - NOT touched, deferred).
- Memory: skill-prose-must-match-real-flowctl-2026-06-10 (verify JSON emitters before review); rename-smoke-rewire-variable-form-cli-2026-05-09 (smoke discipline); fn-81 single-emission discipline.
- land/workflow.md:53 (cfg), plan/steps.md:97/127/279/286/414/427, impl-review/SKILL.md:155/175/219, plan-review/SKILL.md:60-138/124/263.
