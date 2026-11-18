I’ll read the task spec first, then trace the diff through the existing callers and run focused checks where the sandbox permits.
The forge-link tests passed. The broader suites require writable temporary storage, which this sandbox denies. I’ll use read-only checks to verify the credential and PR projection paths.
## Findings

1. **P1 | Confidence 100 | introduced | R-IDs [R1]**  
   **File:Line** `plugins/flow-next/scripts/flowctl_tracker/resolve_verb.py:86`  
   **Problem** A maintainer using the installed `flowctl` to resolve a tracker from an untrusted checkout can execute a program selected by that checkout’s committed `.flow/config.json`. With the provider token unset, the first authenticated request passes the repository’s argv to `subprocess.run` under the maintainer’s account.  
   **Suggestion** Require a trusted local approval or source for the command before executing it. Bind approval to the exact argv so a checkout cannot change an approved command.

2. **P1 | Confidence 100 | introduced | R-IDs [R1]**  
   **File:Line** `plugins/flow-next/scripts/flowctl_tracker/credentials.py:106`  
   **Problem** The existing Linear dependency projection runs read probes in parallel. Two first requests can both miss `_COMMAND_RESULTS` and launch the same helper. A barrier-controlled check confirmed two launches for two concurrent calls.  
   **Suggestion** Synchronize cache initialization so concurrent requests share the first result, including a failed result.

3. **P2 | Confidence 100 | introduced | R-IDs [R1]**  
   **File:Line** `plugins/flow-next/scripts/flowctl_tracker/credentials.py:143`  
   **Problem** An explicitly empty provider environment variable triggers the helper. For example, `LINEAR_API_KEY=""` still invokes the secret store, although R1 permits execution only when the variable is unset.  
   **Suggestion** Check `value is None` before invoking the helper.

4. **P2 | Confidence 100 | introduced | R-IDs [R3]**  
   **File:Line** `plugins/flow-next/scripts/flowctl.py:30046`  
   **Problem** `https://gitlab.com/solo.git` produces `/solo/-/blob/<sha>/…` even though the origin lacks a namespace. The briefing should show a plain file path for this input.  
   **Suggestion** Require at least two path segments for GitLab while allowing nested namespaces.

5. **P2 | Confidence 100 | introduced | R-IDs [R5]**  
   **File:Line** `plugins/flow-next/scripts/make-pr-bitbucket.sh:95`, `plugins/flow-next/scripts/make-pr-gitlab.sh:108`  
   **Problem** Both helpers accept `--json 'number, body'` and return only `number`. The shell validator splits on whitespace, while the jq projection retains the leading space in ` body`. This silently drops a requested field.  
   **Suggestion** Parse the comma-delimited keys once and use the same tokens for validation and projection.

6. **P2 | Confidence 75 | introduced | R-IDs [R5]**  
   **File:Line** `plugins/flow-next/scripts/make-pr-bitbucket.sh:126`  
   **Problem** Atlassian’s listing response example supplies the raw body in `rendered.description.raw` and omits top-level `description`. With that field shape, the helper returns an empty body even when the PR has text. I confirmed the projection against a recorded row reshaped to match that example. [Bitbucket Cloud pull request listing](https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/#api-repositories-workspace-repo-slug-pullrequests-get)  
   **Suggestion** Read the raw description from either supported representation in the same listing response.

7. **P3 | Confidence 100 | introduced | R-IDs [R4]**  
   **File:Line** `plugins/flow-next/skills/flow-next-land/forge-gitlab.md:26`  
   **Problem** Both GitLab skill copies spell out `.selected.pr.open.readiness.head_sha` for the SHA comparison, then still use bare `readiness` when introducing the fields the agent reads. R4 requires the full path in both places.  
   **Suggestion** Use `.selected.pr.open.readiness` in that sentence in both copies.

FYI, duplicated code appears in the two stand-ins: `def pick: if $keys == "" then . else with_entries(select(.key | IN($keys | split(",")[]))) end;`. The duplication is a maintainability heuristic. Finding 5 covers the concrete behavior.

## Requirements coverage

| R-ID | Status | Evidence |
|---|---|---|
| R1 | partial | Jira and Linear use the helper through the bound executor. Command trust, concurrent initialization and empty-variable precedence need fixes. |
| R2 | met | The shared land workflow specifies `BLOCKED` with no commit for a fix that would weaken the PR. Bitbucket retains `NEEDS_HUMAN` for an unknown cause. |
| R3 | partial | Tested SHA-pinned links on all three forges. A malformed single-segment GitLab origin still produces a link. |
| R4 | partial | The head check uses the full path in both forge references. The GitLab field description still uses the shorthand. |
| R5 | partial | Both stand-ins project the requested keys on recorded rows. Key parsing and the alternate Bitbucket description shape still lose data. |
| R6 | met | The cognitive-aid guidance gives the head diff precedence over stale task summaries. |
| R7 | met | The delivery guidance permits only repository-required trailers before `Ref`. |

Unaddressed R-IDs: []

## Global criteria

G1: met - The spec ties the added guidance to reported workflow failures and explains the choice of short guidance over additional checks.  
G2: met - Changed tests assert credential behavior, response fields, link targets and schema contracts.  
G4: met - The credential source is optional and the workflow changes add guidance without an agent gate.

Verification passed for the 30 schema tests, three focused forge-link tests, shell syntax and `git diff --check`. The broader Python suites hit the sandbox’s read-only temporary-directory restriction. Read-only probes independently confirmed the duplicate helper launch, malformed GitLab link and JSON projection failures.

Classification counts: 7 introduced, 0 pre_existing.

```json
{"classification_counts":{"introduced":7,"pre_existing":0},"unaddressed":[]}
```

<verdict>NEEDS_WORK</verdict>