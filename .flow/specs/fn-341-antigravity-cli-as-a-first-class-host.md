# Antigravity CLI as a first-class host and a driven target

## Goal & Context

<!-- Source: 15% user / 25% [paraphrase] / 60% [inferred] -->

Google's Antigravity CLI (`agy`) now ships strong models, and it is installed on the maintainer's machines. Flow-Next should work in it the way it works on the other supported hosts, and it should also be usable as a target that another host drives for implementation offload and for review.

A feasibility pass on Antigravity CLI 1.5.12 (2026-11-19) measured both directions live. The findings below are the basis for every criterion. Nothing here is taken from documentation alone unless it says so.

**As a host, measured:**

- `agy plugin install <dir>` accepts the canonical Claude plugin and converts it. Skills load, and `flowctl` resolves through the existing rule that derives the plugin root from the skill file's own path.
- 19 of the 21 agents are skipped by the loader with "Invalid model tier sonnet" (or `opus`). Antigravity accepts `inherit`, `flash_lite`, `flash` and `pro`.
- `disallowedTools` is ignored. An agent with no `tools` list gets no shell, so a scout dispatched that way came back blocked. Tool access is an allowlist of Antigravity's own tool names.
- With the two frontmatter translations applied, `agy plugin validate` passes with 29 skills and 21 agents, named agents dispatch through `invoke_subagent` by `TypeName`, and two were dispatched concurrently in one turn.
- A full `plan` ran in the TUI on the default model: repo-scout, spec-scout and flow-gap-analyst ran, the approval was a blocking `ask_question` prompt, and the spec and two tasks validated.
- A full `work` ran with `--review=codex`. Codex returned SHIP on task 1 and NEEDS_WORK then a fix pass on task 2, each with a normal receipt.
- The converter also turns the 26 commands into skills named `flow-next-cmd-<name>`, which doubles the skill catalog.
- Plugin skills are typed as `/flow-next:<skill-name>`, so the canonical skills appear as `/flow-next:flow-next-plan`. A short skill named `plan` with `disable-model-invocation: true` appears as `/flow-next:plan`, forwards its arguments to the real skill, and stays out of the model's skill catalog.
- Setup classifies the host as `codex`, because no rung recognises Antigravity.
- The plugin's `rules/` content is not loaded (0 rules). Antigravity reads `rules/AGENTS.md`.
- In Antigravity's default Auto mode, every subagent shell command runs in a sandbox where the repository's git storage is read-only and the network is off, whatever the agent's `commandExecutionPolicy` says. The worker could not commit or run the review, and the conductor did both for it. Narrow `permissions.allow` rules for `git` and `curl` did not lift this. The `toolPermission: always-proceed` setting did: a subagent then committed and reached the network.

**As a target, measured:**

- A headless `agy` child implemented, ran tests and committed without `--dangerously-skip-permissions`. A session-only `--settings` deny rule refused `git push` at the tool level.
- The existing `command:<label>` review backend ran a real two-round implementation review through a small wrapper. Round 1 returned NEEDS_WORK, round 2 resumed the same conversation and returned SHIP, and both receipts recorded `mode: command`, `label: agy` and the model.
- `--mode plan` is not a read-only mode. Its tool list is identical to the default. Deny rules for `write_file` and `command` are tool-enforced.
- An unknown `--conversation` id silently starts a fresh conversation and exits 0.

## Architecture & Data Models

**Host support follows the Muse Code pattern.** [inferred] An installer builds an Antigravity bundle from the canonical plugin at install time and hands it to `agy plugin install`. Nothing Antigravity-specific is committed as a second tree, and the canonical skills, agents and commands stay untouched.

The bundle differs from the canonical plugin in these ways only: [inferred]

- Agent `model` values are mapped to Antigravity tiers: `sonnet` to `flash`, `opus` to `pro`, `inherit` unchanged.
- Each agent's `disallowedTools` line is replaced by a `tools` allowlist in Antigravity's tool names. Read-only agents get shell, file read and web search. Writing agents also get file edit and write, subagent dispatch and the question tool.
- `commands/` is dropped. In its place the bundle carries one short stub skill per command, hidden from model invocation, so the documented `/flow-next:<name>` commands work as typed.
- The plugin's rule content is delivered as `rules/AGENTS.md`.
- A bundle marker file sits at the plugin root for setup detection.

**Setup detection uses the bundle marker, not an environment variable.** [inferred] Antigravity sets `ANTIGRAVITY_CONVERSATION_ID` and similar variables in its agent shell, but child processes inherit them, the same failure class as `CLAUDECODE` and `CURSOR_AGENT`. The marker is present only in an Antigravity install, so its rung can sit beside the Muse marker rung at the top of the cascade.

**Target support adds no code.** [inferred] Implementation offload uses the existing bridge recipe pattern in the usage guide. Review uses the existing `command:<label>` backend with a documented wrapper.

## Edge Cases & Constraints

- **Sandboxed subagents.** In Auto mode a worker cannot commit, write the task lock, or run a review CLI. The measured remedy is starting the session with `toolPermission: always-proceed`. Without it the run still finishes, because the conductor commits and reviews, but that is a degraded path and must not be presented as the supported one. [inferred]
- **Misspelled tool names can hang a subagent.** Antigravity documents this as a known issue. The bundle's allowlists must use names that `agy plugin validate` accepts. [inferred]
- **Host review.** Antigravity reaches Claude and GPT-OSS models as session models, but a subagent's model is a tier (`flash`, `pro`, `inherit`), not a named cross-family model. A cross-family reviewer pin was not demonstrated, so `review.backend host` keeps its existing fail-closed behaviour on this host. [inferred]
- **Instruction files.** Antigravity reads `AGENTS.md` and `GEMINI.md`. `CLAUDE.md` is not documented as read. [inferred]
- **Read-only agents keep the shell**, as on Claude Code and Muse. [inferred]
- **Reviewer read-only is a deny list.** MCP, browser and web tools were not tested against it, and reads outside the workspace are allowed. The review recipe says so. [inferred]
- **Version drift.** Auto as the default mode needs 1.5.7 or later. The docs name the version each claim was verified on. [inferred]
- **POSIX only**, matching the Muse and OpenCode installers. [inferred]

## Acceptance Criteria

- **R1:** An installer builds the Antigravity bundle from the canonical plugin and installs it with `agy plugin install`, and `agy plugin validate` on the installed bundle reports all canonical skills and all 21 agents with no errors. Re-running it updates the install. Errors: `agy` missing from PATH, or a validation failure after install, ends with a clear message and a non-zero exit, and never reports success. [inferred]
- **R2:** In the bundle, every agent has a model tier Antigravity accepts and a `tools` allowlist in Antigravity's tool names. Read-only agents have no file edit or write tool. Errors: a canonical agent whose model or tool restriction the installer has no mapping for fails the build by name instead of shipping an agent the loader skips. [inferred]
- **R3:** The documented `/flow-next:<name>` commands work as typed in the Antigravity TUI and forward their arguments to the matching skill, and the model's skill catalog shows only the canonical skills. Errors: no error surface beyond R1. [inferred]
- **R4:** `/flow-next:setup` in an Antigravity install classifies the host as Antigravity from the bundle marker, writes the `/flow-next:` snippet to `AGENTS.md`, and offers review backends the way it does on Muse and Grok. A Codex or Claude Code child that inherited Antigravity's environment variables still classifies as its own host. Errors: no error surface beyond the existing cascade. [inferred]
- **R5:** The platform docs describe Antigravity as a supported host: the install command, the session setting a flow-next session needs so workers can commit and review, the caveats in Edge Cases, and the version verified. The roster sentence, the install matrix and the downstream properties are updated together. Errors: none. [paraphrase]
- **R6:** A live run on the installed bundle, started with the documented session setting, completes `plan` with scouts and `work` with a worker that itself commits and runs a `codex` review to a receipt. The run is recorded in the verification status line of the platform docs. Errors: if the worker still cannot commit or review under the documented setting, R5 documents the conductor-commits path as the supported one and says why. [inferred]
- **R7:** The usage guide carries an Antigravity bridge recipe beside the existing ones: flags before `-p`, a print timeout, a tool-level deny for push and history rewrite, and the success check (exit 0 and a success status). Errors: the recipe states that a non-zero exit, an error status or an empty diff is a failed bridge call. [paraphrase]
- **R8:** The `command:<label>` documentation carries a working Antigravity review recipe: a wrapper that runs in the repository, enforces read-only through deny rules, passes the print timeout, reports the observed model, and treats a returned conversation id that differs from the requested one as a failed resume. Errors: the recipe states the untested read-only bypass classes. [paraphrase]
- **R9:** Deterministic tests cover the bundle build (model and tool translation, stub skills, marker, dropped commands, fail-closed on an unmapped agent) and the setup detection fixtures for the new rung. Errors: none. [inferred]
- **R10:** On a successful install the installer's closing message prints the command that starts a flow-next session with the documented session setting, with the same trusted-environment caution as the platform docs. Errors: none; the message is not printed when the install failed.

## Boundaries

- No dedicated `agy` review backend, registry entry, `flowctl agy` verb, config key, schema value or model ladder. The `command:<label>` backend covers review. [inferred]
- No dedicated orchestration route or code. The bridge is a documented recipe. [inferred]
- No committed Antigravity mirror of the plugin, and no edits to canonical skills, agents or commands to suit Antigravity. [inferred]
- No hooks, MCP servers or sidecars in the bundle. [inferred]
- The Antigravity IDE and app, Windows, and Gemini Enterprise accounts (which are not offered Auto mode) are not verified by this spec. [inferred]
- No host-review support on Antigravity beyond the existing fail-closed behaviour. [inferred]
- No marketplace listing. [inferred]
- No use of `--dangerously-skip-permissions`, `--json-schema` or ACP in any recipe. [inferred]

## Decision Context

**Installer-built bundle over a native or marketplace install.** A direct install loads skills but skips 19 of 21 agents and leaves setup misclassifying the host, which is the situation Muse had. A bundle built at install time fixes both without a second committed tree. [inferred]

**Stub skills over a host-specific command spelling.** Printing `/flow-next:flow-next-<name>` on this host would need closer and snippet changes across skills, as OpenCode's flat form did. Hidden stubs make the documented commands work with no prose change, and the stub was measured to stay out of the model's catalog. [inferred]

**Marker file over environment detection.** The `ANTIGRAVITY_*` variables are inherited by children, so they cannot prove this plugin is an Antigravity install. [inferred]

**`always-proceed` over narrower permissions.** Allow rules for single commands did not lift the subagent sandbox. The docs present the setting the way the Muse section presents `--disable-sandbox`: use it only in an environment already trusted. [inferred]

**Docs-only target support.** The precedent backends each touched dozens of files. A dedicated `agy` backend would add only a packaged argv and a setup listing, and Antigravity's flags are still changing between releases. A dedicated backend is worth revisiting only if Antigravity should become a packaged setup choice. [inferred]

**One spec.** The maintainer chose to keep host support and the target recipes together, since the recipes land in the same docs pass.

## Strategy Alignment

- Serves the Cross-platform parity track: a new host through installer delivery, with canonical files unchanged and the roster sentence kept as the single source of truth. [strategy:Cross-platform parity]
- Follows the "Agent first" principle: target support is guidance in existing docs, with no new verb, key or gate. [inferred]

## Parked unknowns

- Whether a reviewer subagent can be pinned to a named cross-family model on Antigravity. A measured dispatch with the `Model` parameter and an agent-level model, checked against the receipt, would resolve it.
- Whether three concurrent headless `agy` processes run cleanly for a review fan-out. One measured three-draw run would resolve it.
- Whether a headless bridge child loads the installed flow-next skills when the bundle is present, as Codex does on its route B. One bridge call on a machine with the bundle installed would resolve it.
- Whether `--sandbox` gives usable write containment for a bridge child. One measured run would resolve it.
