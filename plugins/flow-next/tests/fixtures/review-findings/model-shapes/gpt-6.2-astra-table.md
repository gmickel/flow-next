I’ll read the task first, then trace the changed behavior through its callers and check it against the acceptance criteria.
I traced the token-command cache to a caller that starts parallel requests. I’ll check whether those requests can run the helper twice, along with the link and JSON projection edge cases.
The token helper ran twice for two concurrent requests, and both forge helpers can return successful JSON reads with missing or invented field values. Existing Bitbucket briefings also retain broken links after an upgrade.

## Findings

| Severity | Confidence | Classification | File:Line | R-IDs | Problem | Suggestion |
|---|---:|---|---|---|---|---|
| P1 | 75 | introduced | `plugins/flow-next/scripts/flowctl_tracker/resolve_verb.py:86` | [R1] | A contributor can change `tokenCommand` in the branch’s committed `.flow/config.json`. If a maintainer runs a tracker read from that checkout with the token environment variable unset, even a trusted installation of flowctl executes the branch-selected program with the maintainer’s permissions. Passing argv without a shell still permits this. | Keep the shared configuration, but establish the executable and arguments from a trusted revision or locally approved configuration before invoking them. |
| P1 | 100 | introduced | `plugins/flow-next/scripts/flowctl_tracker/credentials.py:106` | [R1] | Two requests can both miss `_COMMAND_RESULTS` before either stores its result. I observed two helper launches for identical argv in one process. Linear’s `relate_many` runs dependency probes in parallel, so a batch can hit this on its first authenticated read. | Synchronize the first lookup, execution and publication of the result. Concurrent callers should share a failure as well as a token. |
| P1 | 75 | introduced | `plugins/flow-next/scripts/flowctl.py:30047` | [R3] | The corrected prefix applies only when expanding new input. On a Bitbucket origin, I passed a pre-upgrade artifact with matching base and head through current-artifact selection and rendering. It was selected as `current` and rendered `/acme/repo/blob/<sha>/src/change_0.py`. Updating the PR at the same head therefore republishes the broken link. | Resolve recognized generated file links against the current forge when rendering reused artifacts. Preserve the immutable artifact and explicitly authored links. |
| P1 | 100 | introduced | `plugins/flow-next/scripts/make-pr-gitlab.sh:133`, `plugins/flow-next/scripts/make-pr-bitbucket.sh:126` | [R5] | Missing listing fields become concrete answers. With the draft, description and SHA fields absent from the GitLab fixture, the helper exited zero with `{"headRefOid":null,"isDraft":false,"body":""}`. Bitbucket likewise reports a missing draft field as `false`. A caller can consequently treat an unknown draft state as ready. | Validate each requested field before projection and exit nonzero naming the unavailable key. Keep the empty-body mapping for a **present**, null description. |
| P2 | 100 | introduced | `plugins/flow-next/scripts/flowctl_tracker/credentials.py:108` | [R1] | `text=True` decodes stderr even though the helper’s stderr is unused. A helper that exited zero with a valid ASCII token on stdout and a non-UTF-8 diagnostic on stderr raised `UnicodeDecodeError`. The failure also bypassed the cache. | Discard stderr, check the exit status before decoding stdout, and cache a sanitized failure if stdout cannot be decoded. |
| P2 | 100 | introduced | `plugins/flow-next/scripts/flowctl.py:30046` | [R3] | `https://gitlab.com/group.git` produced `/group/-/blob/<sha>/`. The GitLab branch accepts a single path component even though a project requires both a namespace and a project name. | Require at least two validated path components for GitLab. Return plain paths otherwise. |
| P2 | 100 | introduced | `plugins/flow-next/scripts/make-pr-gitlab.sh:108`, `plugins/flow-next/scripts/make-pr-bitbucket.sh:95` | [R5] | Validation uses shell word splitting, while projection splits the original string only on commas. `--json 'number, body'` passed validation and returned just `number` in the GitLab check. Both helpers use the same two parsers. | Parse the key list once and use it for validation and projection. A malformed key must either be normalized consistently or produce a named error. |
| P2 | 100 | introduced | `plugins/flow-next/skills/flow-next-land/forge-gitlab.md:24` | [R4] | The revised paragraph qualifies `head_sha`, then introduces the fields agents read with the bare phrase “`readiness` holds”. The Codex copy does the same. R4 explicitly requires the full path wherever the reference describes reading readiness. | Introduce the field list with `.selected.pr.open.readiness` in both GitLab copies, as the Bitbucket copies already do. |

## Requirements coverage

| R-ID | Status | Evidence |
|---|---|---|
| R1 | partial | Environment precedence, argv execution and the 10-second timeout are implemented. Parallel first reads and stderr decoding break the helper contract. |
| R2 | met | The shared land workflow stops `BLOCKED` without a commit and names the check and reason when the only fix weakens the PR. |
| R3 | partial | Fresh links use the correct routes on all three forges. Reused artifacts and namespace-only GitLab origins still produce broken links. |
| R4 | partial | Bitbucket qualifies the readiness object. GitLab qualifies its head check but leaves its field list ambiguous. |
| R5 | partial | Ordinary key projections work. Partial listing rows and inconsistently parsed key lists can still return misleading success. |
| R6 | met | One sentence in the aid guidance gives the head diff precedence over a conflicting task summary. |
| R7 | met | The delivery workflow permits repository-required trailers before `Ref`, and the create step carries that exception forward. |

Unaddressed R-IDs: []

## Global criteria

G1: met - The spec ties the added workflow guidance to specific failures in the field report.  
G2: met - The modified tests exercise behavior, field values, key sets and schema contracts.  
G4: met - The token command is optional, and the spec identifies the unattended failure that warrants the `BLOCKED` stop.

Verification covered 30 passing schema-drift tests, three passing focused link tests, and direct checks for the reported edge cases. The read-only sandbox had no writable temporary directory for the tempfile-based suites.

Classification counts: 8 introduced, 0 pre_existing.

```json
{"classification_counts":{"introduced":8,"pre_existing":0},"unaddressed":[]}
```

<verdict>NEEDS_WORK</verdict>