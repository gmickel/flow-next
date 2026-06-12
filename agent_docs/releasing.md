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

It also rewrites the version badges in `README.md` + `plugins/flow-next/README.md` and re-runs `scripts/sync-codex.sh`. It does **not** touch the prose skill/command/subagent counts inside manifest `description`/`longDescription` strings — when a release adds or removes a skill/command/agent, sweep those counts manually (see memory `skill-adding-version-bump-leaves-stale`).

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

git add -A && git commit -m "chore(flow-next): bump version to X.Y.Z"
git push

git tag flow-next-vX.Y.Z && git push origin flow-next-vX.Y.Z   # triggers release + Discord
```

## Re-sync local installs (dogfood)

Editing `agents/**`, `skills/**`, or `commands/**` does **not** update any LOCAL install — Cursor and
Codex run from snapshot *copies* of `plugins/flow-next/`, not the repo. After an agent/skill change you
want to dogfood locally (and after every release), re-run the installer for the tool you run flow-next in:

- **Cursor:** `./scripts/install-cursor.sh` (macOS/Linux) or `scripts/install-cursor.ps1` (Windows) —
  mirrors `plugins/flow-next/` into `~/.cursor/plugins/local/flow-next`. **Fully restart Cursor** after (a
  reloaded local plugin needs a full Cmd-Q/reopen).
- **Codex:** `./scripts/install-codex.sh` — installs the Codex mirror (`plugins/flow-next/codex/`).
- **Claude Code:** a local source checkout runs the repo directly (no re-sync); marketplace users pick the
  change up on `/plugin` update **after the release tag**.

Each installer is **idempotent** (re-run to update) and snapshots the **current working tree** — sync from
the branch/commit you actually want to dogfood. (For prompt-only optimizations there's no version-bump gate
to dogfood early — just re-run the installer.)

## Docs-site changelog entry (flow-next.dev)

The public, human-readable changelog at `~/work/flow-next.dev/src/content/docs/releases/changelog.mdx` is **not** a copy of the repo `CHANGELOG.md` — it is a *scannable* highlights page with a strict format. Every release MUST follow it so the page stays readable (one line per release, expand for detail) and the right-sidebar TOC stays a version index.

**Per-release format — add to the TOP of the `## Latest` section:**

```mdx
### X.Y.Z — <short title (3-6 words)>

**<one-sentence summary of what changed and why it matters — the "what">.**

<details>
<summary>Detail</summary>

<the full prose — lift the substance from the repo CHANGELOG.md entry. Code spans,
links, file paths all fine. Blank lines around this block so MDX renders the markdown.>

</details>
```

**Rules:**
- **Heading is `### X.Y.Z — title`** (h3). This is what makes the TOC a version index and gives visual breaks. Never use a bare bullet.
- **Bold one-liner is mandatory** — it's the scannable summary. Keep it to one sentence.
- **`<details>` only for verbose releases** (multi-paragraph behavior changes). Trivial patches (a one-liner fix) can skip the disclosure and just carry the bold summary + a sentence or two of plain prose.
- **Newest at the top of `## Latest`.** When `## Latest` grows past ~4-5 entries, migrate the oldest ones down to `## Earlier releases` (same format; collapse their detail or trim to the one-liner).
- **Don't duplicate the whole repo CHANGELOG.** The docs-site page is the public story, not every commit. The repo `CHANGELOG.md` stays canonical (linked at the top of the page).
- **Bump the docs-site version refs** in the same commit: `src/lib/site.ts` `FLOW_NEXT_VERSION` + `package.json` `version` → `X.Y.Z`.
- **Gate:** `cd ~/work/flow-next.dev && pnpm build` must pass (MDX `<details>` + mermaid render). Commit separately in the `flow-next.dev` repo.

The `## Maintaining this page (for contributors)` disclosure at the bottom of `changelog.mdx` documents this same format inline for editors working in the file.

