# Adding and changing skills

Read this when adding, removing or changing a skill, agent, command, reference or platform
transform. [Shipped skill text](#shipped-skill-text) applies to every edit of shipped prose.

## Adding a user-facing skill (checklist)

Every step is part of adding a `/flow-next:<name>` skill; a skipped one degrades a host silently.

1. **Canonical skill** at `plugins/flow-next/skills/flow-next-<name>/SKILL.md` (plus `workflow.md`
   or `phases.md` as needed). Frontmatter: `name`, `description`, `user-invocable: false` for
   slash-only skills, `allowed-tools`.
2. **Slash command** at `plugins/flow-next/commands/<name>.md` (flat directory). Frontmatter
   carries a bare, colon-free `name: <name>` (Claude Code adds the plugin prefix; a colon
   doubles it), a non-empty `description` (Cursor's marketplace requires both), and
   `disable-model-invocation: true`. The command is the user's entry point: any model-side
   invocation (a dispatch, hand-off or "invoke X" in a skill, agent, reference or setup
   snippet) names the skill id `flow-next:flow-next-<name>`. `sync-codex.sh` rewrites skill ids
   to `$flow-next-<name>`. Mirror the shape of `audit.md` or `prospect.md`.
3. **Claude-native tool names** in canonical files (`AskUserQuestion`, `Task`), with no inline
   cross-platform tables. The Codex mirror's rewrite lives in `sync-codex.sh`; the mirror never
   calls `request_user_input` (Plan-mode only in Codex).
4. **`scripts/sync-codex.sh`**: add the skill's `generate_openai_yaml` call (workflow blue
   `#3B82F6`, review red `#EF4444`, utility amber `#F59E0B`; display name, short description,
   explicit `false` for `allow_implicit_invocation`, optional default prompt) and its row in
   `REQUIRED_OPENAI_YAML_SKILLS`.
5. **Run `./scripts/sync-codex.sh`** and commit the regenerated `plugins/flow-next/codex/` with
   the change.
6. **Listings** (experimental skills skip this): the root `README.md` commands table, the
   command count where `CLAUDE.md` names one, and the maintainer-only site listing
   (`~/work/mickel.tech/app/apps/flow-next/page.tsx`; external contributors skip it).
7. **CHANGELOG entry** under the pending release.
8. **Smoke test** only when the skill adds flowctl plumbing (atomic writes, schema). A
   markdown-only skill is checked by running it in a real session.
9. **Conduct checklist** at [`conduct/<skill>.md`](conduct/README.md) plus its index row: 4-6
   falsifiable behaviours of a correct run, each checkable from a transcript in seconds, stated
   per output variant (a row a correct run can fail is a bug in the row). It is the review rubric
   for later prose changes, never referenced from the skill itself, and not merge ceremony.
10. **Route matrix** (`skills/flow-next-flow/references/route-matrix.md`, or
    `route-matrix-more.md` for a rarer starting state) updated in the same change, so the router
    never names a skill that is gone or misses one that ships. Removing a skill is this checklist
    backwards, in one commit: skill dir (canonical and mirror), command, `sync-codex.sh` entries,
    conduct file and index row, listings, route-matrix row.
11. **OpenCode** usually needs nothing: `scripts/install-opencode.sh` scatters canonical skills
    and `scripts/`. A new agent, or a new agent frontmatter key, must extend the closed allowlist
    in `plugins/flow-next/scripts/lib/opencode_generate.py` (it fails loudly otherwise); run the
    installer once against a scratch `--dest`.
12. **Installers write only inside directories they own** (for example
    `$CODEX_HOME/docs/flow-next/`), never loose files in a shared parent and never `rm -rf` of
    one. `test_install_never_touches_non_owned_docs` guards this; a new install surface gets the
    same sentinel test.

### Experimental skills

A skill whose shape is still in question may ship as experimental: invocable, but absent from
the README tables, `plugins/flow-next/docs/skills.md` and every published count (registry
manifests in `.claude-plugin/marketplace.json` and the `plugin.json` files still count it). Its
`description` ends with ` (experimental - can change or disappear)`. It graduates by finishing
steps 6, 7 and 9, and is retired by deletion with a CHANGELOG line, no alias. Use the tier for
iteration room, not to skip the checklist; a skill in a README table is not experimental.

## Shipped skill text

Skills, agents, references and templates are read by agents working in other people's
repositories. Write for that reader.

- **No flow-next history or repo facts.** No internal spec or task ids, PR or issue numbers,
  dated incidents, dogfood anecdotes, or facts about this repository (its Codex mirror, test
  runner, paths). Why a rule exists belongs in the commit message, the CHANGELOG or
  `agent_docs/`; the skill keeps only the rule.
- **Agent first.** Say what outcome is wanted and what the agent must not do; leave routine
  choices to it. No forms, required fields, label sets, validators or new flowctl verbs to make
  the agent prove it followed prose. Stop the agent only for a call that is genuinely the
  person's.
- **Change prose deliberately.** Before editing, know which behaviour the text drives and who
  reads it (conductor, worker, reviewer; always loaded or read on demand). Prefer moving or
  removing text to adding it, and keep one rule in one place: cross-route behaviour lives only
  in `plugins/flow-next/references/working-rules.md`.
- **Measure behaviour changes.** An edit meant to change what agents do is checked against the
  skill's conduct checklist and measured in an eval or hill-climb round
  ([optimizing-skills.md](optimizing-skills.md)), with the result recorded. A clean diff is not
  evidence, and moving text behind a link does not prove the agent still applies it.
- **Moved text stays reachable.** The entry point still sends the agent to it on the branch
  where it applies.
- **Named commands exist.** Every flowctl verb and flag in prose matches
  `flowctl <verb> --help`, and executable fences run as written.
- **Remedies name their command.** A sentence telling the reader how to recover or unblock names
  the command that does it. If no such command exists, say so and what to do instead.

Tests cover behaviour, not sentences: executed fences, flowctl output, generated-mirror parity,
verdict grammar and field names. Sentence-level prose assertions, live-file sizes and hashes of
skill prose are not added.

## Structuring a skill

- **Load only what the run needs.** Keep the common path in the always-read file and move
  default-off or mutually exclusive paths (another backend, an opt-in feature, the multi-task
  route) into `references/*.md`, linked one level deep from the file that decides. The decision
  is one sentence: "When <condition>, read <reference>." When the condition is a probe
  (`flowctl sync active --json`), a probe that fails counts as the condition holding. Content
  every run needs stays inline; a safety net that must run every time (an end-of-run check, a
  mandatory summary line) is never behind a condition. A reference longer than about 100 lines
  opens with a short table of contents.
- **Backend-specific workflows** split into `workflow-<backend>.md` files when the divergent
  content is large (roughly 50 lines or more); smaller differences stay inline.
  `flow-next-impl-review` is the pattern: SKILL.md carries the common codex path, and
  `other-paths.md` routes the other backends and flags.
- **flowctl preamble.** Each top-level skill file that runs flowctl (SKILL.md, workflow.md,
  workflow-common.md, phases.md) defines it once near the top; later blocks in that file use
  `$FLOWCTL`. Agents and subagent prompts that start fresh carry their own. Copy the three rungs
  byte for byte:

  ```bash
  FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
  [ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
  [ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
  ```

  Rung 1 serves Claude Code and Droid (`DROID_PLUGIN_ROOT`, with `CLAUDE_PLUGIN_ROOT` as its
  alias). Rung 2 serves Cursor and Grok, which set no plugin-root variable but give the skill
  file's absolute path. Rung 3 is a silent backstop for an old `.flow/bin` copy; nothing is
  designed around it. Never rely on bare `flowctl` in skill prose. `sync-codex.sh` rewrites rung
  1 for the mirror and fails the sync when a mirrored preamble loses a rung.
- **Each fence is its own tool call.** Shell variables do not survive between fences, so a fence
  assigns or re-declares every variable and path it reads. A fence that re-declares one path but
  borrows another from an earlier fence is the usual slip. A fence cannot pause for the user: it
  exits with a marker (`NEED_INPUT: ...`) and is re-run with the answer set. A fallback replaces a
  failed capture rather than appending to its partial output (`if ! VAR=$(cmd); then VAR='{}';
  fi`, not `VAR=$(cmd || echo '{}')`). A rule that holds at every exit, such as dry-run cleanup,
  is stated once in the verdict contract, not repeated at each exit.
- **Executable fences are portable bash.** Agents run them as written on macOS and Linux. Use
  POSIX classes (`[[:space:]]`, not `\s`, which BSD `grep -E` does not support), tolerate the
  legal whitespace variants of what a check looks for, and run an embedded check against hostile
  input before shipping it. A copy-paste block must agree with the prose rule it implements;
  agents copy the block. `grep -c` prints `0` and exits 1 when nothing matches, so
  `|| echo 0` yields a two-line value: write `N=$(grep -c ... || true); N=${N:-0}`. The same
  holds for any command that prints its result and then exits non-zero.
- **Parsing `$ARGUMENTS`.** The host passes arguments as one string, and word-splitting cannot
  recover the user's quoting, so document token-level passthrough (whitespace-separated, no
  embedded spaces), never "verbatim". Wrap the split in `set -f` / `set +f` so globs reach the
  wrapped CLI unexpanded. A `case` arm that consumes a value checks
  `[[ $# -lt 2 || "$2" == "--" ]]` first and exits 2 with a message, instead of dying under
  `set -e`. A flag that gates a durable write (spec state, a file, config) matches an exact
  standalone token, never a substring; test lookalikes such as `--flag-suffix` and
  `--flag=value`. `plugins/flow-next/scripts/map.sh` is the pattern.
- **Worker references reach both paths.** A reference the worker must read is named on both
  implementation paths: the standard phases and the bridge path in
  [worker-bridge.md](../plugins/flow-next/skills/flow-next-work/references/worker-bridge.md) (its
  pointer list and its On-return check). A bridged child skips the standard phases and sees only
  that list. PR briefing proof cells a route adds are shared per briefing, not one set per task:
  `proof[]` holds at most 16 cells.

## Cross-platform patterns

Read this when changing skills, agents, commands, platform transforms or installation. Canonical
Claude tool names below describe the product source, not the host you are working in.

| Host | Mechanism | Consumes |
|---|---|---|
| Claude Code | canonical plugin (`.claude-plugin/`) | canonical files as-is |
| Codex | mirror at `plugins/flow-next/codex/`, generated by `scripts/sync-codex.sh` | rewritten copies (tool names, ask fallback, dispatch phrases) |
| Factory Droid | translates the Claude plugin format on install | canonical files as-is (`DROID_PLUGIN_ROOT`) |
| Cursor | team-marketplace import (root `.cursor-plugin/marketplace.json`); fallback `scripts/install-cursor.sh` / `.ps1` into `~/.cursor/plugins/local/`; manifest `plugins/flow-next/.cursor-plugin/plugin.json` | canonical files as-is, no rewrite pass |
| Grok Build | reads the Claude plugin format | canonical files as-is |
| OpenCode | `scripts/install-opencode.sh` into `~/.config/opencode/`: skills as-is, `scripts/`, `templates/`, `references/`, `docs/` at the config root, generated agents and commands | canonical files, support dirs, generated glue |

Canonical files use Claude-native tool names and `sync-codex.sh` owns the Codex rewrite. Cursor,
Droid, Grok and OpenCode get no rewrite, so anything Claude-specific in canonical prose must work
there too or carry a portable-host clause.

When adding or editing skills, agents or commands:

1. Run `./scripts/sync-codex.sh` once and commit the mirror with the change; CI runs
   `./scripts/sync-codex.sh --check`. A new Claude-only phrase (a tool dispatch, a model-name
   example) may need a new transform plus a hard-fail guard in the script. A guard failure is
   real: fix the content or extend the transform, never relax the guard. Validate at the
   consumer's layout (the installed `$CODEX_HOME`), not only the repository tree.
2. Claude built-ins (`Explore`, `general-purpose`, `AskUserQuestion`, model names) are invisible
   to hosts that read canonical prose as-is: each needs a fallback clause (a generic read-only
   dispatch with Edit and Write disallowed; a plain-text numbered prompt for questions) or a
   stated degradation.
3. Every bash preamble carries the three flowctl rungs (above).
4. The plugin ships no hooks, and no skill registers one.
5. Installers need no per-skill updates, with two exceptions: the Codex mirror's worker-dispatch
   section (3c in `skills/flow-next-work/references/multi-task.md`) is replaced by a hardcoded
   block (`SECTION3C`) in `sync-codex.sh`, so a change to canonical 3c lands there too; and a new
   agent or agent frontmatter key extends the OpenCode generator's allowlist. Note host
   differences in `plugins/flow-next/docs/platforms.md`.
6. Agent `model` fields are family aliases the host resolves; never pin a version, and never
   assume a tier is honoured off Claude Code.

Host details:

- **Hook matchers** use a regex OR: `"matcher": "Bash|Execute"` (Claude `Bash`, Droid `Execute`).
- **Agent permissions** use a `disallowedTools` list, not a `tools` allowlist. Read-only agents
  deny `Edit`, `Write` and `Task` (a spawned writing subagent is a way out of read-only; shell
  writes also need the host sandbox and a read-only contract); writing agents deny only what
  they must not use (plan-sync: `Write, Task`; worker and pr-comment-resolver: none).
- **Plugin paths**: use `${PLUGIN_ROOT}/.claude-plugin/plugin.json`; Droid reads the Claude
  format, so no `.factory-plugin/plugin.json` is shipped.
- **Blocking questions**: canonical files write bare `AskUserQuestion`; the Codex mirror turns
  it into a plain-text numbered prompt ending with `N+1. Other — type your own answer`.
- **Unattended detection**: a skill that may ask decides from the whole autonomy marker set:
  `FLOW_AUTONOMOUS=1`, `AUTONOMOUS=1`, a `mode:autonomous` token (the list lives in flow
  `SKILL.md`, "Autonomy refusal"). An inline wrapper run for a caller inherits the caller's
  autonomy. Unattended, never prompt: take the documented deferral (`flowctl sync defer` for
  tracker conflicts, a `NEEDS_HUMAN` line elsewhere). Read how sibling skills handle asking
  before writing new ask or defer prose.
- **Subagent dispatch**: canonical writes `Task` with `subagent_type: Explore`; the mirror
  rewrites it to `spawn_agent`. Tool restrictions do not fence shell writes, so keep the host
  sandbox and read-only shell contract too.
