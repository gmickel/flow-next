# Conduct checklist — /flow-next:ralph-init

A correct run scaffolds or refreshes the repo-local Ralph harness under `scripts/ralph/`, merges the guard hook entries into the host's project settings, and hands the user terminal commands to drive the loop.

- [ ] Writes land only under `scripts/ralph/` in the current repo, and an existing directory prompts before updating, preserving `config.env` and `runs/`.
- [ ] Templates, `flowctl` and its bootstrap files, the `flowctl_tracker/` package, and `pick-python.sh` are copied with `cp` (flat, so the resolver lands at `scripts/ralph/pick-python.sh`), and the tracker manifest verification runs right after the copy so a corrupt install fails here rather than as an ImportError mid-run.
- [ ] The executable bit is set on `ralph.sh`, `ralph_once.sh`, `flowctl`, `ralphctl.py`, and both guard hook files.
- [ ] Guard hook entries are merged into the host's existing settings file by reading it first, keyed on the `scripts/ralph/hooks/ralph-guard` fingerprint, so unrelated hooks survive and a re-run is a no-op. A settings file whose hooks object now contains only flow-next entries has broken this.
- [ ] The registered event set matches the host: Codex gets no `SubagentStop` and no file-tool matchers and a top-level `{"hooks": …}` only, Droid gets its own file-tool matcher set, and Cursor gets the scaffold plus a printed note that the guard will not fire — no invented Cursor-format hook file.
- [ ] The run ends by printing the terminal next steps (`ralph_once.sh`, `ralph.sh`, `ralphctl.py status|pause|resume|stop`) and the project-hooks trust note, rather than starting the loop inside the session.
