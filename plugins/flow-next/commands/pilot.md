---
name: pilot
description: Deprecated alias for /flow-next:flow --auto --tick (removed next release)
argument-hint: "[--backlog] [--spec <fn-N>] [--dry-run] [--review=<backend>] [--research=<grep|rp>] [--depth=<level>]"
---

# `/flow-next:pilot` is now `/flow-next:flow --auto --tick`

This command MUST invoke the skill `flow-next-flow`. Print one line to stderr first, then pass the arguments rewritten onto `--auto --tick`:

```bash
echo "pilot is now flow --auto --tick; this alias is removed in the next release" >&2
```

**Arguments:** $ARGUMENTS

Rewrite: `--spec <id>` (or `--spec=<id>`) becomes the positional `<id>`; `--backlog` and pilot's `--auto` become `--backlog`; `--dry-run` becomes `--explain`; `--review`, `--research`, and `--depth` pass through unchanged. The result is `/flow-next:flow --auto --tick [<id>] [--backlog] [--explain] [--review=<backend>] [--research=<grep|rp>] [--depth=<level>]`, one hop with the same terminal `PILOT_VERDICT` line a pilot tick printed.
