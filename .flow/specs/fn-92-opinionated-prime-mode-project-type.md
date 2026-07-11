# Opinionated prime mode: project-type & structure-aware readiness (monorepo vs multi-repo, size, mapping)

> Full spec, ready for `/flow-next:plan`. Captured 2026-07-10 from external-team field feedback; research passes 2026-07-11 (5 research agents, 2025-2026 sources; catalogs and per-stack matrix below). Interview intentionally skipped - the open design decisions are made in Decision Context and flagged for review there. Today `/flow-next:prime` largely checks file/config **existence**, so repos reach "Level 5" without the substance behind it, and there is no way to hand-verify hundreds of repos across 10-11 tech stacks. This spec makes prime **opinionated + structure-aware**: classify what kind of project this is (greenfield | single repo | monorepo | multi-repo constellation), probe size/legibility and operability with bounded deterministic evidence, judge substance not existence, and lead the report with a verdict + ranked next-actions instead of a level.

## Goal & Context
<!-- scope: business -->

At scale, existence-checks lie. A repo can pass prime's criteria - a CLAUDE.md exists, a hook file exists, a script exists - yet be un-agentic in practice: the file is an empty template, the repo is too big to navigate, imports can't be resolved, the app cannot be compiled by anyone but the IDE, or it's really one of 99 sibling repos that only make sense together. Leads/reviewers can't hand-verify at portfolio scale, so a top "readiness level" stops meaning anything. Prime should encode the judgment a senior applies on a first look - how big is this, can an agent find its way around, can it BUILD anything, is this a monorepo or a swarm of repos, is it a day-old empty shell - and say so **opinionatedly**, with a concrete ranked recommendation list rather than a pass/level.

The same prime run must give grounded, realistic guidance across radically different repos: a modern TS pnpm/Nx monorepo (everything works, deepen the loops), a 15M LoC Delphi codebase (no LSP, no map tooling, encoding hazards, compile-only feedback), and a product spread over 99 sibling repos (per-repo priming stays valid, but a home-base coordination layer is the unlock). One playbook per shape, one matrix across stacks.

Origin: a portfolio-company rollout (three product lines), 100+ repos across ~10-11 stacks, where "häufig nur Existenz geprüft -> Level 5 erreicht, ohne dass es stimmt." Gordon owns the write-up.

## Architecture & Data Models
<!-- scope: technical -->

### Mode shape (decided)

**No new mode or flag.** Classification, substance checks, the operability verdict, and the ranked-actions headline become prime's DEFAULT behavior. The existing 8-pillar / 48-criteria scan stays as the evidence layer underneath; existing args (`--report-only`, `--fix-all`, repo-root path) keep their semantics. Rationale: the old existence-only behavior is exactly what fn-92 exists to retire; keeping it reachable behind a flag preserves the failure mode. The one new arg is `--classify-only` (print the Phase 0.5 classification block and exit; cheap portfolio triage over many repos).

Skill layout: three new reference files keep SKILL.md/workflow.md lean, mirroring the existing pillars.md/remediation.md pattern:

- `classification.md` - detection signals, thresholds, confidence tiers (Phase 0.5)
- `playbooks.md` - per-shape playbooks (greenfield, standard, TS-style monorepo, huge/legacy, constellation) + report-shape templates
- `stacks.md` - per-stack readiness matrix (detect / verify / LSP / map support / gotchas)

### Phase 0.5: Classify (new phase, before scout dispatch)

Deterministic, host-inline (no scout), bounded to `git ls-files` / `find -maxdepth` / config-presence / at most one sampled `rg` probe. Produces a classification block that parameterizes everything downstream (scout dispatch hints, N/A denominators, report shape, playbook selection).

**Axis 1 - lifecycle:** greenfield | hybrid ("young but real") | brownfield.
Greenfield = (`git rev-list --count HEAD` < ~25 AND no tags AND no CI config) OR (tracked files < ~30 with no domain source beyond a recognizable generator scaffold - create-next-app, cargo new, uv init, dotnet new fingerprints). Corroborators: repo age, single contributor, no lockfile. Multi-signal, never one heuristic; borderline cases land in hybrid.

**Axis 2 - topology:** single | monorepo | constellation-member.
Monorepo = workspace/build-graph config present (`pnpm-workspace.yaml`, `nx.json`, `turbo.json`, `WORKSPACE`/`MODULE.bazel`, `go.work`, Cargo workspace, `.groupproj` for Delphi, multi-module Maven/Gradle) OR many manifest files under one root. Constellation-member, three confidence tiers:
- (a) LIKELY: sibling dirs with `.git` (`ls ../*/.git`), shared org in remotes, shared naming prefix (`acme-api`, `acme-web`)
- (b) CONFIRMED: parent-level CLAUDE.md/AGENTS.md or manifest (`repos.yaml`, `mani.yaml`, `.meta`, `*.repos`, `workspace.toml`, `default.xml`, `.code-workspace`), parent docker-compose/justfile/mise.toml, `_plans/` dir
- (c) ASK THE USER: only in-repo external references - compose `build: ../other-service` or same-org images, CI checkout of a second repository, OpenAPI/proto client generation pointing at another repo's spec, `go.mod` replace / pnpm `link:` / `pip -e ../` outside the repo, env vars referencing ports of services this repo doesn't define

**Axis 3 - size/legibility band:** small (<100K LOC) | medium (100-400K) | large (400K-2M) | huge (>2M or >20K files).
LOC via `scc` when available (seconds even at 15M LoC), else `tokei`, else file-count x estimate - NEVER `cloc` (8-20x slower), NEVER exhaustive reads. Legibility sub-signals: top-level dir count, entrypoint-glob hits (`main.*`, `index.*`, `cmd/*/main.go`, `*.dpr`, framework markers), packages-vs-instruction-files ratio, tracked generated/vendored code (`vendor/`, `dist/`, `*_pb2.py`, `.dcu`), root instruction file >~300 lines with zero nested files, one bounded grep-ambiguity probe (2-3 core domain identifiers; hundreds of hits predicts wrong-file/wrong-symbol thrash). Empirical anchors: agent pass rates collapse >100K LOC (RepoMod-Bench); code-intelligence tooling is net NEGATIVE <400K LOC and strongly positive 400K-2M (Sourcegraph CodeScaleBench, 1,281 runs) - recommendations must tier accordingly; recommending heavy tooling on a small repo is itself a prime failure.

**Axis 4 - stack(s):** manifest-based detection per `stacks.md` (package.json, pyproject.toml, pom.xml/build.gradle, *.sln/*.csproj + TargetFramework era, composer.json, go.mod, Gemfile, CMakeLists, *.dproj/*.dpr, *.vbp, *.pks/*.pkb, *.cbl). Polyglot count feeds the legibility verdict.

Classification is heuristic: the block always prints its evidence and confidence, and interactive runs confirm low-confidence calls via AskUserQuestion; `--report-only`/autonomous runs state the assumption instead of asking.

### Operability ladder (replaces "can the app run" as the baseline)

The single most important substance signal, graded as a LADDER so legacy stacks get honest treatment instead of a Node-centric fail:

| Tier | Meaning | Verify evidence |
|---|---|---|
| 0 static-parse-only | no compiler/runtime reachable (mainframe, licensed compiler absent) | linter/parser passes on a sample |
| 1 compile-only | agent can build the touched project headlessly | build command exits 0 (bounded timeout ~5 min) |
| 2 compile + test subset | console test runner exists and is discoverable | list-tests/dry-run succeeds (existing TS4 machinery) |
| 3 run | app boots with seeded data; smoke one-liner | port bound / health 200 / ready line within ~60s |

The report names the CURRENT tier (from executed evidence, extending the existing Phase 2 verification - never from config existence) and the **cheapest move up one tier** (e.g. "add a console DUnitX target compiled in CI" for a tier-1 Delphi repo; "add `make bootstrap` chaining install -> services -> migrate -> seed" for a tier-2 web app). Never prescribe "start the app" for a stack whose realistic ceiling is tier 1-2. Tier-3 boot probes run only when a cheap ready-signal is detectable (health endpoint, dev-server ready line) and always time-bounded; otherwise the tier is recorded as "not probed", not failed.

**Hard gates (cap the maturity level regardless of score):** (G1) the detected build command actually runs, or tier >= 1 evidence exists; (G2) tests are discoverable when a test framework is claimed (existing TS4); (G3) commands quoted in CLAUDE.md/AGENTS.md actually resolve/execute. Any gate failing caps agent readiness at Level 2 with the failure named in the headline. This kills "Level 5 with a broken build".

### Substance-not-existence upgrades (specific criteria)

General principle: **execute it (bounded) over parse it; cross-reference it against the code over read it in isolation.** Cross-reference failures (dangling commands, undeclared env vars, CI/local mismatch) are the cheapest high-precision substance detectors, no LLM judgment needed. Concrete criterion changes:

- **SV4 pre-commit hooks:** pass requires hook CONTENT that invokes a real linter/test - `.husky/` with only `_/` scaffold or `echo`, or a pre-commit-config with only whitespace hooks, scores ❌ "stub hook" with the evidence quoted
- **SV5/SV6, BS2/BS3:** the named script must exist in the manifest AND execute (Phase 2 extension); a `lint` script that crashes is ❌ with the error
- **DC2 instruction-file quality (claude-md-scout rubric deepened):** grade on substance tells - repo-specific nouns, >=3 fenced copy-paste-runnable commands in the top ~50 lines, commands appear verbatim in manifests, 1-3 real code snippets, three-tier boundaries with concrete paths, don'ts paired with dos; template tells (generic personas, restated universal conventions, full directory listings, unedited /init scaffold order, placeholders, zero fenced blocks) are DEDUCTIONS. Length band 30-150 lines; >300 flagged. ETH Zurich (arXiv 2602.11988): LLM-generated instruction files reduce task success ~3% at +20% cost while hand-curated add ~+4% - so prime downgrades generated-looking files and its own remediation NEVER bulk-generates a full CLAUDE.md (offers a short, commands-first skeleton the human fills, or an interview-derived augment)
- **DC2 execute check (host, Phase 2):** run 1-2 commands quoted in the agent file; a CLAUDE.md whose stated test command fails is worse than none (feeds gate G3)
- **DE1 .env.example:** diff declared vars against env reads in source (`process.env`, `os.environ`, `getenv`); >~30% undeclared = "stale template" ⚠️
- **DE4 setup script:** must chain real stages (install AND migrate/seed keywords found, or it executes); a setup.sh that only prints instructions is ❌
- **DE5 devcontainer:** empty json with no features/postCreateCommand = "checkbox artifact" ⚠️, not ✅
- **Content the agent could discover itself** (directory trees, standard conventions restated) counts as negative signal in DC2, never neutral

Substance judgment stays skill/scout work anchored to quoted file content and executed evidence (host agent IS the judge, per repo architecture rules) - no new regex engines in flowctl. Fabrication guard: every substance verdict quotes its evidence (file line or command output); no evidence, no verdict.

### Report: verdict + ranked actions headline

The report headline becomes: **classification line + operability tier + hard-gate status + top-5 ranked next-actions** (each with the exact file to create/edit and, where cheap, a starter diff). The maturity level moves to secondary metadata below the scores table. Ranked-actions catalog (leverage order, from research; full list in `playbooks.md`):

1. Single verify/smoke command, documented in the agent file
2. Fix/write the agent file BY HAND, short, commands-first (warn against LLM regeneration - measured harm)
3. One-command bootstrap with seeded data (tier-3 stacks) / one-command headless compile wrapper (tier-1 stacks)
4. File-scoped feedback commands (single test, single-file lint/typecheck)
5. Non-interactive fast default test command (no watch-mode default; CI=true terminates)
6. Advisory rules -> deterministic hooks (with real content, see SV4)
7. `.env.example` covering every env var actually read
8. Seeded db reset (where a db exists)
9. Cloud-agent env config (copilot-setup-steps.yml / devcontainer postCreate that installs)
10. Prune doc sprawl; root file becomes pointers ("where to look" table)
11. Per-package instruction files in monorepos past ~200 root lines
12. CI/local command parity (CI steps exist as identically named local scripts)

Plus structural actions when classification fires: generate a map, adopt nested instruction files, create the home base, write the bootstrap plan (below). Emit findings with a freshness caveat and a suggested re-run cadence - never imply a durable badge.

### Report shapes per classification (playbooks.md)

**Greenfield:** the 48-criterion scorecard is suppressed; emit an ordered **bootstrap plan** (~8-12 stage-appropriate items): hand-curated agent-file seed (short, commands-first), STRATEGY.md first (`/flow-next:strategy` exists), stack decision recorded with exact versions, verify loop before feature 1 (test + smoke), smallest CI (install+lint+test), hygiene files (.gitignore, lockfile, .env.example, .editorconfig - never LICENSE per guardrails), first spec = first vertical slice with explicit non-goals. Pillars that are premature get **recorded-deferral N/A** ("no observability yet - deferred until first deploy"): a documented deferral beats BOTH a silent gap AND a stub file - the stub is the rot generator this spec exists to kill. Anti-pattern rules: prime never emits stub artifacts that would pass its own checks (anything scaffolded is exercised in the same pass); no big-bang scaffolding; no heavyweight spec ceremony on an empty repo.

**Standard single repo (small/medium):** current report, upgraded with the verdict headline, substance criteria, and size-tier recommendations. Below 400K LOC do NOT recommend LSP/index tooling (measured net-negative); recommend orientation map + loops instead.

**Monorepo (exemplar: modern TS pnpm/Nx/Turbo):** usually already legible - the build graph IS the map. Playbook: (1) verify per-package commands work from each package dir and are file-scoped (`pnpm --filter <pkg> test`, affected-only where Nx/Turbo exists); (2) nested per-package CLAUDE.md/AGENTS.md when >2-3 distinct subsystems or root file >~200 lines (nearest-wins per the AGENTS.md spec; reference point: OpenAI's Codex repo carries 88); (3) scoping config - read-deny for `dist/`/generated, sparse worktrees for subagents, launch-from-package-dir guidance; (4) if Nx present, recommend its agent wiring (graph + affected-only as the feedback loop); (5) verify the lockfile/task-runner single-source rule (one package manager). Score per existing pillars; monorepo N/A handling (BS6) already exists.

**Huge and/or legacy (exemplar: 15M LoC Delphi):** legibility-first block AHEAD of pillar detail. Realistic playbook:
- Name the operability tier honestly. For Delphi: tier 1 is the workhorse - one-command headless compile per project (`Build.cmd` wrapping `rsvars.bat && msbuild X.dproj /t:Build`); one paid RAD Studio seat legally covers an unattended build server (EULA unattended-build clause); tier 2 = a DUnitX console target emitting NUnit XML in CI. Do not prescribe tier 3.
- **No-LSP/no-map honesty:** DelphiLSP is license-bound to a RAD Studio machine (64-bit variant needs Enterprise); pasls forks cover the Delphi dialect only partially; aider repomap has no Pascal tags and clawpatch does not list Pascal - so `/flow-next:map` is NOT the recommendation here. Recommend instead: a unit-dependency-graph artifact (DUDS / MMX / Pascal Analyzer export) checked in or regenerable - deterministic dependency maps are prerequisites, not nice-to-haves (Microsoft COBOL-agents lesson); a hand-written orientation map (top-level dirs, entrypoints from the .dpr, module one-liners); static analysis as the proxy verifier where tests are absent (SonarDelphi, FixInsightCL, StaticCodeAnalyser SARIF).
- **Inventory the pathologies as first-class findings:** top-20 largest files (50K-line units are common; agents read whole files without symbol tooling - token burn), generated-file globs, binary artifacts (.res, .dcu, binary .dfm), vendored trees - all excluded from agent-readable scope in the agent file.
- **Encoding sweep (P1 finding):** BOM/charset sniff on a sample per extension. Legacy Delphi is typically ANSI/Windows-1252 (umlauts in identifiers); Claude Code has multiple open corruption bugs on non-UTF-8 files (anthropics/claude-code #7134, #28523, #28316, #50717). Recommendation: deliberate one-time UTF-8-with-BOM conversion commit, or an encoding-guard hook, or a never-edit list for known-ANSI files.
- **Stack-specific agent rules for the agent file:** .dfm+.pas are an atomic pair (never rename a component in only one); binary .dfm converted to text or frozen; IDE-managed files agents must not touch (.dproj reordering, .res, .dsk, .identcache, __history/); dialect + version + non-English identifier conventions stated.
- **Module carve-outs** as the unit of agent-workability (strangler-fig): name which subsystems are safe agent territory vs frozen; a carve-out with its own build + tests is what "agent-ready" means at this scale - never the whole 15M LoC.
- Same playbook shape applies to other legacy stacks (.NET Framework 4.x: msbuild not dotnet-build, Windows-only, WSL cannot build; VB6/PowerBuilder: source-export prerequisites, honest "ecosystem answer is migration tooling"; COBOL: static-parse tier, characterization tests).

**Constellation-member (exemplar: 99 repos):** per-repo priming STAYS VALID - every repo still gets its own assessment and fixes; the constellation block is ADDITIVE guidance on top. Recommend the **home-base pattern** (industry-consensus "repo-of-repos"/"virtual monorepo"): parent dir (optionally a tiny git repo) with siblings as plain gitignored checkouts - NOT submodules (update friction, worktree incompatibility, agents forget init; exception: deliberate version-pinning); the highest-leverage artifact is a **repo manifest with one-line purposes** (`repos.yaml`/md) that a LEAN parent CLAUDE.md points at (manifest = single source of truth, never duplicate the list). Home-base contents: lean parent instruction file (workspace map, cross-repo change workflow, git-directory-safety rule, docs-update-as-DoD), the manifest, clone-all/status-all/test-all scripts (mani/gita/vcstool or plain scripts; mise `monorepo_root` for task namespace), constellation docker-compose, ports + env bootstrap map, `_plans/` for cross-repo plans. Platform caveat stated in the report: Codex ignores an AGENTS.md above the git root (openai/codex#15683), so per-repo files must link BACK to the home base explicitly; Claude Code `--add-dir` solves access, not knowledge. Cross-repo change choreography documented in the home base: contract-first ordering (schema -> provider -> consumers), one repo per worker, linked PRs, merge order libraries-before-consumers, contract tests at boundaries. Scale ladder: manifest + home base at 2-30 repos; dependency/release-ordering registry at 20+ (Mabl's 79-repo registry cut context-drift failures ~40% -> <5%); recommend TRUE monorepo consolidation only when cross-repo changes dominate (>~30-50% of features touch multiple repos) and no isolation constraint exists - the home base is the middle option capturing most of the benefit at near-zero migration cost. Prime running in the home-base dir itself assesses the constellation layer (manifest present? compose boots? parent file lean + pointing?).

### Per-stack matrix (stacks.md)

One row per stack; drives Phase 2 verify commands, LSP/map recommendations, and gotcha findings. Claude Code has native LSP via code-intelligence plugins since v2.0.74; Serena MCP is the cross-agent alternative; NEITHER covers Pascal/Delphi, VB6, PowerBuilder, or PL/SQL - the matrix is honest about that.

| Stack | Detect | Verify (non-interactive) | LSP for agents | Map tooling | Gotchas |
|---|---|---|---|---|---|
| TS/JS | package.json | `pnpm lint && pnpm test` (CI=true) | tsserver plugin (trivial) | clawpatch yes; aider yes | watch-mode default test scripts; pick ONE package manager |
| Python | pyproject.toml | `ruff check && pytest -q` | pyright (trivial) | yes | env resolution (uv/poetry/pip) is the probe |
| Go | go.mod | `go build ./... && go vet ./... && go test ./...` | gopls (trivial) | yes | gold standard; little to fix |
| Java | pom.xml / gradlew | `./mvnw -B verify` / `./gradlew build --console=plain` | jdtls (setup cost) | yes | wrapper scripts are the readiness marker; old Java EE often drops to compile-only |
| C#/.NET modern | *.csproj net6+ | `dotnet build && dotnet test --no-build` | Roslyn LSP plugins | yes | central package mgmt, nullable-as-errors |
| C#/.NET Framework 4.x | old-style csproj, packages.config | `msbuild /t:Build /restore`; `vstest.console.exe` | partial | partial | Windows-only build; WSL agents cannot build; NOT `dotnet build` |
| PHP | composer.json | `composer validate && vendor/bin/phpstan && vendor/bin/pest` | Intelephense/phpactor | yes | facades/container blind the LSP; phpstan is the real verifier |
| Ruby/Rails | Gemfile | `bundle exec rubocop && bundle exec rspec` | ruby-lsp | yes | metaprogramming limits LSP payoff; DB-dependent tests need services |
| C/C++ | CMakeLists/Makefile | `cmake --build build && ctest` | clangd REQUIRES compile_commands.json | yes | compile_commands.json presence is THE readiness probe |
| Kotlin/Android | settings.gradle.kts | `./gradlew assembleDebug lint testDebugUnitTest` | jdtls/kotlin-ls | yes | distinguish unit (Robolectric) vs instrumented tiers; emulator not agent-verifiable |
| Swift/iOS | Package.swift / xcodeproj | SPM `swift build && swift test`; app `xcodebuild ... | xcbeautify` | SourceKit-LSP (SPM good, xcodeproj weak) | SPM only | macOS-only; SPM packages far stronger agent territory than xcodeproj apps |
| SQL/PLSQL | *.pks/*.pkb | utPLSQL-cli against a disposable Oracle container (gvenzl images) | none practical | none | cannot verify without a DB; container or dev schema is the readiness move |
| Delphi | *.dpr/*.dproj | `rsvars.bat && msbuild X.dproj /t:Build`; DUnitX console -> NUnit XML | none practical (license-bound) | none | see huge/legacy playbook: encoding, dfm/pas pairing, IDE-managed files |
| VB6/PowerBuilder | *.vbp / *.pbl | `vb6.exe /make`; OrcaScript | none | none | binary .pbl needs source export first; honest answer is migration tooling |
| COBOL | *.cbl + JCL | static-parse tier; characterization tests | none | none | Anthropic Code Modernization Playbook is the canonical reference |

Rows are starting opinions maintained in `stacks.md`; unknown stacks degrade to the generic ladder (find manifest -> find build -> find test-list command) plus an honest "no per-stack playbook yet" line.

## API Contracts
<!-- scope: technical -->

Anchor points (all under `plugins/flow-next/skills/flow-next-prime/`):

- `SKILL.md` - add Phase 0.5 to the phase list; verdict-headline description; `--classify-only` arg; three new reference files linked
- `workflow.md` - new Phase 0.5 section (classification block + confirm-on-low-confidence); Phase 1 scout dispatch gains a classification context line per scout ("This is a huge Delphi tier-1 repo - do not assess Node conventions"); Phase 2 extends to build execution, agent-file quoted-command execution, hook-content check, .env cross-ref (per stacks.md verify column, bounded timeouts); Phase 3 gains hard-gate evaluation + verdict computation + greenfield scorecard suppression; Phase 4 report template gains the classification block, operability tier line, gate status, ranked top-5, and the per-shape blocks; Phase 5 remediation options draw from the ranked catalog (playbooks.md) instead of the fixed four questions only
- `pillars.md` - substance pass-condition upgrades for SV4, SV5/SV6, BS2/BS3, DC2, DE1, DE4, DE5 (wording per Architecture section); N/A whitelist extended with classification-driven entries (greenfield recorded-deferrals; tier-capped stacks exempt from tier-3 criteria)
- `remediation.md` - new templates: orientation-map skeleton, home-base starter kit (parent CLAUDE.md + repos.yaml + scripts), bootstrap-plan template, encoding-guard hook, Build.cmd wrapper (Delphi), never-edit list block; existing templates keep their non-destructive rules
- NEW `classification.md`, `playbooks.md`, `stacks.md` per Architecture section
- `agents/` - claude-md-scout rubric deepened (substance tells + deductions); build-scout/testing-scout dispatch prompts accept the stack row so they probe the right commands; no new scouts (classification is host-inline)
- Report assembly: `--classify-only` prints the Phase 0.5 block and exits; `--report-only` unchanged otherwise
- Cross-platform parity via `scripts/sync-codex.sh` (canonical files Claude-native; AskUserQuestion rewritten for the Codex mirror as usual)
- Docs: `plugins/flow-next/docs/` prime section + README mention; flow-next.dev docs-site page for prime updated in the same workstream (maintainer walks the downstream chain at release)

flowctl: NO new engine. At most trivial plumbing if planning finds it useful (e.g. a `prime classify --json` emitter for portfolio scripting) - default is none; the skill computes classification inline with standard tools (`git`, `find`, `rg`, `scc`/`tokei` when present - both optional, degrade to file-count estimates).

## Edge Cases & Constraints
<!-- scope: technical -->

- **Boundedness is load-bearing:** every probe is deterministic and capped - `git ls-files` counts, `find -maxdepth`, config presence, ONE sampled grep probe, `scc`/`tokei` (never `cloc`, never exhaustive reads); execution probes get timeouts (build ~5 min, test-list ~2 min, boot ~60s) and size caps on file reads (giant generated files). No full-repo LLM crawl - that is the exact case that breaks.
- **Execution trust surface unchanged:** Phase 2 extensions run only commands the repo itself declares (its own scripts/manifests) - same surface as today's test verification; no new arbitrary execution. Windows-only builds (Delphi, .NET Framework) that cannot run on the current host are recorded "not probed on this host", never fabricated ✅ - the unverified-counts-as-fail rule from Phase 2 extends to every executed criterion.
- **Classification is heuristic:** three-tier confidence, evidence always printed, low-confidence calls confirmed interactively; autonomous/`--report-only` runs state the assumption. Misclassification must degrade gracefully - a monorepo misread as single repo still gets a correct base report, only the playbook block is off.
- **Fabrication guard:** every substance verdict quotes its evidence (file line or command output). A criterion with no evidence is NOT ASSESSED, never guessed. Existing scout-failure and five-state scoring rules (N/A whitelist, ⚠️ unverified) stay authoritative; classification only ADDS N/A entries via the documented whitelist, the model still may not invent N/A.
- **Do not regress the existing scan:** all 48 criteria remain; substance upgrades tighten pass conditions, never remove checks. Existing guardrails hold (never modify code files, never commit, never delete, never LICENSE, pillar 6-8 report-only, DC7/DE7/DC8 handling, glossary read-back).
- **Size-tiering is bidirectional:** below 400K LOC do NOT recommend LSP/index/code-intel tooling (measured net-negative); above it, DO. Over-recommending equals under-recommending as a failure.
- **Stack honesty over aspiration:** where the matrix says "none practical" (Delphi LSP, PL/SQL, VB6 maps), prime must say so and recommend the realistic alternative (dependency-graph artifact, hand-written map, static analysis as proxy verifier) - never suggest `/flow-next:map` on a stack clawpatch does not parse (extend the DE7 suggestion gate with the stack check).
- **Never scaffold what would pass prime's own checks unexercised:** every remediation artifact prime creates is exercised in the same pass (command run, hook invoked) or explicitly marked unverified. LLM-bulk-generated CLAUDE.md is forbidden as a fix (measured harm); offer skeleton + human fill or interview-derived augment.
- **Encoding hazards:** the encoding sweep must not itself corrupt anything (read-only probes); recommendations only.
- **Provider-free stays:** prime requires no API keys/providers; `scc`/`tokei`/`rg` are optional accelerators with fallbacks; clawpatch stays optional (DE7).
- **`--classify-only` must stay cheap** (<~10s on a huge repo): it is the portfolio-triage entry point for 100+ repos.
- **Home-base assessment mode** (prime run in a parent dir that is not itself a project repo): detect via manifest + sibling checkouts; assess the constellation layer instead of erroring on "no manifest found".

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Prime classifies every repo on four axes (lifecycle greenfield/hybrid/brownfield; topology single/monorepo/constellation-member; size band small/medium/large/huge; stack set) using only bounded deterministic probes, prints the classification with evidence and confidence, and confirms low-confidence topology calls interactively (states the assumption in non-interactive runs).
- **R2:** `--classify-only` prints the classification block and exits in seconds, even on a multi-M LOC repo.
- **R3:** The report headline is: classification + operability tier + hard-gate status + top-5 ranked specific next-actions (file-level, from the playbooks catalog). The maturity level appears only as secondary metadata.
- **R4:** Operability is graded on the 4-tier ladder from executed evidence with bounded timeouts; the report names the current tier and the cheapest move up one tier; tier-3 prescriptions are never emitted for stacks whose matrix ceiling is tier 1-2; unverifiable-on-this-host is reported as not-probed, never as pass.
- **R5:** Hard gates (build runs OR tier >= 1 evidence; tests discoverable when claimed; agent-file quoted commands resolve) cap the maturity level at 2 when failing, with the failure named in the headline.
- **R6:** Substance pass-conditions ship for SV4 (hook content), SV5/SV6 + BS2/BS3 (script executes), DC2 (substance tells + deductions + length band + executed quoted commands), DE1 (env cross-ref), DE4 (setup chains stages), DE5 (non-empty devcontainer) - each verdict quoting its evidence; a stub artifact that would previously pass now scores ❌/⚠️ with the stub named.
- **R7:** Greenfield repos get the bootstrap-plan report shape (scorecard suppressed, ~8-12 ordered stage-appropriate items, recorded-deferral N/A lines for premature pillars); prime never creates stub files that would pass its own checks unexercised, and never bulk-generates a full instruction file.
- **R8:** Monorepos get the monorepo playbook block (per-package command verification, nested-instruction-file recommendation past the thresholds, scoping config, build-graph wiring when Nx/Turbo/Bazel present).
- **R9:** Huge/legacy repos get the legibility-first block: pathology inventories (largest files, generated globs, binary artifacts, encoding sweep) as first-class findings, no-LSP/no-map honesty per the stack matrix with realistic alternatives (dependency-graph artifact, hand-written orientation map, static analysis as proxy verifier, module carve-outs), and stack-specific agent-file rules (e.g. Delphi dfm/pas pairing, IDE-managed never-edit list, encoding guard).
- **R10:** Constellation members get the constellation block: per-repo assessment unchanged PLUS home-base recommendation (manifest with one-line purposes as the headline artifact, lean parent instruction file, run-everything scripts, compose, ports/env map), the Codex parent-file caveat, cross-repo change choreography, and the scale ladder (registry at 20+, consolidation criteria as >~30-50% cross-repo change rate). Prime run in a home-base dir assesses the constellation layer instead of erroring.
- **R11:** `stacks.md` ships rows for at least: TS/JS, Python, Go, Java, .NET modern, .NET Framework 4.x, PHP, Ruby, C/C++, Kotlin/Android, Swift/iOS, SQL/PLSQL, Delphi, VB6/PowerBuilder, COBOL - each with detect/verify/LSP/map/gotchas; Phase 2 uses the stack's verify column; the `/flow-next:map` suggestion (DE7) is gated on clawpatch actually supporting a detected language; unknown stacks degrade to the generic ladder with an honest no-playbook line.
- **R12:** Size-tiered recommendations: <400K LOC never recommends LSP/index tooling; 100-400K or ambiguity-probe hit recommends map + scoped scouts; >400K adds LSP/build-graph where the stack supports it; hosted index only at multi-M with the staleness caveat.
- **R13:** All 48 existing criteria, the five-state scoring, N/A whitelist discipline, scout-failure rules, guardrails, and remediation consent gates remain intact (regression: the current smoke assessment on this repo still produces a complete scored report).
- **R14:** Codex mirror parity via sync-codex.sh; docs updated (prime docs page, README mention, docs-site page staged per the release process); CHANGELOG entry under Unreleased; no version bump (batched releases).

## Boundaries
<!-- scope: business -->

- In: classification, operability ladder + hard gates, substance upgrades to existing criteria, verdict + ranked-actions headline, per-shape playbooks (greenfield/standard/monorepo/huge-legacy/constellation), per-stack matrix, `--classify-only`, remediation templates for the new artifacts (orientation map, home-base kit, encoding guard, compile wrapper).
- Out: auto-FIXING repo structure (prime recommends, never restructures or migrates); the mapping engine itself (clawpatch consumes); building/hosting any index, LSP integration, or MCP server (recommend-only); readiness as a KPI/score surface (strictly separate from PSVI/measurement - DX guidance only); tracker/portfolio dashboards; migrating legacy stacks (prime points at the honest ecosystem answer, does not perform it); new scouts; new flowctl engines.
- Not a rewrite of the 8-pillar scan - additive tightening.

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->
At portfolio scale the binary existence-check produces false "ready" signals and no actionable guidance, and leads cannot hand-verify hundreds of repos across many stacks. Encoding a senior's first-look judgment - size, legibility, topology, operability tier, single most-valuable next action - makes prime trustworthy at scale and directly unblocks portfolio-scale multi-repo, multi-stack rollouts (the current bottleneck). `--classify-only` gives the portfolio lead a cheap triage sweep across 100+ repos before any deep assessment.

### Implementation Tradeoffs
<!-- scope: technical -->
Decisions made in lieu of the interview (flag any to revisit):

- **Default behavior, not a new mode.** Keeping the existence-only path reachable would preserve the failure mode fn-92 retires. Only `--classify-only` is added. Revisit if a "fast legacy-compatible run" proves necessary.
- **Operability ladder over boot-probe-by-default.** Tier 3 probes run only on cheap ready-signals with timeouts; the ladder makes legacy honest instead of failed. Alternative considered (opt-in `--boot` flag) rejected as another knob; the ready-signal gate bounds risk equally.
- **Hard gates cap at Level 2** rather than zeroing the score: preserves score comparability while killing false Level 5s. The gate list is deliberately tiny (3) to stay uncontroversial.
- **Classification host-inline, no new scout:** it is deterministic bash, not judgment; a scout adds latency and a failure mode for no gain. Scout dispatch CONSUMES the classification instead.
- **Three reference files** over inflating workflow.md: mirrors pillars/remediation precedent; keeps always-loaded prose small (fn-82 discipline).
- **stacks.md as maintained opinion table** over auto-detection cleverness: rows are explicit, reviewable, and correctable per portfolio experience; unknown stacks degrade generically.
- **No flowctl engine:** repo architecture rule (skills own judgment; flowctl owns plumbing); classification needs no atomicity. `prime classify --json` emitter left as a planning-time option only.
- **Greenfield suppresses the scorecard** rather than scoring with N/As: a 10-item bootstrap plan is the honest report for an empty repo; a scored husk invites Goodharting the checklist from day one.
- Thresholds (~25 commits, ~30 files, 100K/400K/2M LOC, 20K files, ~200/~300 line instruction-file bands, 30-50% cross-repo change rate, 20+ repos for a registry) are research-anchored starting opinions living in classification.md/playbooks.md - tune with portfolio data, not in flowctl code.

## Strategy Alignment
- **Agent-readiness / adoption-at-scale** track - makes prime a trustworthy gate for large multi-repo, multi-stack portfolios (the rollout bottleneck); pairs with `/flow-next:map` where the stack supports it and is honest where it does not.

## Conversation Evidence
> Field origin - external-team AI-SDLC weekly, 2026-07-10 (head of software engineering + backend lead): "dadurch, dass häufig nur Existenz geprüft wird, haben die jetzt aus irgendeinem Grund Level 5 erreicht ... es ist nicht möglich, dass wir das händisch überprüfen ... hunderte Repositories, 10-11 verschiedene Tech-Stacks." Gordon's steer: check repo size + can it read structure / imports-exports -> else recommend a mapping tool; if multiple repos, propose how to structure them (fake-monorepo); judge whether a pre-commit hook / script has sensible content vs just a template/header; baseline = "kann ich die App betreiben / kompilieren?" - "vielleicht braucht es einen neuen Mode ... kann man wiederverwenden, Erfahrungen mitnehmen und überall applizieren." Follow-up steers 2026-07-11: per-repo priming stays valid alongside a home-base folder; greenfield needs its own handling; flesh out in full with grounded per-stack help (modern TS monorepo vs 15M LoC Delphi vs 99-repo project) - interview skipped, decisions recorded above. Detailed notes in the maintainer's vault (AI-SDLC weekly 2026-07-10).

## Research Sources (2026-07-11 passes)

Substance checks / readiness rubrics: Factory.ai Agent Readiness (news + docs, 9-pillar gated levels); kodustech/agent-readiness (skip-not-fail); Kenogami-AI/codebase-readiness (lifecycle classification, ceiling scoring, deferral credit); GitHub blog "great agents.md, 2,500 repos"; ETH Zurich arXiv 2602.11988 (LLM-generated instruction files harm); Augment Code agents-md guides; roborhythms.com 8 checks; Marmelab agent-experience (2026-01-21); gmoigneu readiness-checklist gist; agent-next/agent-ready; USENIX Reliability Maturity Model (anti-Goodhart); vstorm full-stack-ai-agent-template (make bootstrap model).

Large codebases: Sourcegraph CodeScaleBench (2026-05-08; 400K crossover, Kubernetes 67x case); RepoMod-Bench arXiv 2602.22518; code.claude.com/docs/en/large-codebases (nested CLAUDE.md, read-deny, sparsePaths, LSP plugins); aider repomap docs; Cognition/Windsurf Codemaps (2025-11); oraios/serena; nx.dev agent skills + monorepo.tools/ai; Chroma context-rot (2025-07); AGENTS.md spec (Linux Foundation stewarded); codegateway.dev AGENTS.md playbook (32 KiB chain cap); Piebald-AI/claude-code-lsps (native LSP since 2.0.74).

Multi-repo: raffertyuy repo-of-repos (2026-05-02); karun.me bootstrap-repo + mani (2026-03-26); rajiv.com polyrepo synthesis (2025-11-30); Mabl 75+ repos parts 1-2 (2026-04); riftmap.dev; claude.com/blog large-codebases (2026-05-14); openai/codex#15683 (ancestor AGENTS.md ignored); Cursor 3.2 multi-root (2026-04-24); dortort.com (2026-05-20); Faros.ai mono-vs-poly benchmark; tools: mani, gita, vcstool, meta, git-workspace, mise monorepo tasks.

Greenfield: koder.ai vertical-slice workflow; github/spec-kit + Scott Logic critique (2025-11-26) + Marmelab "waterfall strikes back" (2025-11-12); handsonarchitects Harness Model (2026 Q1); TestMu loop engineering; dev.to "Debloating the AI-Grown Codebase"; arXiv 2601.18345 + 2606.07448 (repo-maturity heuristics).

Legacy / per-stack: blog.dummzeuch.de DelphiLSP experiment (2026-02-07); SkybuckFlying/Delphi-LSP-MCP-Server; Embarcadero DelphiLSP docs + 64-bit LSP post; genericptr + castle-engine pasls forks; Isopod/tree-sitter-pascal; aider languages table (Pascal: no repo map); openclaw/clawpatch language list (no Pascal); RAD Studio 12 EULA unattended-build clause; VSoftTechnologies/DUnitX; integrated-application-development/sonar-delphi + delphilint; nrodear/StaticCodeAnalyser (SARIF + Claude hand-off, 2026); DUDS/MMX/Pascal Analyzer; gabrielmoraru.com Claude-Code-on-Delphi field report (early 2026); thedelphigeek.com part 11 (2026-07); ethea.it vibe-coding guide; anthropics/claude-code encoding issues #7134/#28523/#28316/#50717; resources.anthropic.com Code Modernization Playbook (2025-09); Microsoft COBOL-agents (Azure-Samples/Legacy-Modernization-Agents); AWS Transform; Open Mainframe mentorship 2025; feststelltaste/awesome-agentic-software-modernization; DeepWiki MCP; boyter scc vs cloc; talkthinkdo .NET Framework migration guides (2026); utPLSQL-cli + gvenzl Oracle images; Mobilize VB6 AI Migrator (2025-08).
