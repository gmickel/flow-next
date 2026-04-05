# Codex First-Class Citizen: Native Plugin, Dual Skills, Pre-Built Agents

## Goal & Context

Make flow-next a first-class Codex plugin alongside its existing Claude Code and Factory Droid support — without breaking anything for existing users. Currently Codex support requires users to clone the repo and run `install-codex.sh`, which does heavy runtime conversion (MD→TOML agents, skill path patching, Task→agent invocation rewrites). Codex now has a native plugin system with `.codex-plugin/plugin.json` manifests, marketplace discovery, custom subagents (.toml), and hooks.

**Why now:** Issue #99 requests `.codex-plugin/plugin.json` for discoverability via awesome-codex-plugins (a community marketplace that mirrors plugins). Codex shipped native plugin support, subagents, skills (identical SKILL.md format to Claude Code), and hooks. We can eliminate most runtime conversion by pre-generating Codex-specific files at dev time.

**Success criteria:**
- flow-next is discoverable by codex-plugin-scanner and eligible for awesome-codex-plugins listing
- Codex users can install via native plugin system (clone repo → `codex /plugins` → install)
- Codex users can install globally via simplified `install-codex.sh`
- All 16 skills work on Codex with correct invocation patterns (agent roles, not Task tool)
- All 20 agents available as pre-built .toml files with Codex subagent optimizations
- Ralph hooks work on Codex (within platform limitations)
- Claude Code and Factory Droid users see zero changes
- `bump.sh` keeps both platforms in sync

## Architecture & Design

### Dual-Manifest Plugin

Both platforms coexist in the same plugin directory via separate manifest directories:

```
plugins/flow-next/
├── .claude-plugin/plugin.json      # Claude Code manifest (existing)
├── .codex-plugin/plugin.json       # Codex manifest (NEW)
├── skills/                         # Claude Code / Droid skills (canonical source)
├── agents/                         # Claude Code agents (.md, canonical source)
├── commands/flow-next/             # Claude Code commands (unchanged)
├── hooks/hooks.json                # Claude Code hooks (unchanged)
├── codex/                          # NEW: Pre-built Codex-specific files
│   ├── skills/                     # Patched skills (Task→agent, path fixes)
│   ├── agents/                     # .toml agent configs
│   └── hooks.json                  # Codex-format hooks
├── scripts/                        # Shared (flowctl, etc.)
└── docs/
```

The Codex manifest's `"skills"` field points to `"./codex/skills/"` (pre-patched).
The Claude Code manifest implicitly uses `skills/` (unchanged).

### Dual Marketplaces at Repo Root

```
repo-root/
├── .claude-plugin/marketplace.json          # Claude Code (existing, unchanged)
├── .agents/plugins/marketplace.json         # Codex (NEW)
```

### Skill Patching Categories

Skills need platform-specific adaptations. These are applied at dev time by `sync-codex.sh`, NOT at user install time:

**1. PATH fixes** (all skills that reference flowctl):
- `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl` → `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl` with `.flow/bin/flowctl` fallback

**2. STRUCTURAL: Task tool → agent invocation** (flow-next-work, flow-next-plan, flow-next-prime):
- `Task flow-next:worker` → "Use the worker agent"
- `flow-next:context-scout` → `context_scout` agent (hyphens→underscores, namespace removed)
- `Task flow-next:X-scout` → "Use the X_scout agent"
- `spawn the plan-sync subagent` → "use the plan_sync agent"

**3. BEHAVIORAL: RP warnings** (flow-next-impl-review, flow-next-plan-review, flow-next-epic-review):
- Add "DO NOT RETRY" warnings for slow RepoPrompt commands
- These could also be added to Claude Code skills (harmless, potentially useful)

**4. NAMING: claude-md-scout → agents-md-scout** (Codex uses AGENTS.md, not CLAUDE.md):
- References in flow-next-prime workflow
- Agent file rename

### Agent Conversion (.md → .toml)

Pre-build all 20 agents as .toml files with Codex subagent optimizations:

**Model mapping (updated with gpt-5.4-mini):**

| Claude Code | Codex | Reasoning | Agents |
|-------------|-------|-----------|--------|
| opus | gpt-5.4 | high | quality-auditor, flow-gap-analyst, context-scout |
| sonnet (smart) | gpt-5.4 | high | epic-scout, agents-md-scout, docs-gap-scout |
| sonnet (fast) | gpt-5.4-mini | (omit) | build, env, testing, tooling, observability, security, workflow, memory scouts |
| inherit | inherited | inherited | worker, plan-sync |

**New Codex subagent features to apply:**
- `sandbox_mode = "read-only"` for all scouts and reviewers (they don't write)
- `nickname_candidates` for scouts (better UX when 9+ run in parallel)
- `sandbox_mode = "workspace-write"` for worker only

### Codex Hooks

Codex hooks differ from Claude Code:
- Only `Bash` tool supported for PreToolUse/PostToolUse (no Edit/Write yet)
- No `SubagentStop` event
- Has `SessionStart` and `UserPromptSubmit` (new opportunities)

Ralph guard hooks adapted: drop Edit/Write matchers, drop SubagentStop, keep Bash+Stop.
Add SessionStart hook for flow context loading.

### install-codex.sh Simplification

Before: 785 lines — copies skills, converts agents MD→TOML, patches paths, patches invocations, merges config.toml.
After: ~150 lines — copies pre-built `codex/` contents to `~/.codex/`, merges config.toml, copies flowctl.

Skills no longer need runtime patching (pre-built in `codex/skills/`).
Agents no longer need runtime conversion (pre-built in `codex/agents/`).

### flowctl Installation Path

`install-codex.sh` should install flowctl to `~/.codex/scripts/flowctl` (not `bin/`) so the path pattern `${ROOT}/scripts/flowctl` is consistent across platforms:
- Claude Code: `${CLAUDE_PLUGIN_ROOT}/scripts/flowctl` ✓
- Droid: `${DROID_PLUGIN_ROOT}/scripts/flowctl` ✓
- Codex: `$HOME/.codex/scripts/flowctl` ✓

### Skill UI Metadata (openai.yaml)

Add `agents/openai.yaml` to key skills for Codex app/IDE display:
- `display_name`, `short_description`, `brand_color`
- `allow_implicit_invocation: false` for workflow skills (plan, work) — explicit only
- `allow_implicit_invocation: true` for utility skills (browser, worktree-kit)

### bump.sh Updates

Must update both manifests when bumping:
- `.claude-plugin/marketplace.json` (existing)
- `plugins/flow-next/.claude-plugin/plugin.json` (existing)
- `plugins/flow-next/.codex-plugin/plugin.json` (NEW)
- `.agents/plugins/marketplace.json` version (NEW)

And trigger `sync-codex.sh` to regenerate `codex/` directory.

### Repo Rename (Optional, Separate)

Rename `gmickel-claude-marketplace` → `flow-next`. GitHub auto-redirects old URLs. Plugin name stays `flow-next` in both manifests. This is cosmetic and can be done independently.

## Edge Cases & Constraints

**Codex hook limitations:**
- PreToolUse/PostToolUse only intercept `Bash` tool — Ralph guard can't protect Edit/Write on Codex. Document this limitation. Monitor Codex releases for expanded hook support.

**No CODEX_PLUGIN_ROOT variable:**
- Codex doesn't set a plugin root env var like Claude Code does. Skills must use the fallback chain: `${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}/scripts/flowctl` then `.flow/bin/flowctl`.

**Codex plugin cache path:**
- Native plugin installs go to `~/.codex/plugins/cache/$MARKETPLACE/$PLUGIN/$VERSION/`. Skills in the plugin can reference `./scripts/` relative to plugin root, but we don't control the cache path. The fallback chain handles this.

**awesome-codex-plugins mirroring:**
- If they mirror our plugin, they'll copy the `plugins/flow-next/` directory including `codex/`. The `codex/skills/` will work standalone since paths are pre-patched.

**gpt-5.4-mini reasoning:**
- gpt-5.4-mini may or may not support `model_reasoning_effort`. The sync script should omit reasoning settings for mini models (same pattern as current Spark handling).

**Sync discipline:**
- When canonical skills/ or agents/ change, devs MUST run `scripts/sync-codex.sh` and commit the regenerated `codex/` directory. CI could enforce this (diff check).

**Plugin version sync:**
- Both `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` must have the same version. `bump.sh` enforces this.

## Acceptance Criteria

- [ ] `.codex-plugin/plugin.json` exists and passes codex-plugin-scanner validation
- [ ] `.agents/plugins/marketplace.json` exists and Codex discovers the plugin when opened in the repo
- [ ] `codex/skills/` contains all 16 skills with correct Codex invocation patterns
- [ ] `codex/agents/` contains all 20 agents as .toml files with correct model mapping
- [ ] `codex/hooks.json` contains Codex-compatible Ralph guard hooks
- [ ] `scripts/sync-codex.sh` regenerates `codex/` from canonical sources idempotently
- [ ] `install-codex.sh` simplified to copy pre-built files + config merge
- [ ] `bump.sh` updates both platform manifests and marketplace files
- [ ] All existing Claude Code / Droid functionality unchanged (skills, agents, hooks, commands)
- [ ] Key skills have `agents/openai.yaml` for Codex UI metadata
- [ ] Scout agents have `sandbox_mode = "read-only"` and `nickname_candidates`
- [ ] Model mapping uses gpt-5.4 (intelligent), gpt-5.4-mini (fast scouts), inherited (worker)
- [ ] README updated with Codex native install instructions
- [ ] Issue #99 can be closed

## Boundaries

**In scope:**
- Native Codex plugin support (manifests, marketplace, skills, agents, hooks)
- Pre-built Codex-specific files (codex/ directory)
- Build/sync tooling (sync-codex.sh)
- install-codex.sh simplification
- bump.sh dual-manifest support
- Codex subagent optimizations (sandbox_mode, nicknames, model mapping)
- Skill UI metadata (openai.yaml)
- Documentation updates

**Out of scope:**
- Repo rename (separate decision, can be done independently)
- OpenAI Plugin Directory submission (not available for third-party yet)
- awesome-codex-plugins PR (do after this epic, once we pass their scanner)
- Codex Edit/Write hook support (blocked on Codex platform)
- CSV batch processing for scouts (future optimization)
- New skills or commands (scope is platform parity, not new features)
- flow (legacy) plugin Codex support
- flowctl.py changes

## Decision Context

**Why dual skills directory instead of platform-adaptive skills?**
The structural differences (Task tool vs agent invocation, scout naming) can't be cleanly handled with conditionals in skill text. Models get confused by "if Platform A do X, if Platform B do Y" patterns. Separate pre-patched skills are cleaner, testable, and what install-codex.sh was already doing at runtime — we're just moving the patching to dev time.

**Why pre-build agents instead of runtime conversion?**
The MD→TOML bash conversion is fragile (YAML parsing in bash, backslash escaping, frontmatter extraction). Pre-built files can be validated, tested, and diffed. The sync script uses the same logic but runs once at dev time, not on every user install.

**Why keep install-codex.sh?**
Codex plugins can't bundle agents or hooks — those live outside the plugin system. install-codex.sh is the only way to set up global ~/.codex/ agents and hooks. It also handles config.toml merging. The native plugin is for discoverability and skills; install-codex.sh is for the full experience.

**Why gpt-5.4-mini instead of gpt-5.3-codex-spark?**
gpt-5.4-mini is newer, same family as gpt-5.4. For lightweight scanning scouts (build, env, testing, etc.), mini provides sufficient quality at lower cost. Spark is fast but may lack capability for some scouts. User preference.
