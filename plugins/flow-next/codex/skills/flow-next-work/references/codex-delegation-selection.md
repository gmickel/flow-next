# Codex delegation selection — exact host gates

Read this file only when Phase 0 resolved `delegation_requested=true`. It owns
the complete pre-loop selection. Run the gates once, in order, in the host work
skill. Any failed, unavailable, or declined gate sets
`delegation_active=false`, continues in standard in-session mode, and does not
load `codex-delegation.md`.

## Gate 0 — original input kind

Phase 1 must capture the original input before promoting a bare idea:

```bash
if <original input is idea text — none of: Flow id, resolvable handle, existing .md spec path>; then
 INPUT_WAS_BARE_PROMPT=1
else
 INPUT_WAS_BARE_PROMPT=0
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

In headless mode (`FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` set), never ask.
Proceed only when consent was already `true`; otherwise delegation stays
silently off.

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
prompts before each task interactively. Headless treats `ask` as `auto` only
with pre-granted consent; otherwise delegation stays off.

Only after all gates pass:

1. set `delegation_active=true`;
2. read `codex-delegation.md` once, top to bottom;
3. follow its invocation, path-handoff, safety, worker-signal, and
 circuit-breaker contract for the rest of the run.

Any other terminal sets `delegation_active=false`, reads no active reference,
and continues the ordinary Work path.
