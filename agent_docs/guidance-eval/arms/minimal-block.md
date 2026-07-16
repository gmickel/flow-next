## Flow-Next (task tracking)

This repo uses flow-next. ALL task tracking goes through `.flow/bin/flowctl` - never TodoWrite or markdown TODO lists.

- Discover commands: `.flow/bin/flowctl --help` and `.flow/bin/flowctl <cmd> --help`.
- Typical flow: `spec create --title "..." --json` -> `task create --spec <spec-id> --title "..." --json` -> `start <task-id>` -> implement -> `done <task-id> --summary-file s.md --evidence-json e.json`.
- Evidence schema (`e.json`): `{"commits": ["<sha>"], "tests": ["<command>"], "prs": []}`.
- Re-read the spec and `flowctl show <task-id>` before each task.
