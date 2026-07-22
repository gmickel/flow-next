---
name: make-pr
description: Render a cognitive-aid PR body from flow-next state and open via gh
argument-hint: "[spec-id] [--draft|--ready] [--no-mermaid] [--base <ref>] [--memory] [--dry-run]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-make-pr`

The ONLY purpose of this command is to call the `flow-next-make-pr` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill verbatim. The skill handles flag parsing (`--draft`, `--ready`, `--no-mermaid`, `--base <ref>`, `--memory`, `--dry-run`), spec resolution (positional arg or current-branch match), pre-flight (gh / base / branch / tasks / existing-PR), input gathering, body rendering, mermaid, push, PR creation, and footer.
