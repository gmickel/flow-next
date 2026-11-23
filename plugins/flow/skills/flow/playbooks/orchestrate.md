# Orchestrate

Reach another model or harness for review, a read-only scout, or a build the person asked to hand over.

## Choosing the reviewer

A stated preference is not a fact about availability. Ask the active harness what it can reach and resolve a person's words at run time rather than copying model identifiers or flags from documents.

Unless the instruction files or the request say otherwise, review with a model from a different family than the one that built the change, in this order of preference: GPT-6.2 Sol at medium effort, Opus 5.5 at high, Gemini 4 Neon at high, Grok 4.7 at high, Muse Wonder 1.0 at high. Family means vendor: another model from the builder's own vendor is the same family, so skip it. Take the first of the rest this host can itself run and use the host's own subagent for it, because the host can enforce read-only tools and no second login is needed; when the host offers none of them, take the first that another installed tool can reach. Use the named version and effort exactly; a different version or effort is a different model, so move down the list. Say which model and effort reviewed and by which route.

- A reviewer the person named that cannot be reached is not replaced: stop and report.
- A model in the order above that cannot be reached means the next one. When no other family can be reached at all, `review.md` says what happens.
- A budget word in the project's instruction file (`large`, `medium`, or `small`) is the person's own choice of effort for handed work, in the harness's high, medium, or low terms, and overrides the efforts named above. It lowers no rule. If the host cannot set effort for handed work, say so once.

## Routes

Two routes exist: a parameter on the host's subagent spawn, or a second command-line tool run non-interactively. Where the host's subagents cannot take a model, a second process of the same host on the chosen model is still the host's own route.

These fail without any error, so guard them:

- Give a reviewer a read-only or sandboxed mode.
- Close standard input, or a non-interactive tool can hang waiting for it.
- When nothing will wake the session again (a headless or unattended run), wait for the reviewer before ending the turn.
- Pass the brief as a file and capture the answer to a file, both in a temporary directory outside the repository, so the working tree is left untouched.
- Keep the reviewer's session id; later rounds resume it.
- Say in the brief not to route through Flow, since the other tool reads this repo's instruction files too.

## Handing over work

Send a self-contained brief naming goal, paths, rules, and expected output. This session keeps scope, git, review, and the verdict; a handed builder may commit checkpoints on the named branch and never pushes, rewrites history, or issues a verdict. Name the building and reviewing models in the handoff and PR. A preference other than the reviewer that cannot be met falls back to this session with one notice.
