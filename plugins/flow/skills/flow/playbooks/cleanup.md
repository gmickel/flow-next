# Cleanup

Use this playbook for structural changes meant to preserve behaviour: renaming, extracting, deduplicating, or moving code.

Pin the current behaviour before changing structure, using existing tests or adding characterization tests wherever the moved code has none. Make the structural change, then show the exact same pins pass unchanged.

Do not slip behaviour changes or bug fixes discovered along the way into the cleanup; report them separately so the structural diff stays safe to verify. Put any bulk mechanical step—such as a formatter, codemod, or mass rename—in its own commit with the exact command that produced it in the commit message, so a reviewer can confirm it by re-running the command rather than reading every changed line.
