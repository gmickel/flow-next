---
name: flow-next-pilot
description: Deprecated alias for flow-next-flow --auto --tick (one hop, PILOT_VERDICT line); removed next release. Invoke the flow skill with --auto instead.
user-invocable: false
disable-model-invocation: true
---

# `/flow-next:pilot` is now `/flow-next:flow --auto --tick`

Print exactly one line to stderr, then invoke the `flow-next-flow` skill with the arguments rewritten as below:

```bash
echo "pilot is now flow --auto --tick; this alias is removed in the next release" >&2
```

Argument mapping (every pilot argument has a place; nothing is dropped):

| Pilot argument | Flow argument |
|---|---|
| `--spec <id>` or `--spec=<id>` | the positional `<id>` |
| `--backlog` or `--auto` (pilot's backlog switch) | `--backlog` |
| `--dry-run` | `--explain` (`--dry-run` is also accepted for this release) |
| `--review=<backend>`, `--research=<grep|rp>`, `--depth=<level>` | passed through unchanged |
