# Waiting

A spec may wait on others with one frontmatter line, `after: [<spec-id>, ...]`, kept on one line. It is ready when every id it names is a finished spec on the default branch's latest remote state; an id still in `open/` or `parked/`, or only on an unmerged branch, is not finished, and an id that exists nowhere is unknown and is reported. `grep -H '^after:' .flow/specs/open/*.md` reads every relation among waiting specs, and `tsort` orders them and names a loop (read its messages, not its exit code; order by reading where it is missing).

When writing or changing an `after` line, check for a loop and stop on one. Dropping a waiting spec deletes its file and fixes every `after` that names it, in any spec folder, in the same commit.

Before starting a spec, check its `after`. With a person, say what it waits on and ask; if they say start anyway, remove that id from the line and add one Decision Context line saying who decided and why. Unattended, never start a spec that is not ready. With no tracker configured, start the first ready spec in `open/` that it waits on instead and say so; with a tracker configured, or when none can start, end as `NO_WORK` with the reason. Start on top of another spec's unmerged branch only when a person asks; that PR says so and stays a draft until the first has landed.
