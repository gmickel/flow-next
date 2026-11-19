# 9.17.0 audit fixes: machine-local review commands and eight small findings

## Goal & Context

<!-- Source: 10% user / 70% [paraphrase] / 20% [inferred] -->

A cross-family audit of everything unreleased since 9.16.0 (fn-335, fn-315, fn-337, fn-336) returned NEEDS_WORK: one release blocker in the command review backend and eight small findings, each checked against the code. This spec fixes all nine so 9.17.0 can ship. They are small and go through quickly as one change.

The blocker: the command backend reads the program it runs from `review.commands` in the tracked `.flow/config.json` of the checked-out branch. A contributor branch can name any argv there, and a maintainer who reviews that branch runs it with their own permissions. People run review on untrusted branches on the assumption that it is read-only.

The unattended failure this prevents: reviewing a branch executes a program that branch chose.

## Architecture & Data Models

- The argv for a command review backend comes only from a machine-local environment variable, one per label, the same shape as the machine-local tracker token command. Tracked config keeps only the choice of backend and label (`command:<label>`). [paraphrase]
- `review.commands` is removed from config and from the schema. It was never released, so there is nothing to migrate. [inferred]
- Labels are restricted to lowercase letters, digits, `-` and `_`, so a label maps to exactly one variable name and the schema and runtime agree. [inferred]

## API Contracts

- `FLOW_REVIEW_COMMAND_<LABEL>`: a JSON array of non-empty strings, run as argv without a shell. `<LABEL>` is the label upper-cased with `-` written as `_` (`command:kimi-pro` reads `FLOW_REVIEW_COMMAND_KIMI_PRO`). [inferred]
- A leading `~` expands in every argv element. [inferred]
- The request and response shapes, the receipt fields and everything else about the backend stay as fn-337 shipped them. [paraphrase]

## Edge Cases & Constraints

- An empty variable counts as unset. Neither the variable's value nor the command's output appears in an error, log, receipt or `.flow/` file beyond what fn-337 already records. [inferred]
- A `review.commands` key left in a config file is not read. Dispatch says so and names the variable, instead of silently running nothing or something else. [inferred]
- On Windows the argv names the interpreter first (`["python", "~/bin/review.py"]`); a `.cmd` or `.bat` first element is refused, because those run through `cmd.exe` and its interpolation. [paraphrase]
- Existing SHIP specs reviewed by a CLI backend on 9.16.0 already carry the reviewed commit, so the drift check applies to them right after upgrade. That is intended; the changelog must say it. [paraphrase]
- A skill contract change updates that skill's conduct checklist, and the Codex mirror is regenerated after the last flowctl edit. [inferred]

## Acceptance Criteria

- **R1:** A command review runs the argv from `FLOW_REVIEW_COMMAND_<LABEL>` and from nowhere else. No value in any tracked or checked-out file can supply or change the argv. [paraphrase]
  Errors: variable unset or empty, not a JSON array of non-empty strings, or a label outside the allowed characters → fails before dispatch naming the variable and the label, without echoing the value; no review round is consumed. A `review.commands` key present in config → the same failure, saying the key is no longer read.
- **R2:** The config schema, setup, the three review skills, the docs with their example, the changelog entry for the command backend and the Codex mirror describe the variable form and no longer mention `review.commands`. The schema and the runtime accept exactly the same labels. [paraphrase]
  Errors: no error surface beyond R1.
- **R3:** On Windows a `.cmd` or `.bat` first argv element is refused with a message that says to name the interpreter; the docs example shows the interpreter-first form and no longer depends on a `#!` line. [paraphrase]
  Errors: not run on a Windows host → the docs say the Windows path is covered by unit tests only.
- **R4:** An explicit `--review=command:<label>` is carried through every implementation-review path, including `--validate`, `--deep` and `--no-triage` and the re-review in the fix loop, so the named label is the one that runs. [paraphrase]
  Errors: no silent fall back to the configured label; a missing label fails as in R1.
- **R5:** Plan review accepts a bare `--review=command` and takes the label from the configured backend, as implementation review and work already do. [paraphrase]
  Errors: no label configured → fails as in R1.
- **R6:** The drift check reads the reviewed commit from the latest plan review whose verdict took effect, so a verdict whose receipt never published cannot hide drift. [paraphrase]
  Errors: no effective review with an observed commit → no drift, as today.
- **R7:** In unattended flow, a plan-review hop that was routed for drift and leaves the spec still drifted is not counted as an advance. [paraphrase]
  Errors: no error surface beyond the existing strike rules.
- **R8:** The changelog entry for the drift re-review says that SHIP specs reviewed by a CLI backend on 9.16.0 are checked right after upgrade, and that only host-reviewed ones keep the previous behaviour until their next review. [paraphrase]
  Errors: no error surface.
- **R9:** The teams guide's list of which review backends can read a criteria-referenced file outside the repository includes the command backend, stating that it depends on the wrapper. [paraphrase]
  Errors: no error surface.
- **R10:** A live command review through the real third-family wrapper reaches a verdict with the variable set, and fails cleanly with a tracked `review.commands` and no variable. [inferred]
  Errors: if the live run cannot be made, the release notes say the variable path was tested with a stand-in only.

## Boundaries

- No user-level config file and no local config overlay; the variable is the only machine-local source. [paraphrase]
- No fallback from the variable to tracked config. [paraphrase]
- No change to the other review backends, to the request or response shape, or to receipts. [inferred]
- Nothing from fn-339's follow-up list is built here. [inferred]
- No new stage, flowctl verb or receipt field. [inferred]

## Decision Context

Three options were weighed for the blocker: the variable only, tracked config with a documented risk, or both with the variable winning. The variable alone was chosen because it removes the risk structurally and matches how the tracker token command became machine-local in 9.14.0; wrapper paths are machine-specific anyway. Keeping tracked commands, even as a fallback, keeps the hole wherever only tracked config is set.
