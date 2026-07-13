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

**Create vs. augment - this is the common 2026 case.** Most repos now HAVE an agent file; few have a *good* one. When agents-md-scout reports a low coverage score (a stub like "Be careful, write tests"), the fix is **augment**: add ONLY the sections it flagged missing (Quick Commands, Project Structure, Conventions, …) via the existing-file consent path - never overwrite the user's content, and never offer a no-op "create" when a file already exists. DC2 passes only when the file exists AND clears the coverage bar on the single published scale **X/8** (pass ~5/8 - the 8-row agents-md-scout rubric; there is no /10 variant); a thin stub is a ⚠️ that this fix targets.

**NEVER bulk-generate a full instruction file (hard - measured harm).** LLM-bulk-generated CLAUDE.md/AGENTS.md is FORBIDDEN as a fix: ETH Zurich arXiv 2602.11988 measured that generated instruction files harm agent performance (they read plausibly and drift from the code). The only sanctioned shapes are (a) a **short hand-fill skeleton** the human completes (the template below - headings + placeholders, commands-first, never prose the model invented), or (b) a **targeted augment** adding only the specific missing sections agents-md-scout flagged, drawn from evidence prime actually gathered (Phase-2-verified commands, detected structure). Prime never emits a paragraph of invented conventions, a generic persona, or a full directory listing the agent could discover itself. When in doubt, offer fewer sections and let the human fill them.

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

### Deterministic gates at the RIGHT layer (SV4 / catalog #6)

**The layering rule is load-bearing - read before offering any hook.** Deterministic gates belong
at the layer that fits their cost (SV4, pillars.md):

- **Edit / commit layer (L1/L2):** fast, file/staged-**scoped** FORMAT + LINT only - `<10s`,
 auto-fix, scoped to the staged files. This is what a git / harness hook is FOR.
- **Verify + acceptance + CI layer (L3/L4):** TESTS, typecheck-all, coverage, E2E. These are the
 verify command + acceptance requirements + a CI required check - NOT a hook.

**Prime NEVER offers a test-running pre-commit hook.** A test suite / E2E / coverage wired into a
pre-commit hook is a known agent bypass/stall risk (the `--no-verify` incident, terminal-hook
failures) - it duplicates flow-next's own work-loop gate with a worse failure mode. "No git hooks
but a hardened CI + verify command" is a legitimate PASS; the ABSENCE of edit/commit-layer
format/lint enforcement is a headroom warn, never a pass-blocker.

**HP7 read-vs-exercise + exercise-in-pass (hard).** During ASSESSMENT prime READS hook content and
never executes it (a committed hook is an RCE vector - CVE-2025-59536 class). During REMEDIATION
the distinction inverts: any hook prime OFFERS is built from **Phase-2-verified commands**,
read-back gated, and **EXERCISED in the same pass** (the hook is invoked once against a sample so
it is never a stub that would pass prime's own checks unexercised). This exercise-what-you-scaffold
rule applies to EVERY artifact prime creates, not just hooks. Harness settings/hook files are
**explicit-consent-only** even under `--fix-all` (they are the harness attack surface).

### Add a format/lint commit hook (JavaScript/TypeScript) - staged-scope, format+lint ONLY

**Why**: Agents get instant format/lint feedback on the staged files instead of waiting 10min for
CI. This hook runs formatters + file-scoped linters ONLY - never the test suite (tests are the
verify command + CI, above).

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

### Add a format/lint commit hook (Python) - staged-scope, format+lint ONLY

Create `.pre-commit-config.yaml` with format + lint hooks ONLY (no `pytest` hook - tests are the
verify command + CI, per the layering rule above):

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

Exercise it once after writing (`pre-commit run --all-files` or against a sample) so the offered
hook is verified, not a stub.

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

## Structural & consent-classed templates (fn-92)

These are the artifacts the classification-driven playbooks (playbooks.md) offer. **Every one is
explicit-consent-only - NEVER auto-applied under `--fix-all`** (they restructure the repo, touch
the harness attack surface, or live outside the repo ROOT). The consent CLASS is marked on each.
The **exercise-what-you-scaffold** rule holds throughout: anything prime creates is exercised in
the same pass (the wrapper runs, the hook fires) or is explicitly marked unverified - prime never
leaves a stub that would pass its own checks.

### Orientation map skeleton (consent: explicit - structural)

The LEG3 substitute-navigation artifact for stacks where `/flow-next:map` is not practical (Map cell
`none`/`partial` in stacks.md) - a hand-written top-level map. Prime fills the top-level dirs +
entrypoints it can detect; the human writes the one-line module purposes (prime never invents them):

```markdown
# Orientation map

> Where things live. Nearest-wins with any nested instruction files.

## Entrypoints
- `[detected main.* / index.* / cmd/*/main.go / *.dpr]` - [one line: what boots here]

## Top-level modules
- `[dir]/` - [one-line purpose - human fills]
- `[dir]/` - [one-line purpose - human fills]

## Build & verify
- Build: `[Phase-2-verified build command]`
- Test: `[Phase-2-verified test-list command]`

## Never-edit / generated (LEG7)
- `[tool-managed dir]/` - regenerated by `[script]`; never hand-edit
```

### Headless compile wrapper (consent: explicit - structural; LEG1)

The tier-1 top recommendation: a one-command headless build per project/module so the agent has a
compile feedback loop. The concrete command is DATA from the detected stack's stacks.md verify
column (e.g. Delphi `rsvars.bat && msbuild X.dproj /t:Build`; .NET Framework `msbuild /t:Build
/restore`, never `dotnet build`). Generic POSIX skeleton - exercise it once (run the wrapper) before
offering:

```bash
#!/usr/bin/env sh
# build.sh - headless compile wrapper. Exits non-zero on build failure so CI/agents get a gate.
set -eu
# <stacks.md verify-column build command for the detected stack/module>
# e.g. Go: go build ./...
# e.g. .NET Framework (Windows host only): msbuild /t:Build /restore MySolution.sln
exec <build command> "$@"
```

Windows-only / license-bound builds that cannot run on the current host are documented as "not
probed on this host" - the wrapper is still offered, but its exercise step is skipped with that note.

### Encoding-guard hook (consent: explicit - harness file; LEG5)

For legacy sources with BOM/codepage hazards (ANSI/Windows-1252/UTF-16 - coding agents have
documented corruption bugs on non-UTF-8 files). A **read-only** staged-files guard that BLOCKS a
commit introducing a non-UTF-8 (or newly BOM-carrying) file - it never rewrites content (the sweep
must never itself corrupt anything). Exercise it once against a sample before offering:

```bash
#!/usr/bin/env sh
# .husky/pre-commit (or pre-commit-config local hook) - encoding guard, format/lint layer.
# Read-only: flags non-UTF-8 staged files, never rewrites them.
set -eu
bad=0
for f in $(git diff --cached --name-only --diff-filter=ACM); do
 [ -f "$f" ] || continue
 # `file` returns charset; block anything not utf-8/us-ascii. POSIX classes only.
 enc=$(file --mime-encoding -b "$f" 2>/dev/null || echo unknown)
 case "$enc" in
 utf-8|us-ascii|binary) : ;;
 *) echo "encoding-guard: $f is $enc (expected utf-8) - normalize deliberately or add to the never-edit list"; bad=1 ;;
 esac
done
[ "$bad" -eq 0 ] || exit 1
```

Alternative offers (per LEG5): a deliberate one-time normalization commit, or a never-edit list for
the affected files in the agent file.

### Deny-rules baseline (consent: explicit - harness file)

**Deny/ask rules are the ONLY permissions artifact safe to scaffold** - they apply WITHOUT workspace
trust and only RESTRICT (modelled on anthropics/claude-code `examples/settings`). Never scaffold
allow rules except entries derived from commands prime itself executed in Phase 2, and state that
project allow rules are inert until the workspace-trust dialog is accepted. **Never scaffold:**
`defaultMode` changes, `bypassPermissions`, `danger-full-access`, `approval_policy` never,
`additionalDirectories`, HTTP hooks, MCP server installs. Secret paths come from the repo's own
`.gitignore` secret-shaped entries (HP5). Claude Code `.claude/settings.json`:

```json
{
 "permissions": {
 "deny": [
 "Read(./.env)",
 "Read(./.env.*)",
 "Read(./**/*.pem)",
 "Read(./**/secrets/**)"
 ],
 "ask": [
 "Bash(git push:*)",
 "Bash(rm -rf:*)",
 "Bash(curl:*)",
 "Bash(wget:*)"
 ]
 }
}
```

Cursor parity: `.cursorignore` carrying `.env*`, key files, and secret dirs (Cursor has no
allow/deny model - access-scoping is the mechanism). Never report "allow rules present" as "prompts
eliminated" - project allow rules are inert until workspace trust is accepted; say so.

### Run-and-observe recipe (consent: `--fix-all` in-root - agent-file content; catalog #13)

The AO/DR drivability unlock: a block in the agent file giving the agent everything it needs to boot
the app and read its own runtime evidence. In-root agent-file content, so `--fix-all`-eligible - but
only the recipe TEXT, never an MCP install (explicit-consent). Fill every field from detected
evidence; omit a field rather than guess it:

```markdown
## Run & observe (for agents)

```bash
# Start dev server (fixed port, non-interactive)
[detected dev command] # e.g. PORT=3000 pnpm dev
```

- **Ready line**: `[literal ready line to wait for, e.g. "ready on http://localhost:3000"]`
- **Port**: `[fixed port]`
- **Logs**: `[log file path OR "stdout - tail with the dev command above"]`
- **Verbose**: set `[DEBUG / LOG_LEVEL var]` for request-level logging
- **Health check**: `curl -sf http://localhost:[port]/[health path]`
- **Dev login / seeded user**: `[env-gated test user, or the seed command]`
```

### Home-base starter kit (consent: EXPLICIT - OUTSIDE the repo ROOT)

**This kit is written to the PARENT directory, outside the assessed repo ROOT - explicit-consent-only,
NEVER `--fix-all`, regardless of tier.** Offered only for the full home-base constellation variant
(service composition detected - playbooks.md selector); the light product-family variant gets the
R15 "Repo context" block + a docs-update-as-DoD line instead, not this kit. The manifest is the
single source of truth - the parent instruction file POINTS at it, never duplicates the repo list.

Parent `CLAUDE.md` / `AGENTS.md` (LEAN - workspace map + workflow, not a repo catalogue):

```markdown
# <constellation> home base

Workspace-of-repos. Siblings are plain gitignored checkouts here (NOT submodules).

## Repos
See `repos.yaml` (single source of truth - one-line purpose per repo).

## Cross-repo change workflow
Contract-first ordering: schema → provider → consumers. One repo per worker, linked PRs,
merge libraries-before-consumers, contract tests at the boundaries.

## Rules
- Git-directory safety: only run git in the intended repo dir.
- Docs update is Definition-of-Done for any cross-repo change.
- Codex ignores an AGENTS.md above the git root (openai/codex#15683) - each per-repo file must
 link BACK here explicitly; Claude Code `--add-dir` solves access, not knowledge.
```

`repos.yaml` (the headline artifact):

```yaml
# One line per repo - purpose only. This file is the single source of truth.
repos:
 acme-api: { path: ./acme-api, purpose: "REST API + auth" }
 acme-web: { path: ./acme-web, purpose: "customer web app" }
 acme-jobs: { path: ./acme-jobs, purpose: "background workers" }
```

Run-everything scripts (`clone-all` / `status-all` / `test-all` - plain scripts, or mani/gita/vcstool;
mise `monorepo_root` for the task namespace), a constellation `docker-compose.yml`, a ports+env
bootstrap map, and a `_plans/` dir for cross-repo plans complete the kit. **Scale ladder:** manifest +
home base at 2-30 repos; a dependency/release-ordering registry at 20+; TRUE monorepo consolidation
only when >~30-50% of features touch multiple repos and no isolation constraint exists.

### Bootstrap plan (consent: EXPLICIT - greenfield structural)

Greenfield gets an ordered PLAN, not scaffolded stubs (playbooks.md greenfield block). Under
`--fix-all`, greenfield remediation applies ONLY to exercised hygiene files (`.gitignore`, lockfile,
`.env.example`, `.editorconfig`) - never the structural items below. Emit the plan as a checklist;
each item names the exact file and why it comes now. **No big-bang scaffolding; NEVER a
bulk-generated instruction file; every scaffolded artifact is exercised in the same pass.**

```markdown
# Bootstrap plan (greenfield)

1. [ ] Agent instruction file SEED - hand-fill skeleton (above), commands-first, short. NOT generated.
2. [ ] `STRATEGY.md` - target problem, approach, who it is for (`/flow-next:strategy`).
3. [ ] Stack decision recorded - runtime + package manager pinned; version file + lockfile committed.
4. [ ] Hygiene files - `.gitignore`, lockfile, `.env.example`, `.editorconfig`. NEVER a LICENSE.
5. [ ] Verify loop BEFORE feature 1 - one test command + one smoke command, in the agent file.
6. [ ] Smallest real CI - install + lint + test, gated on pull_request / default-branch push (FH3).
7. [ ] Secrets deny-rules baseline (above) - the one harness artifact safe to scaffold on an empty repo.
8. [ ] First spec = first vertical slice with explicit non-goals (`/flow-next:plan`).
9. [ ] Recorded-deferral N/A lines for premature pillars (observability, security scan, container,
 E2E) - each naming the trigger that un-defers it. A documented deferral beats a stub.
```

---

## Application Rules

1. **Detect before creating** - Check if file exists first
2. **Preserve existing content** - Merge with existing configs when possible
3. **Match project style** - Use detected indent (tabs/spaces), quote style
4. **Don't add unused features** - Only add what the project needs
5. **Explain changes** - Tell user what was created and why
6. **Respect user choices** - Never force changes without consent
