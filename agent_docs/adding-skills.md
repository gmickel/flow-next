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

10. **Conduct checklist** at [`agent_docs/conduct/<skill>.md`](conduct/README.md) plus an index row in `conduct/README.md`: 4–6 falsifiable observable behaviors of a session running the skill correctly, each checkable from a transcript in seconds. This is the review rubric for future prose changes to the skill and the dogfood pass/fail list after edits — a skill without one has no prose regression harness. Never reference it from the skill's own files; it carries zero runtime context. **State each assertion per emission variant, not per phase** — a skill with multiple output branches (base/rewrite/split footers, per-spec blocks) needs the count scoped to the variant ("one line per emitted footer block"), because a row a CORRECT run can fail is a bug in the row (PR #363: an "exactly one line" row failed every correct split run).

11. **Guide's routing surface** (`plugins/flow-next/skills/flow-next-guide/SKILL.md`) updated in the **same change** whenever a skill is added or removed, so the router never names a skill that is gone and never omits a starting state a shipped skill now owns. Removal is this checklist run backwards - delete the skill dir (canonical + `codex/` mirror), the command shim, the `sync-codex.sh` entry and `REQUIRED_OPENAI_YAML_SKILLS` row, the conduct checklist and its index row, the listing/count surfaces from step 7, and the guide row - in one commit.

12. **OpenCode: usually nothing — but know the two seams.** `scripts/install-opencode.sh` blanket-scatters canonical skills (setup included) and copies `scripts/` (flowctl + lib) to the config root, so a new SKILL adds itself on the next install and the flowctl preamble's derived-root rung resolves unchanged. The generated glue is the seam: `plugins/flow-next/scripts/lib/opencode_generate.py` builds OpenCode agents/commands from frontmatter through a **closed allowlist** — a new AGENT, or a new frontmatter key on any agent, raises `GenerateError` at install (fail-closed, loud). When adding an agent or agent frontmatter, extend the generator's mapping in the same change and run the installer once against a scratch `--dest` to prove it generates.

13. **Installer ownership invariant (any host).** An installer may create, overwrite, or delete files ONLY inside a directory it owns outright (e.g. `$CODEX_HOME/docs/flow-next/`, never loose files in `$CODEX_HOME/docs/`). A shared parent directory is never `rm -rf`'d and never receives loose generic names (`README.md`, `architecture.md`) that could clobber another package's or the user's files. Enforced by sentinel regression test (`test_install_never_touches_non_owned_docs` — pre-existing non-owned files must survive an install byte-identical); a new install surface adds the same sentinel shape. Learned the hard way: PR #363's first docs-install attempt recursively deleted a user-owned `$CODEX_HOME/docs/reach` (codex P1, reproduced with a sentinel).

## Experimental skills (tier)

A skill may ship **before** it has earned the full checklist above. An experimental skill lives in the plugin and is invocable, but it is deliberately absent from every surface that promises stability:

- **Excluded from** the root `README.md` commands/skills tables, `plugins/flow-next/docs/skills.md`, the docs catalog, and any published skill/command count (step 7 is skipped entirely, including the marketing site).
- **Marked in its own frontmatter** - the SKILL.md `description` ends with ` (experimental - can change or disappear)`, so anything routing on descriptions sees the tier without a registry lookup.
- **Retired by deletion.** There is no deprecation window, no alias, no tombstone doc. The skill dir and its shim go; the CHANGELOG line says it was experimental and is gone.
- **Graduates by doing the full checklist** - steps 7, 8, and 10 in particular are what an experimental skill is allowed to defer, and graduation is exactly the change that pays them off.

**Heuristic - use the tier when the shape is still in question, not to dodge paperwork.** If you already know the skill's contract and expect it to survive the next release, ship it normally; the tier buys iteration room, and its only real cost is that nobody is told the skill exists.

**Failure signature.** A skill carrying the experimental suffix that also appears in a README table or a published count is not experimental - it is an undocumented promise. Either finish the checklist or take it out of the tables.

No skill currently ships in this tier; existing skills are not demoted into it.

## Backend-split workflow.md (heuristic)

When a skill's `workflow.md` carries backend-specific content (RP / Codex / Copilot, or parallel-vs-serial dispatch), split it so only the active backend's content enters the agent's context per invocation.

**Heuristic — split when divergent content ≥ 50 lines.** Smaller divergences stay inline; extracting them costs more in maintenance (extra files, sync-codex rewrites, link drift) than they save in context.

**Canonical 4-file shape** (when split is warranted):

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
- `flow-next-impl-review` (commit `06f6e6f`) — workflow.md 1126 → 4 files; `workflow-common.md` 565 LOC (over the ≤500 target, accepted vs duplicating gated phases). Auxiliary `deep-passes.md` / `walkthrough.md` untouched (already cross-backend).
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

## Prose-contract tests — pin content + reachability (heuristic)

A prose-contract test asserts against skill/command/agent markdown (string pins, executed bash fences, cross-skill parity, verb inventories, mirror parity). It exists to stop a *behavior* from silently regressing — not to freeze the current file layout.

**Rule — pin two things, never a third:**

1. **CONTENT** — the substantive string, fence, or inventory, asserted against the file that actually carries it today (its reference home).
2. **REACHABILITY** — the always-loaded file the agent starts from links or names that home, so the content is still on the agent's path: `self.assertIn("[references/foo.md](references/foo.md)", skill_md)`.

Never pin bare **location** — "this sentence lives in `workflow.md`" — when the contract would survive the sentence moving one level down into a reachable reference. `workflow.md` is where the prose happens to sit this release; that it is *reachable* is the contract.

**Exception — when location IS the contract** (pin it, and say why in the test docstring):

- **Executed fences whose placement is load-bearing** — a gate skeleton must sit in the file that runs it; a `## Preamble` `$FLOWCTL` definition must sit at the top of each canonical file that uses it.
- **Preamble/ordering rules** — "the gate resolves before the forcing read", "the claim precedes the work". These are position assertions by construction (see `test_setup_reference_routing.test_model_pin_gate_is_resolved_before_forcing_read`).
- **Mirror-parity paths** — canonical ↔ `codex/` ↔ Cursor twins, and byte-identical dual copies. The path pair IS the invariant.
- **Cold-path / token-budget negatives** — "this payload must NOT appear in the always-loaded spine". The point of the assertion is that the content is *not* in a particular file.
- **Reachability assertions themselves** — asserting the link exists is pinning location on purpose.

**Failure signature.** A test that breaks when verbatim content moves to a reachable reference has pinned the wrong thing. That is a test bug, not a prose regression: nothing the agent can reach changed, so nothing the agent does changed. The fix is to retarget the assertion at the new home and add the reachability link pin — not to move the prose back.

The inverse signature is just as useful: a test that keeps passing after the sentence is deleted from every reachable file has pinned nothing at all. Delete it.

**Corollary — one copy, one pin.** When branch-disclosure dedupes a phrase down to a single home, the test follows it there and pins the spine's cross-link instead of a second copy. Byte-exact pins survive only on the side that still owns the wording; the other side gets pinned by its load-bearing clauses.

**Landed examples** (fn-169 retarget round):
- `test_interview_source_tags.test_skill_md_states_per_pass_user_semantics` — per-pass `[user]` semantics moved into `references/pass-business.md` / `pass-technical.md`; the test now pins each pass's own sentence in its own file, plus SKILL.md's pass-neutral rule and both `references/…` links.
- `test_interview_source_tags.test_tag_definitions_match_capture` — capture's second tag table was deduped out of `workflow.md`; the definition pins target the surviving `phases.md` copy and `workflow.md` is pinned to still route there (`[phases.md](phases.md) §Source-tag taxonomy`).
- `test_capture_readiness_contract` — readiness gate skeletons asserted in their reference homes (content), `workflow.md` pinned for the link (reachability), both copies checked canonical + codex mirror (location-is-contract exception).

## Reference

This checklist captures the lessons from the 0.34.0 → 0.37.0 era when (a) 4 user-facing skills (resolve-pr, prospect, audit, memory-migrate) silently shipped to Codex without UI metadata, and (b) several skills shipped with inline cross-platform tables (`AskUserQuestion` / `request_user_input` / `ask_user`) that polluted the agent's context. Both fixed in 0.37.1. Don't repeat them.
