# /flow-next:map workflow

Use the `FLOWCTL` resolved in SKILL.md and pass the host argument string as one
quoted argument. The script owns argument parsing, install/version checks,
init, the local ignore skeleton, streaming invocation and result counts.

```bash
export FLOWCTL
bash "$(dirname "$FLOWCTL")/map.sh" "$ARGUMENTS"
```

Exit 1 reports missing install or failed init; exit 2 reports the Ralph block or
invalid arguments; other nonzero map exits propagate unchanged. Never install
or opt up the source automatically. The script never writes review receipts.

Summarize the reported feature count and timestamp. For zero heuristic features,
explain the optional `--source=auto|agent` route and provider cost; leave that
choice to the user. Point to `flowctl repo-map list`, `/flow-next:plan` and
`/flow-next:capture`. Missing output after a successful map stays a warning.
