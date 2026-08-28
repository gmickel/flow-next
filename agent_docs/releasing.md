# Release process

Steps to ship a new version of flow-next.

## When to bump

- **Bump version** when skill / phase / agent / command files change (affects plugin behavior):
  - `plugins/<plugin>/skills/**/*.md`
  - `plugins/<plugin>/agents/**/*.md`
  - `plugins/<plugin>/commands/**/*.md`
- **Don't bump** for pure README / docs / agent_docs changes (users don't need an update).
- Use semver. Major (1.0+) requires breaking-change documentation in CHANGELOG.

## Files kept in sync

`scripts/bump.sh` handles all five version surfaces; verify with `jq` after running:

- `plugins/flow-next/.claude-plugin/plugin.json` — version
- `plugins/flow-next/.codex-plugin/plugin.json` — version
- `plugins/flow-next/.cursor-plugin/plugin.json` — version (Cursor local-install manifest — easy to miss)
- `.claude-plugin/marketplace.json` — plugin version inside the `plugins[]` array AND `metadata.version`
- `.agents/plugins/marketplace.json` — plugin version inside the `plugins[]` array (Codex marketplace, no `metadata` block)

It re-runs `scripts/sync-codex.sh` (so release step 2 below is a belt-and-braces re-check, not a required extra run). Version badges no longer exist in either README (removed in the fn-151 front-door rework); bump.sh rewrites none. It does **not** touch the prose skill/command/subagent counts inside manifest `description`/`longDescription` strings — when a release adds or removes a skill/command/agent, sweep those counts manually (see memory `skill-adding-version-bump-leaves-stale`).

## Marketplace rules

- Keep `marketplace.json` and each plugin's `plugin.json` in sync (name, version, description, author, homepage).
- Only include fields supported by Claude Code specs.
- `source` in marketplace must point at plugin root.

## flow-next release

```bash
./scripts/bump.sh <patch|minor|major> flow-next   # 1. bump versions
./scripts/sync-codex.sh                            # 2. regenerate Codex mirror
jq . plugins/flow-next/.codex-plugin/plugin.json   # 3. verify version
# 4. update CHANGELOG.md with [flow-next X.Y.Z] entry (repo canonical, keep-a-changelog style)
# 5. update the flow-next.dev docs-site changelog — see "Docs-site changelog entry" below
#    ALSO bump FLOW_NEXT_VERSION in that repo's src/lib/site.ts (the site version
#    badge) — bump.sh does NOT touch it and it goes stale silently (caught at 3.18.0)
# 6. if this release has a behavior-affecting change or new opt-in default, append one line
#    to plugins/flow-next/docs/README.md § "Notable updates" (newest first; format is
#    documented inline in that section). Same story on the flow-next.dev landing page
#    when that surface exists for the release.
# 7. BIG-PICTURE DOCS SWEEP (repo docs AND flow-next.dev) — a feature page is not enough.
#    Ask: which OTHER pages does this change touch? Does it alter the pipeline picture
#    (strategy/pipeline, teams.md lifecycle map, the guide's pipeline breakdown)? Does it
#    give a team role a new surface (teams/collaboration, teams.md roles table)? Does it
#    interact with an existing feature's page (cross-link both ways)? A new capability
#    documented only on its own page is half-shipped.
# 8. NEW OR CHANGED CONFIG KEYS → the flow-next.dev config reference
#    (src/content/docs/flowctl/configuration.mdx) is generated from
#    plugins/flow-next/schema/flow-config.schema.json and documents EVERY key. When a
#    release adds/renames/retypes a key, the schema learns it (fn-138 drift test) AND the
#    config page gets the row in the same downstream walk — half-hidden knobs that only
#    exist in skill prose are the failure mode this step closes.

git add -A && git commit -m "chore(flow-next): bump version to X.Y.Z"
git push

git tag flow-next-vX.Y.Z && git push origin flow-next-vX.Y.Z   # triggers release + Discord
```

## Changelog writing gate

`CHANGELOG.md` is the canonical technical record, but it is also copied verbatim
into the GitHub release. It is a user-facing release surface, not an engineering
ledger. Keep the Keep a Changelog headings (`Added`, `Changed`, `Fixed`), but
make the release understandable before the inventory begins.

This gate is a changelog specialization of the generic artifact-prose contract in [`plugins/flow-next/docs/prose.md`](../plugins/flow-next/docs/prose.md) (the documentation specialization is [`writing-docs.md`](writing-docs.md)) (portability test, mechanism-or-number, outcome-first ordering, honesty, the style bans). The generic rules live there; below they appear only inside changelog specializations, never as standalone restatements — everything that follows is the changelog-specific machinery that operationalizes them: the four-slot ordering, the hard rejection test with its worked examples, and the docs-site register.

For every feature release, write in this order:

1. **User outcome.** Open the release section with a short unheaded paragraph:
   who benefits, what became easier or newly possible, and why it matters.
2. **Changed journey.** Explain the before-and-after workflow in user concepts.
   For review features, describe what the human reviewer sees, where attention
   goes, what evidence is available, and what judgment remains theirs.
3. **Feature bullets.** Lead each bullet with the benefit or observable behavior.
   Follow with the mechanism and proof needed to make the claim credible.
4. **Under the hood.** Commands, internal type names, schema fields, fixtures,
   hashes, parser behavior, and benchmarks come last.

The outcome paragraph is mandatory for a minor release or any release whose
value spans more than one changelog bullet. A narrowly scoped patch may express
the outcome in its first bullet.

**Hard rejection test:** stop and rewrite when any of these is true:

- the first substantive sentence names a command, function, schema, artifact,
  fixture, hash, benchmark, or internal subsystem;
- a reader cannot explain what became easier, safer, faster, or newly possible
  after reading the opening paragraph;
- the entry lists what was built without walking through how the user's work
  changes;
- "exciting" is carried by adjectives rather than a concrete new capability;
- tests, timings, or compatibility contracts appear as the feature instead of
  evidence for it.

Use this shape:

```md
## [flow-next X.Y.Z] - YYYY-MM-DD

<Who gets what better, and why that changes their work.>

### Added

- **<User-visible capability or outcome>.** <Changed journey and retained
  control.> <Mechanism, contract, and proof after the benefit is clear.>
```

Example:

- Weak: "**Make PR now persists a portable v1 change walkthrough.**"
- Strong: "**Reviewers can follow the change as a deliberate journey instead of
  rebuilding it from file order.** Each logical step explains its purpose,
  groups the files that implement it, names deliberate non-changes, and attaches
  evidence. The walkthrough is also stored as a portable v1 object for
  downstream tools."

Technical completeness still matters. Preserve migration notes, compatibility
bounds, failure behavior, and measured proof, but place them after the reader
understands the value.

### Notable updates (docs home)

`plugins/flow-next/docs/README.md` § **Notable updates** is the GitHub docs entry point for behavior-affecting changes and new opt-in defaults - one line each plus how to enable, newest first. Append when a release introduces something a user (or agent reading the docs home) would otherwise miss. Do not dump the full CHANGELOG there; the section documents its own format inline.

The flow-next.dev homepage carries a shorter rotating desk: one prominent latest
update plus the three preceding notable releases, all visible at once. Do not
turn it into a carousel or hide entries behind controls. On each behavior
release, add the new outcome-first item at the front, remove the oldest homepage
item, and keep the full history in the changelog.

## Re-sync local installs (dogfood)

Editing `agents/**`, `skills/**`, or `commands/**` does **not** update any LOCAL install — Cursor and
Codex run from snapshot *copies* of `plugins/flow-next/`, not the repo. After an agent/skill change you
want to dogfood locally (and after every release), re-run the installer for the tool you run flow-next in:

- **Cursor:** `./scripts/install-cursor.sh` (macOS/Linux) or `scripts/install-cursor.ps1` (Windows) —
  mirrors `plugins/flow-next/` into `~/.cursor/plugins/local/flow-next`. **Fully restart Cursor** after (a
  reloaded local plugin needs a full Cmd-Q/reopen).
- **Codex:** `./scripts/install-codex.sh` — installs the Codex mirror (`plugins/flow-next/codex/`).
- **OpenCode:** `./scripts/install-opencode.sh` — scatters canonical skills + generated agents/commands into `~/.config/opencode/`. Restart OpenCode (new session) after.
- **Claude Code:** a local source checkout runs the repo directly (no re-sync); marketplace users pick the
  change up on `/plugin` update **after the release tag**.

Each installer is **idempotent** (re-run to update) and snapshots the **current working tree** — sync from
the branch/commit you actually want to dogfood. (For prompt-only optimizations there's no version-bump gate
to dogfood early — just re-run the installer.)

## Docs-site changelog entry (flow-next.dev)

The public, human-readable changelog at `~/work/flow-next.dev/src/content/docs/releases/changelog.mdx` is **not** a copy of the repo `CHANGELOG.md` — it is a *scannable* highlights page with a strict format. Every release MUST follow it so the page stays readable (one line per release, expand for detail) and the right-sidebar TOC stays a version index.

**Per-release format - add to the TOP of the `## Latest` section:**

```mdx
### X.Y.Z - <short title (3-6 words)>

**<the reader's problem, then what changes for them - the "why", in plain language>.**

<details>
<summary>Detail</summary>

<goal-oriented prose - see the register rules below. Code spans, links, file paths
fine WHERE THE READER ACTS ON THEM. Blank lines around this block so MDX renders.>

</details>
```

**Register (MANDATORY - the docs-site changelog is customer-facing, NOT the repo CHANGELOG in disguise):**

- **The generic prose contract applies** ([`prose.md`](../plugins/flow-next/docs/prose.md), cited above): outcome first with mechanism last, name the number, plain hyphens, honesty. Changelog-specific register on top of it: this page is customer-facing, and for review features the human reviewer is the protagonist - explain how they orient themselves, follow the change, focus risk, inspect evidence, and retain merge judgment. The first detail paragraphs describe the old burden, the new flow, and the control or confidence gained; internal machinery belongs in an "Under the hood" tail.
- **The title and bold one-liner answer "what was hard before, what can I do now, and why should I care?"** They never lead with a command, schema, artifact name, fixture, parser, or benchmark. Wrong: "Snapshot-based config get: three read forms backed by one command-scoped snapshot". Right: "The skills you run most now read configuration once instead of seven times - less waiting, fewer places for a half-written task to exist."
- **Every paragraph earns its place by answering why / what it means for you.**
  Function names, LOC counts, fence/prose-contract mechanics, fn-task numbering,
  test counts, and compatibility contracts belong in the repo CHANGELOG or the
  technical tail - reference them earlier only when the reader must act on them.
- **Upgrade actions come FIRST and are imperative.** If the reader must do something ("re-run ralph-init", "switch off the legacy JSON keys"), it opens the details block under a "do these first" framing - never buried mid-list. **If `SNIPPET_SCHEMA_VERSION` bumped in this release, say so there** - it is the only thing that makes a user re-run `/flow-next:setup` (plugin updates never do).
- **Numbers are outcomes, not inventory.** "30 seconds to half a second" and "half the wall-clock" persuade; "-1,251 LOC" and "ran=1935" are inventory. Keep measured evidence (that is the register: proof-backed, never adjective-backed), drop bookkeeping.
- **Honesty stays** (prose.md rule 10, load-bearing in this register). Bounds, deliberate misses, and what did NOT change are part of the story ("about 35% of runs still force a full suite as the safety floor"). The register is candid practitioner, zero hype - see the messaging architecture (claim hierarchy) in the maintainer's private config.

**Docs-site hard rejection test:** hide the final technical paragraph and ask:
"Can a user explain why this release matters, how their workflow changes, and
what control they retain?" If any answer is missing, the entry is not ready.
Also reject any entry whose title or opening sentence starts with `/flow-next:*`,
a schema/type name, or an internal artifact name.

**Rules:**
- **Heading is `### X.Y.Z - title`** (h3). This is what makes the TOC a version index and gives visual breaks. Never use a bare bullet.
- **Bold one-liner is mandatory** - it's the scannable summary. Keep it to one sentence.
- **`<details>` only for verbose releases** (multi-paragraph behavior changes). Trivial patches (a one-liner fix) can skip the disclosure and just carry the bold summary + a sentence or two of plain prose.
- **Newest at the top of `## Latest`.** When `## Latest` grows past ~10 entries, migrate the oldest ones down to `## Earlier releases` (same format; collapse their detail or trim to the one-liner). The threshold is deliberately generous - the release cadence is part of the story the page tells (raised from ~4-5, 2026-08-09).
- **Don't duplicate the whole repo CHANGELOG.** The docs-site page is the public story, not every commit. The repo `CHANGELOG.md` stays canonical (linked at the top of the page). Translating repo-changelog substance into the customer register above is the actual work of this step - budget for it; a copy-paste-and-trim is the failure mode.
- **Bump the docs-site version refs** in the same commit: `src/lib/site.ts` `FLOW_NEXT_VERSION` + `package.json` `version` → `X.Y.Z`.
- **Gate:** `cd ~/work/flow-next.dev && pnpm build` must pass (MDX `<details>` + mermaid render). Commit separately in the `flow-next.dev` repo.

The `## Maintaining this page (for contributors)` disclosure at the bottom of `changelog.mdx` documents this same format inline for editors working in the file.
