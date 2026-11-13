# Bitbucket Cloud forge adapter and make-pr over Bitbucket pull requests

> **Captured 2026-11-13** from GitHub issue #602 (filed by @benjamin-benz-42, who offered to implement and to test against a real Bitbucket Cloud + Jira setup). The maintainer builds it, following the GitLab path (fn-73, fn-316, fn-317); the issue author tests and contributes. First of three Bitbucket specs: this one (adapter, make-pr, and `flow --auto` up to an open PR), then resolve-pr over Bitbucket PR comments, then land and merge evidence.

## Goal & Context
<!-- Source: 10% user / 60% [paraphrase] / 30% [inferred] -->

A repository hosted on Bitbucket Cloud cannot run `flow --auto` at all today. No forge adapter claims `bitbucket.org`, so the PR read falls through to the GitHub adapter, `gh pr list` fails, and the route judge stops on `pr_probe_failed` before the first stage. Everything after that (make-pr, resolve-pr, land) calls `gh` or `glab` directly. Bitbucket Cloud plus Jira is a common pairing in Atlassian shops.

fn-73 laid the forge seam for exactly this: "A later forge (Bitbucket Cloud, Bitbucket Data Center) adds one adapter and one reference per skill and changes no flowctl caller." This spec adds the Bitbucket Cloud adapter and make-pr's Bitbucket reference, so `flow --auto` on a Bitbucket origin ends at an open pull request.

## Architecture & Data Models

- **Same seam as GitLab.** Bitbucket is one more entry in fn-73's internal adapter registry, and one more `forge-bitbucket.md` reference beside make-pr, loaded by forge name. No flowctl caller branches on the forge. [paraphrase]
- **flowctl answers questions; skills act.** The adapter owns deterministic reads; creating and updating the PR stays with the agent, using Bitbucket's CLI as make-pr's reference describes. [paraphrase]
- **`bkt` is Bitbucket's CLI.** Bitbucket has no first-party CLI comparable to `gh` or `glab`; `bkt` (avivsinai/bitbucket-cli) is gh-shaped, emits JSON, and holds the user's login, so flow-next never handles a Bitbucket token. Reads it has no command for (PRs by source branch) go through its authenticated API passthrough. [paraphrase]
- **The forge rule for Bitbucket Cloud is the host alone.** `bitbucket.org`, its SSH clone host `ssh.bitbucket.org` (measured 2026-11-13: the clone link Bitbucket returns for a new repository), and its SSH-over-443 host `altssh.bitbucket.org` name Bitbucket; no CLI login probe is needed to recognise it. The shell copy of the forge rule in make-pr's preflight gets the same arm, kept equal to the Python rule by the existing parity test. [inferred]
- **The shared row** is fn-73's: `number`, `url`, `state` (`OPEN` / `CLOSED` / `MERGED`), `headRefName`, `headRefOid`, `mergedAt`, `isDraft`, plus `baseRefName` where make-pr needs it. Bitbucket maps into it: `id`, the PR's HTML link, `OPEN`, `MERGED`, `DECLINED` and `SUPERSEDED` to `CLOSED`, source branch name, the full head commit, the merge time, the draft flag, and destination branch name. [paraphrase]

## API Contracts

- Internal only. `flowctl pilot snapshot`'s existing `forge` field reports `bitbucket` on a Bitbucket Cloud origin. No other output shape changes. [inferred]
- Commands recorded live before relying (R6): PR list by source branch (all states and open, with pagination), single PR view, PR create (draft and ready), PR update (description, title, draft to ready), the answer for a branch Bitbucket cannot see yet, and `bkt`'s answer when logged out. [inferred]

## Edge Cases & Constraints

- Bitbucket returns a short source commit hash (measured 2026-11-13: 12 characters in listings). A branch's own PR rows carry the full SHA, resolved from the local clone first and Bitbucket's commit read otherwise, and a hash that cannot be resolved is a probe failure. The open listing, which only names branches, carries the short hash Bitbucket reports, so it costs no commit reads. [paraphrase]
- Bitbucket has no usable merge timestamp on the PR (measured 2026-11-13: listings carry no `closed_on`, and a single read of a merged PR leaves it out; only the merge call's own answer had it), and the issue reports that `updated_on` moves with later comments; `mergedAt` comes from the `MERGED` update in the PR's activity, never `updated_on`. [paraphrase]
- PRs from forks can share the branch name; only PRs whose source repository is the origin repository count, as on GitLab. [inferred]
- Bitbucket pages its listings; a listing that cannot prove it is complete is a probe failure, never "no PR". [inferred]
- **`bkt api` needs a target beyond the login (measured 2026-11-13, bkt 0.38.1).** With a keyring login and no active `bkt` context, `bkt api` fails with "no active context"; `BKT_HOST` alone fails with "BKT_HOST is set but BKT_TOKEN is not". The login's host key is `https://api.bitbucket.org/2.0`, not `bitbucket.org`. `--workspace`/`--repo` do not help (measured: still "no active context"). Each read therefore picks a context whose host is `api.bitbucket.org` from `bkt context list --json`, the active one first, and names it with `--context`, so the user's active context may point anywhere. No Cloud context, or a `bkt` that refuses the call, is a probe failure; make-pr then stops naming the login and the context commands. [inferred]
- A missing or logged-out `bkt` on a Bitbucket origin stops make-pr before any close or push, naming the `bkt auth login` command. [inferred]
- **A create on a branch that already has an open PR does not fail (measured 2026-11-13).** Bitbucket answers it with the existing PR, its title and description overwritten. make-pr's existing-PR check before create is what keeps a second create from clobbering an open PR. [inferred]
- Bitbucket's answer for a branch it cannot see yet is `400 Bad Request: source: branch not found: <branch>` (measured 2026-11-13); make-pr retries on exactly that answer for the pushed branch. [inferred]
- Until the resolve-pr and land specs ship, resolve-pr, land and `flow --auto --until=merge` on a Bitbucket origin stop with `NEEDS_HUMAN` instead of running GitHub commands against a Bitbucket PR; `--until=merge` stops after make-pr with the PR URL. [inferred]
- A self-hosted Bitbucket (Data Center) host is not recognised and keeps today's unknown-host behaviour. The adapter does not assume `bitbucket.org` beyond the forge rule, so a later Data Center adapter is not precluded. [paraphrase]

## Acceptance Criteria

- **R1:** The forge comes from the origin remote's host, with no config key: an HTTPS or SSH origin on `bitbucket.org`, `ssh.bitbucket.org` or `altssh.bitbucket.org` (including an SSH alias resolving to one of them) is `bitbucket`, and `flowctl pilot snapshot` reports `forge: "bitbucket"`. [paraphrase] Errors: no origin remote, an unknown self-hosted host (unchanged behaviour), `bkt` absent (the forge is still recognised; reads then fail as probe failures).
- **R2:** The route judge and the pilot snapshot (open listing and per-branch history) read Bitbucket PRs through the adapter as the shared row, so `flow --auto` on a Bitbucket origin gets past the first tick and its make-pr verify reads the same answer. [paraphrase] Errors: `bkt` missing, logged out or failing, malformed rows, an unresolvable short hash, and a listing that may be truncated are each a probe failure, never "no PR".
- **R3:** On a Bitbucket origin, make-pr opens or updates a pull request with the same rendered body and close behaviour it uses on GitHub, honouring `--draft`, `--ready` and `--update`. [paraphrase] Errors: `bkt` absent or logged out (stops before close), an existing open PR without `--update`, an existing-PR or parent read that fails (stops before close, never read as "no PR"), a just-pushed branch Bitbucket cannot see yet (retried on Bitbucket's exact answer).
- **R4:** On a Bitbucket origin, a spec that depends on another spec's branch gets the base selection make-pr applies on GitHub and GitLab: the parent branch while the parent's PR is open, the default branch once it is merged. [inferred] Errors: the parent PR state unreadable (stops `NEEDS_HUMAN`, as on GitHub).
- **R5:** Behaviour on GitHub and GitLab origins is unchanged: the existing forge, make-pr, route, pilot and flow-auto tests whose subject is unchanged pass unmodified. [inferred] Errors: no new subprocess on the GitHub or GitLab path.
- **R6:** Each `bkt` command this spec relies on is first run against the live Bitbucket Cloud test workspace and its real output saved as a test fixture; tests with a stubbed `bkt` built from those fixtures cover R1–R4 in CI. [paraphrase] Errors: none beyond the fixtures being real output (recorded, not hand-written).

## Boundaries

- No new public flowctl verb and no config key; the forge stays derived from the origin remote. [paraphrase]
- No resolve-pr or land over Bitbucket PRs here; they are the next two specs. Tracker merge evidence on Bitbucket is the land spec's. [paraphrase]
- Bitbucket Cloud only; no Data Center adapter. [paraphrase]
- No Bitbucket Issues tracker (Atlassian removed Cloud Issues). [paraphrase]
- Spec approval through PR reviews stays GitHub-only, as on GitLab. [inferred]
- No `bkt auth status` probe to claim hosts; that only matters for self-hosted Data Center. [paraphrase]

## Strategy Alignment

- **Cross-platform parity** — extends code-hosting parity from GitHub and GitLab to Bitbucket Cloud. [strategy:Cross-platform parity]
- `bkt` is a runtime prerequisite only on a Bitbucket origin, as `glab` is on GitLab; flowctl core never imports it, so the zero-dependency base install holds. [inferred]

## Decision Context

### Motivation
Issue #602 shows a Bitbucket Cloud run cannot pass tick one, and a stand-in `gh` shim proved the rest of the loop works once PRs can be read. make-pr is the first blocker, so it ships first, on fn-73's seam. "we will build it, they can test and contribute" and "we build it according to our strategy etc while taking their stuff into account if it fits" set the ownership: the issue's proposal and measurements are inputs, adopted where they fit.

### Implementation Tradeoffs
- **`bkt` over `curl` against the REST API, Atlassian's beta `twg`, or flowctl performing writes.** `curl` puts long shell and token handling in every skill call; `twg` is beta with changing commands; flowctl writes would break fn-73's split between reads and agent actions. `bkt` keeps "the forge's own CLI" true and leaves auth to the user's login. [paraphrase]
- **Static host, not a CLI login probe (amended from the issue's proposal).** Bitbucket Cloud has one host, so the rule needs no subprocess. The issue's `bkt auth status` claim is only needed for self-hosted hosts, which are out of scope. [inferred]
- **Record before relying.** No `bkt` command has been run here; fixtures come from a live workspace first, as fn-73 R11 did for `glab`. The live target is a free Bitbucket Cloud workspace on the maintainer's Atlassian test account; the issue author tests the branch on their own Bitbucket Cloud + Jira setup. [paraphrase]
- **New dependency check.** `bkt` at capture time: MIT, v0.38.1 released 2026-11-09, frequent releases through October and November 2026, 261 stars, mostly one maintainer with outside contributors. Single-maintainer risk is accepted because reads use its API passthrough, which a later swap could replace without changing callers. [inferred]
