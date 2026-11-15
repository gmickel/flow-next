# Bitbucket and Jira field-report follow-ups (#602, #611)

## Goal & Context

<!-- Source: 10% user / 70% [paraphrase] / 20% [inferred] -->

A team ran 9.10.0 on Bitbucket Cloud and Jira Cloud (two repos, autonomous mode, bkt 0.38.1, no
`gh` on PATH) and reported back in GitHub issue #602 (comment 6900082575) and issue #611. make-pr
opened pull requests, land squash-merged two and refused a red one, and Jira sync moved a merged
spec's issue to Done. The run also turned up seven gaps. This spec fixes all of them in one pass,
"so 602, 611 etc".

1. **Credentials.** None of their developers has `JIRA_API_TOKEN` in their environment. They reach
   Jira through the Atlassian Rovo MCP or their company's own MCP server, so they minted a token
   just for flowctl. They asked for a credential source other than environment variables, such as
   a command that prints the token, the way git credential helpers work.
2. **Land verdict.** On a red build whose cause land found, but where the only "fix" would delete
   the pull request's own test, land's shared workflow defines no verdict. Land chose `BLOCKED`,
   which was right.
3. **PR body links.** make-pr's file links use GitHub's `/blob/` path, and Bitbucket answers
   "Resource not found"; `/src/` works. A GitLab project in a subgroup gets no links at all.
4. **Readiness path wording.** Land's Bitbucket and GitLab references read as if `readiness` sits
   beside `.selected.pr.open`. An agent read `.selected.pr.readiness`, got `null`, and took it for
   "no readiness".
5. **`pr view --json` keys.** The Bitbucket stand-in for `gh` answers a fixed key set. A request
   for `isDraft` and `body` gets neither, plus three keys nobody asked for. The GitLab stand-in has
   the same behaviour.
6. **Stale briefing claims.** The PR briefing restated a task summary that a later review fix had
   made false at the head. The author rewrote the description by hand. This affects every forge.
7. **Mandated footer.** Their repos require a fixed footer line on every PR body. make-pr says to
   use the rendered body unchanged, so the agent appended the footer against that instruction.
   This affects every forge.

## Architecture & Data Models

- **Credentials** stay in the per-provider credential resolver, resolved by exact name, with no
  generic ladder and no keyring. The new step runs only after the provider's environment variable
  turns up nothing. [inferred]
- **Links.** The briefing link prefix is built from the forge that hosts the pull request, not from
  GitHub's path shape. [paraphrase]
- **Land verdict.** One sentence in land's shared workflow; every forge reference already defers
  its verdicts there. [inferred]
- **Readiness path.** A wording fix in the Bitbucket and GitLab land references. [inferred]
- **`gh` stand-ins.** The Bitbucket and GitLab stand-ins share one projection for list and view
  reads, so one change covers both reads. [inferred]
- **Stale briefing claims and footer** are guidance in make-pr's aid and create steps. They add no
  new flowctl surface and no extra model call. [inferred]

## API Contracts

- **Token command.** A per-tracker config value, `tracker.perTracker.tokenCommand`, holds an argv
  array, documented in the published config schema. When the provider's credential environment
  variable is unset, flowctl runs the command and uses its trimmed stdout as the credential:
  - Jira Cloud: the API token;
  - Jira Data Center: the personal access token;
  - Linear: the API key. [inferred]
- **Jira email.** Jira Cloud's account email still comes from `JIRA_EMAIL`. [inferred]
- **Precedence.** An environment variable always wins over the token command. [inferred]
- **Link prefix per forge**, each pinned to the head SHA [paraphrase]:
  - GitHub: `<owner>/<repo>/blob/<sha>/`;
  - GitLab: `<namespace path>/-/blob/<sha>/`, for a namespace of any depth;
  - Bitbucket Cloud: `<workspace>/<repo>/src/<sha>/`.
- **`pr view --json` and `pr list --json`** on the Bitbucket and GitLab stand-ins answer exactly the
  requested keys, with gh's meanings. [paraphrase]

## Edge Cases & Constraints

- **Token command output.** The command may print a trailing newline, which is trimmed. Empty
  output, a non-zero exit, a missing executable or a timeout each count as "no credential".
  [inferred]
- **Interactive secret stores.** A store that would prompt in an unattended run hits the timeout;
  it never hangs. [inferred]
- **Secrets stay out of output.** Neither the command's stdout nor its stderr ever appears in
  flowctl output, receipts, logs or `.flow/` state. The resolved token joins the existing
  redaction set. [inferred]
- **No shell.** The command runs without one, so it behaves the same on every OS in the smoke
  matrix. [inferred]
- **Run cost.** The command runs at most once per flowctl process, and only when a request needs
  the credential. A sync of many requests pays for one secret-store read. [inferred]
- **Unrecognized remotes.** A remote whose forge or path can't be recognized gets plain paths, not
  links. A link that is wrong by construction is worse than no link. [inferred]

## Acceptance Criteria

- **R1:** When a tracker's credential environment variable is unset, flowctl obtains the
  credential by running the configured token command and using its trimmed stdout. An environment
  variable always wins. The command runs as argv without a shell, at most once per flowctl process
  and only for a request that needs the credential, with a 10-second timeout like the existing
  glab read. Its output is never written anywhere. [inferred] [strategy:Tracker determinism]
  Errors: the existing missing-credential failure, with the cause added, for each of:
  - a non-zero exit;
  - a timeout;
  - a missing executable;
  - empty output.

  The failure message contains no fragment of the command's output.
- **R2:** When land finds a red build's cause, but the only change that would turn it green removes
  or weakens what the pull request is for (for example, deleting the failing test), land makes no
  commit and stops `BLOCKED`, naming the check and that reason. Land's shared workflow states this
  once. The Bitbucket reference's `NEEDS_HUMAN` stays for a cause that cannot be found.
  [paraphrase]
  Errors: no error surface beyond the existing `BLOCKED` stop.
- **R3:** File links in a make-pr briefing open the file at the reviewed head on the hosting forge:
  - GitHub;
  - GitLab, including projects in nested groups;
  - Bitbucket Cloud. [paraphrase]

  Errors: an origin remote whose forge or path is not recognized yields plain paths and no links.
- **R4:** Land's Bitbucket and GitLab references name the full path `.selected.pr.open.readiness`
  wherever they describe reading readiness. [paraphrase]
  Errors: no error surface beyond documentation wording.
- **R5:** Both stand-ins for `gh` (Bitbucket and GitLab), for `pr view --json <keys>` and
  `pr list --json <keys>`, return exactly the requested keys. That includes `isDraft` and `body`,
  with gh's meanings, taken from the listing each read already fetches, with no extra API call.
  [paraphrase]
  Errors: a key the stand-in cannot answer exits non-zero naming it, never a silent omission or
  substitution.
- **R6:** make-pr's aid guidance says, in one sentence, that the diff at the head is the source for
  what the code does. A task summary records what that task did at its commit; where the two
  disagree, the briefing follows the head. [inferred]
  Errors: none; guidance only.
- **R7:** make-pr may append the trailer lines the repository's own instructions require to the
  freshly rendered body, before the `Ref` line, and nothing else. [inferred]
  Errors: no error surface beyond the existing body write.

## Boundaries

- **No MCP route.** Routine tracker operations (push, pull, status with merge evidence, comments,
  relations, `list-open`, land's move to Done) are not routed through an MCP server. flowctl cannot
  call MCP tools, and unattended runs have none. [inferred] [strategy:Tracker determinism]
- **No stored secrets.** flow-next adds no keyring and stores no secret. The token command
  delegates to the store the team already uses. [inferred]
- **No email config key.** The Jira email is per developer, and `.flow/config.json` is committed.
  [inferred]
- **No merge checks.** Bitbucket merge checks are out of scope: the feature is Premium-only, and
  the reporter could not test it. [paraphrase]
- **No footer knob.** There's no config key for the PR footer; the repository's own instructions
  name it. [inferred]
- **No per-claim check pass.** make-pr gets no per-claim check pass and no staleness label in the
  briefing. [inferred]

## Decision Context

- **MCP isn't a substitute for a token.** An instruction to "use Rovo/MCP" was rejected. MCP tools
  exist only in the host agent's session, and Linear's MCP route already covers just discovery and
  one create before handing off to flowctl's key. Headless `flow --auto`, `--from-issue`, backlog
  mode and land's post-merge Done have no MCP connection. [inferred]
- **Token command in config, not an env var.** A per-developer environment variable would recreate
  the setup step the report complains about. [inferred]
- **Footer as one rule, not a key.** A config key like `CLOSE_COMMIT_MESSAGE` for the body would
  work, but one rule covers it with no new knob. make-pr already appends lines after the rendered
  body. [inferred]
- **Stale claims: guidance, not a check pass.** Flagging a claim whenever a file it mentions
  changed after the task's evidence commit was the reporter's suggestion, and so was a per-claim
  host check. Both would add work to every PR, written from one case. One guidance sentence keeps
  make-pr's wall clock unchanged; measure it with the existing make-pr body study, not a unit
  test. [inferred]

## Strategy Alignment

- **R1 serves Tracker determinism.** Routine tracker writes stay in flowctl's tested REST
  transport instead of moving to agent-run MCP calls. The zero-dependency contract holds, because
  the token command is the team's own tool. [strategy:Tracker determinism]
- **R1's no-shell rule serves the smoke OS matrix** (Key metrics). R3 and R5 are forge parity,
  which no track names. [inferred]

## Parked unknowns

- **Listing fields.** Whether Bitbucket's pull-request listing carries `description` and `draft`
  without a second request. If it doesn't, the plan decides between one request with a field
  selector and dropping the key with a named error.
- **Email default.** Whether teams want a Jira email default anywhere other than `JIRA_EMAIL`.
  The reporter's team would settle it.
