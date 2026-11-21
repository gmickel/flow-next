---
name: refine
description: Refine a spec, task, or spec file - one question pass that asks only what would change the build, optionally focused by a free-text scope lens, or a read-only research pass
argument-hint: "[spec ID, task ID, or file path] [--scope=<lens> | --scope=research | --biz | --tech] [--docs | --no-docs] [--strategy | --no-strategy] [--force]"
disable-model-invocation: true
---

# IMPORTANT: This command MUST invoke the skill `flow-next-refine`

The ONLY purpose of this command is to call the `flow-next-refine` skill. You MUST use that skill now.

**User input:** $ARGUMENTS

Pass the arguments to the skill verbatim. The skill handles scope lenses (`--scope=<lens>`, `--biz`, `--tech`, `--scope=research`), doc/strategy flags (`--docs`, `--no-docs`, `--strategy`, `--no-strategy`, `--force`), the interview, and write-back.
