# NEEDS_WORK fix-loop procedure (INTERNAL)

Read this only when the delivered verdict is `NEEDS_WORK`. A SHIP run never
needs it; `MAJOR_RETHINK` escalates as `BLOCKED: DESIGN_CONFLICT` and never
enters this loop (see [../other-paths.md](../other-paths.md) § Fix Loop for the verdict
contract, the iteration cap, and the two anti-patterns — those stay in force
here).

One fix pass, then one re-review:

0. **Deep-pass phase (only if `DEEP=true`)** — see [../optional-phases.md](../optional-phases.md) § Deep-Pass Phase.
1. **Validator pass (only if `VALIDATE=true`)** — see [../optional-phases.md](../optional-phases.md) § Validator Pass.
2. **Interactive walkthrough (only if `INTERACTIVE=true` AND verdict still NEEDS_WORK)** — see [../walkthrough.md](../walkthrough.md).
3. **Parse issues** from reviewer feedback (Critical → Major → Minor); fix those the Review section of [working-rules.md](../../../references/working-rules.md) says to fix and list the rest as follow-ups
4. **Fix code** and run tests/lints
5. **Commit fixes**, with one `Declined #<n>: <reason>` line in the message for each finding listed as a follow-up (mandatory before re-review; never blanket-stage with `git add --all`). Then, only when step 4's green run included one of the repo's full-gate commands: read [fix-gate-receipt.md](../../../references/fix-gate-receipt.md) and mint its receipt.
6. **Re-review** (always a SINGLE dispatch — the first-round fan-out never re-runs):
   - **Codex, Claude, Copilot, Cursor**: Re-run `flowctl <backend> impl-review` per [../workflow-cli.md](../workflow-cli.md) Step 5 (the receipt resumes the reviewer's session when its `mode` is that backend). After a fan-out round (`draws[]` on the receipt) the FULL merged prior-finding container is injected with every merged ordinal — automatic, no flag.
   - **Host**: Continue through [../workflow-host.md](../workflow-host.md)'s selected
     re-review path — one FRESH read-only subagent (host sessions are never
     resumed) with the full merged prior-finding container injected into its
     prompt.
7. **Stop.** The re-review's verdict is terminal unless working-rules.md's review loop applies (an unattended run, or a request to review until SHIP): `SHIP` completes; `NEEDS_WORK` surfaces its surviving findings to the caller, never a second fix pass
