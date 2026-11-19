# Evaluate Pi as a host

## Goal & Context

<!-- Source: 15% user / 55% [paraphrase] / 30% [inferred] -->

GitHub issue #616 asks for native support for the Pi coding agent: installing the skills and bundled flowctl, host detection in setup, scouts, workers and reviewers running through Pi, and user questions and review evidence handled through Pi, with no Claude Code or Codex needed.

Whether that is possible is not known. Subagents and delegation in Pi work very differently from the hosts flow-next supports, so this spec only evaluates: it ends in a verdict and a cost, and ships no Pi support. [paraphrase]

## Architecture & Data Models

- The evaluation runs Pi itself against a small throwaway repository; documentation alone does not settle any row. [inferred]
- It maps each thing flow-next needs from a host to the Pi mechanism that provides it, or records that none exists. [paraphrase]

What flow-next needs from a host:

- Loading skills with their reference files, and a way to invoke one by name. [inferred]
- Reaching the bundled flowctl from a skill. [inferred]
- Delegation with fresh context: scouts that only read, a worker that edits, several running at once. [paraphrase]
- A reviewer with fresh context and enforced read-only access, or a headless run flowctl could call as a review backend. [inferred]
- A blocking question to the person, with options. [paraphrase]
- An unattended run that continues hop after hop without a person. [inferred]
- Model selection left to Pi. [paraphrase]

## Edge Cases & Constraints

- Pi is extended through its own extension mechanism; a need met only by writing and maintaining a Pi extension counts as a cost, not as native support. [inferred]
- Cross-platform parity is a standing rule: a host is first-class only when install, smoke tests and skills hold on it. A degraded path is named as degraded. [strategy:Cross-platform parity]

## Acceptance Criteria

- **R1:** Each need listed above has a row saying which Pi mechanism meets it, how it was exercised, and what was observed; or that nothing meets it. [paraphrase]
  Errors: a row that could not be exercised is marked unverified with the reason, never filled from documentation as if observed.
- **R2:** The evaluation states one verdict: first-class host, degraded single-agent path, or not feasible now. For a degraded path it says what is lost (parallel scouts, fresh-context review, questions) and whether the quality gates still hold. [paraphrase]
  Errors: no error surface.
- **R3:** The verdict comes with the cost of supporting it: installer, any Pi-side extension, mirror or rewrite of skill files, smoke coverage, and what would have to be kept in step on each release. [inferred]
  Errors: no error surface.
- **R4:** The result is written into this spec, and a reply for #616 is drafted for the maintainer to post. [inferred]
  Errors: the reply is not posted by the agent.
- **R5:** No Pi installer, skill change, platform-roster change or documentation claim of Pi support ships from this spec. [paraphrase]
  Errors: no error surface.

## Evaluation result (2026-11-19)

**Verdict: first-class host is feasible, but only if flow-next ships and maintains a Pi package that includes a delegation extension.** Pi does not delegate on its own; its README says it leaves sub-agents to extensions and packages. Without that extension, Pi supports only the degraded single-agent path described below. Per this spec's constraints, the extension counts as cost, not native support.

### How it was exercised

- Pi 1.5.2 (Linux), run headless (`pi -p --mode json --no-session --no-context-files`) and once in its TUI under tmux.
- A throwaway git repository outside this checkout, with a two-function Python module, unittest, and `.flow/` initialised by Pi itself. A second clone was used for plan and worker runs.
- A copy of the canonical `plugins/flow-next/` tree from this commit was loaded with `--skill <plugin>/skills`, and once as a package with `-e <plugin dir>`.
- Delegation used Pi's shipped example `subagent` extension, loaded with `-e`. Questions used its example `question` extension. Neither was modified. flow-next's agent files were copied into the repository's `.pi/agents/` twice: as-is, then translated (tools allowlist instead of `disallowedTools`, `model` dropped, names kept as `flow-next:<name>`).
- Model: `xai/grok-4.7`, switched to `xai/grok-4.6` after repeated provider "model at capacity" errors. This is a host evaluation, not a model comparison.
- Every Pi process in these runs was started from a Claude Code shell, so it inherited `CLAUDECODE=1`. Of the paths exercised, only setup detection reads that variable, and it was also run without it.
- Run logs (JSON event streams) are kept outside the repository.

### Needs and the Pi mechanism for each

| Need | Pi mechanism | How exercised | Observed |
|---|---|---|---|
| Load skills with their reference files; invoke one by name | Native Agent Skills support: `--skill <dir>`, a package directory via `-e <dir>`, or `~/.agents/skills` / `.agents/skills`. Each skill's path is listed in the system prompt; `/skill:<name>` forces one. | Listed the skills Pi advertised; ran `/skill:flow-next` headless; ran `/skill:flow-next-flow --auto`, which hands off to other skills; loaded the plugin directory with `-e`. | All 29 canonical skills loaded unchanged with no warnings, both ways. `/skill:<name>` works in print mode. Relative reference reads worked (`auto.md`, `references/working-rules.md`, `phases.md`, `no-plan-route.md`). The hand-off from one skill to another worked: the model read the next stage's `SKILL.md` by path. The command form is `/skill:flow-next-<name>`, but skill closers print `/flow-next:<name>`. |
| Reach the bundled flowctl | The existing plugin-root rung: the directory two levels above `SKILL.md`, which Pi makes known through the listed skill path. | Every skill run. | Resolved on every run; the env-var rungs are empty under Pi. No prose change needed. |
| Delegation with fresh context: read-only scouts, an editing worker, several at once | **Not native.** The example `subagent` extension starts a separate `pi -p --mode json --no-session` process per agent. It has single, parallel (at most 8 tasks, 4 at once) and chain modes, and a per-agent `tools` allowlist. It discovers agents only in `~/.pi/agent/agents` or the project's `.pi/agents`. | Ran canonical agent files as-is; ran two translated scouts in one parallel call, one asked to write a file; ran `/skill:flow-next-plan` (SHORT); ran `/skill:flow-next-work` with `implementer: worker`. | As-is fails. `model: sonnet` resolved to an amazon-bedrock model, and both children exited with "No API key found for amazon-bedrock". `disallowedTools` is ignored, so an untranslated scout would get write tools. Translated agents worked. Two scouts ran concurrently: their turn counts interleaved in the progress events. Plan's prose dispatched `flow-next:repo-scout` and `flow-next:spec-scout` in one parallel call, then `flow-next:flow-gap-analyst`, which is the canonical SHORT set. `flow-next:worker` ran for 11 turns, committed the test before the fix, and its task reached `done`. Both runs had a one-line dispatch hint in the prompt (tool name, `agentScope: "project"`). An installed package would have to carry that hint. |
| Reviewer with fresh context and enforced read-only access, or a headless run flowctl could call | (a) A subagent whose agent file grants only `read, grep, find, ls`. (b) Headless `pi -p --mode json --no-session --no-context-files --no-skills --no-extensions --tools read,grep,find,ls --model <id>`. | The scout write probe for (a). For (b), a review of a seeded bug (`sub` returning `b - a`) that first tried to create a file. | Read-only held both times: no write tool existed and no file appeared. The headless reviewer found the seeded bug and ended with `<verdict>NEEDS_WORK</verdict>`. Limits: Pi has no shell sandbox (its security doc relies on OS-level isolation), so enforced read-only means no `bash`, and therefore no `git diff`. The reviewer must get the change as files. When a provider error stops a run, Pi still exits 0, with `stopReason: "error"` in the JSON events (seen twice). flowctl has no Pi backend; only the command shape was exercised. |
| A blocking question with options | **Not native.** The example `question` tool draws a TUI picker and returns an error in print or JSON mode. Pi's RPC mode carries `select` dialogs over its extension-UI protocol. | TUI under tmux: the model called `question` with two options, option 2 was picked, and the model replied `CHOSEN=pytest`. | Works interactively, with the extension. The plain-text numbered fallback already in canonical prose was not exercised on its own. The RPC dialog path is **unverified**: not run. |
| An unattended run that continues hop after hop | `pi -p` runs the agent loop until the model stops. | `/skill:flow-next-flow fn-1-fix-sub-operand-order --auto` on a ready spec. | It routed to direct work, minted the implicit task, created the spec branch, committed a failing test (`-3 != 3`), committed the fix, ran `flowctl done` and committed the receipt. It then re-routed to make-pr and stopped with `PILOT_VERDICT=NEEDS_HUMAN` because the throwaway repo has no forge remote. Two earlier attempts ended mid-run on provider "model at capacity" errors, still exiting 0; a driver has to read `stopReason` and restart. |
| Model selection left to Pi | `--model` and `--thinking`. A subagent `model` field is optional; when absent, the child inherits the session model and thinking level. | Child usage reported in the subagent results of the scout, plan and worker runs. | Inheritance works: every child reported the session model. The canonical `model: sonnet`/`opus` pins break it (delegation row), so translation must drop or map them. |
| Setup host detection (part of #616) | None today. Pi's bash tool sets `PI_CODING_AGENT`, `PI_SESSION_ID`, `PI_PROVIDER`, `PI_MODEL` and `PI_REASONING_LEVEL`. | Ran the canonical setup detection block inside Pi's bash tool, with and without an inherited `CLAUDECODE`. | Wrong both ways: `claude-code` when nested under Claude Code, `codex` when standalone. A Pi rung is needed. |

### Degraded single-agent path (Pi without a delegation extension)

What is lost:

- Parallel scouts. Plan's scouts would run one after another inside the host's own context.
- Worker fresh context and multi-task scheduling (rolling or wave). A single task already runs inline on every host.
- Native questions. Skills fall back to the numbered plain-text prompt; OpenCode is already first-class with this same fallback.
- Fresh-context host review. A flowctl `pi` backend can replace it without an extension: a separate headless `pi` process with a read-only tools allowlist, as exercised above.

Quality gates hold only if flowctl gains that `pi` review backend, or another configured backend is reachable. Without one, plan review and implementation review cannot run, and #616 rules out the other runtimes.

### Cost of first-class support

- **Delivery.** A Pi package. The plugin directory already loads unchanged via `-e <dir>` (observed). A persistent `pi install git:github.com/gmickel/flow-next` needs a `package.json` with a `pi` manifest at the repository root pointing at the skills, the extension and the agents. That install is **unverified**: it writes the user's Pi settings and was not run. The alternative is an install script in the shape of `install-opencode.sh` (454 lines plus a 576-line test).
- **Pi-side extension.** Vendor and adapt Pi's MIT-licensed example `subagent` extension (`index.ts`, `agents.ts`). It must discover agents inside the package (it only looks in `~/.pi/agent/agents` and `.pi/agents` today) and keep each agent's tools allowlist. It is TypeScript against `@earendil-works/pi-coding-agent`'s extension API, so it must be checked on every Pi release. A question tool adapted from the example is optional, since the numbered fallback exists.
- **Agent translation.** A generator for the 21 canonical agents: a `tools` allowlist instead of `disallowedTools`, no `model` pin, `flow-next:` names. It also needs a frontmatter test; OpenCode's is 189 lines. No agent body changes.
- **Skill text.** No rewrite; skills and flowctl ran unchanged. Two install-time additions are needed. One is a dispatch note for the subagent tool (Muse already gets a note appended to working-rules). The other is the `/skill:flow-next-<name>` command form in closers and the setup snippet (OpenCode already has its flat-form mapping).
- **Setup.** A new detection rung: a package marker file at the plugin root as the positive signal, plus `PI_CODING_AGENT`. It sits above the inherited `CLAUDECODE` rung, with fixtures like the existing matrix.
- **Review.** A flowctl `pi` backend built on the headless command shape. It reads the JSON events, fails closed on `stopReason: "error"` despite exit code 0, and passes the change as files because the reviewer has no shell. It needs tests in the pattern of the other backends. A host review through a read-only subagent has the same no-git constraint.
- **Web scouts.** Pi has no built-in web search or fetch. STANDARD and DEEP web scouts need an MCP server or an extension. **Unverified.**
- **Smoke coverage.** Deterministic tests for the package layout, agent translation and the setup rung. Each release also needs a live multi-agent check, which requires a provider key. macOS and Windows are **unverified**: only Linux was run.
- **Kept in step on each release.** Pi's extension API and the vendored extension, the CLI flags flowctl and the extension rely on (`-p`, `--mode json`, `--tools`, `--no-session`, `-e`), Pi's Agent Skills discovery and the JSON event schema. When the follow-up ships, it also includes the platform roster and the downstream docs chain.

### Not exercised (unverified)

- `pi install` of a git or npm package. It writes user settings, so it was not run.
- The RPC-mode question dialog.
- The plain-text numbered-question fallback on its own.
- make-pr against a real forge.
- plan-review, impl-review and completion review through any backend on Pi.
- QA/drive.
- Web scouts.
- The setup skill end to end; only its detection block ran.
- macOS and Windows.

## Strategy Alignment

Cross-platform parity track: a new host is added only as first-class or as a clearly named degraded path, never as a silent partial. [strategy:Cross-platform parity]

## Boundaries

- No implementation of Pi support. A follow-up spec does that if the verdict supports it. [paraphrase]
- No evaluation of other unsupported hosts. [inferred]
- No change to how existing hosts delegate. [inferred]

## Decision Context

"Loading skills alone" is not support, as the issue itself says: flow-next's quality comes from fresh-context workers and reviewers, and a host without delegation would need either a single-agent path that drops them or a CLI bridge that the issue rules out. Evaluating first avoids building an installer for a host whose shape may not fit.
