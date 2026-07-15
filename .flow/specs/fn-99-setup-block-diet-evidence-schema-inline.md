# fn-99 Setup-block diet: evidence schema inline, minimal tracking block, usage.md trim

## Goal & Context
<!-- scope: business -->

An 18-run clean-room guidance eval (2026-07-15: claude -p sonnet/haiku + codex exec terra-medium in scratch repos, 4 guidance arms, deterministic .flow-state grading; maintainer memory note `usage-md-guidance-eval-2026-07-15`) measured how much documentation agents actually need to use flow-next correctly:

- The setup-written "## Flow-Next" block (~575 tokens, always-loaded in every session of every flow-next repo) reliably produces `done` WITHOUT valid evidence - 3/3 sonnet reps plus the haiku floor - because it names `--evidence-json e.json` but never shows the schema, and `flowctl done --help` names the flag but not the shape. The ONLY failure mode measured anywhere.
- A ~90-token block with the inline evidence example strictly dominates: 7/7 outcomes on sonnet-5, terra-medium, AND haiku-4.5 (weakest-tier floor holds).
- `.flow/usage.md` (~5.3k tokens, on-demand) buys efficiency, not correctness: bare-guidance agents take ~2.3x the flowctl calls exploring `--help` but complete everything. Its `## Common Commands` (lines 48-194, the largest section) duplicates `--help`.
- Zero TodoWrite/markdown-TODO violations in 18/18 runs from a single prohibition sentence.

External grounding (practice research): Anthropic guidance says inline the minimal set that fully determines behavior; schema examples anchor output shape better than prose; `--help` discovery is a legitimate layer; prohibitions must stay literal; re-verify on the smallest routed model after any trim.

Goal, in strict value order: (1) evidence schema into the always-loaded block; (2) block diet toward ~250 tokens; (3) usage.md trim gated on an extended eval. Zero-quality-loss standard (fn-82/fn-85 conventions).

## Architecture & Data Models
<!-- scope: technical -->

Ground truth from research (corrects the draft's assumptions):

- The block lives in `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md` (42 lines, ~575 tok) with a HAND-MAINTAINED lockstep twin `templates/agents-md-snippet.md` (identical except `/flow-next:` vs `$flow-next-` invocation syntax; selection at `workflow.md:691-696`). sync-codex.sh does NOT generate the agents twin.
- Refresh on re-run is ALREADY marker-based (`workflow.md:698-712`): no marker -> append; marker present -> byte-compare vs new canonical -> identical = no-op, different = AskUserQuestion (Keep mine / Overwrite). CONSEQUENCE (gap analysis): byte-compare cannot distinguish stale-pristine from user-customized, so shipping ANY block change makes every existing repo hit the prompt - users who decline never get the correctness fix.
- No test pins the snippet contents today; `test_dogfood_template_parity.py:36-45` pins usage.md template <-> `.flow/usage.md` byte parity; sync-codex.sh CI guard (`:1654-1666`) fails on literal `/flow-next:` refs surviving in the mirror's usage.md copy.
- `cmd_done` accepts evidence keys `commits`/`tests`/`prs` (loose validation, flowctl.py ~17867); the canonical example string already exists at usage.md:268 and in `agents/worker.md:381-421` (worker teaches the schema with a worked example - the block's new example must match that shape exactly).
- usage.md section map: CLI :5-11 keep; File Structure :12-40 cut; IDs :41-47 keep; Common Commands :48-194 prime cut (duplicates --help); Orchestration :195-256 keep; Workflow :257-264 keep; Evidence JSON :265-270 keep; Parallel Worktrees :271-282 keep; Deprecation :283-293 cut; More Info :294-297 keep.

Design decisions (from gap analysis, binding):

1. **Pristine-upgrade detection via thin flowctl plumbing.** Mechanics (marker-scoped replace, per-target `setup.block_hashes` map, transition table - see API Contracts) live in a small unit-testable flowctl helper; workflow.md calls it and owns only the ask. Per-target keying is required because Codex installs can carry BOTH files with different canonical bytes (slash vs dollar syntax). This makes R1's fix actually reach existing pristine installs silently.
2. **Snippet lockstep test.** New test asserting claude-md-snippet.md == agents-md-snippet.md modulo the known invocation-syntax substitutions (same pattern as dogfood parity). Kills the silent-desync class.
3. **Token-budget tripwire tests.** Assert claude-md-snippet.md <= 300 tokens-equivalent (chars/4) and templates/usage.md <= 2.8k tokens-equivalent, with a comment pointing at this spec's eval - the durable guard R4's honor-system gate lacks. Budgets deliberately sit above targets to allow drift headroom without letting regrowth go unnoticed.
4. **Sandbox-blocked-commit guidance goes where autonomous agents READ**: one line in `agents/worker.md` near its evidence/commit teaching (primary) AND one line in usage.md's Workflow section (ad-hoc agents). Eval showed on-demand docs are exactly what unattended loops skip.
5. **usage.md consumer audit before cutting**: grep all skills/agents/docs for `usage.md` section-specific pointers; any section still pointed at is kept or the pointer updated in the same change.
6. **Eval harness home**: `agent_docs/guidance-eval/` (runner script + scenario prompts + README with the grading contract), following the tracker-sync-spikes dev-archive precedent. Harness runs `claude -p --bare` (without --bare, `~/.claude` global state leaks in - observed round-1 contamination) and `codex exec` with explicit `--sandbox`/`--skip-git-repo-check`. Results recorded in the README's ledger table, optimization-log style. Not CI-wired (dev tool).

## API Contracts
<!-- scope: technical -->

One thin flowctl plumbing addition (fits the skill+plumbing architecture rule - deterministic mechanics belong in flowctl, judgment stays in the skill): a `flowctl` helper the setup skill calls for block install/refresh mechanics - marker-scoped replace, per-target hash record/compare, transition decisions. State: `.flow/meta.json` `setup.block_hashes` map keyed by target file (`{"CLAUDE.md": "<sha256>", "AGENTS.md": "<sha256>"}`); values are sha256 over the canonical block bytes with newline normalization to `\n`. Defined transitions: no marker -> append + record hash; marker + installed-hash == recorded -> pristine -> silent replace + update hash; marker + mismatch or hash-absent -> surface to the skill, which asks (Keep mine / Overwrite); on Keep with hash absent -> record the sentinel value `"customized"` (never re-ask, never silently overwrite); on Overwrite -> replace + record new hash; abort -> no writes. Old installs: map absent -> hash-absent path, at most one ask ever thanks to the sentinel.

## Edge Cases & Constraints
<!-- scope: technical -->

- Zero-quality-loss: every cut must be duplicated in `--help`, demonstrated unused by the eval, or unreferenced by the consumer audit; when in doubt, keep.
- The two snippet templates must change in lockstep (hand-maintained twins) - the new lockstep test enforces from now on.
- usage.md changes land 3-way atomically (template + `.flow/usage.md` dogfood + codex mirror regen) or parity/CI fails.
- New prose in usage.md must survive sync-codex.sh's `/flow-next:` -> `$flow-next-` rewrite (or be syntax-neutral) - CI guard at sync-codex.sh:1654.
- The block's evidence example must be STRUCTURALLY identical to what worker.md teaches and cmd_done accepts: exactly the keys `commits`/`tests`/`prs`, each a list of strings (byte equality is impossible - worker.md uses concrete values and its operative evidence adds `base_commit`; the block uses placeholders). The lockstep/shape test asserts parsed-JSON key set + value types, not bytes.
- Interrupted marker-replace mid-write: the writer already uses whole-file rewrites via the setup flow; keep it that way (no partial-marker states).
- token counts: chars/4 convention; record before/after in CHANGELOG. The <=250 block target is a target; the test budget (300) is the hard line.
- Overlapping open specs (file-level, no logical deps): fn-96 (same workflow.md neighborhood + usage.md copy gate), fn-94 (adds a recipe to usage.md orchestration section - KEPT section, conflict-risk only), fn-85 (tier-C sweep lists setup), fn-98 (self-bridge parenthetical). Whichever lands second rebases; fn-99 tasks note this.
- Weak-model floor: post-trim eval must include the haiku arm (practice guidance + round-2 precedent).
- Loading-contract wording: repo + docs-site orchestration pages currently say usage.md is "read every session"; this spec's framing (on-demand) must be reconciled during the consumer audit - correct the claim to the actual loading contract wherever stated, preserving section anchors.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The setup-written block includes the inline evidence-schema example; a fresh clean-room agent run (sonnet, block-only arm) completes `done` with valid evidence.
- **R2:** The block is <=250 tokens (chars/4) while retaining: flowctl-only + no-TodoWrite rules, quick command shape, spec-creation guidance incl. template cascade, re-anchor rule, evidence schema, usage.md pointer.
- **R3:** Setup re-run refreshes an existing block in place without touching user content outside it.
- **R4:** The guidance eval is extended with a multi-task/deps/reset scenario and re-run green on the trimmed docs (minimal arm; sonnet + terra + haiku floor) BEFORE the usage.md trim merges; harness committed as a repeatable script under agent_docs/guidance-eval/ using `claude -p --bare`.
- **R5:** usage.md trimmed to ~2-2.5k tokens with the keep-list intact plus the sandbox-blocked-commit guidance line; dogfood copy + codex mirror in lockstep; parity test green.
- **R6:** CHANGELOG Unreleased entry with before/after token counts; docs-site changelog staged. No version bump (batched).
- **R7:** Docs downstreams staged in the same workstream (docs-site; maintainer walks private downstreams at release).
- **R8:** Pristine-upgrade detection: setup records the written block's hash in the per-target `setup.block_hashes` map in meta.json (keyed by target file - CLAUDE.md and AGENTS.md hash independently); re-run silently refreshes hash-matching (uncustomized) blocks and asks only for genuinely customized ones; hash-absent installs get at most one ask ever (the `"customized"` sentinel records a Keep).
- **R9:** A lockstep parity test asserts the two snippet templates are identical modulo the documented invocation-syntax substitutions.
- **R10:** Token-budget assertion tests exist for claude-md-snippet.md (<=300 tok-equiv) and templates/usage.md (<=2.8k tok-equiv), commented with the eval rationale.
- **R12:** The block install/refresh mechanics are implemented as a thin flowctl helper with an automated fixture test covering: both targets simultaneously, pristine refresh, customized Keep/Overwrite, hash-absent migration (incl. the `"customized"` sentinel), malformed metadata, outside-marker byte preservation, hash update only after successful write, and idempotent re-run.
- **R13:** The eval baseline is named and attributable: task .2's baseline runs post-block-diet / pre-usage-trim (task .2 depends on .1), with an explicit scenario x arm x model x repetition matrix recorded in the ledger.
- **R11:** A consumer audit (skills/agents/docs grep for usage.md section pointers) runs before the trim; every cut section is unreferenced or its pointers are updated in the same change; the sandbox guidance line also lands in agents/worker.md near its evidence teaching.

## Boundaries
<!-- scope: business -->

- NOT touching the model-routing scaffold block (fn-97's) or flowctl behavior/validation.
- NOT cutting content that serves untested flows (worktrees, orchestration, IDs compat stay).
- NOT a general prose pass over skills (fn-83/84/85 territory); NOT fn-96's copy-gate work (coordinate on rebase only).
- The eval harness is a dev tool: committed + documented, not CI-wired. The token-budget tests ARE CI (cheap, deterministic).

## Decision Context
<!-- scope: both -->

- Value ordering (schema line > block diet > usage.md trim) follows measured impact; usage.md is on-demand so its trim carries the least ROI and the most risk - hence the eval gate and consumer audit.
- Pristine-upgrade hashing (R8) exists because shipping this very spec's block change would otherwise prompt every existing repo with "Keep mine / Overwrite" - users declining never receive the R1 correctness fix. Hash-at-write is the smallest mechanism that distinguishes stale-pristine from customized; prior-canonical hash lists were rejected (unbounded, misses local edits that coincide with old canonicals).
- Sandbox-commit guidance placement (worker.md primary) follows the eval's own lesson: unattended agents read their packaged prompts, not on-demand docs.
- Token-budget tests over CI-wiring the eval: the eval is judgment + network + model-dependent (wrong for CI); budget regression is the mechanical proxy that catches doc regrowth, with the eval re-run reserved for content changes.
- Harness containment (plan-review finding): the runner keeps `codex exec --sandbox danger-full-access` (workspace-write demonstrably blocks `git commit` in scratch dirs and confounds grading) but adds operational hardening: per-run timeout + process-tree termination, unique run ids, cwd + nested-git-root preflight before any bridge call, retained stdout/stderr/grade artifacts per run, and a final failed/incomplete summary. A container/VM requirement was DECLINED with rationale: this is a maintainer dev tool in agent_docs/, same trust level as the maintainer's daily `danger-full-access` codex usage; the README documents the exposure so other contributors can choose containment.
- Eval methodology conventions (2026-07-14/15): clean-room bridge agents (`claude -p --bare`, `codex exec` explicit sandbox), >=3 reps on discriminating cells, deterministic state grading, weak-model floor arm, scratch dirs under the harness's own tmp.
- The current block's failure generalizes: an instruction naming a flag without its value shape produces confident wrong usage; examples beat references for schemas (Anthropic guidance concurs).
