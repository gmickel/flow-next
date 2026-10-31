# Implementation Review — flowctl setup and foreground rule

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Foreground rule — review CLI calls are blocking.** Run every `flowctl <backend> …` review command (`impl-review` / `validate` / `deep-pass`) as a single **foreground** Bash call with a generous timeout (10 minutes; verdicts typically land in 1–7). **Never** launch one with `run_in_background` + a monitor/poll — a background completion does not reliably resume a subagent context, and the call is bounded, so blocking is safe and simpler. (An ad-hoc bridge call that writes its output to a file and is polled in foreground calls is a different pattern; this rule binds review commands.)
