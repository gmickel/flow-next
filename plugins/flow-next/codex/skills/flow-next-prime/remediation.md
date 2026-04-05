# Remediation Templates

Templates for fixing agent readiness gaps. Focus on what helps agents work effectively: fast local feedback, clear commands, documented conventions.

**Priority order:**
1. **Critical**: CLAUDE.md, .env.example, lint/format commands
2. **High**: Pre-commit hooks, test command, runtime version
3. **Medium**: Build scripts, .gitignore entries
4. **Low/Bonus**: Devcontainer, Docker (nice-to-have, not essential)

**NOT offered** (team governance, not agent readiness):
- CONTRIBUTING.md, PR templates, issue templates, CODEOWNERS, LICENSE

---

## Critical: Documentation

### Create CLAUDE.md

Location: `CLAUDE.md` (repo root)

**Why**: Agents need to know project conventions, commands, and structure. Without this, they guess.

Template (adapt based on detected stack):

```markdown
# Project Name

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

# Format code
[detected format command]
```

## Project Structure

```
[detected structure - key directories only]
```

## Code Conventions

- [Detected naming convention]
- [Detected file organization]
- [Patterns from existing code]

## Things to Avoid

- [Common pitfalls for this stack]
```

### Create .env.example

Location: `.env.example` (repo root)

**Why**: Agents waste cycles guessing env vars. This documents what's required.

Process:
1. Scan code for env var usage (process.env.*, os.environ, etc.)
2. Create template with detected vars
3. Add placeholder values and comments

Template:

```bash
# Required for [feature]
VAR_NAME=your_value_here

# Optional: [description]
OPTIONAL_VAR=default_value
```

---

## High: Fast Local Feedback

### Add Pre-commit Hooks (JavaScript/TypeScript)

**Why**: Agents get instant feedback instead of waiting 10min for CI.

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

### Add Linter Config (if NO linter detected)

**Important**: Only offer if NO linter exists. ESLint, Biome, oxlint, Ruff are all valid. Don't replace one with another.

Recommend based on project:
- **Biome** (recommended for new projects): fast, does lint + format
- **ESLint** (established projects): wide ecosystem
- **oxlint** (performance-critical): very fast
- **Ruff** (Python): very fast

Example ESLint - `eslint.config.js`:

```javascript
import js from '@eslint/js';

export default [
  js.configs.recommended,
];
```

Example Biome - `biome.json`:

```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.4/schema.json",
  "linter": { "enabled": true },
  "formatter": { "enabled": true }
}
```

### Add Formatter Config (if NO formatter detected)

**Important**: Only offer if NO formatter exists. Biome handles both lint + format. Prettier, Black, gofmt are all valid.

Example Prettier - `.prettierrc`:

```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2
}
```

Note: If Biome is already configured, it handles formatting. Don't add Prettier.

### Add Runtime Version File

For Node.js, create `.nvmrc`:
```
20
```

For Python, create `.python-version`:
```
3.12
```

---

## Medium: Build & Environment

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

### Add Test Config (if test framework detected but no config)

Jest - create `jest.config.js`:

```javascript
/** @type {import('jest').Config} */
const config = {
  testEnvironment: 'node',
  testMatch: ['**/*.test.js', '**/*.test.ts'],
};

module.exports = config;
```

Vitest - create `vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
  },
});
```

pytest - create `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
```

---

## Low/Bonus: Optional Enhancements

These are nice-to-have but NOT essential for agent readiness. Only offer if user explicitly wants them.

### Create Devcontainer (Bonus)

Create `.devcontainer/devcontainer.json`:

```json
{
  "name": "[Project Name]",
  "image": "mcr.microsoft.com/devcontainers/[language]:latest",
  "features": {},
  "postCreateCommand": "[install command]"
}
```

### Add Basic CI Workflow (Bonus)

**Note**: Agents benefit more from pre-commit hooks (instant feedback) than CI (slow feedback). Only add if user wants CI.

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
      - name: Install
        run: [install command]
      - name: Lint
        run: [lint command]
      - name: Test
        run: [test command]
```

---

## Application Rules

1. **Detect before creating** - Check if file exists first
2. **Preserve existing content** - Merge with existing configs when possible
3. **Match project style** - Use detected indent (tabs/spaces), quote style
4. **Don't add unused features** - Only add what the project needs
5. **Explain changes** - Tell user what was created and why
6. **Respect user choices** - Never force changes without consent
