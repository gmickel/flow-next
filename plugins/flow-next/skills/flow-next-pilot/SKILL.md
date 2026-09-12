---
name: flow-next-pilot
description: Deprecated alias for flow-next-flow --auto --tick, removed next release. Invoke /flow-next:flow --auto.
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

The rewritten invocation is `/flow-next:flow --auto --tick [<id>] [--backlog] [--explain] [--review=<backend>] [--research=<grep|rp>] [--depth=<level>]`. It behaves byte-for-byte as a pilot tick: one hop, one terminal `PILOT_VERDICT` line with the same grammar, the same rails, `pipeline.chainStages` still honoured under the tick. This file carries no logic of its own; the unattended driver lives in `../flow-next-flow/auto.md`.
