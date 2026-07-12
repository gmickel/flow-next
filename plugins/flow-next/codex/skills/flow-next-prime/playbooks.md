# Per-shape playbooks

Prime leads with a **verdict + ranked next-actions**, not a level. This file carries the per-shape playbooks (one per classification), the report-shape templates, and the ranked-actions catalog that the verdict headline draws from. Playbook selection is driven by the Phase 0.5 classification block in [classification.md](classification.md); scoring behavior, pass conditions, and the N/A whitelist live in [pillars.md](pillars.md); per-stack instantiations of the generic patterns live in [stacks.md](stacks.md).

**One-line-pointer discipline (load-bearing).** This file references the GENERIC patterns only - the operability ladder, the LEG1-LEG9 legibility patterns, the ranked-actions catalog. It never restates a pass condition, a criterion-to-score row, an N/A rule, or a stack's concrete instantiation - those have a single home elsewhere and are pointed at, never duplicated. Adding a stack = adding a row in stacks.md, never editing a playbook here.

**Classification is heuristic, degradation graceful.** A misread shape still gets a correct base report (the pillar scores hold); only the playbook block is off. Every playbook block prints under the scored report except greenfield, which suppresses the scorecard entirely (below).

---

## Playbook selector

Selection reads the classification block's axes + `assessment_scope`. Bits are independent, so **more than one playbook block can fire** (a monorepo that is also a constellation member gets both). Order of resolution:

| Classification signal | Playbook block emitted |
|---|---|
| `assessment_scope = constellation-home-base` | **Constellation** (home-base assessment) - the per-repo scorecard is replaced by the constellation-layer assessment |
| `lifecycle = greenfield` | **Greenfield** - scorecard SUPPRESSED, bootstrap plan emitted instead |
| `topology.monorepo = yes` | **Monorepo** block, additive on top of the standard report |
| `topology.constellation-member != none` | **Constellation** block (member variant), additive; light-vs-full variant per the selector below |
| `size.band = large \| huge` OR any legacy/no-LSP stack row | **Huge/legacy** legibility-first block, ahead of pillar detail |
| everything else (`brownfield`, `small \| medium`, standalone) | **Standard single repo** |

`hybrid` lifecycle keeps the standard report with the young-but-real caveat printed. Shape ceilings (Axis 5: library/plugin/prose ceiling = tier 2, per classification.md) cap the operability line inside whichever block fires.

---

## Greenfield

An empty or scaffold-only repo does NOT get the 48-criterion scorecard - a scored husk invites Goodharting the checklist from day one. **The scorecard is suppressed** (per the N/A whitelist's greenfield row in pillars.md) and prime emits an ordered **bootstrap plan** instead: stage-appropriate items in leverage order, each with the exact file to create and why it comes now rather than later.

**Recorded-deferral mechanic.** Pillars that are premature at this stage get a **recorded-deferral N/A line** - a documented "not yet, deferred until X" rather than a silent gap OR a stub file. This is the core greenfield discipline: a documented deferral beats both, because **the stub is the rot generator this whole spec exists to kill**. Example lines: "observability - deferred until first deploy"; "E2E harness - deferred until the first UI surface exists"; "container - deferred until a service boundary exists".

**Bootstrap plan (~8-12 ordered items, adapt to the detected stack):**

1. **Hand-curated agent instruction file seed** - short, commands-first (a handful of fenced runnable commands + a one-line project purpose). NEVER LLM-bulk-generated (measured harm, ETH Zurich arXiv 2602.11988); prime offers a skeleton the human fills, never a generated full file.
2. **`STRATEGY.md` first** - target problem, approach, who it is for (`/flow-next:strategy` exists for this). Direction before code.
3. **Stack decision recorded with exact versions** - runtime + package manager pinned (the version file, the lockfile committed) so day-2 agents do not drift.
4. **Hygiene files** - `.gitignore`, committed lockfile, `.env.example`, `.editorconfig`. NEVER a LICENSE (guardrail - team governance, not agent readiness).
5. **A verify loop before feature 1** - one test command + one smoke command, documented in the agent file. The closed verify loop is the single highest-leverage artifact; it comes before the first feature, not after.
6. **The smallest real CI** - install + lint + test, gated on `pull_request` / default-branch `push` (trigger correctness matters even on day one - see FH3 in pillars.md).
7. **Secrets deny-rules baseline** - the one harness artifact safe to scaffold on an empty repo (deny/ask only; see the safety rules in [harness.md](harness.md)).
8. **First spec = the first vertical slice** with explicit non-goals (`/flow-next:plan`). No big-bang scaffolding; no heavyweight spec ceremony on an empty repo.
9. **Recorded-deferral N/A lines** for every premature pillar (observability, security scanning, containers, E2E), each naming the trigger that un-defers it.

**Anti-pattern rules (hard).** Prime NEVER emits a stub artifact that would pass its own checks unexercised - anything scaffolded in the bootstrap plan is exercised in the same pass (the command runs, the hook fires) or is explicitly marked unverified. No big-bang scaffolding, no full generated instruction file. Under `--fix-all`, greenfield remediation applies ONLY to exercised hygiene files (resolution 5) - never structural or generated artifacts.

---

## Standard single repo (small / medium)

The current scored report, upgraded with the verdict headline (classification + operability tier + hard-gate status + top-5 ranked actions) and the substance pass-conditions from pillars.md.

- **Size-tiered recommendations (bidirectional - over-recommending equals under-recommending as a failure).** Below ~400K LOC do NOT recommend LSP / index / code-intelligence tooling - it is measured net-negative at that size (Sourcegraph CodeScaleBench). Recommend an orientation map + tighter loops instead. Above ~400K LOC, DO recommend it where the stack row in stacks.md supports it.
- **Operability line** names the current ladder tier from executed evidence and the cheapest move up one tier (per the ladder in workflow.md / pillars.md), capped by the Axis-5 shape ceiling.
- LEG4/6/7 (pathology inventory, atomic file-pairs, tool-managed never-edit list) fire here too - they are all-shapes patterns (below), not legacy-only.

---

## Monorepo (exemplar: modern TS pnpm / Nx / Turbo)

Usually already legible - the build graph IS the map. The block is additive on top of the standard scored report:

1. **Per-package command verification** - verify each package's commands work from its own package dir and are file-scoped (`pnpm --filter <pkg> test`, affected-only where Nx/Turbo exists). Per-member operability tiers, NOT one repo tier. Execution is SAMPLED, not exhaustive (resolution 18: deployable members first, then entry members, ~5 member executions and a global wall-clock cap per run; unsampled members are listed NOT ASSESSED, never silently skipped; graph-native `affected` commands may substitute).
2. **Nested per-package instruction files** when >2-3 distinct subsystems or the root instruction file exceeds ~200 lines (nearest-wins per the AGENTS.md spec; reference point: OpenAI's Codex repo carries 88). This is ranked-action catalog item 11.
3. **Scoping config** - read-deny for `dist/` / generated dirs, sparse worktrees for subagents, launch-from-package-dir guidance.
4. **Build-graph agent wiring** when Nx / Turbo / Bazel present - recommend the graph + affected-only run as the feedback loop.
5. **Single-source task-runner rule** - one package manager, one lockfile (verify BS5 / BS6).

Scored per the existing pillars; monorepo N/A handling (BS6) already lives in the pillars.md whitelist.

---

## Huge and/or legacy

A **legibility-first block AHEAD of pillar detail**. The playbook is a set of NAMED GENERIC PATTERNS - LEG1-LEG9. **Skill logic and report prose stay stack-agnostic**: they reference only the pattern names; each pattern's concrete instantiation for a given stack lives ONLY in that stack's row in [stacks.md](stacks.md) (the Delphi row is the worked exemplar that exercises every pattern - it is data, never skill logic). No stack name is hardcoded in a playbook.

**LEG4, LEG6, and LEG7 are ALL-SHAPES patterns** (eval promoted them from the legacy-only playbook - both fired on a modern plugin repo). They run on every report, including the standard single-repo one, not just huge/legacy.

| Pattern | Scope | Definition (generic - instantiations in stacks.md) |
|---|---|---|
| **LEG1** Honest tier + headless-feedback wrapper | huge/legacy | Name the operability tier from executed evidence; at tier 1 the top recommendation is always a one-command headless build per project/module so the agent has a compile feedback loop. Never fabricate a higher tier. |
| **LEG2** Toolchain/license reality check | huge/legacy | Detect when build or code-intelligence tooling is bound to a licensed IDE/machine or an unavailable platform; report what CAN run headlessly on which host; record what cannot as "not probed on this host", never a fabricated pass. |
| **LEG3** No-LSP/no-map honesty + substitute navigation | huge/legacy | When the stack's row says code intelligence / `/flow-next:map` is not practical, say so and recommend the substitute class: (a) a generated dependency-graph artifact, checked in or regenerable (deterministic dependency maps are prerequisites, not nice-to-haves); (b) a hand-written orientation map (top-level dirs, entrypoints, module one-liners); (c) static analysis as the proxy verifier where tests are absent. |
| **LEG4** Pathology inventory as first-class findings | **ALL SHAPES** | Top-N largest files (agents without symbol tooling read whole files - token burn), generated-file globs, binary/opaque artifacts, vendored trees - all excluded from agent-readable scope in the agent file. Generalized to every repo as FH2 in pillars.md. |
| **LEG5** Encoding/codepage sweep (P1 finding) | huge/legacy | BOM/charset sniff on a sample per extension; legacy sources are often ANSI/Windows-1252 or UTF-16, and coding agents have documented corruption bugs on non-UTF-8 files. Recommend a deliberate one-time normalization commit, an encoding-guard hook, or a never-edit list for affected files. Read-only probe - the sweep must never itself corrupt anything. |
| **LEG6** Atomic file-pair rule | **ALL SHAPES** | Detect designer/generator paired files where editing one side without the other corrupts the project, and require a pairing rule in the agent file. |
| **LEG7** Tool-managed never-edit list | **ALL SHAPES** | Files/dirs an IDE or toolchain rewrites, regenerates, or that are semantically opaque get an explicit never-touch list in the agent file. Feeds from the destructive-script scan's "repo-internal dir the same script regenerates" class (FH5). |
| **LEG8** Module carve-outs as the unit of agent-workability | huge/legacy | Name which subsystems are safe agent territory vs frozen (strangler-fig); a carve-out with its own build + tests is what "agent-ready" means at multi-M LOC, never the whole tree. Where the ecosystem's honest answer is migration tooling rather than in-place agent work, say that too. |
| **LEG9** Characterization/snapshot tests as the verify strategy | huge/legacy | Where unit tests are absent and behavior must be preserved during modification, characterization/snapshot tests are the verify strategy. |

The **HP7 read-never-execute vs remediation exercise-what-you-scaffold distinction** applies to LEG5's encoding-guard hook exactly as to any hook: during ASSESSMENT prime reads hook content and never executes it; during REMEDIATION a scaffolded encoding-guard hook is exercised in the same pass. See [harness.md](harness.md).

---

## Constellation-member (exemplar: 99 sibling repos)

**Per-repo priming STAYS VALID** - every repo still gets its own full assessment and fixes. The constellation block is ADDITIVE guidance on top. The variant is chosen by the selector below.

### Full home-base variant (service composition detected)

Recommend the **home-base pattern** (industry-consensus "repo-of-repos" / "virtual monorepo"): a parent dir (optionally a tiny git repo) with siblings as plain gitignored checkouts - NOT submodules (update friction, worktree incompatibility, agents forget to init; exception: deliberate version-pinning). The highest-leverage artifact is a **repo manifest with one-line purposes** (`repos.yaml` / `.md`) that a LEAN parent instruction file points at - the manifest is the single source of truth, never duplicated into the instruction file.

Home-base contents to recommend:
- A lean parent instruction file (workspace map, cross-repo change workflow, git-directory-safety rule, docs-update-as-DoD).
- The repo manifest (one-line purpose per repo).
- Run-everything scripts: clone-all / status-all / test-all (mani / gita / vcstool, or plain scripts; mise `monorepo_root` for the task namespace).
- The constellation docker-compose, a ports + env bootstrap map, a `_plans/` dir for cross-repo plans.

**Platform caveat (state in the report):** Codex ignores an AGENTS.md above the git root (openai/codex#15683), so each per-repo instruction file must link BACK to the home base explicitly; Claude Code `--add-dir` solves access, not knowledge.

**Cross-repo change choreography (documented in the home base):** contract-first ordering (schema -> provider -> consumers), one repo per worker, linked PRs, merge order libraries-before-consumers, contract tests at the boundaries.

**Scale ladder:** manifest + home base at 2-30 repos; a dependency/release-ordering registry at 20+ (Mabl's 79-repo registry cut context-drift failures ~40% -> <5%); recommend TRUE monorepo consolidation only when cross-repo changes dominate (>~30-50% of features touch multiple repos) and no isolation constraint exists - the home base is the middle option capturing most of the benefit at near-zero migration cost.

**Home-base scope.** When `assessment_scope = constellation-home-base`, prime is running in the parent dir itself and assesses the constellation layer (manifest present? compose boots? parent file lean and pointing?) instead of erroring on "no manifest found".

### Lightweight product-family variant (prose/docs coupling only)

A 2-3 repo family (a code repo + a docs site + a sister product) whose coordination need is **docs currency, not service composition**, must NOT receive the home-base / compose / ports boilerplate - the microservice-shaped playbook is oversized there. The right emission is the R15 "Repo context" block naming the siblings plus a **docs-update-as-DoD** line in the agent file.

### Variant selector

| Signal | Variant |
|---|---|
| Service composition detected (constellation docker-compose, cross-service `build: ../`, shared ports/env, contract/OpenAPI coupling) | **Full home base** |
| Prose/docs coupling only (sibling docs site, textual cross-repo references, shared release notes, no service wiring) | **Light product-family variant** |

---

## Ranked-actions catalog

The verdict headline leads with the **top-5 ranked next-actions** drawn from this catalog (leverage order, from research). Each carries a **tier** (Critical / High / Medium / Bonus) that maps to the existing `--fix-all` semantics (resolution 5) and mirrors the remediation.md priority order, plus a **consent boundary**.

**Consent boundaries (resolution 5).** `--fix-all` auto-applies only the Pillars 1-5 in-ROOT fixes at Critical/High/Medium tier. **Explicit-consent-only regardless of tier:** anything outside the repo ROOT (the home-base kit), any harness settings/hook file (deny/ask/hook scaffolds), and ALL structural/playbook artifacts (a generated map, nested instruction files, the home base, the bootstrap plan). On greenfield, `--fix-all` applies only to exercised hygiene files. **Re-run (resolution 6):** Phase 7 re-assessment reuses the session's Phase 0.5 classification and R15 answers; only affected criteria/gates re-verify, so the catalog is re-ranked, not re-derived.

| # | Action | Tier | Consent |
|---|---|---|---|
| 1 | Single verify/smoke command, documented in the agent file | Critical | `--fix-all` (in-root) |
| 2 | Fix/write the agent file BY HAND, short, commands-first (warn against LLM regeneration - measured harm) | Critical | `--fix-all` augment only; never bulk-generate |
| 3 | One-command bootstrap with seeded data (tier-3 stacks) / one-command headless compile wrapper (tier-1 stacks) | High | `--fix-all` (in-root) |
| 4 | File-scoped feedback commands (single test, single-file lint/typecheck) | High | `--fix-all` (in-root) |
| 5 | Non-interactive fast default test command (no watch-mode default; `CI=true` terminates) | High | `--fix-all` (in-root) |
| 6 | Deterministic gates at the RIGHT layer (SV4): format/lint via harness hook or staged-files commit hook; tests via the verify command + acceptance requirements + CI required check - never test suites in pre-commit | High | harness-hook portion = explicit-consent; CI/verify config = `--fix-all` |
| 7 | `.env.example` covering every env var actually read | Critical | `--fix-all` (in-root) |
| 8 | Seeded db reset (where a db exists) | Medium | `--fix-all` (in-root) |
| 9 | Cloud-agent env config (copilot-setup-steps.yml / devcontainer postCreate that installs) | Medium | `--fix-all` (in-root) |
| 10 | Prune doc sprawl; root file becomes pointers ("where to look" table) | Medium | explicit-consent (restructures the instruction file) |
| 11 | Per-package instruction files in monorepos past ~200 root lines | Medium | explicit-consent (structural) |
| 12 | CI/local command parity (CI steps exist as identically named local scripts) | Medium | `--fix-all` (in-root) |
| 13 | Run-and-observe recipe in the agent file + agent-readable dev logs (exact dev command, fixed port, literal ready line, log file location, DEBUG var; agent-tail-style capture) | High | `--fix-all` (in-root, agent-file content) |
| 14 | Documented dev login + seeded test user + a browser surface (test-ids/roles on key elements; Playwright or chrome-devtools MCP entry) so the agent can drive the app past the login wall | Medium | `--fix-all` (in-root); MCP-install portion = explicit-consent |
| 15 | Destructive scripts named in the agent file's never/ask-first tiers (from the destructive-script scan, FH5) | High | `--fix-all` (agent-file content) |

**Structural actions** fire only when classification triggers them and are ALWAYS explicit-consent-only: generate a map, adopt nested instruction files, create the home base, write the greenfield bootstrap plan. Emit every finding with a freshness caveat and a suggested re-run cadence - never imply a durable badge.

---

## Report shapes per classification

The report headline is uniform across shapes: **classification line + operability tier + hard-gate status + top-5 ranked actions**, with the maturity level demoted to secondary metadata below the scores table. The BODY differs per shape:

| Shape | Body |
|---|---|
| **Greenfield** | Scorecard SUPPRESSED. Ordered bootstrap plan (~8-12 items) + recorded-deferral N/A lines. No scores table. |
| **Standard** | Full scored report + verdict headline + size-tiered recommendations. |
| **Monorepo** | Standard report + the monorepo block (per-member tiers, nested-file recommendation, scoping config, build-graph wiring). |
| **Huge/legacy** | Legibility-first LEG block AHEAD of pillar detail, then the scored report. |
| **Constellation-member** | Per-repo scored report UNCHANGED + the additive constellation block (full home base OR light variant per the selector). |
| **Constellation home-base** | Constellation-layer assessment IN PLACE OF the per-repo scorecard. |

**Compression rule (resolution 13, fn-82 discipline).** Failing and ⚠️ criteria render in DETAIL (the finding, the quoted evidence, the ranked fix). **Passing rows compress to one line per pillar** (e.g. "Pillar 1 Style & Validation: 5/6 pass"). The report spends its budget on what needs action, never on a wall of green checkmarks. Group pass-count lines (AO / DR / TO / HP) follow the same rule - one line each unless a member fails.
