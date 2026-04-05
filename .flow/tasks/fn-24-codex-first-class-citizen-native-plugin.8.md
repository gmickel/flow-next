Update all documentation for Codex native support. This is a **minor** version bump (0.26.1 → 0.27.0).

## plugins/flow-next/README.md (primary changes)

This is the main user-facing README (1606 lines). Several sections need updates:

### 1. Header badges — add Codex badge
After the "Claude Code" badge, add an "OpenAI Codex" badge.

### 2. Quick Start section (~line 129) — add Codex install path
Currently only shows Claude Code install. Add Codex native + script install options:

```markdown
### Claude Code / Factory Droid

\`\`\`bash
/plugin marketplace add https://github.com/gmickel/gmickel-claude-marketplace
/plugin install flow-next
\`\`\`

### OpenAI Codex (Native Plugin)

Clone this repo and open Codex — the plugin appears in `/plugins`:

\`\`\`bash
git clone https://github.com/gmickel/gmickel-claude-marketplace.git
cd gmickel-claude-marketplace
codex  # → /plugins → install Flow-Next
\`\`\`

Then run `$flow-next-setup` in your project.

### OpenAI Codex (Global Install)

\`\`\`bash
git clone --depth 1 https://github.com/gmickel/gmickel-claude-marketplace.git /tmp/flow-next-install \
  && /tmp/flow-next-install/scripts/install-codex.sh flow-next
\`\`\`
```

### 3. "OpenAI Codex" section (~line 1496-1577) — full rewrite

Replace the entire section. Key changes:
- **Native plugin support** is now the primary install method
- **Simplified install-codex.sh** as alternative (no more "runtime conversion" language)
- **Updated model mapping**: gpt-5.4 + gpt-5.4-mini (not gpt-5.3-codex-spark)
- **flowctl path**: `~/.codex/scripts/flowctl` (not bin/)
- **Hooks**: Codex now supports hooks (experimental) — Ralph guard works for Bash tool
- **awesome-codex-plugins**: mention discoverability
- **Subagent features**: sandbox_mode, nickname_candidates

Updated section should cover:
- Native plugin install (clone → /plugins → install)
- Global install (install-codex.sh)
- Command differences ($flow-next-plan vs /flow-next:plan)
- Model mapping table (3-tier with gpt-5.4-mini)
- What works / what's limited (hooks only intercept Bash, no Ralph Edit/Write guard)
- Setup in projects ($flow-next-setup copies agents/hooks/flowctl)

### 4. Cross-Model Reviews section — update Codex references
Line ~843: "Codex (Cross-Platform Alternative)" section — update to mention native plugin, not just CLI tool.

### 5. Requirements section (~line 1457) — update Codex line
Currently says "OpenAI Codex CLI" — update to mention native plugin + CLI options.

## README.md (repo root)

### Update Codex CLI Installation section
Currently references old install path and models. Update to:
- Mention native plugin support as primary
- Update model mapping table
- Update flowctl path
- Add one-liner install

## CLAUDE.md (repo root project instructions)

### Update "Codex CLI Installation" section
- Add `.codex-plugin/plugin.json` to structure description
- Add `.agents/plugins/marketplace.json` to structure description
- Add `codex/` directory under plugins/flow-next/
- Update model mapping
- Update flowctl path (scripts/ not bin/)

### Update "Versioning" section
- Add `.codex-plugin/plugin.json` to list of files bumped
- Mention sync-codex.sh runs after bump

### Update "Release checklist (flow-next)"
- Add: verify sync-codex.sh was run
- Add: verify .codex-plugin/plugin.json version matches

### Update "Structure" section
- Add codex/ directory description

## CHANGELOG.md

Add entry:

```markdown
## [flow-next 0.27.0] - 2026-04-XX

### Added
- Native Codex plugin support (`.codex-plugin/plugin.json`) — closes #99
- Codex marketplace discovery (`.agents/plugins/marketplace.json`)
- Pre-built Codex agents as .toml files with subagent optimizations (sandbox_mode, nickname_candidates)
- Pre-built Codex skills with platform-specific invocation patterns
- Codex-compatible hooks for Ralph mode (Bash tool guard + Stop)
- `agents/openai.yaml` UI metadata for Codex app display
- `scripts/sync-codex.sh` for dev-time codex/ generation from canonical sources
- SessionStart hook for Codex (flow context loading)

### Changed
- `install-codex.sh` simplified: uses pre-built codex/ files instead of runtime conversion
- Model mapping updated: gpt-5.4-mini replaces gpt-5.3-codex-spark for scanning scouts
- flowctl installed to `~/.codex/scripts/` (was `~/.codex/bin/`) for path consistency
- `bump.sh` updates both `.claude-plugin/` and `.codex-plugin/` manifests
- Setup skill detects Codex and configures project-scoped agents/hooks
- Plugin README updated with native Codex install instructions
```

## Done summary
Updated all documentation for Codex native plugin support (0.27.0):

1. **CHANGELOG.md** — Added [flow-next 0.27.0] entry with 8 Added items + 6 Changed items
2. **plugins/flow-next/README.md** — Added Codex badge, Codex install paths in Quick Start, full rewrite of OpenAI Codex section (native plugin primary, install-codex.sh secondary, $-prefix commands, gpt-5.4-mini model mapping, hooks experimental, setup skill)
3. **README.md (root)** — Updated Codex tip box (native plugin primary, $ prefix), fixed anchor link
4. **CLAUDE.md** — Updated Structure (codex-plugin, agents marketplace, codex/ dir), Versioning (codex-plugin in bump, sync-codex.sh), Release checklist (sync-codex + verify steps), Codex Installation (complete rewrite with native plugin + global install)
## Evidence
- Commits:
- Tests:
- PRs:
## Acceptance criteria
- [ ] plugins/flow-next/README.md has Codex badge
- [ ] plugins/flow-next/README.md Quick Start shows both CC and Codex install
- [ ] plugins/flow-next/README.md "OpenAI Codex" section fully rewritten
- [ ] plugins/flow-next/README.md model mapping table updated throughout
- [ ] README.md (root) Codex section updated
- [ ] CLAUDE.md structure/versioning/release sections updated
- [ ] CHANGELOG.md has 0.27.0 entry
- [ ] No broken markdown links
- [ ] Existing CC/Droid documentation unchanged
- [ ] Version references show 0.27.0 (after bump)
