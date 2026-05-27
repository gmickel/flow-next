<!-- BEGIN FLOW-NEXT -->
## Flow-Next

This project uses Flow-Next for task tracking. Use `.flow/bin/flowctl` instead of markdown TODOs or TodoWrite.

**Quick commands:**
```bash
.flow/bin/flowctl list                # List all specs + tasks
.flow/bin/flowctl specs               # List all specs
.flow/bin/flowctl tasks --spec fn-N   # List tasks for spec
.flow/bin/flowctl ready --spec fn-N   # What's ready
.flow/bin/flowctl show fn-N.M         # View task
.flow/bin/flowctl start fn-N.M        # Claim task
.flow/bin/flowctl done fn-N.M --summary-file s.md --evidence-json e.json
```

**Creating a spec** ("create a spec", "spec out X", "write a spec for X"):

Create one directly — do NOT use `/flow-next:plan` (that breaks specs into tasks). The canonical 7-section spec scaffold lives at `.flow/templates/spec.md` (copied here by `/flow-next:setup`) — read it for the section list, scope ownership, and `## Decision Context` H3 conditional. To customize the scaffold for this project, copy `.flow/templates/spec.md` to `<repo-root>/SPEC.md` and edit there — the discovery cascade prefers it (first match wins): `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → `.flow/templates/spec.md` → bundled plugin template.

```bash
.flow/bin/flowctl spec create --title "Short title" --json
.flow/bin/flowctl spec set-plan <spec-id> --file - --json <<'EOF'
# Title

# ... fill the 7 canonical sections (see SPEC.md / .flow/templates/spec.md)
EOF
```

After creating a spec, choose next step:
- `/flow-next:plan <spec-id>` — research + break into tasks
- `/flow-next:interview <spec-id>` — deep Q&A to refine the spec

**Rules:**
- Use `.flow/bin/flowctl` for ALL task tracking
- Do NOT create markdown TODOs or use TodoWrite
- Re-anchor (re-read spec + status) before every task

**Optional — codebase feature map:** `/flow-next:map` wraps [openclaw/clawpatch](https://github.com/openclaw/clawpatch)'s `clawpatch map` command to build a semantic feature index under `.clawpatch/features/*.json`. When present, `repo-scout` and `context-scout` use it to anchor R-IDs and `Investigation targets` to concrete codebase regions. Provider-free by default; install via `pnpm add -g clawpatch` (Node 22+).

**More info:** `.flow/bin/flowctl --help` or read `.flow/usage.md`
<!-- END FLOW-NEXT -->
