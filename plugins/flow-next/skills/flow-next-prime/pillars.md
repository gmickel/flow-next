# Agent Readiness Pillars

Eight pillars for comprehensive codebase assessment. Pillars 1-5 measure **agent readiness** (fixes offered). Pillars 6-8 measure **production readiness** (reported only).

---

## Pillar 1: Style & Validation

Automated tools that catch bugs instantly. Without them, agents waste cycles on syntax errors and style drift.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| SV1 | Linter configured | ESLint, Biome, oxlint, Flake8, Ruff, golangci-lint, or Clippy config exists |
| SV2 | Formatter configured | Prettier, Biome, Black, gofmt, or rustfmt config/usage detected |
| SV3 | Type checking | TypeScript strict, mypy, pyright, or language with static types |
| SV4 | Pre-commit hooks | Husky, pre-commit, lefthook, or similar configured |
| SV5 | Lint script exists | `lint` command in package.json, Makefile, or equivalent |
| SV6 | Format script exists | `format` command available |

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
| BS2 | Build command exists | `build` script in package.json/Makefile |
| BS3 | Dev command exists | `dev` or `start` script available |
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
| TS5 | Coverage configured | nyc, c8, coverage.py, etc. |
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
| DC2 | CLAUDE.md/AGENTS.md exists | Agent instruction file present |
| DC3 | Setup documented | Installation/setup instructions in README or docs |
| DC4 | Build commands documented | How to build/run in README or CLAUDE.md |
| DC5 | Test commands documented | How to run tests documented |
| DC6 | Architecture documented | ARCHITECTURE.md, ADRs, or docs/ with structure |

### Scoring
- ✅ 80%+: Agents can self-serve
- ⚠️ 40-79%: Basic docs present
- ❌ <40%: Agents must guess

---

## Pillar 5: Dev Environment

Reproducible environment setup.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| DE1 | .env.example exists | Template for required env vars |
| DE2 | .env gitignored | .env in .gitignore |
| DE3 | Runtime version pinned | .nvmrc, .python-version, .tool-versions, etc. |
| DE4 | Setup script or docs | setup.sh or clear setup instructions |
| DE5 | Devcontainer available | .devcontainer/ config present |
| DE6 | Docker available | Dockerfile or docker-compose.yml |

### Scoring
- ✅ 80%+: One-command setup possible
- ⚠️ 40-79%: Setup mostly documented
- ❌ <40%: Setup requires tribal knowledge

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
| SE1 | Branch protection | Main/master branch protected (via `gh api`) |
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

**Agent Readiness Score** = average of Pillars 1-5 scores

### Production Readiness Score (Pillars 6-8)

Informational only. Reported for awareness.

**Production Readiness Score** = average of Pillars 6-8 scores

### Overall Score

**Overall Score** = average of all 8 pillars

---

## What Gets Fixed vs Reported

| Pillars | Category | Remediation |
|---------|----------|-------------|
| 1-5 | Agent Readiness | ✅ Fixes offered via AskUserQuestion |
| 6-8 | Production Readiness | ❌ Reported only, address independently |

**Level 3 (Standardized)** is the target for agent readiness. It means agents can handle routine work: bug fixes, tests, docs, dependency updates.
