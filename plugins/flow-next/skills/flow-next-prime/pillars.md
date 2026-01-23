# Agent Readiness Pillars

Six pillars for evaluating codebase agent-readiness. Each criterion is binary (pass/fail).

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

## Pillar 2: Build System

Clear build process that agents can execute reliably.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| BS1 | Build tool detected | Vite, webpack, tsc, cargo, go build, etc. |
| BS2 | Build command exists | `build` script in package.json/Makefile |
| BS3 | Dev command exists | `dev` or `start` script available |
| BS4 | Build output gitignored | dist/, build/, .next/, target/ in .gitignore |
| BS5 | Lock file committed | package-lock.json, pnpm-lock.yaml, Cargo.lock, etc. |
| BS6 | CI builds project | Build step in GitHub Actions or equivalent |

### Scoring
- ✅ 80%+: Reproducible builds
- ⚠️ 40-79%: Builds work but fragile
- ❌ <40%: Build process unclear

## Pillar 3: Testing

Test infrastructure that lets agents verify their work.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| TS1 | Test framework configured | Jest, Vitest, pytest, go test, etc. |
| TS2 | Test command exists | `test` script available |
| TS3 | Tests exist | >0 test files in repo |
| TS4 | Tests run in CI | Test step in CI config |
| TS5 | Coverage configured | nyc, c8, coverage.py, etc. |
| TS6 | E2E tests exist | Playwright, Cypress, or integration tests |

### Scoring
- ✅ 80%+: Comprehensive test setup
- ⚠️ 40-79%: Basic testing in place
- ❌ <40%: Testing gaps

## Pillar 4: Documentation

Clear docs that tell agents how the project works.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| DC1 | README exists | README.md with content |
| DC2 | CLAUDE.md/AGENTS.md exists | Agent instruction file present |
| DC3 | Setup documented | Installation/setup instructions in README or docs |
| DC4 | Build commands documented | How to build/run in README or CLAUDE.md |
| DC5 | Test commands documented | How to run tests documented |
| DC6 | Architecture documented | ARCHITECTURE.md, ADRs, or docs/ with structure |

### Scoring
- ✅ 80%+: Agents can self-serve
- ⚠️ 40-79%: Basic docs present
- ❌ <40%: Agents must guess

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

## Pillar 6: Team Governance (Informational)

**Note**: This pillar measures team processes, NOT agent readiness. Reported for awareness but NOT included in agent maturity calculation. No remediation offered for these items.

### Criteria

| ID | Criterion | Pass Condition |
|----|-----------|----------------|
| CQ1 | CONTRIBUTING.md exists | Contribution guidelines present |
| CQ2 | Branch protection | Main branch protected (check via gh api if possible) |
| CQ3 | PR template exists | .github/PULL_REQUEST_TEMPLATE.md |
| CQ4 | Issue templates exist | .github/ISSUE_TEMPLATE/ |
| CQ5 | CODEOWNERS exists | .github/CODEOWNERS file |
| CQ6 | License exists | LICENSE file present |

### Scoring
- Reported for awareness only
- Does NOT affect agent maturity level
- Team should address these independently if desired

---

## Maturity Level Calculation

**Based on Pillars 1-5 only** (Style, Build, Testing, Documentation, Dev Environment). Pillar 6 (Team Governance) is informational and excluded from scoring.

| Level | Name | Requirements |
|-------|------|--------------|
| 1 | Minimal | <30% overall |
| 2 | Functional | 30-49% overall |
| 3 | Standardized | 50-69% overall, all pillars ≥40% |
| 4 | Optimized | 70-84% overall, all pillars ≥60% |
| 5 | Autonomous | 85%+ overall, all pillars ≥80% |

**Overall score** = average of Pillars 1-5 scores

**Level 3 (Standardized)** is the target for most teams. It means agents can handle routine work: bug fixes, tests, docs, dependency updates.
