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

### Create OR Augment the Agent Instruction File

**Pick the right file, and detect the existing convention first:**
- If the repo already has a real (non-symlink) `AGENTS.md` OR `CLAUDE.md`, **augment that one** — do NOT create a second competing file. (Many repos standardize on `AGENTS.md` + a `CLAUDE.md` symlink; respect it.)
- If neither exists, create the host platform's file: **`CLAUDE.md`** on Claude Code / Droid, **`AGENTS.md`** on Codex. (The Codex mirror rewrites this section accordingly.)

**Create vs. augment — this is the common 2026 case.** Most repos now HAVE an agent file; few have a *good* one. When agents-md-scout reports a low coverage score (a stub like "Be careful, write tests"), the fix is **augment**: add ONLY the sections it flagged missing (Quick Commands, Project Structure, Conventions, …) via the existing-file consent path — never overwrite the user's content, and never offer a no-op "create" when a file already exists. DC2 passes only when the file exists AND clears the coverage bar (scout score ≥ ~5/10); a thin stub is a ⚠️ that this fix targets.

**Why**: Agents need to know project conventions, commands, and structure. Without this, they guess.

Template (adapt based on detected stack — for AUGMENT, take only the missing sections):

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

**CRITICAL — the lint-staged commands MUST match the linter/formatter tooling-scout detected;
never reference a tool that isn't in the repo.** A hardcoded `eslint --fix`/`prettier --write`
in a Biome-only repo makes EVERY subsequent `git commit` fail with `eslint: command not found` —
a "fix" that actively breaks agent readiness. Pick the block for the detected stack:

```jsonc
// Biome repo: "*.{js,ts,tsx,json}": ["biome check --write --no-errors-on-unmatched"]
// ESLint+Prettier: "*.{js,ts,tsx}": ["eslint --fix", "prettier --write"], "*.{json,md}": ["prettier --write"]
// Ruff (Python): "*.py": ["ruff check --fix", "ruff format"]
```

If husky not installed, add `husky` + `lint-staged` to devDependencies, then:
```bash
npx husky init
# APPEND, don't truncate an existing hook:
grep -q 'lint-staged' .husky/pre-commit 2>/dev/null || echo "npx lint-staged" >> .husky/pre-commit
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

**Detect the version — never write a literal.** Writing a stale/EOL version (`.nvmrc` 20 is
EOL Apr 2026) manufactures the exact env drift (DE3) this fix exists to prevent: local nvm/fnm
and devcontainers silently switch to a runtime that diverges from CI. Source the version from,
in order: `package.json` `engines.node` / CI workflow matrix / `node --version`; for Python,
`pyproject.toml requires-python` / `python --version`. Only write the file if a version is
actually evidenced in the repo/toolchain.

```bash
# Node: e.g. NODE_VER=$(node --version | sed 's/^v//; s/\..*//') → echo "$NODE_VER" > .nvmrc
# Python: derive from requires-python or `python --version` → echo "$PY_VER" > .python-version
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
*.swp
```

> Do NOT append `.vscode/` — many teams deliberately commit `.vscode/settings.json`
> (shared debug/task config). Only add it if it isn't already tracked (`git ls-files .vscode`
> is empty), and prefer ignoring only local files (`.vscode/*` with `!.vscode/settings.json`).

### Add Test Config (if test framework detected but no config)

Jest - create `jest.config.cjs` (use `.cjs`, not `.js` — `module.exports` fails to load in a
`"type": "module"` package; `.cjs` is safe in both CJS and ESM repos):

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

pytest - create `pytest.ini` (set `testpaths` ONLY to the directory testing-scout actually
found tests in — hardcoding `tests` when tests live in `src/**/test_*.py` makes pytest
discover ZERO tests, regressing TS3/TS4 on the next run; omit the key entirely if unsure):

```ini
[pytest]
# testpaths = <detected test dir(s)> # omit if tests aren't in a single known dir — auto-discovery works
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
