# Remediation Templates

Templates for fixing common agent readiness gaps. Each section includes what to create and where.

## Documentation Fixes

### Create CLAUDE.md

Location: `CLAUDE.md` (repo root)

Template (adapt based on detected stack):

```markdown
# Project Name

## Overview
[One paragraph describing what this project does]

## Quick Commands

```bash
# Install dependencies
[detected package manager] install

# Run development server
[detected dev command]

# Run tests
[detected test command]

# Build for production
[detected build command]

# Lint code
[detected lint command]
```

## Project Structure

```
[detected structure]
```

## Code Conventions

- [Detected naming convention]
- [Detected file organization]
- [Any patterns from existing code]

## Things to Avoid

- [Common pitfalls for this stack]
```

### Create .env.example

Location: `.env.example` (repo root)

Process:
1. Scan code for env var usage (process.env.*, os.environ, etc.)
2. Create template with detected vars
3. Add placeholder values and comments

Template:

```bash
# Required for [feature]
VAR_NAME=placeholder_value

# Optional: [description]
OPTIONAL_VAR=default_value
```

### Create ADR Template

Location: `docs/adr/0001-record-architecture-decisions.md`

First, create directory and template:

```markdown
# 1. Record Architecture Decisions

Date: [today]

## Status

Accepted

## Context

We need to record the architectural decisions made on this project.

## Decision

We will use Architecture Decision Records (ADRs) as described by Michael Nygard.

## Consequences

- Decisions are documented and discoverable
- New team members can understand past choices
- Agents can reference decisions when making changes
```

Also create `docs/adr/template.md`:

```markdown
# [Number]. [Title]

Date: [YYYY-MM-DD]

## Status

[Proposed | Accepted | Deprecated | Superseded by [link]]

## Context

[What is the issue that we're seeing that is motivating this decision?]

## Decision

[What is the change that we're proposing and/or doing?]

## Consequences

[What becomes easier or harder as a result of this change?]
```

## Tooling Fixes

### Add Pre-commit Hooks (JavaScript/TypeScript)

If husky not installed, add to package.json devDependencies:

```json
{
  "devDependencies": {
    "husky": "^9.0.0",
    "lint-staged": "^15.0.0"
  },
  "lint-staged": {
    "*.{js,ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.{json,md}": ["prettier --write"]
  }
}
```

Then run:
```bash
npx husky init
echo "npx lint-staged" > .husky/pre-commit
```

### Add Pre-commit Hooks (Python)

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

### Add ESLint Config (if missing)

Create `eslint.config.js` (flat config, modern):

```javascript
import js from '@eslint/js';

export default [
  js.configs.recommended,
  {
    rules: {
      // Add project-specific rules
    }
  }
];
```

### Add Prettier Config (if missing)

Create `.prettierrc`:

```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5"
}
```

## Environment Fixes

### Add .gitignore Entries

Append to `.gitignore` if missing:

```
# Environment
.env
.env.local
.env.*.local

# Build outputs
dist/
build/
.next/
out/

# Dependencies
node_modules/

# IDE
.idea/
.vscode/
*.swp
```

### Add Runtime Version File

For Node.js, create `.nvmrc`:
```
20
```

For Python, create `.python-version`:
```
3.12
```

### Create Devcontainer

Create `.devcontainer/devcontainer.json`:

```json
{
  "name": "[Project Name]",
  "image": "mcr.microsoft.com/devcontainers/[language]:latest",
  "features": {},
  "postCreateCommand": "[install command]",
  "customizations": {
    "vscode": {
      "extensions": [
        // Add relevant extensions
      ]
    }
  }
}
```

## Testing Fixes

### Add Jest Config (JavaScript/TypeScript)

Create `jest.config.js`:

```javascript
/** @type {import('jest').Config} */
const config = {
  testEnvironment: 'node',
  testMatch: ['**/*.test.js', '**/*.test.ts'],
  collectCoverageFrom: ['src/**/*.{js,ts}'],
};

module.exports = config;
```

### Add Vitest Config (modern alternative)

Create `vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    coverage: {
      reporter: ['text', 'json', 'html'],
    },
  },
});
```

### Add pytest.ini (Python)

Create `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
```

## CI Fixes

### Add GitHub Actions Workflow

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup [runtime]
        uses: actions/setup-[runtime]@v4
        with:
          [runtime]-version-file: '.[runtime]-version'

      - name: Install dependencies
        run: [install command]

      - name: Lint
        run: [lint command]

      - name: Test
        run: [test command]

      - name: Build
        run: [build command]
```

## Code Quality Fixes

### Create CONTRIBUTING.md

```markdown
# Contributing to [Project Name]

## Getting Started

1. Fork the repository
2. Clone your fork
3. Install dependencies: `[install command]`
4. Create a branch: `git checkout -b feature/your-feature`

## Development

```bash
# Run development server
[dev command]

# Run tests
[test command]

# Lint code
[lint command]
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Update CHANGELOG.md if applicable

## Code Style

[Describe code style or link to CLAUDE.md]
```

### Create PR Template

Create `.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
## Description

[Describe your changes]

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Checklist

- [ ] Tests pass locally
- [ ] Lint passes
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG updated (if needed)
```

---

## Application Rules

1. **Detect before creating** - Check if file exists first
2. **Preserve existing content** - Merge with existing configs when possible
3. **Match project style** - Use detected indent (tabs/spaces), quote style, etc.
4. **Don't add unused features** - Only add what the project needs
5. **Explain changes** - Tell user what was created and why
