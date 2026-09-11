---
name: flow-next-interview
description: Deprecated alias for flow-next-refine, removed next release. Invoke /flow-next:refine.
user-invocable: false
disable-model-invocation: true
---

# `/flow-next:interview` is now `/flow-next:refine`

Print exactly one line, then invoke the `flow-next-refine` skill with `$ARGUMENTS` unchanged:

```
Deprecated: /flow-next:interview is now /flow-next:refine (this alias is removed next release). Continuing with refine.
```

Every scope and flag (`--scope=business|technical|both|research`, `--biz`, `--tech`, `--docs`, `--strategy`, `--force`) passes through verbatim. This file carries no logic of its own.
