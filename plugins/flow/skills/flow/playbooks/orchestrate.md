# Orchestrate

Reach another model or harness for review, a read-only scout, or a build the person asked to hand over.

A stated preference is not a fact about availability. Ask the active harness what it can reach and resolve a person's words at run time rather than copying model identifiers or flags from documents. With no preference stated, use the other tool's or host's own default model and effort as configured; do not pick a more expensive tier than asked for.

Two routes exist: a parameter on the host's subagent spawn, or a second command-line tool run non-interactively. When the host's own subagent can run a model from another family, prefer it because the host can enforce read-only tools and no second login is needed; otherwise use a command-line tool. Ask the tool for its current options and guard its traps: use read-only or sandboxed mode for a reviewer; close standard input so a non-interactive tool does not hang waiting for input; run long calls in the background and wait with a deadline so they outlast shell limits; pass the brief as a file and capture output to a file in a temporary directory outside the repository so a review leaves the working tree untouched; keep the session id to resume later rounds; and tell it in the brief not to route through Flow, since it reads this repo's instruction files too.

Send a self-contained brief naming goal, paths, rules, and expected output. This session keeps scope, git, review, and the verdict; a handed builder may commit checkpoints on the named branch and never pushes, rewrites history, or issues a verdict.

An optional budget word (`large`, `medium`, or `small`) in the project's instruction file sets effort for handed work using the harness's high, medium, or low terms without lowering any rule; if unsupported, say so once. Name the building and reviewing models in the handoff and PR. If a reviewer is unreachable, stop and report; anything else falls back here with one notice.
