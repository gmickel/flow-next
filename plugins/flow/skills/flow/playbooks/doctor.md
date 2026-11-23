# Doctor

Check this person's setup on this machine by running each tool's own commands and reporting what you observed. No code in this plugin detects hosts, harnesses, or models.

Ask once what the person does if their role is not already stated in this session or their personal instruction file. With no role stated anywhere, Flow behaves as for a developer. Check only what their role needs:

- **Product owner:** the repository clone is readable, the installed plugin is current (report the version or development install as the harness shows it), and the configured tracker is reachable.
- **Developer:** everything above, plus required tools present, working logins for forge and tracker, a working Python 3.11+ interpreter for `../../scripts/edge` (`edge.cmd` on Windows), and whether a second model family can be reached for review.

Report what is reachable and what is not, quoting the command and key output behind each line (never secret values), and state how to fix anything missing.

Write nothing, with one exception: offer to save the person's role as one sentence (such as "I'm a product owner.") in their personal instruction file—never in the project's shared instruction file, since role is about the person. Nothing parses that sentence.
