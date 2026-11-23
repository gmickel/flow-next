# Prime

Make one repository ready for agentic work. Prove each outcome by doing it rather than checking whether files exist; prime gives no score or grade.

## Outcomes

- **Operate** (build, focused test, start, sign in, drive, read logs): prove with bounded, clean-tree runs of the build and a focused test, then start the app, sign in, drive one action, and read logs.
- **Detect** (a planted defect gets caught): prove by planting a temporary defect, confirming the check fails clearly, then reverting it and confirming the check passes.
- **Navigate** (only what code cannot show: legacy and frozen areas, owners, misleading spots—never a directory inventory): ask one question for legacy and frozen areas, and prove by verifying each recorded path exists.
- **Constrain** (team rules where agents meet them): prove by checking rules sit in loaded files and existing checks pass in check mode; suggest a mechanical check only where a cheap tool already exists, never building new enforcement or CI.
- **Isolate** (two agents work without colliding): prove by running a build or focused test in a temporary second git worktree to catch env or state collisions, then removing it.
- **Govern** (merge authority, instruction-file owners, and what agents must not read or reach—secrets, production, unnecessary network): prove by checking forge protection, ownership rules, and access limits against what is recorded.

## Acting and leaving behind

Inside one repo, fill gaps using outcome defaults and stack-fitting tools without installing unchosen tools. Ask once where specs go and how they get there, show fitting shapes, and offer to record the team's answer; prime recommends, the team decides. Keep `CLAUDE.md` / `AGENTS.md` short, write no version markers, and offer to add this exact sentence:

`Use the Flow skill for development work in this repository.`

Leave a verified run-and-prove page, a short instruction file, the legacy zones, and a plain list of anything you could not make work (often sign-in) with what you tried and its output. Re-running prime re-runs the run-and-prove page.

Across several repos, analyse and recommend without building anything. Report what fits—one repo holding map, priming, and specs; a context repo beside code; or per-repo priming with a sibling list—and how each fails; the team decides.
