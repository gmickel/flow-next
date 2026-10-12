# Muse Code as a first-class host via an installer

## Goal & Context
<!-- Goal & Context: 20% [user], 60% [paraphrase], 20% [inferred] -->

Make flow-next work in Meta's Muse Code, either out of the box or through an install script like the ones for Codex and OpenCode. [paraphrase] The maintainer chose the installer route after a live smoke on Muse Code 1.4.6, and wants it tested until everything works, especially on a machine that also has Claude Code and Codex installed. [paraphrase]

Muse already installs Claude-format plugins as-is: skills, commands and agents load, and `${CLAUDE_PLUGIN_ROOT}` is substituted in skill text so flowctl resolves from the plugin cache. The smoke found that the plugin installs and runs but its multi-agent layer is silently degraded, and two defects in shared files block it outright. [paraphrase] The installer exists because one agent file cannot carry tool names that both Claude Code and Muse accept. [paraphrase]

## Architecture & Data Models
<!-- Architecture & Data Models: 80% [paraphrase], 20% [inferred] -->

- **Installer bundle.** The installer builds a temporary Muse bundle from the canonical plugin, installs it through Muse's own local-plugin install at user scope, approves its agent definitions, and discards the bundle. Muse owns the installed copy in its plugin cache; the installer keeps no state of its own and a re-run replaces the install. [paraphrase]
- **Agent translation.** In the bundle only, each agent's `disallowedTools` is rewritten to Muse's work-tool names (`Edit` to `edit_file`, `Write` to `write_file`). `Task` has no deniable Muse equivalent and is dropped; an emptied list drops the key. Canonical agent files are not changed. [paraphrase]
- **Dispatch spelling.** Muse exposes plugin agents as `flow-next/<name>`. In the bundle only, references to the shipped agents spelled `flow-next:<name>` become `flow-next/<name>`, so a skill's dispatch selects the agent definition instead of the built-in general-purpose agent. Skill ids (`flow-next:flow-next-<skill>`) are not agent names and are not rewritten. [paraphrase]
- **Install integrity.** Muse binds agent approval to the installed package's digest. flowctl must write nothing into its own install; the bootstrap disables bytecode writes, so importing the tracker package leaves the cache unchanged. [paraphrase]
- **Agent colors.** Shared agent files use the named colors Claude Code documents; Muse rejects hex values and ignores named ones. [paraphrase]
- **Host detection.** Setup classifies Muse when Muse's session variable is set and the resolved plugin root sits inside a Muse plugin cache. It sits above the Grok and inherited-`CLAUDECODE` rungs, because a Muse session launched from a Claude Code shell inherits `CLAUDECODE` and Muse's plugin cache also carries the Claude manifest. [paraphrase]

## API Contracts
<!-- API Contracts: 100% [paraphrase] -->

- Install: `./scripts/install-muse.sh` from a flow-next checkout, mirroring the Codex and OpenCode installers. Re-run after `git pull` to update. [paraphrase]
- Command form on Muse: `/flow-next:<name>`, identical to Claude Code. [paraphrase]
- Headless form: `muse exec "/flow-next:<name> ..."`. [paraphrase]

## Edge Cases & Constraints
<!-- Edge Cases & Constraints: 70% [paraphrase], 30% [inferred] -->

- **Mixed tool lists are rejected.** Muse marks an agent invalid at spawn time when `disallowedTools` names any non-Muse tool, so canonical files cannot list both spellings. Installation and approval still succeed; only the spawn fails, which is why the defect was silent. [paraphrase]
- **Read-only is partial on Muse.** A translated read-only scout cannot write files or edit them, but it keeps shell access (as on Claude Code) and can still spawn a child agent, which Muse does not let an agent definition deny. [paraphrase]
- **Same-machine installs.** Muse also loads skills from `~/.codex/skills` and `~/.claude/skills` by default, so a machine with the Codex install shows each flow-next skill twice, once as the Codex-shaped mirror. Muse's `context.foreign_personal_skills` setting turns that off. [paraphrase]
- **Inherited host markers.** A Muse child of a Claude Code shell sees `CLAUDECODE`; a Codex or Claude Code child of a Muse shell sees Muse's session variable. Detection must classify each by its own plugin root. [paraphrase]
- **Sandbox.** Muse's default sandbox allows writes to the active repository including its git storage, and denies writes under the home cache, so tools that cache there fail inside it. [paraphrase]
- **Instruction files.** Muse reads `AGENTS.md` before `CLAUDE.md` in the same directory and uses only the first it finds. [paraphrase]
- **Model pins.** Muse accepts the agents' Claude model aliases without error. [paraphrase]

## Acceptance Criteria

- **R1:** `scripts/install-muse.sh` installs flow-next into Muse at user scope, and afterwards every shipped agent is listed as trusted and spawns as its own definition (not general-purpose) when dispatched by `flow-next/<name>`. Errors: `muse` not on PATH, a failed install or a failed approval exits non-zero with Muse's message and leaves no temporary bundle behind; a re-run over an existing install replaces it. [paraphrase]
- **R2:** In the installed bundle every agent's tool restrictions use only Muse work-tool names, read-only scouts are refused `write_file` and `edit_file` at run time, and skill text dispatches the shipped agents as `flow-next/<name>` while skill ids stay unchanged. Errors: an agent whose list empties after translation carries no `disallowedTools` key, and an unknown tool name fails the installer instead of producing an invalid agent. [paraphrase]
- **R3:** Running flowctl from an install writes no file into that install; a regression test fails if a sibling package import leaves `__pycache__` behind. Errors: no error surface beyond the test. [paraphrase]
- **R4:** Shared agent files use only Claude Code's documented named colors. Errors: no error surface beyond the existing agent-frontmatter tests. [paraphrase]
- **R5:** Setup on Muse classifies the host as Muse, writes the `/flow-next:` command form into `AGENTS.md` by default, and offers review backends the way it does on other single-family hosts. Errors: the Muse signal absent leaves the existing cascade unchanged; a Codex or Claude Code process that inherited Muse's variable still classifies by its own plugin root. [paraphrase]
- **R6:** No existing host changes behaviour: Claude Code plugin validation, the Codex sync and manifest checks, and the Cursor and OpenCode install tests pass, and the only shared-file changes are R3 and R4. Errors: no error surface beyond the existing CI. [paraphrase]
- **R7:** A live run on Muse with Claude Code and Codex installed on the same machine completes setup, a plan whose scouts run as their own definitions, a work run that commits, and an implementation review through a CLI review backend, with any remaining degradation recorded in the docs. Errors: a stage that cannot run on Muse is documented with its cause, never claimed. [paraphrase]
- **R8:** Repo docs cover Muse: the canonical first-class sentence and its restatements, an install-matrix row, a platforms section with install, command form, detection, the same-machine skill duplication and its setting, and the degradations; the cross-platform checklist gains a Muse row noting the tool-name translation. Errors: the docs link check passes. [paraphrase]

## Boundaries
<!-- Boundaries: 100% [paraphrase] -->

- No change to canonical agent tool restrictions or skill dispatch text beyond R3 and R4; Muse spellings exist only in the installed bundle. [paraphrase]
- No reverse-engineered native `.muse-plugin` manifest; the documented Claude-plugin install path is the only one used. [paraphrase]
- No Windows PowerShell installer, matching the OpenCode installer. [inferred]
- No write to the user's Muse settings; the installer and docs name the foreign-skills setting, and the user decides. [inferred]
- The public docs site and the release downstream chain are walked at release time, not in this change. [inferred]

## Decision Context

The maintainer picked the installer over a native Muse manifest because that manifest's schema is undocumented and would be reverse-engineered from binary strings, and over a shared-file change because no single tool-name list is valid on both Claude Code and Muse. The installer follows the OpenCode precedent: generate host-specific files at install time, never commit a host tree, never rewrite canonical prose. A report to Meta that Muse should translate Claude tool names in agent definitions, as it already does for skill `allowed-tools`, is a separate follow-up. [paraphrase]

## Parked unknowns

- Whether the model on Muse picks `subagent_type` from a `flow-next/<name>` mention in skill text without further guidance; the R7 live plan run settles it.
