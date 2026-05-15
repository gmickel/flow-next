<!-- BEGIN FLOW-NEXT -->
## Flow-Next

This project uses Flow-Next for task tracking. Use `.flow/bin/flowctl` instead of markdown TODOs or TodoWrite.

**Quick commands:**
```bash
.flow/bin/flowctl list # List all specs + tasks
.flow/bin/flowctl specs # List all specs
.flow/bin/flowctl tasks --spec fn-N # List tasks for spec
.flow/bin/flowctl ready --spec fn-N # What's ready
.flow/bin/flowctl show fn-N.M # View task
.flow/bin/flowctl start fn-N.M # Claim task
.flow/bin/flowctl done fn-N.M --summary-file s.md --evidence-json e.json
```

**Creating a spec** ("create a spec", "spec out X", "write a spec for X"):

Create one directly — do NOT use `/flow-next:plan` (that breaks specs into tasks). The canonical 7-section spec scaffold lives at `.flow/templates/spec.md` (copied here by `/flow-next:setup`) — read it for the section list, scope ownership, and `## Decision Context` H3 conditional.

```bash
.flow/bin/flowctl spec create --title "Short title" --json
.flow/bin/flowctl spec set-plan <spec-id> --file - --json <<'EOF'
# Title

# ... fill the 7 canonical sections (see .flow/templates/spec.md)
EOF
```

After creating a spec, choose next step:
- `/flow-next:plan <spec-id>` — research + break into tasks
- `/flow-next:interview <spec-id>` — deep Q&A to refine the spec

**Rules:**
- Use `.flow/bin/flowctl` for ALL task tracking
- Do NOT create markdown TODOs or use TodoWrite
- Re-anchor (re-read spec + status) before every task

**More info:** `.flow/bin/flowctl --help` or read `.flow/usage.md`
<!-- END FLOW-NEXT -->
