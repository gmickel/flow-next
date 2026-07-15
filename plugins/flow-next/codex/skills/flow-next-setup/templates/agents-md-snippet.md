<!-- BEGIN FLOW-NEXT -->
## Flow-Next

This project uses Flow-Next. Use `.flow/bin/flowctl` for ALL task tracking. Do NOT create markdown TODOs or use TodoWrite. Re-anchor (re-read spec + task status) before every task.

```bash
.flow/bin/flowctl list # specs + tasks
.flow/bin/flowctl show fn-N.M # view task
.flow/bin/flowctl start fn-N.M # claim task
.flow/bin/flowctl done fn-N.M --summary-file s.md --evidence-json e.json
# e.json: {"commits": ["abc123"], "tests": ["npm test"], "prs": []}
```

**Creating a spec:** write it directly - do NOT use `$flow-next-plan` (that only breaks a spec into tasks). Scaffold cascade (first match wins): `SPEC.md` -> `spec.md` -> `.flow/templates/spec.md` -> bundled template.

```bash
.flow/bin/flowctl spec create --title "Short title" --json
.flow/bin/flowctl spec set-plan <spec-id> --file plan.md
```

Then `$flow-next-plan <spec-id>`.

**More:** `.flow/bin/flowctl --help` or `.flow/usage.md`
<!-- END FLOW-NEXT -->
