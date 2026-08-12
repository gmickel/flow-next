# Codex delegation selection — exact host gates

Read this file only when Phase 0 resolved `delegation_requested=true`. It owns
the complete pre-loop selection. Run the gates once, in order, in the host work
skill. Any failed, unavailable, or declined gate sets
`delegation_active=false`, continues in standard in-session mode, and does not
load `codex-delegation.md`.

```text
delegation_requested = host_is_claude_code && (arg delegate:codex | work.delegate == "codex") && not arg delegate:local
delegation_active = delegation_requested && Phase 1.5 selection passed
```

The executable request check and fail-open selection stay beside their
consuming phases in `phases.md`. Once selected, the host (NOT the worker) reads
the active reference once and follows its complete path-handoff, safety,
worker-signal, and circuit-breaker contract.

## Gate 0 — original input kind

**Original-input-kind capture (ONLY when `delegation_requested` — Phase 0).** A bare
idea-text input (phases.md Phase 1 match #5 — not a Flow id, not a resolvable handle, not an
existing `.md` spec path) gets promoted into a spec+task by the Phase 1 steps, so
its original kind must be recorded **before** that promotion. Set the flag in Phase 1,
on the ORIGINAL input, immediately after detection and **before** running any
"Spec file start" / "Spec-less start" promotion step:

```bash
# Runs ONLY when delegation_requested (resolved in Phase 0). On the default
# (delegation-off) path this step does not exist — Phase 0 already returned.
if <original input matched #5 idea text — none of: Flow id, resolvable handle, existing .md spec path>; then
  INPUT_WAS_BARE_PROMPT=1   # promoted bare prompt → NOT eligible for delegation (Gate 5)
else
  INPUT_WAS_BARE_PROMPT=0   # Flow id / resolvable handle / existing .md spec → eligible
fi
```

## Gate 1 — Claude Code host

Delegation is Claude-Code-only. `CODEX_SANDBOX=auto` is a flow-next review
setting, not evidence that the host is Codex.

```bash
platform_gate_ok() {
  [ -n "${CLAUDECODE:-}" ] || return 1
  [ -z "${DROID_PLUGIN_ROOT:-}" ] || return 1
  [ -z "${OPENCODE:-}" ] || return 1
  env | grep -q '^OPENCODE_' && return 1
  return 0
}
```

## Gate 2 — recursion

Only a Codex runtime sandbox value, or its runtime-only network marker, trips
the recursion guard:

```bash
not_inside_codex_sandbox() {
  case "${CODEX_SANDBOX:-}" in
    ""|read-only|workspace-write|danger-full-access|auto)
      RUNTIME_SANDBOX=0 ;;
    *)
      RUNTIME_SANDBOX=1 ;;
  esac
  if [ -n "${CODEX_SANDBOX_NETWORK_DISABLED:-}" ] || [ "${RUNTIME_SANDBOX:-0}" = "1" ]; then
    return 1
  fi
  return 0
}
```

## Gate 3 — CLI availability

```bash
codex_available() {
  command -v codex >/dev/null 2>&1 || return 1
  return 0
}
```

On failure, print exactly: `codex not found — install via npm i -g
@openai/codex; running in standard in-session mode.` Then continue standard
mode.

## Gate 4 — one-time host consent

The host, never a worker subagent, resolves consent. Existing
`work.delegateConsent=true` wins and must not re-prompt; use its persisted
`work.delegateSandbox`.

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

Otherwise, in an interactive run use `plain-text numbered prompt` once. Explain that
`yolo` is recommended because implementation commonly needs tests,
dependencies, and network access; `full-auto` is the tighter alternative:

- `yolo (Recommended)` → `--dangerously-bypass-approvals-and-sandbox`
- `full-auto` → `-s workspace-write`, with no network by default
- decline → delegation off for this run

Persist both keys only after acceptance:

```bash
$FLOWCTL config set work.delegateConsent true
$FLOWCTL config set work.delegateSandbox <yolo|full-auto>
```

Every Headless Work no-question marker uses the same exact predicate:

```bash
delegation_headless() {
  [ "${FLOW_RALPH:-}" = "1" ] && return 0
  [ -n "${REVIEW_RECEIPT_PATH:-}" ] && return 0
  [ "${FLOW_AUTONOMOUS:-}" = "1" ] && return 0
  [ "${AUTONOMOUS:-}" = "1" ] && return 0  # parsed mode:autonomous token
  return 1
}
```

When `delegation_headless` succeeds, never ask. Proceed only when consent was
already `true`; otherwise set `delegation_active=false` and continue standard
in-session Work. Do not write either consent key on this fallback. Empty or
`0` environment flags are interactive, except that any nonempty receipt path
is headless.

## Gate 5 — eligible input

```bash
input_kind_ok() {
  [ "${INPUT_WAS_BARE_PROMPT:-0}" = "1" ] && return 1
  return 0
}
```

## Gate 6 — clean code baseline

Delegation may not begin with pre-existing non-`.flow/` changes. Never stash
automatically. `.flow/` is host-owned and excluded:

```bash
DIRTY="$(git status --porcelain | grep -v '^.. \.flow/' || true)"
if [ -n "$DIRTY" ]; then
  : # offer commit or standard mode; do not delegate dirty
fi
```

## Per-task decision and terminal selection

Read `work.delegateDecision`. `auto` delegates every eligible task. `ask`
prompts before each task only when `delegation_headless` fails. When it
succeeds, treat `ask` as `auto` only with pre-granted consent; otherwise
delegation stays off and standard Work continues without a prompt or config
write.

Only after all gates pass:

1. set `delegation_active=true`;
2. read `codex-delegation.md` once, top to bottom;
3. follow its invocation, path-handoff, safety, worker-signal, and
   circuit-breaker contract for the rest of the run.

Any other terminal sets `delegation_active=false`, reads no active reference,
and continues the ordinary Work path.
