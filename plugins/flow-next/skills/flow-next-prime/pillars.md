# Agent Readiness Pillars

Eight pillars for comprehensive codebase assessment. Pillars 1-5 measure **agent readiness** (fixes offered). Pillars 6-8 measure **production readiness** (reported only).

**Substance, not existence.** Pass conditions grade what a criterion actually delivers - executed evidence (bounded) over parsed config, cross-referenced against the code over read in isolation. Every substance verdict quotes its evidence (a file line or command output); a criterion with no evidence is NOT ASSESSED, never guessed (fabrication guard). A stub artifact that would previously pass now scores ❌/⚠️ with the stub named.

**Three scoring layers:**
1. **The maturity level** = average of Pillars 1-5 scores ONLY (Pillars 6-8 are report-only). The legacy Pillars 1-5 criteria are the stable level denominator for cross-repo comparability; the full 48 legacy set is never diluted by the new groups.
2. **Agent-readiness tier GROUPS** (AO, DR, TO, HP scored-core, the scored gap-diff FH criteria) are scored and fix-offered but **EXCLUDED from the maturity-level formula** (resolution 1). They report as group pass-count lines and feed the verdict headline + ranked actions, never the level.
3. **Report-only / informational** rows (Pillars 6-8, DT, HP-informational, FH report-only, gh-CLI) are surfaced but never scored.

The **criterion-to-score map** (below the pillar and group tables) is the single source of truth for every criterion's group, taxonomy, denominator behavior, aggregate presentation, remediation eligibility, hard-gate impact, and **probe owner** (emitter / host-inline / scout). The **N/A whitelist** (single table) is the only source of N/A entries.

---

## Pillar 1: Style & Validation

Automated tools that catch bugs instantly. Without them, agents waste cycles on syntax errors and style drift.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| SV1 | Linter configured | ESLint, Biome, oxlint, Flake8, Ruff, golangci-lint, or Clippy config exists |
| SV2 | Formatter configured | Prettier, Biome, Black, gofmt, or rustfmt config/usage detected |
| SV3 | Type-checking depth (substance) | Grade strictness SUBSTANCE, not "a typed language exists": strict flags enumerated (tsconfig `strict`/`noImplicitAny`/`strictNullChecks`; mypy `strict`; pyright `strict`) PLUS a bounded `: any`-ratio probe on TS sources. A typed project with strictness disabled or a high `any` ratio = ⚠️ with the flag/ratio quoted. Evidence = the config lines quoted. |
| SV4 | Deterministic feedback gate (layer-agnostic) | **Rewritten from "pre-commit hooks configured".** PASS = the acceptance/verify layer runs the tests: a verify command gated by ACCEPTANCE REQUIREMENTS (L3 - flow-next's own work-loop quality gates / Stop hooks) AND/OR a CI required check running the SAME verify command (L4). Evidence = the gate config quoted. Edit-time enforcement (L1 harness hooks: PostToolUse / afterFileEdit format + file-scoped lint/typecheck) and commit-gate enforcement (L2 git hooks scoped to format/lint on staged files, <~10s, auto-fix) with real content are a reported **STRENGTH**; their ABSENCE is a **headroom warn, never a pass-blocker** ("no git hooks but hardened CI + verify command" is a legitimate pass). Flags (each quotes evidence): stub hook content (`.husky/` echo scaffold, whitespace-only pre-commit config) = ❌; test-suite/E2E/coverage in a pre-commit hook = ⚠️ "heavyweight hook - known agent bypass/stall risk; move tests to verify + CI"; git hooks in an agent-committing repo without bypass hardening (deny `git commit --no-verify` / PreToolUse guard) = ⚠️ "advisory only for agents"; L1/L2 tooling diverging from L3/L4 (different tools/flags per layer) = a finding (one verify command is the single source of truth). Prime **NEVER** recommends test-running pre-commit hooks. **Boundary (resolution 2):** SV4 grades gate TOPOLOGY (which layer owns what); workflow TRIGGER correctness is **FH3 (CI actually gates)**, never double-scored; Pillar 8 WP1 report-only row untouched. |
| SV5 | Lint script exists AND executes | `lint` command present in manifest/Makefile AND runs in CHECK mode exiting cleanly or with real findings; a `lint` script that crashes = ❌ with the error quoted. Non-mutating execution policy: check mode only, never `--fix`/`--write` against the worktree. |
| SV6 | Format script exists AND executes (check mode) | `format` command present AND runs via its CHECK/`--check` mode ONLY (never `--write`/`--fix` against the worktree - non-mutating execution policy); evidence = the check-mode invocation output. No check mode available = report that the format command resolves statically, do not execute it. |

### Scoring
- ✅ 80%+: All core tools configured
- ⚠️ 40-79%: Partial setup
- ❌ <40%: Missing fundamentals

---

## Pillar 2: Build System

Clear build process that agents can execute reliably.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| BS1 | Build tool detected | Vite, webpack, tsc, cargo, go build, Turbo, etc. |
| BS2 | Build command exists AND builds | `build` script present AND the bounded build executes (exit 0, ~5 min timeout) OR operability tier >= 1 evidence exists; a build that fails = ❌ with the error quoted. Windows-only / host-unbuildable targets = "not probed on this host", never a fabricated ✅ (unverified-counts-as-fail). |
| BS3 | Dev command exists (evidence = boot probe) | `dev`/`start` script present; its runnable evidence comes ONLY from the gated tier-3 boot probe output (ready line + bound port), NEVER a second long-lived server run (non-mutating execution policy). Absent a boot probe, the script is reported as resolving statically. |
| BS4 | Build output gitignored | dist/, build/, .next/, target/ in .gitignore |
| BS5 | Lock file committed | package-lock.json, pnpm-lock.yaml, Cargo.lock, uv.lock, etc. |
| BS6 | Monorepo tooling | Turborepo, Nx, Lerna, or pnpm workspaces (if applicable) |

### Scoring
- ✅ 80%+: Reproducible builds
- ⚠️ 40-79%: Builds work but fragile
- ❌ <40%: Build process unclear

---

## Pillar 3: Testing

Test infrastructure that lets agents verify their work.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| TS1 | Test framework configured | Jest, Vitest, pytest, go test, etc. |
| TS2 | Test command exists | `test` script available |
| TS3 | Tests exist | >0 test files in repo |
| TS4 | Tests runnable | `pytest --collect-only` or equivalent succeeds |
| TS5 | Coverage threshold ENFORCED | Not "coverage tooling exists": an ENFORCED threshold quoted (`fail_under`, `--cov-fail-under`, `branches:`/`lines:` gate in config). A threshold of 0, or tooling wired with no gate, = the same stub pattern = ⚠️. |
| TS6 | E2E tests exist | Playwright, Cypress, or integration tests |

### Scoring
- ✅ 80%+: Comprehensive test setup
- ⚠️ 40-79%: Basic testing in place
- ❌ <40%: Testing gaps

---

## Pillar 4: Documentation

Clear docs that tell agents how the project works.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| DC1 | README exists | README.md with meaningful content (not just template) |
| DC2 | CLAUDE.md/AGENTS.md quality (substance) | Agent instruction file present AND clears the claude-md-scout coverage bar on the **single published scale X/8** (pass ~5/8 - the 8-row scout rubric; every file normalizes to this scale). Graded on SUBSTANCE TELLS, not existence: repo-specific nouns; >=3 fenced copy-paste-runnable commands in the top ~50 lines; commands appearing verbatim in manifests; 1-3 real code snippets; three-tier boundaries with concrete paths; don'ts paired with dos. Template tells are DEDUCTIONS: generic personas, restated universal conventions, full directory listings, unedited /init scaffold order, placeholders, zero fenced blocks. Length band 30-150 lines; >300 lines is a REVIEW TRIGGER routing to prune-to-pointers remediation, NEVER an automatic deduction (substance tells rule - a 659-line file passing every tell earns the prune recommendation, not a downgrade). Flag instruction-file SPRAWL (multiple root instruction files beyond the canonical-plus-bridge pattern). Generated-looking files are downgraded (ETH Zurich arXiv 2602.11988: LLM-generated instruction files harm). A thin stub = ⚠️ -> offer *augment*, not a no-op create. **DC2 execute check (host, Phase 2, feeds gate G3):** run 1-2 commands quoted in the file; a CLAUDE.md whose stated test command fails is worse than none. Extraction is HOST-AGENT work (read fenced blocks + inline backticks, take each command's leading token, resolve against tracked files / manifest scripts / PATH); **zero commands extracted from a file that HAS fenced blocks = an extraction-failure flag, never a vacuous G3 pass or a stub grade.** Content the agent could discover itself (directory trees, restated conventions) is NEGATIVE signal, never neutral. |
| DC3 | Setup documented | Installation/setup instructions in README or docs |
| DC4 | Build commands documented | How to build/run in README or CLAUDE.md |
| DC5 | Test commands documented | How to run tests documented |
| DC6 | Architecture documented | ARCHITECTURE.md, ADRs, or docs/ with structure |
| DC7 | DESIGN.md exists (frontend projects) | DESIGN.md with color + typography + component sections (informational — not scored for backend-only projects) |
| DC8 | Glossary populated | `"$FLOWCTL" glossary list --json` reports `total_terms > 0` (informational — not scored; husk-aware: gate on the term count, never `[[ -f GLOSSARY.md ]]` — `glossary remove` leaves an H1 husk; see `workflow.md` glossary signal block) |

### Scoring
- ✅ 80%+: Agents can self-serve
- ⚠️ 40-79%: Basic docs present
- ❌ <40%: Agents must guess

DC8 is **informational** — excluded from the Pillar 4 score and the agent-readiness baseline. Unlike DC7/DE7 (suggestion-only), a negative DC8 routes to the dedicated **Phase 5.5 glossary bootstrap** (read-back gated) — never to a Phase 5 template fix. A populated glossary is report-only: prime states term coverage and never rewrites or re-proposes existing terms (staleness/alias pruning belongs to `/flow-next:audit`).

---

## Pillar 5: Dev Environment

Reproducible environment setup.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| DE1 | .env.example mirrors real env reads | Not existence: diff declared vars against env reads in SOURCE (`process.env`, `os.environ`, `getenv`) across WORKSPACE MEMBER dirs (per-package `.env.example` is the correct monorepo pattern - never root-only); scan only source extensions in the git index, excluding tests/fixtures/eval corpora/docs snippets/node_modules; filter well-known platform/CI vars. >~30% undeclared = "stale template" ⚠️ (quote the offending vars); downgrade to "template does not mirror documented config" when the vars are documented in a config doc. Emitter owns the cross-ref counts. |
| DE2 | .env gitignored | .env in .gitignore |
| DE3 | Runtime version pinned | .nvmrc, .python-version, .tool-versions, etc. |
| DE4 | Setup script chains real stages (static + cross-ref) | Not existence: the setup script must chain real stages - `install` AND `migrate`/`seed` keywords found in its CONTENT (static + cross-reference evidence only; setup/migrate/seed are NEVER executed during assessment per the non-mutating policy). A `setup.sh` that only prints instructions = ❌. |
| DE5 | Devcontainer is non-empty | Empty devcontainer json with no `features`/`postCreateCommand` = "checkbox artifact" ⚠️, not ✅. Evidence = the config quoted. |
| DE6 | Docker available | Dockerfile or docker-compose.yml |
| DE7 | Codebase feature map present | `[[ -d .clawpatch ]]` + `"$FLOWCTL" repo-map list --count > 0` (informational — not scored; surfaces `/flow-next:map` suggestion in Top Recommendations when missing; `$FLOWCTL` resolved via the bundled Droid+Claude fallback — see `workflow.md` DE7 detection block) |

### Scoring
- ✅ 80%+: One-command setup possible
- ⚠️ 40-79%: Setup mostly documented
- ❌ <40%: Setup requires tribal knowledge

DE7 is **informational** - like DC7 and DC8, it is excluded from the Pillar 5 score and the agent-readiness baseline. The **48 legacy scored criteria** (Pillars 1-5 feed the maturity level; Pillars 6-8 are report-only) all remain present and scored per R13 - substance upgrades tighten pass conditions, never remove checks; including the informational DE7 and DC8 rows the legacy table totals **50**. The new agent-readiness tier GROUPS (AO 5, DR 7, TO 4, HP scored-core HP1/2/5/7/9/12, and the scored gap-diff criteria FH1-FH6) are scored and fix-offered but EXCLUDED from the maturity-level formula (resolution 1) - they surface as group pass-count lines, never in the 48-criterion level denominator. See the criterion-to-score map and N/A whitelist below.

---

## Pillar 6: Observability (Production Readiness)

**Informational only** — reported but not scored for agent readiness. No fixes offered.

Runtime visibility that helps debug issues.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| OB1 | Structured logging | winston, pino, bunyan, structlog, or similar |
| OB2 | Distributed tracing | OpenTelemetry, X-Request-ID propagation |
| OB3 | Metrics collection | Prometheus, Datadog, NewRelic instrumentation |
| OB4 | Error tracking | Sentry, Bugsnag, Rollbar configured |
| OB5 | Health endpoints | /health, /healthz, /ready endpoints |
| OB6 | Alerting configured | PagerDuty, OpsGenie, or alert rules |

### Status Indicators
- ✅ Configured
- ❌ Not detected

---

## Pillar 7: Security (Production Readiness)

**Informational only** — reported but not scored for agent readiness. No fixes offered.

Security posture and access controls.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| SE1 | Branch protection | Main/master branch protected via classic branch protection OR rulesets (repo / org / enterprise level — any layer counts) |
| SE2 | Secret scanning | GitHub secret scanning enabled |
| SE3 | CODEOWNERS | .github/CODEOWNERS file exists |
| SE4 | Dependency updates | Dependabot or Renovate configured |
| SE5 | Secrets management | .env gitignored, no secrets in code |
| SE6 | Security scanning | CodeQL, Snyk, or similar configured |

### Status Indicators
- ✅ Configured
- ❌ Not detected

---

## Pillar 8: Workflow & Process (Production Readiness)

**Informational only** — reported but not scored for agent readiness. No fixes offered.

Team processes and automation.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| WP1 | CI/CD pipeline | GitHub Actions, GitLab CI, or similar |
| WP2 | PR template | .github/PULL_REQUEST_TEMPLATE.md exists |
| WP3 | Issue templates | .github/ISSUE_TEMPLATE/ exists |
| WP4 | Automated PR review | CodeRabbit, Greptile, or similar configured |
| WP5 | Release automation | Semantic-release, changesets, or similar |
| WP6 | CONTRIBUTING.md | Contribution guidelines present |

### Status Indicators
- ✅ Configured
- ❌ Not detected

---

## Agent-Readiness Tier Groups (scored, EXCLUDED from the level formula)

These groups are scored and fix-offered in the agent-readiness tier, but per **resolution 1** they are **excluded from the maturity-level formula** (the level stays avg(Pillars 1-5) for cross-repo comparability). Each group reports a **pass-count line** (e.g. "AO: 3/5 pass"), never folded into the level, and feeds the verdict headline + ranked actions + remediation. Taxonomy per row: `scored-in-tier` / `report-only` / `informational`.

### Agent Observability & Drivability (AO / DR / TO / DT)

Ladder tier-3 sub-signals (runs -> **observable** -> **drivable**). AO/DR/TO are scored fix-offered; DT is informational (adoption is genuinely early - suggestion line only). Collection is **HOST-INLINE** (Phase 3), reusing the tier-3 boot probe and the existing `--help` CLI pattern for the two executed probes; the other 14 are bounded greps with quoted evidence - no new execution budget. Tier-capped stacks (tier 1-2 ceilings) and non-web shapes get N/A whitelist entries.

| ID | Criterion | Taxonomy | Pass Condition (evidence quoted) |
|----|-----------|----------|----------------------------------|
| AO1 | Agent-readable runtime feedback | scored-in-tier | Dev-server logs readable as files - log path/recipe in the agent file OR agent-tail-style `tmp/logs/` layout (token-cheaper than MCP schemas). **DR-core readable-evidence option (OR TO1).** |
| AO2 | Browser console reachable | scored-in-tier | chrome-devtools/Playwright MCP entry OR a console-capture script. |
| AO3 | Parseable ready line + deterministic port | scored-in-tier | From the boot probe: a literal ready line and a fixed port. |
| AO4 | Dev request-logging middleware | scored-in-tier | Request-logging middleware wired in dev. |
| AO5 | DEBUG/LOG_LEVEL escalation documented | scored-in-tier | Documented DEBUG/LOG_LEVEL escalation path. |
| DR1 | Seeded/demo data one-command | scored-in-tier | One command seeds demo data (merges with ranked-action catalog item 3). **DR-core member.** |
| DR2 | Documented dev login / test user | scored-in-tier | Documented, env-gated dev login path or test user (every drivability path dies at the login wall without it). **DR-core member.** |
| DR3 | Curl-able API + health endpoint | scored-in-tier | OpenAPI/route-list + health endpoint + dev token. **DR-core drivable-surface option (OR DR5).** |
| DR4 | Stable selectors | scored-in-tier | data-testid/roles/labels counts (the substrate browser agents drive via the a11y tree). |
| DR5 | Browser-automation harness | scored-in-tier | Playwright/Cypress config; screenshot command documented. **DR-core drivable-surface option (OR DR3).** |
| DR6 | Agent-first CLI (service-shaped) | scored-in-tier | `--json`, stdout=data/stderr=errors, stable exit codes, `--dry-run` on mutations. Primary drivability surface for CLI-shaped repos (swaps in for the DR web rows). Executed probe reuses the existing `--help` pattern. |
| DR7 | Framework dev-MCP (stack-gated) | scored-in-tier | Where the stack ships one (Next 16+ next-devtools-mcp); stack-gated via stacks.md rows, N/A otherwise. |
| TO1 | e2e failure artifacts configured | scored-in-tier | trace on-first-retry, screenshot only-on-failure, video retain-on-failure. **DR-core readable-evidence option (OR AO1).** |
| TO2 | App logs captured on e2e failure | scored-in-tier | playwright webServer stdout 'pipe'. |
| TO3 | Real reporter with assertion diffs | scored-in-tier | A real reporter emitting assertion diffs (extends catalog item 5). |
| TO4 | Flaky-quarantine visible | scored-in-tier | Retry config + annotated skips with tickets; >~5-10% quarantined = systemic flag. |
| DT1 | Dev-mode OTel wiring | informational | jaeger/collector in compose, `OTEL_` vars in .env.example. Suggestion line only. |
| DT2 | Trace-query surface for agents | informational | otel-mcp/grafana-mcp OR a documented "what happened when I hit /checkout" recipe. Suggestion line only. |

**DR-core (the named QA-readiness set).** QA-readiness (the `/flow-next:qa` / `pipeline.qa` gate) requires operability **tier 3 PLUS all four** DR-core criteria passing (not a threshold):
1. seeded/demo data (**DR1**)
2. documented dev login (**DR2**)
3. a drivable surface (**DR3** curl-able API with health **OR DR5** browser harness)
4. readable runtime evidence (**AO1** agent-readable logs **OR TO1** e2e failure artifacts)

The report emits the QA-readiness line only from here: tier 3 + DR-core all-pass -> recommend `/flow-next:qa` / enabling `pipeline.qa`; anything less -> name the missing DR items ("QA stage would fail here: <missing>"); shape/tier-capped repos state "QA stage not applicable to this shape".

### Harness & Permissions (HP)

The checked-in agent-harness config. Two governing principles: (1) **score the FUNCTION, not the file** - five function classes (instructions, permission/sandbox posture, lifecycle hooks, MCP config, cloud-agent/env bootstrap); detect ACTIVE harnesses first (config dirs present + commit recency) and grade ONLY those, mapping each criterion to the harness's native mechanism, N/A otherwise (never fail a Codex-only repo for missing `.claude/hooks`; Cursor "permissions" = access-scoping via `.cursorignore`; Codex posture = config.toml + trust). One deep harness + an AGENTS.md bridge outscores five shallow stubs. (2) **Zero harness config is today's normal** - the group reads as headroom, not shame, EXCEPT two P0 findings regardless of score: inline secrets in MCP config, and suspicious hook content. Collection is **HOST-INLINE** (harness config reads with security-sensitive quoting - **key names only, never values**); hook-content classification INPUTS come from the emitter; **hooks are READ, never executed, during assessment** (committed hook config is an RCE vector, CVE-2025-59536 class). Scored core = **HP1, HP2, HP5, HP7, HP9, HP12**; the rest informational at first.

| ID | Criterion | Taxonomy | Pass Condition (evidence quoted) |
|----|-----------|----------|----------------------------------|
| HP1 | Cross-harness instruction bridge | scored-in-tier | One canonical instruction file; the other harness's file is an `@AGENTS.md` import/symlink/thin adapter, NOT a diverged duplicate (Claude Code does not read AGENTS.md natively - the import IS the bridge). **Resolve the SYMLINK GRAPH before diffing and report it whole.** Diverged duplicates = ❌ with diff summary. |
| HP2 | Project permissions file present + parses | scored-in-tier | `.claude/settings.json` (or `.codex/config.toml` / `opencode.json` equivalent) valid with a permissions block. |
| HP3 | Verify-loop allowlist | informational | The repo's own Phase-2-verified test/lint/build commands are pre-approved (allow rules), cross-referenced against manifests. |
| HP4 | Allowlist freshness | informational | A dangling allow rule naming a nonexistent command = stale-config warn. |
| HP5 | Secrets deny rules | scored-in-tier | `.env` family + repo-specific secret paths deny-read in each active harness (`permissions.deny Read(...)`; Cursor parity: `.cursorignore` carries `.env*`/keys/secrets dirs). Repo-specific secret paths discovered from the repo's own .gitignore secret-shaped entries. |
| HP6 | Destructive/network guardrails | informational | curl/wget/`rm -rf` denied or sandbox-gated; push-class ops on ask. |
| HP7 | Hook substance + safety screen | scored-in-tier | Enumerate configured hooks; READ each including the COMMAND STRINGS (bounded, never executed); classify real gate / stub / suspicious. Stub = ❌ with quote; **suspicious (network calls, credential paths, obfuscation) = P0 security finding.** Emitter provides the hook-content inputs. |
| HP8 | Hook perf | informational | Heavy whole-project checks wired to PostToolUse (fires per edit) = perf warn. |
| HP9 | MCP secrets by indirection | scored-in-tier | `.mcp.json`-family values use `${VAR}` env indirection; any inline literal secret shape = ❌ quoting the **KEY NAME only** (never the value) + "rotate it - it is already in git history". |
| HP10 | MCP command hygiene | informational | stdio commands resolve; versions pinned not `@latest`; server count sane (~10+ = tool-bloat warn). |
| HP11 | MCP when-to-use docs | informational | Each server has a when-to-use line in the agent file. |
| HP12 | Personal-scope files uncommitted | scored-in-tier | `.claude/settings.local.json`, `CLAUDE.local.md`, `.env` absent from the git index. **When a local-scope file IS committed, its CONTENT feeds the HP3/HP5/HP7 posture assessment** (reading only settings.json misstates the posture). |
| HP13 | Cloud-agent env parity | informational | Cloud-agent env config parity with verified install commands (ties to DE5 / catalog 9). |
| HP14 | Sandbox/isolation posture | informational | Ladder: none < deny-rules < sandbox/network-allowlist < devcontainer firewall. Windows hosts: N/A, never fail. |
| HP15 | Path-scoped rule hygiene | informational | Dangling `paths:`/`applyTo:` globs matching zero tracked files = stale-rule warn. |
| HP16 | PR-template agent-evidence section | informational | PR template carries an agent-evidence section. |

### Feedback Latency & Hygiene (FH) - 13-rubric gap-diff

Net-new criteria from the gap-diff, deduped against everything above. Scored rows (FH1-FH6) are agent-readiness tier, EXCLUDED from the level formula (group pass-count line); report-only/informational rows carry no fix.

| ID | Criterion | Taxonomy | Pass Condition (evidence quoted) |
|----|-----------|----------|----------------------------------|
| FH1 | Docs freshness vs code churn | scored-in-tier | `git log -1 --format=%ct` on CLAUDE.md/README/docs vs src churn (emitter); instruction files untouched for months while src churned = drift flag. Fix = targeted refresh, never bulk regeneration. |
| FH2 | Large-file/legibility metrics | scored-in-tier | p50/max file LOC + top-N offenders via scc (emitter; LEG4 pathology inventory generalized to ALL repos); fix = report offenders + offer a max-lines lint rule. |
| FH3 | CI actually gates | scored-in-tier | Workflows contain test AND lint steps AND **gate-relevant TRIGGERS** (pull_request / push on the default branch) - step content alone is insufficient. When `gh` is authed, corroborate with required-status/branch-protection. A CI "lint" step that MUTATES (`--write`/`--fix`) can never fail = flag it. External deploy platforms (vercel.json/.netlify) INFERRED as a compile gate -> recommendation becomes "add test-gating CI (compile gate already external)"; tags=0 suppressed for continuously-deployed web repos. **Boundary (resolution 2):** FH3 grades workflow TRIGGER correctness; gate TOPOLOGY is **SV4**, never double-scored; Pillar 8 WP1 untouched. |
| FH4 | Local secrets gate | scored-in-tier | gitleaks/detect-secrets/trufflehog in the commit gate or CI (SV4-content extension) - agents generate and commit fast. Push-protection status reported alongside SE2 (report-only). |
| FH5 | Destructive-script scan | scored-in-tier | Bounded scan (POSIX classes) for recursive-delete/`--force`/`push -f`/db-drop patterns in manifest scripts, Makefiles, scripts/. Severity by CONTEXT AND TARGET (emitter provides raw hits + context class): string-literal/comment/doc-snippet = dropped; repo-internal dir the same script regenerates = informational (feeds a LEG7 never-edit line); `$HOME`/env-derived bounded path = ask-tier mention; unbounded or parameterized target = P1, named in the never/ask tiers. |
| FH6 | API contract presence (conditional) | scored-in-tier | When an HTTP framework is detected: OpenAPI/GraphQL schema/proto files as a machine-verifiable diff target; fix = suggest generation from routes. N/A when no HTTP framework detected. |
| FH7 | Module-boundary enforcement | informational | import-linter/dependency-cruiser/eslint-boundaries/Nx tags/ArchUnit config (size-tiered); suggest only above the size tiers where it pays. |
| FH8 | Feedback latency | report-only | Local suite wall time from what ALREADY executed (resolution 3 - never run a full suite for timing) + CI median derived locally from `gh run list --limit 20 --json startedAt,updatedAt,status,conclusion,headBranch` on completed default-branch runs (no `durationMs` field - compute updatedAt minus startedAt). >~10 min median caps agent iteration. Build-caching config reported alongside. |
| FH9 | gh CLI available + authed | informational (host) | `command -v gh && gh auth status` - a **host-environment line EXCLUDED from ALL repo scores** (a machine property must never make the same repo score differently per assessor). Reported in the report header. |
| FH10 | Dependency/runtime currency | report-only | Runtime major vs EOL table (ancient stacks fall outside model training distribution). |
| FH11 | Test isolation / parallel safety | report-only | Parallel agents + worktrees are flow-next's own model. |
| FH12 | Flaky-test signals | report-only | Retry config, re-run rate. |
| FH13 | LLM-eval harness (conditional) | informational | Only when an LLM SDK is in deps: `evals/` dir OR promptfoo/braintrust config - repos shipping LLM features need a verify loop for prompts like tests for code. |

---

## Criterion-to-Score Map (resolution 21a)

The single source of truth for every new/upgraded criterion's scoring behavior. Columns:
- **Group** - which pillar or tier group it belongs to.
- **Taxonomy** - `scored-in-tier` / `report-only` / `informational`.
- **Denominator** - `Pillar N` (in-pillar, feeds the level) / `group` (own group denom, EXCLUDED from level) / `none (report)` / `none (host env)`.
- **Aggregate** - how it surfaces: `pillar %` / `group pass-count` / `report line` / `info line` / `header line`.
- **Remediation** - `fix-offered` (subject to remediation.md safety rules) / `report-only` / `P0-always` (surfaced regardless of score) / `none`.
- **Hard-gate** - which of G1/G2/G3 the row feeds, else `none`.
- **Owner** - the EVIDENCE COLLECTOR: `emitter` (deterministic greps/globs/timestamps) / `host-inline` (executed or judged) / `scout` (existing rubric). Emitter-owned rows get fixture coverage; host-owned rows get prose-contract coverage.

**Upgraded legacy criteria** (stay in their pillars, feed the level; only the pass condition tightened):

| ID | Group | Taxonomy | Denominator | Aggregate | Remediation | Hard-gate | Owner |
|----|-------|----------|-------------|-----------|-------------|-----------|-------|
| SV3 | Pillar 1 | scored | Pillar 1 | pillar % | fix-offered | none | emitter (strict flags + any-ratio) + host judgment |
| SV4 | Pillar 1 | scored | Pillar 1 | pillar % | fix-offered | none | host-inline (topology judgment; emitter provides hook content) |
| SV5 | Pillar 1 | scored | Pillar 1 | pillar % | fix-offered | none | host-inline (check-mode execution) |
| SV6 | Pillar 1 | scored | Pillar 1 | pillar % | fix-offered | none | host-inline (check-mode execution) |
| BS2 | Pillar 2 | scored | Pillar 2 | pillar % | fix-offered | **G1** | host-inline (bounded build) |
| BS3 | Pillar 2 | scored | Pillar 2 | pillar % | fix-offered | none | host-inline (tier-3 boot probe) |
| TS5 | Pillar 3 | scored | Pillar 3 | pillar % | fix-offered | none | emitter (threshold config) |
| DC2 | Pillar 4 | scored | Pillar 4 | pillar % | fix-offered (augment) | **G3** | scout (quality) + host-inline (execute check) |
| DE1 | Pillar 5 | scored | Pillar 5 | pillar % | fix-offered | none | emitter (env cross-ref counts) |
| DE4 | Pillar 5 | scored | Pillar 5 | pillar % | fix-offered | none | emitter (content grep, static + cross-ref) |
| DE5 | Pillar 5 | scored | Pillar 5 | pillar % | fix-offered | none | emitter (config grep) |

**New tier-group criteria** (group denominator, EXCLUDED from the level formula):

| ID | Group | Taxonomy | Denominator | Aggregate | Remediation | Hard-gate | Owner |
|----|-------|----------|-------------|-----------|-------------|-----------|-------|
| AO1-AO5 | AO | scored-in-tier | group | group pass-count | fix-offered | none | host-inline (boot-probe reuse + greps) |
| DR1-DR5 | DR | scored-in-tier | group | group pass-count | fix-offered | none | host-inline (greps + boot-probe reuse) |
| DR6 | DR | scored-in-tier | group | group pass-count | fix-offered | none | host-inline (`--help` pattern reuse) |
| DR7 | DR | scored-in-tier | group | group pass-count | fix-offered | none | host-inline (stack-gated grep) |
| TO1-TO4 | TO | scored-in-tier | group | group pass-count | fix-offered | none | host-inline (config greps) |
| DT1-DT2 | DT | informational | none (report) | info line | none | none | host-inline (config greps) |
| HP1 | HP | scored-in-tier | group | group pass-count | fix-offered (deny/ask-safe) | none | host-inline (symlink-graph diff) |
| HP2 | HP | scored-in-tier | group | group pass-count | fix-offered (deny/ask-safe) | none | host-inline (config parse) |
| HP5 | HP | scored-in-tier | group | group pass-count | fix-offered (deny-safe) | none | host-inline (config read + .gitignore derive) |
| HP7 | HP | scored-in-tier | group | group pass-count | fix-offered (read-back + exercised) / **P0-always** on suspicious | none | host-inline (hook content from emitter) |
| HP9 | HP | scored-in-tier | group | group pass-count | **P0-always** on inline secret (key name only) | none | host-inline (config read) |
| HP12 | HP | scored-in-tier | group | group pass-count | fix-offered | none | host-inline (git-index check; committed content feeds HP3/5/7) |
| HP3,4,6,8,10,11,13-16 | HP | informational | none (report) | info line | report-only | none | host-inline (config reads) |
| FH1 | FH | scored-in-tier | group | group pass-count | fix-offered (targeted refresh) | none | emitter (timestamps vs churn) |
| FH2 | FH | scored-in-tier | group | group pass-count | fix-offered (max-lines rule) | none | emitter (scc metrics) |
| FH3 | FH | scored-in-tier | group | group pass-count | fix-offered | none | emitter (trigger + mutating-lint greps) + host (gh corroboration) |
| FH4 | FH | scored-in-tier | group | group pass-count | fix-offered | none | emitter (`tools_found` = enforced invocations; `configs_found` = config presence, evidence-only) |
| FH5 | FH | scored-in-tier | group | group pass-count | fix-offered (never/ask tiers) | none | emitter (raw hits + context class) |
| FH6 | FH | scored-in-tier | group | group pass-count | fix-offered (suggest gen) | none | emitter (contract globs) |
| FH7 | FH | informational | none (report) | info line | report-only | none | emitter (config presence) |
| FH8 | FH | report-only | none (report) | report line | none | none | host-inline (latency derivation) |
| FH9 | FH | informational (host) | none (host env) | header line | none | none | host-inline (`command -v gh`) |
| FH10-FH12 | FH | report-only | none (report) | report line | none | none | emitter (config presence) |
| FH13 | FH | informational | none (report) | info line | report-only | none | emitter (config presence, deps-gated) |

---

## N/A Whitelist (single source - resolution 11)

Only these criteria may be marked **N/A**; the model may NOT invent N/A elsewhere. Excluded criteria drop from **both** numerator and denominator of their pillar/group and are listed separately - never counted as ❌. Classification (Phase 0.5) adds N/A entries ONLY via this table. `workflow.md` references this table; it never restates the list.

| Criterion(s) | N/A condition |
|---|---|
| BS6 | Non-monorepo (no workspace/build-graph config) |
| TS6 | No E2E surface (library/CLI with no UI/integration boundary) |
| DE5 | No container need |
| DE6 | No container need |
| DC7 | Backend-only project (no frontend) |
| AO1-AO5, DR1-DR5, DR7, TO1-TO4 | Ladder-capped stack (tier 1-2 ceiling) OR non-web shape (library/plugin/prose/docs) - web observability/drivability inapplicable |
| DR3, DR4, DR5 | CLI-shaped repo - swapped for DR6 (agent-first CLI) as the drivability surface |
| DR6 | Non-CLI shape with no service binary |
| DR7 | Stack ships no framework dev-MCP (per the stacks.md map column) |
| HP1-HP16 | Harness INACTIVE (no config dir / stale by commit recency) - grade only ACTIVE harnesses, mapping each criterion to the active harness's native mechanism or N/A |
| HP14 | Windows host (Claude sandbox unavailable) - N/A, never fail |
| FH6 | No HTTP framework detected |
| FH13 | No LLM SDK in deps |
| All Pillars 1-8 scored criteria | **Greenfield lifecycle** - scorecard SUPPRESSED; premature pillars get **recorded-deferral N/A** ("no observability yet - deferred until first deploy"). A documented deferral beats BOTH a silent gap AND a stub file. |

**Floor-check rule (resolution 1):** pillars OR groups whose criteria are **ALL excluded** (shape/tier N/A, greenfield deferral, inactive harness) are **SKIPPED from the floor checks** - never counted as a 0% pillar that caps the level. This stops a healthy library (no monorepo/E2E/Docker) from being capped at 67% and locked out of Level 5, and stops a Codex-only repo from being floored by inactive HP criteria.

---

## Scoring Summary

### Agent Readiness Score (Pillars 1-5)

Used for maturity level calculation and remediation decisions.

| Level | Name | Requirements |
|-------|------|--------------|
| 1 | Minimal | <30% overall |
| 2 | Functional | 30-49% overall |
| 3 | Standardized | 50-69% overall, all pillars ≥40% |
| 4 | Optimized | 70-84% overall, all pillars ≥60% |
| 5 | Autonomous | 85%+ overall, all pillars ≥80% |

**Agent Readiness Score / maturity level** = average of Pillars 1-5 scores **ONLY**. The scored tier groups (AO/DR/TO/HP-core/FH-scored) are NOT folded in - cross-repo level comparability requires a stable denominator (the 48 legacy criteria). The tier groups surface as separate group pass-count lines and drive the verdict headline + ranked actions instead.

**Floor checks (the "all pillars ≥ N%" columns above):** pillars OR groups whose criteria are ALL excluded (shape/tier N/A, greenfield deferral, inactive harness - per the N/A whitelist) are SKIPPED, never counted as a 0% pillar that caps the level.

### Hard gates (cap the maturity level regardless of score)

Three gates cap agent readiness at **Level 2** when failing, with the failure named in the headline (this kills "Level 5 with a broken build"):

- **G1** - the detected build command actually runs, OR operability tier >= 1 evidence exists (feeds from BS2 + the operability ladder).
- **G2** - tests are discoverable when a test framework is claimed (existing TS4).
- **G3** - commands quoted in CLAUDE.md/AGENTS.md actually resolve/execute (DC2 execute check; extraction-failure on a file that HAS fenced blocks is itself a flag, never a vacuous pass).

Windows-only / host-unbuildable targets are recorded "not probed on this host", never a fabricated ✅; the unverified-counts-as-fail rule extends to every executed gate.

### DC2 published scale

The single published DC2 coverage scale is **X/8** (the 8-row claude-md-scout rubric; pass ~5/8). Every file that cites the DC2 bar normalizes to this scale - there is no /10 variant.

### Production Readiness Score (Pillars 6-8)

Informational only. Reported for awareness.

**Production Readiness Score** = average of Pillars 6-8 scores

### Overall Score

**Overall Score** = average of all 8 pillars. (The tier groups are reported as pass-count lines and are not part of any pillar average.)

---

## What Gets Fixed vs Reported

| Scope | Category | Remediation |
|-------|----------|-------------|
| Pillars 1-5 | Agent Readiness (level basis) | ✅ Fixes offered via AskUserQuestion |
| Tier groups: AO / DR / TO scored, HP scored-core, FH1-FH6 | Agent Readiness (level-excluded) | ✅ Fixes offered per the ranked catalog + remediation.md safety rules; inline-secret (HP9) and suspicious-hook (HP7) findings surface as P0 regardless of score |
| Pillars 6-8, DT, HP-informational, FH report-only, gh-CLI | Production / report-only | ❌ Reported only, address independently |

**Level 3 (Standardized)** is the target for agent readiness. It means agents can handle routine work: bug fixes, tests, docs, dependency updates.
