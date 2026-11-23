# Port

Convert a repository from Flow-Next Classic to Flow as one reviewable change on its own branch. One plugin per repo; specs stay under `.flow/specs/`. Never touch uncommitted files, and delete nothing without the person's yes.

## Specs and open work

For each spec under `.flow/specs/`, copy identity fields from its JSON twin (`id`, `title`, and where present `tracker` with `id`, `identifier`, and `url`) into YAML frontmatter at the top of the markdown file, leaving the body unchanged. The JSON twin is then no longer needed.

Check `.flow/tasks/` for unfinished tasks on open specs and move what remains into the spec in the person's words so open work is not silently lost.

## Config, leftovers, and instructions

Keep the `.flow/config.json` keys Flow reads: `tracker.type`, `tracker.readyState`, `tracker.perTracker`, `tracker.resolved`, and `tracker.transport`. Linked issues keep working because `edge` still reads and writes Classic's markers.

List every remaining Classic artefact with what it was for—`.flow/tasks/`, `.flow/memory/`, `.flow/review-receipts/`, `.flow/artifacts/`, `.flow/meta.json`, `.flow/.flow_version`, unused `.flow/config.json` keys, spec JSON twins, and runtime state—and delete only what the person approves.

In `CLAUDE.md` / `AGENTS.md`, replace Classic's block with the sentence from `prime.md`: `Use the Flow skill for development work in this repository.`
