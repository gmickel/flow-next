# Adding a new user-facing skill (checklist)

When adding a new `/flow-next:<name>` skill, every step below MUST be done. Skipping any creates silent Codex degradation that won't surface for releases.

1. **Canonical skill** at `plugins/flow-next/skills/flow-next-<name>/SKILL.md` (+ `workflow.md` / `phases.md` as needed). Frontmatter: `name`, `description`, `user-invocable: false` (default for slash-only skills), `allowed-tools`.

2. **Slash command** at `plugins/flow-next/commands/<name>.md` (flat directory - never a `commands/flow-next/` subdir). Frontmatter carries a **bare, colon-free `name: <name>`** (e.g. `name: qa`, NOT `name: flow-next:qa`) plus a non-empty `description`: Claude Code prepends the plugin prefix to the last segment, so a bare name renders `/flow-next:<name>` while a colon re-triples it; Cursor's marketplace review checklist (fn-123 R11) requires both `name` and `description` on every command. Mirror the existing `audit.md` / `prospect.md` shape.

3. **Tool names in canonical = Claude-native** — write `AskUserQuestion`, `Task`, etc. directly. NO inline cross-platform tables. If you reference these tools, optionally add a parenthetical "(`sync-codex.sh` transforms `AskUserQuestion` into a plain-text numbered-prompt instruction for Codex)" for maintainer clarity — sync strips it from the Codex mirror. The Codex mirror never calls `request_user_input` (Plan-mode-only per openai/codex#10384/#11536/#12694).

4. **`scripts/sync-codex.sh` `generate_openai_yaml` call** added in the appropriate section (workflow blue `#3B82F6`, review red `#EF4444`, utility amber `#F59E0B`). Include display name, short description, brand color, explicit `false` for `allow_implicit_invocation`, optional default prompt.

5. **`scripts/sync-codex.sh` `REQUIRED_OPENAI_YAML_SKILLS` array** updated to include the new skill name. Validation will fail otherwise.

6. **Run `./scripts/sync-codex.sh`** — verify zero errors, all REQUIRED skills have `agents/openai.yaml`, and the Codex mirror has the rewritten tool names. Commit the regenerated `plugins/flow-next/codex/` directory.

7. **Commands list** updated in (experimental skills skip this step - see the experimental tier below):
   - `CLAUDE.md` (where the `<!-- BEGIN FLOW-NEXT -->` template block lives, OR the project guide's command count)
   - Root `README.md` — the "Commands" table is the canonical user-facing surface (plugin `plugins/flow-next/README.md` is now a thin stub pointing at the root)
   - `~/work/mickel.tech/app/apps/flow-next/page.tsx` (commands array + lede count + FAQ if applicable) — **maintainer-only; external contributors skip per the contributing guide**

8. **CHANGELOG entry** under the appropriate `[flow-next X.Y.Z]` block describing what the skill does.

9. **Smoke test** if the skill has any flowctl plumbing (atomic file writes, schema additions). Pure-skill additions (markdown-only) get verified by manual invocation in a real session.

10. **Conduct checklist** at [`agent_docs/conduct/<skill>.md`](conduct/README.md) plus an index row in `conduct/README.md`: 4–6 falsifiable observable behaviors of a session running the skill correctly, each checkable from a transcript in seconds. This is the review rubric for future prose changes to the skill — a skill without one has no prose regression harness. It is a rubric, not merge ceremony: no dogfood run or pass/fail record is required to hand off an edit. Never reference it from the skill's own files; it carries zero runtime context. **State each assertion per emission variant, not per phase** — a skill with multiple output branches (base/rewrite/split footers, per-spec blocks) needs the count scoped to the variant ("one line per emitted footer block"), because a row a CORRECT run can fail is a bug in the row (PR #363: an "exactly one line" row failed every correct split run).

11. **Guide's routing surface** (`plugins/flow-next/skills/flow-next-guide/SKILL.md`) updated in the **same change** whenever a skill is added or removed, so the router never names a skill that is gone and never omits a starting state a shipped skill now owns. Removal is this checklist run backwards - delete the skill dir (canonical + `codex/` mirror), the command shim, the `sync-codex.sh` entry and `REQUIRED_OPENAI_YAML_SKILLS` row, the conduct checklist and its index row, the listing/count surfaces from step 7, and the guide row - in one commit.

12. **OpenCode: usually nothing — but know the two seams.** `scripts/install-opencode.sh` blanket-scatters canonical skills (setup included) and copies `scripts/` (flowctl + lib) to the config root, so a new SKILL adds itself on the next install and the flowctl preamble's derived-root rung resolves unchanged. The generated glue is the seam: `plugins/flow-next/scripts/lib/opencode_generate.py` builds OpenCode agents/commands from frontmatter through a **closed allowlist** — a new AGENT, or a new frontmatter key on any agent, raises `GenerateError` at install (fail-closed, loud). When adding an agent or agent frontmatter, extend the generator's mapping in the same change and run the installer once against a scratch `--dest` to prove it generates.

13. **Installer ownership invariant (any host).** An installer may create, overwrite, or delete files ONLY inside a directory it owns outright (e.g. `$CODEX_HOME/docs/flow-next/`, never loose files in `$CODEX_HOME/docs/`). A shared parent directory is never `rm -rf`'d and never receives loose generic names (`README.md`, `architecture.md`) that could clobber another package's or the user's files. Enforced by sentinel regression test (`test_install_never_touches_non_owned_docs` — pre-existing non-owned files must survive an install byte-identical); a new install surface adds the same sentinel shape. Learned the hard way: PR #363's first docs-install attempt recursively deleted a user-owned `$CODEX_HOME/docs/reach` (codex P1, reproduced with a sentinel).

## Experimental skills (tier)

A skill may ship **before** it has earned the full checklist above. An experimental skill lives in the plugin and is invocable, but it is deliberately absent from every surface that promises stability:

- **Excluded from** the root `README.md` commands/skills tables, `plugins/flow-next/docs/skills.md`, the docs catalog, and any published skill/command count (step 7 is skipped entirely, including the marketing site). **Registry manifests are inventory, not published counts**: the count strings in `.claude-plugin/marketplace.json` and the two `plugin.json` files enumerate every shipped dir, experimental included, and DO get bumped — the `ChartRegistryCounts` carve-out in `test_chart_docs_inventory.py` (commit 5b9e039f) pins exactly this split (bump filesystem/registry assertions; leave the published README/docs phrases at the stable total).
- **Marked in its own frontmatter** - the SKILL.md `description` ends with ` (experimental - can change or disappear)`, so anything routing on descriptions sees the tier without a registry lookup.
- **Retired by deletion.** There is no deprecation window, no alias, no tombstone doc. The skill dir and its shim go; the CHANGELOG line says it was experimental and is gone.
- **Graduates by doing the full checklist** - steps 7, 8, and 10 in particular are what an experimental skill is allowed to defer, and graduation is exactly the change that pays them off.

**Heuristic - use the tier when the shape is still in question, not to dodge paperwork.** If you already know the skill's contract and expect it to survive the next release, ship it normally; the tier buys iteration room, and its only real cost is that nobody is told the skill exists.

**Failure signature.** A skill carrying the experimental suffix that also appears in a README table or a published count is not experimental - it is an undocumented promise. Either finish the checklist or take it out of the tables.

Currently in this tier: none (`flow-next-work-rolling` graduated into `/flow-next:work` as its default scheduler, fn-218). Existing stable skills are not demoted into the tier.

## Backend-split workflow.md (heuristic)

When a skill's `workflow.md` carries backend-specific content (RP / Codex / Copilot, or parallel-vs-serial dispatch), split it so only the active backend's content enters the agent's context per invocation.

**Heuristic — split when divergent content ≥ 50 lines.** Smaller divergences stay inline; extracting them costs more in maintenance (extra files, sync-codex rewrites, link drift) than they save in context.

**Backend-selected shape** (when split is warranted; include only supported backends):

```
skills/flow-next-<name>/
  SKILL.md            # routing table: BACKEND → workflow-<backend>.md
  workflow-common.md  # backend-detection + shared phases (gated deep/validator/walkthrough if applicable)
  workflow-rp.md      # RepoPrompt-only
  workflow-codex.md   # Codex CLI-only
  workflow-copilot.md # GitHub Copilot CLI-only
```

SKILL.md routing block (canonical pattern in `flow-next-impl-review/SKILL.md`): `BACKEND=codex` → `workflow-codex.md`, etc., with explicit "Do not load the other two."

**Landed examples** (fn-48):
- `flow-next-spec-completion-review` (commit `b2f6f0e`) — workflow.md 645 → 4 files; RP-prompt template (~430 lines) isolated to `workflow-rp.md`.
- `flow-next-impl-review` (commit `06f6e6f`) — workflow.md 1126 → 4 files; `workflow-common.md` 565 LOC (historical measurement, not a size limit). Auxiliary `deep-passes.md` / `walkthrough.md` untouched (already cross-backend).
- `flow-next-resolve-pr` — **inline-kept**: divergence is one ~22-line Phase 5 (parallel-vs-serial dispatch); below threshold.

**sync-codex.sh impact:** the RP-warning injector (grep `rp_warning` / the workflow-rp preference block in sync-codex.sh - line numbers rot, names don't) auto-prefers `workflow-rp.md` when present, falling back to monolithic `workflow.md`. No sync edits needed unless new tool-name references are introduced (see memory entry `bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18`).

## Gated references/*.md — progressive disclosure (heuristic)

When a skill's always-loaded file (`SKILL.md` / `workflow.md` / `phases.md`) inlines **default-OFF machinery** — a code path that runs only when an opt-in feature is active — that text is dead weight on every default-path invocation. Move it into a `references/*.md` file that the agent reads **only when a forcing-sentinel gate tells it to**. Referenced files under a skill dir cost **zero tokens until Read** (Anthropic Agent Skills 3-level loading) and auto-mirror to Codex (`sync-codex.sh` wholesale skill-dir copy).

**Heuristic — gate when the path is genuinely default-OFF or mutually-exclusive.** If the content is consumed on *every* run (an always-checked checklist), do NOT gate — the probe cost + skip risk outweigh the load saving; **fold** it inline toward the richer copy instead (make-pr's `phases.md` fold, fn-82.4). Gating pays only when the default path skips the content entirely.

**Canonical gate skeleton** (binding — fail OPEN, no unguarded pipeline):

```bash
ACTIVE=0
# NO pipelines in the probe — a failed producer masked by a healthy consumer
# (flowctl … | jq …) fails CLOSED. Capture raw first, rc-checked; parse separately.
RAW="$(<probe-cmd> --json 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '<path>' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "<active-condition on $VAL>" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — STOP. Read references/<file>.md#<section> before continuing."
fi   # default branch: bare no-op — NO link, NO read path
```

The always-loaded prose immediately after the gate repeats the imperative ("When the sentinel prints, STOP and Read the named reference before any further step") and links the reference **one level deep** — a `[references/<file>.md](references/<file>.md)` markdown link in the gating file itself (nested refs trigger partial reads). Any safety net that must run on EVERY invocation (an end-of-run reconcile, a mandatory summary slot) stays **inline** — never behind the gate. A reference file >100 lines opens with a short table of contents.

**Grep-gate contract** (a final-task check should verify, per gate): the sentinel text is present, `|| ACTIVE=1` appears on BOTH the probe and the parse, no unguarded `| jq` pipeline sits inside any gate block, the reference is linked one level deep, and the default branch contains no Read of the reference.

**Landed examples** (fn-82):
- `flow-next-work` (fn-82.1) — three tracker touchpoints (first-claim / done / completion-review) → `references/tracker-touchpoints.md` behind the `flowctl sync active` bridge predicate; Phase-5 sync-check + four-state summary kept inline. **−984 tok** default path.
- `flow-next-pilot` (fn-82.1) — QA-stage freshness probe → `references/qa-stage.md` behind `pipeline.qa == on`; Phase 5/6 qa routing kept inline. **−2207 tok** default path.
- `flow-next-make-pr` (fn-82.4) — **inline-fold, NOT gated**: the per-phase Done-when checklists run every render, so folded into `workflow.md` + `phases.md` reduced to a stub and un-force-loaded (eval held 5/5).

## FLOWCTL prelude consolidation (heuristic)

When a skill invokes `flowctl` from bash, define the variable **once per canonical file** in a `## Preamble` section near the top; subsequent bash blocks call `$FLOWCTL` bare.

**Canonical preamble pattern:**

```markdown
## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail on every host except Claude Code with the plugin enabled (which injects the plugin's `bin/` onto PATH) — skill preambles must NEVER rely on that; the three-rung `$FLOWCTL` resolution below is the cross-host contract and stays mandatory in every skill. Define once; subsequent blocks (here and in `<workflow.md>` / `<phases.md>`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**The three rungs, and why each is there (fn-197).** Rung 1 is mechanical and always right on Claude Code and Droid. Rung 2 carries Cursor and Grok: neither sets a plugin-root env var, but both inject the loaded skill file's absolute on-disk path, and the plugin root is two levels above it — the wording above is probe-proven, so copy it **byte-identically** into every new preamble rather than paraphrasing. Rung 3 is a silent backstop for a repo that still has a `/flow-next:setup` copy at `.flow/bin/flowctl`; copies are dead weight and nothing is designed around them, so never document, test, or reason from that rung.
```

**Heuristic — one preamble per top-level skill file.** SKILL.md, workflow.md / workflow-common.md / phases.md / steps.md each get their own preamble at the top. Internal bash blocks within the file use `$FLOWCTL` without redefining it. Worker / scout / dispatched-subagent prompts that run in fresh context (e.g. `agents/worker.md`, plan-sync invocation template in `flow-next-sync/SKILL.md`) need their own prelude — they're separate execution contexts.

**Why the env-var fallback stays.** `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` is **not** dead code. Per `.flow/memory/knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25.md` (fn-48.2 web-verified against Factory docs on 2026-05-25), Droid still uses `DROID_PLUGIN_ROOT` as its canonical plugin-root env var; `CLAUDE_PLUGIN_ROOT` is documented as the Claude Code compat alias. Both resolve on Droid via the interop layer.

**What's NOT in the prelude.**
- `.factory-plugin/plugin.json` fallback — dropped per fn-48.2; Droid auto-translates Claude Code plugin format via its interop layer for Claude-first plugins like flow-next. The sync-codex.sh rewrite (grep `factory-plugin` in the script) `'s|\.factory-plugin/plugin\.json|.claude-plugin/plugin.json|g'` remains as defense-in-depth but is now effectively a no-op.
- Platform detection (`if [ -n "${DROID_PLUGIN_ROOT:-}" ]`) — that's a distinct concern from the FLOWCTL prelude; lives in `flow-next-setup/workflow.md` as-is.

**Landed examples** (fn-48):
- `flow-next-resolve-pr` (fn-48.5, gold standard) — SKILL.md preamble (`FLOWCTL` + `SCRIPTS`) at lines 18-19; workflow.md preamble at lines 9-10; all subsequent blocks call `$FLOWCTL` / `$SCRIPTS` bare.
- `flow-next-deps` (fn-48.6) — collapsed 5 inline `FLOWCTL=...` blocks to one preamble.
- `flow-next-ralph-init` (fn-48.6) — uses `PLUGIN_ROOT="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}"` to collapse 10+ inline expansions in the cp commands.

**sync-codex.sh impact:** only rung 1 is rewritten for the mirror (grep `\.codex/scripts/flowctl` in sync-codex.sh) — it becomes `${CODEX_HOME:-$HOME/.codex}/scripts/flowctl`, and rungs 2 and 3 flow through untouched. fn-197 deleted the two fallback-injector awks that used to append the `.flow/bin` rung: the canonical text now carries every rung itself, and the injectors keyed on exact next-line equality with that rung, so they would duplicate it. A validation guard in the same script (grep `Three-rung FLOWCTL chain`) asserts the mirrored chain instead — so a new preamble that omits a rung fails the sync, not a user's host.

## Remedy sentences name the verb that performs them (heuristic)

Any sentence that tells a reader how to get unstuck — a recovery, a repair, an unblock, a "if this happens, do X" — names the command that does it, in that sentence. Prose that describes the shape of a remedy without its invocation is the same defect class as a stale router: it reads confident and sends the reader nowhere, and nothing detects it, because docs have no runtime.

Two measured incidents:

- **A recovery that could not exist.** `tracker-sync.md` and the site told operators that an explicit re-ready clears a pilot strike; since fn-87 a projection-set ready deliberately never clears one, and a deliberate board move is byte-identical to a projection echo in every durable artifact. The remedy sentence named a gesture, not a verb — so it survived unfalsified until a consumer measured it (fn-184, #325). The fix that stuck was naming `flowctl pilot strikes clear <spec-id>`.
- **A router that lies.** The same class one surface over: `/flow-next:guide`'s inventory recommending a skill that no longer ships (see the router-staleness rule in that skill).

**Failure signature.** A remedy paragraph with no command in it — or one whose command is described ("clear the strike", "re-run the gate", "hand-edit the ledger") rather than written. If the invocation does not exist yet, that is the finding: either build the verb or say plainly that no recovery exists and what to do instead.

## Prose-contract tests: behavior and reachability

Follow [standing criterion G2](../.flow/criteria.md). Tests exercise observable
behavior or the smallest distinctive contract token: verdict grammar, field
names, headings, inventories, executed fences, and required parity relations.
Do not assert prose sentences, paragraph order, live-file sizes, or frozen
hashes of skill prose. Deliberate prompt-change detection belongs only in
`test_prompt_text_pinned.py`.

When moving guidance into a reference, verify that the entry point reaches the
reference on the correct branch. Preserve tests of executable ordering and
canonical/mirror parity where those are the actual contract. A link check proves
reachability; it does not prove that a model will apply relocated text equally
well. The failed capture trim in [the optimization record](optimizing-skills.md)
shows that drafting-adjacent taxonomy can matter despite an intact link.

For a behavior-changing prompt edit, use the affected conduct checklist and
appropriate evaluations. Do not replace that evidence with sentence pins or
relax a behavioral gate merely to make a change pass. Existing sentence-level
tests are historical debt, not a template for new tests; migrating the shipped
prompt tests is a separate change.

## Reference

This checklist captures the lessons from the 0.34.0 → 0.37.0 era when (a) 4 user-facing skills (resolve-pr, prospect, audit, memory-migrate) silently shipped to Codex without UI metadata, and (b) several skills shipped with inline cross-platform tables (`AskUserQuestion` / `request_user_input` / `ask_user`) that polluted the agent's context. Both fixed in 0.37.1. Don't repeat them.

## Cross-platform patterns

Read this checklist when changing skills, agents, commands, hooks, platform
transforms, or installation. It is shared development guidance; canonical
Claude tool names below describe the product source, not the current host.


**Supported host roster (check affected consumers when building features):**

| Host | Mechanism | Consumes |
|---|---|---|
| Claude Code | canonical plugin (`.claude-plugin/`) | canonical files as-is |
| Codex | pre-built mirror at `plugins/flow-next/codex/`, regenerated by `scripts/sync-codex.sh` | REWRITTEN copies (tool names, ask fallback, dispatch phrases) |
| Factory Droid | auto-translates the Claude plugin format on install | canonical files as-is (`DROID_PLUGIN_ROOT` alias) |
| Cursor | RECOMMENDED: team-marketplace repo import (root `.cursor-plugin/marketplace.json`); fallback: `scripts/install-cursor.sh` / `.ps1` (blanket rsync to `~/.cursor/plugins/local/`, excludes codex/ + tests/); manifest at `plugins/flow-next/.cursor-plugin/plugin.json` | canonical files AS-IS - no rewrite pass exists |
| Grok Build | reads the Claude plugin format directly (compat, verified) | canonical files as-is |
| OpenCode | installer scatter (`scripts/install-opencode.sh` -> `~/.config/opencode/`; skills as-is, support dirs `scripts/`+`templates/`+`references/`+`docs/` at the config root — plugin-root geometry, so relative docs links resolve; generated agents/commands; setup detects via the ownership manifest) | canonical files + support dirs + generated glue |

**Architectural rule:** canonical skill files use Claude-native tool names; `sync-codex.sh` rewrites them in the Codex mirror. Skill prose stays concrete; cross-platform maintenance lives in one place — the sync script. Cursor/Droid/Grok get NO rewrite pass, so anything Claude-specific in canonical prose must either work there or carry an explicit portable-host clause.

**Checklist when adding/editing skills, agents, or hooks (walk ALL of it):**

1. Run `./scripts/sync-codex.sh` TWICE (idempotency) and commit the mirror diff with the canonical change. Its validation guards must stay green; new Claude-only phrases (tool dispatches, model-name examples) may need a new transform + hard-fail guard (pattern: the fn-100 Explore-dispatch and scout-tier rules).
2. Claude BUILTIN references (`Explore`, `general-purpose`, `AskUserQuestion`, model names) are invisible to the Cursor/Droid/OpenCode consumers (all three read canonical prose as-is) - every such reference needs a portable-host fallback clause in the canonical prose (generic read-only dispatch with Edit/Write disallowed; plain-text numbered-prompt fallback for asks) or graceful degradation stated inline.
3. Plugin-root env vars: Cursor and Grok expose NONE - every bash preamble carries the three rungs in order: `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl`, then the plugin root derived from the skill's own SKILL.md absolute path (two levels up), then the legacy `.flow/bin/flowctl` backstop. Setup copies nothing into a repo; on Claude Code bare `flowctl` also resolves via bin-PATH injection in plain Bash ONLY - never in skill prose.
4. No plugin-level hooks (`plugins/flow-next/hooks/` is gone): Ralph registration is agent-driven via `/flow-next:ralph-init` (merge fingerprinted entries into project settings per host). Guard matchers stay Claude-schema (`PreToolUse`/`Stop`, `Bash|Execute` shell + file-tool set); works on Claude Code + Droid, NOT Cursor (different hook events) - never assume the guard fires there.
5. Installers need no enumeration updates for SKILLS (Cursor installers blanket-copy; the codex mirror is a full regen; the OpenCode installer blanket-scatters) - with two exceptions: (a) the codex mirror's `phases.md` 3c is a HARDCODED heredoc in `sync-codex.sh` (`SECTION3C`), so canonical 3c edits must land in the heredoc too or the mirror can drift unless its dispatch-field guards cover the change; (b) a new AGENT (or new agent-frontmatter key) must extend the closed allowlist in `plugins/flow-next/scripts/lib/opencode_generate.py` — it fails loudly (`GenerateError`) at OpenCode install otherwise. `plugins/flow-next/docs/platforms.md` DOES need a note when host behavior differs.
   **Validate at the CONSUMER's layout, not the producer's** (PR #363 lesson: three review rounds came from checking only the repo tree while the real consumer is the installed `$CODEX_HOME` — shallower, partial, different invocation syntax). `sync-codex.sh` now carries hard-fail guards for the whole class: mirror docs-link resolution, the installed-docs link-universe closure (resolve on disk or absolute URL), and actionable-invocation rewrites (`/flow-next:` → `$flow-next-`). A canonical edit that adds a docs link or a user-copyable command is covered by those guards — **a guard failure is load-bearing; fix the content or extend the transform, never relax the guard.**
6. `agents/*.md` model fields are family aliases resolved by the host; on non-Claude hosts they map to host defaults - never version-pin, and never assume a specific tier is honored off Claude Code.

- **Variable references** — bash fallback: `FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"`. Droid sets `DROID_PLUGIN_ROOT` and also exposes `CLAUDE_PLUGIN_ROOT` as an alias (per Factory docs, "Alias for `${DROID_PLUGIN_ROOT}` (Claude Code compatibility)"). The fallback order is conservative but correct on both platforms. *(Last verified against Factory docs 2026-05-25 — fn-48.2.)*
- **Hook matchers** — regex OR: `"matcher": "Bash|Execute"` (Claude `Bash`, Droid `Execute` — Factory hooks-reference 2026-05-25 still lists `Execute` as canonical and `Bash` as not recognized).
- **Agent permissions** — `disallowedTools` blacklist (not `tools` whitelist). Tool names differ across platforms; blacklist works because both understand `Edit`, `Write`, `Task`. Read-only agents deny all three (shell writes also need the host sandbox and explicit read-only contract) — `Task` because a spawned writing subagent is an escape hatch out of read-only; writing agents deny only the subset they must not use (plan-sync: `Write, Bash`; worker and pr-comment-resolver: none). `Task` is subagent dispatch (renamed Agent in Claude Code v2.1.63), not a planning tool.
- **Plugin paths** — flow-next is a Claude-first plugin; use `${PLUGIN_ROOT}/.claude-plugin/plugin.json` directly. Droid auto-translates Claude Code plugin format on install (Factory docs: "Droid is compatible with plugins built for Claude Code… the plugin format is interoperable"), so a `.factory-plugin/plugin.json` fallback is **not** needed for Claude-first plugins like flow-next. Native Droid-first plugins (e.g. Factory-AI/factory-plugins marketplace) ship `.factory-plugin/plugin.json`; we don't.
- **Blocking-question tool** — every interactive skill MUST use the platform's blocking primitive. Canonical writes `AskUserQuestion`; `sync-codex.sh` transforms canonical invocations into a plain-text numbered-prompt instruction (with `N+1. Other — type your own answer` as the final option) for the Codex mirror — the mirror never mentions `request_user_input` (Plan-mode-only per openai/codex#10384/#11536/#12694; closed without resolution as of Feb 2026). Droid (currently) sees the canonical name. Always bare `AskUserQuestion` in canonical files; an optional parenthetical breadcrumb noting the rewrite is fine.
- **Subagent dispatch** — canonical writes `Task` with `subagent_type: Explore`; sync rewrites to `spawn_agent`. Those tool restrictions do not fence shell writes. Preserve the host sandbox and read-only shell contract as well.
