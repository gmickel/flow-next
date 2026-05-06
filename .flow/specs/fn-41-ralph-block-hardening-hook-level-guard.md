# Ralph-block hardening: hook-level guard for user-only skills

## Goal & Context

The current Ralph-block mechanism in user-only skills (`/flow-next:capture`, `/flow-next:prospect`, `/flow-next:strategy`, and `/flow-next:diagnose` from fn-40) is a **prose-level guard** — a bash snippet at the top of SKILL.md that exits 2 when `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` is set. It works in practice: bash exits inside the agent's tool call, the agent reads the stderr message, well-behaved agents abandon the skill flow.

But it's soft. `bash exit 2` doesn't kill the worker (claude/codex/droid) process — only the single Bash tool call. A worker that misreads the prompt or drifts could see `Error: requires user` and proceed anyway. The guarantee is **agent compliance, not a process-level rail**. Ralph's outer loop only inspects the worker's overall exit code + receipt files; a single Bash rc=2 inside a tool call doesn't surface to Ralph at all.

This epic adds a `PreToolUse` hook on the `Skill` tool that intercepts user-only skill invocations under Ralph and **blocks them at the harness level — before the skill body runs at all**. The agent never sees the option to "ignore the error and proceed"; the hook fires from outside the agent's reasoning.

The hardening matters more as the user-only skill list grows. Today it's four. Two years from now if there are 10+, the prose-level guard's failure mode (drift, prompt-misreading) gets more likely.

## Architecture & Data Models

Three layers of defense, in priority order:

```
User-only skill invocation under Ralph
         │
         ▼
   Layer 1: PreToolUse hook on Skill tool   ← primary rail (Claude Code)
   ─ Hook script reads stdin JSON,
     checks .tool_input.skill against user-only registry,
     checks FLOW_RALPH / REVIEW_RECEIPT_PATH env,
     exits 2 with stderr block message.
   ─ Agent never receives the Skill tool result;
     hook fires before tool execution.
         │
         │  (hook missing, misconfigured, or platform doesn't
         │   intercept Skill — e.g. Codex today)
         ▼
   Layer 2: Prose-level guard at top of SKILL.md   ← defense-in-depth
   ─ Existing pattern. Bash snippet exits 2 inside agent's
     tool call. Agent reads stderr, abandons flow.
         │
         │  (user typed slash command directly in non-Ralph
         │   terminal that happens to have FLOW_RALPH=1 set)
         ▼
   Layer 3: Slash command file refusal              ← belt-and-suspenders
   ─ commands/flow-next/<name>.md includes the env-var check
     at the top so a direct typed invocation also refuses.
```

**Layer 1: PreToolUse hook (Claude Code, primary).**

Canonical config at `plugins/flow-next/hooks.json`:

```json
{
  "PreToolUse": [
    {
      "matcher": "Skill",
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/ralph-skill-guard.sh"
        }
      ]
    }
  ]
}
```

Hook script at `plugins/flow-next/scripts/hooks/ralph-skill-guard.sh`:

- Reads stdin JSON (Claude Code passes tool input).
- Extracts `.tool_input.skill` (handles both bare `flow-next-capture` and namespaced `flow-next:flow-next-capture` forms).
- Reads user-only registry at `plugins/flow-next/scripts/hooks/user-only-skills.txt`.
- Checks `FLOW_RALPH=1` OR `REVIEW_RECEIPT_PATH` non-empty.
- Both conditions hold + skill in registry → exit 2 with stderr message.
- Otherwise → exit 0 (allow).

User-only registry at `plugins/flow-next/scripts/hooks/user-only-skills.txt` (single source of truth):

```
flow-next-capture
flow-next-prospect
flow-next-strategy
flow-next-diagnose
```

**Layer 2: Codex hook coverage (best-effort).**

Per `CLAUDE.md`: *"Codex hooks only intercept Bash (not Edit/Write), no SubagentStop."* Skill-tool interception isn't currently in Codex's hook surface. For Codex Ralph workers, the prose-level guard remains the only rail. The Codex `hooks.json` mirror gets the same `PreToolUse Skill` entry (forward-compatible, harmless if Codex ignores it); revisit when Codex's hook surface expands.

**Layer 3: Slash command file refusal.**

Each `plugins/flow-next/commands/flow-next/{capture,prospect,strategy,diagnose}.md` adds the same env-var check at the top so a user typing the command in a terminal that happens to have those vars set also sees the refusal — covers the unlikely-but-possible case of a user with stale env vars from a previous Ralph session.

## API Contracts

Hook output contract (Claude Code `PreToolUse`):

```bash
# Block — agent receives this as a tool-error before Skill tool runs
echo "Error: /flow-next:<name> requires a user at the terminal; not compatible with Ralph mode (FLOW_RALPH=1 or REVIEW_RECEIPT_PATH set). Ralph workers stay on the existing review-iteration loop." >&2
exit 2

# Allow — Skill tool runs normally
exit 0
```

User-only skill registry — text file, one skill name per line:

```
plugins/flow-next/scripts/hooks/user-only-skills.txt
```

Adding a new user-only skill is a two-step contract:

1. Add the skill name to `user-only-skills.txt`.
2. Add (or keep) the prose-level guard at the top of `SKILL.md`.

`ci_test.sh` enforces both directions: skill-in-registry MUST have prose guard; skill-with-prose-guard MUST be in registry.

## Edge Cases & Constraints

- **Hook script not executable.** If +x bit missing, Claude Code logs warning but doesn't block. Mitigation: `ci_test.sh` verifies +x bit on `ralph-skill-guard.sh`. Install-time check in `flow-next:setup` if applicable.
- **`CLAUDE_PLUGIN_ROOT` vs `DROID_PLUGIN_ROOT`.** Hook command uses `${CLAUDE_PLUGIN_ROOT:-${DROID_PLUGIN_ROOT}}` fallback per the repo's documented cross-platform pattern.
- **Codex coverage gap.** Codex Ralph workers don't hit the hook because Codex doesn't intercept the `Skill` tool. Prose guard remains the only rail there. Document the asymmetry in `CLAUDE.md`.
- **Hook misfires under non-Ralph invocation.** Hook MUST allow when `FLOW_RALPH` unset AND `REVIEW_RECEIPT_PATH` unset. Test case: invoke `/flow-next:capture` in a normal session — hook allows; Ralph session — hook blocks. Both must hold.
- **Skill argument parsing.** Hook input is the full Skill tool input. Need to handle `flow-next-capture`, `flow-next:flow-next-capture` (Codex namespacing), and any future plugin-namespaced form. Conservative match: substring contains the registered skill name.
- **Hook fails-open on JSON parse error.** If stdin isn't valid JSON, exit 0 (don't block legitimate use). Log the parse error to stderr for debugging but don't fail closed — would block normal sessions on harness changes.

## Acceptance Criteria

- **R1:** PreToolUse hook configured in canonical `plugins/flow-next/hooks.json` (Claude Code) with `matcher: "Skill"` invoking `${CLAUDE_PLUGIN_ROOT}/scripts/hooks/ralph-skill-guard.sh`. Mirrored in `plugins/flow-next/codex/hooks.json` for forward-compatibility (harmless on Codex today; activates when Codex's hook surface expands).
- **R2:** Hook script at `plugins/flow-next/scripts/hooks/ralph-skill-guard.sh` reads stdin JSON, extracts `.tool_input.skill`, reads the user-only registry, checks `FLOW_RALPH=1` OR `REVIEW_RECEIPT_PATH` non-empty. Exits 2 with the canonical stderr block message when (skill ∈ registry) AND (Ralph env detected). Exits 0 otherwise.
- **R3:** User-only skill registry at `plugins/flow-next/scripts/hooks/user-only-skills.txt` lists `flow-next-capture`, `flow-next-prospect`, `flow-next-strategy`, `flow-next-diagnose` — one skill name per line, no comments. Single source of truth; hook script reads this file rather than hardcoding.
- **R4:** Hook fails open on JSON parse error or missing registry file (logs warning; exits 0). Fails closed when both Ralph env vars set AND skill in registry. Test cases cover both branches.
- **R5:** Each Ralph-blocked skill (`capture`, `prospect`, `strategy`, `diagnose`) keeps its existing prose-level guard at the top of `SKILL.md` as defense-in-depth. The hook is primary; the prose guard is backup if the hook is missing or the platform doesn't intercept Skill (Codex today).
- **R6:** Slash command files at `plugins/flow-next/commands/flow-next/{capture,prospect,strategy,diagnose}.md` include a brief Ralph-block notice at the top covering the case of a user typing the command in a terminal that happens to have those env vars set.
- **R7:** `scripts/sync-codex.sh` mirrors `hooks.json` updates from canonical to Codex `hooks.json`. The new hook + script + registry file land in `plugins/flow-next/codex/scripts/hooks/`.
- **R8:** `plugins/flow-next/scripts/ci_test.sh` adds a parity test asserting (a) every skill in `user-only-skills.txt` has the prose-level guard at the top of its SKILL.md (grep `FLOW_RALPH` + `exit 2` near top); (b) every Ralph-blocked skill name discovered via prose-guard grep appears in `user-only-skills.txt`. Test fails the build if either direction is broken.
- **R9:** `CLAUDE.md` "Adding a new user-facing skill" checklist gets a new item (between current step 6 and step 7): "**Ralph-block decision.** If skill requires user-at-terminal, (a) add the skill name to `plugins/flow-next/scripts/hooks/user-only-skills.txt`, AND (b) keep the prose-level guard at the top of SKILL.md (`FLOW_RALPH` / `REVIEW_RECEIPT_PATH` exit 2). Both required: hook is primary rail, prose is defense-in-depth + Codex coverage."
- **R10:** Documentation updates: `CHANGELOG.md` entry; `plugins/flow-next/README.md` mentions the hardening + the Codex coverage asymmetry; `CLAUDE.md` Hooks section documents the user-only skill registry pattern.

## Boundaries

- **Out of scope:** A `flowctl skill-allowed --name <skill> --json` subcommand. Hook is sufficient; centralizing the policy via flowctl is belt-and-suspenders that adds maintenance surface for marginal benefit. Add later if accumulated need justifies.
- **Out of scope:** Hardening Codex hooks beyond what their hook API currently supports. When Codex's hook surface expands to Skill tool interception (or equivalent), extend coverage; until then, document the asymmetry in `CLAUDE.md` and rely on the prose guard for Codex.
- **Out of scope:** Droid hook coverage. Droid's hook surface needs investigation; deferred until a real Droid Ralph user appears.
- **Out of scope:** Auto-discovery of user-only skills. Registry is explicit; new skills get added by the contributor via the `CLAUDE.md` checklist.
- **Out of scope:** Behavior changes to the four existing Ralph-blocked skills. They keep their current behavior; the hook is purely additive.

## Decision Context

- **Why hook-level instead of trusting the prose guard?** Prose guards are agent-compliance contracts. Well-behaved agents respect them; drifting agents may not. Hook-level fires from outside the agent's reasoning — the agent doesn't get to "decide" to ignore the result.
- **Why keep the prose guard as defense-in-depth?** Two layers cost almost nothing; one layer fails silently if it breaks. If the hook script is missing / misconfigured / disabled OR the platform doesn't intercept Skill (Codex today), the prose guard still fires. Asymmetric platforms make defense-in-depth load-bearing here.
- **Why a registry file rather than hardcoding in the hook script?** Single source of truth. The CI parity test checks both directions: skill-has-prose-guard AND prose-guard-skill-in-registry. Keeps the user-only skill list in one place; future contributors edit one file.
- **Why land before fn-40 (diagnose) ships?** fn-40 will be the fourth Ralph-blocked skill. Ship the rail first so diagnose lands with hook-level enforcement from day one rather than retrofitted. The existing three skills (capture / prospect / strategy) get hardened transparently as part of this epic.
- **Why fail open on JSON parse errors / missing registry?** Failing closed would break normal sessions if anything in the hook plumbing breaks (file move, JSON-format change in Claude Code, registry not yet synced). The cost of fail-closed (Ralph workers can run user-only skills) is mitigated by the prose guard layer; the cost of fail-open in normal sessions (hook does nothing) is acceptable. The asymmetry favors not breaking interactive use.

## Requirement coverage

| R-ID | Task |
|------|------|
| R1  | fn-41.M (TBD — populate via /flow-next:plan) |
| R2  | fn-41.M (TBD) |
| R3  | fn-41.M (TBD) |
| R4  | fn-41.M (TBD) |
| R5  | fn-41.M (TBD) |
| R6  | fn-41.M (TBD) |
| R7  | fn-41.M (TBD) |
| R8  | fn-41.M (TBD) |
| R9  | fn-41.M (TBD) |
| R10 | fn-41.M (TBD) |
