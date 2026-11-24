# Goal

A goal is an outcome needing several PRs: one goal spec with child specs, each independently shippable. A child is never itself a goal, and starting a goal from a tracker issue is not supported.

Keep a readable list of children in the goal spec and end it with `## Goal log`, adding a dated one-line entry after acting. Outside tools read that heading and list, so keep both stable, and leave the goal's criteria and boundaries unchanged unless the person edits them. The goal spec waits in `.flow/specs/open/`, and its last child's PR moves it (`pr.md`).

Run children one at a time unless parallel work was requested, each on its own branch with its own review and PR. A child is routed exactly as a spec a person wrote. Read a stage's playbook each time a child reaches that stage, even when its text is already in context: running its steps from memory is copying them, and so is a merge without the land playbook.

Merge consent comes only from the current invocation; without it, stop at the first PR needing landing. Stop when a person is needed. Once the last child has landed, review the goal as a whole against its criteria through the review playbook, and only then, with every criterion met on observed evidence, is the goal done. When unattended, follow `unattended.md` for stopping and the terminal line, using `GOAL_MET` once complete.
