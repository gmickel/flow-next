---
name: interview
description: Deprecated alias for /flow-next:refine (removed next release)
argument-hint: "[spec ID, task ID, or file path] [--scope=business|technical|both|research] [--biz | --tech] [--docs | --no-docs] [--strategy | --no-strategy] [--force]"
---

# `/flow-next:interview` is renamed to `/flow-next:refine`

This command MUST invoke the skill `flow-next-refine`. Print one line first, then pass `$ARGUMENTS` through unchanged:

```
Deprecated: /flow-next:interview is now /flow-next:refine (this alias is removed next release). Continuing with refine.
```

**User input:** $ARGUMENTS

The scopes and flags are unchanged; `/flow-next:refine` documents them.
