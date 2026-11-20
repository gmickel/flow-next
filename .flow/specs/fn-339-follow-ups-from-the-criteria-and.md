# Follow-ups from the criteria and command-backend work

## Goal & Context

<!-- Source: 10% user / 60% [paraphrase] / 30% [inferred] -->

Building fn-336 (#619) and fn-337 (#592) turned up five small things that were listed as follow-ups and not built. This spec keeps them so they are not lost. Four are small fixes; one is a check that could not run. A sixth item, a narrower whole-branch review lens, is parked here because it needs its own measured round.

The unattended failure the first two prevent: a review that silently judges no standing criteria, or records none, while everything looks green.

## Edge Cases & Constraints

- A criteria file with only headings, prose or commented examples legitimately holds zero criteria and stays valid; only the link-as-file shape is an error. [inferred]
- The parser fix must not change what a receipt records for output that already parses. [inferred]
- Killing a process tree differs by platform; the fix holds on Linux, macOS and Windows or says where it does not. [inferred]

## Acceptance Criteria

- **R1:** A `.flow/criteria.md` that git's index records as a symbolic link, but that this checkout wrote as a plain file still holding the link's target path (what git does on a checkout without symlink support), fails the review closed with a message that says so, the way a broken link already does. The link is detected from the index, never from the file's text. [paraphrase]
  Errors: a regular file with zero criteria stays valid and silent, as today, whatever it holds (headings, prose, commented examples, or text that looks like a path), and so does a link's placeholder once real content replaces it.
- **R2:** The receipt keeps a review's per-criterion section when a tally line follows it directly. The defect is reproduced from the reviewer output that showed it before it is fixed, and a regression test covers it. [paraphrase]
  Errors: if it no longer reproduces on current main, record that and change nothing.
- **R3:** When a command review backend times out, its whole process tree is stopped, not only the direct child, so a wrapper's CLI does not keep running. [paraphrase]
  Errors: a tree that cannot be stopped is reported in the failure reason; the round is still refunded.
- **R4:** Setting `review.backend` to a bare `command` with no label is refused when it is set, naming the `command:<label>` form, instead of failing later at review time. [paraphrase]
  Errors: `command:<label>` with a label that is not configured yet is still accepted at set time, since the entry may be added afterwards. [inferred]
- **R5:** The copilot backend's outside-repository read check from fn-336 is run once its quota allows, and the teams guide's backend list is updated from unchecked to the observed result. [paraphrase]
  Errors: if it still cannot be exercised, the docs keep saying unchecked.
- **R6:** A command review backend's error for a program that cannot be found names the variable and the label and does not print the program path or any other part of the variable's value. [paraphrase]
  Errors: no error surface beyond the message itself.
- **R7:** In a fan-out whose draws use different command labels, the validate and deep passes continue on a session of the label that ran the primary draw, never on another label's session. [paraphrase]
  Errors: no session for the primary draw's label → the validate and deep passes do not run, as on every backend when there is no session to resume.
- **R8:** The runtime and the config schema accept exactly the same backend strings around whitespace: `command: grok` is refused by both. [paraphrase]
  Errors: no error surface beyond the refusal.
- **R9:** On a host that reads `AGENTS.md` (Muse, Antigravity), re-running setup with a saved "CLAUDE.md only" answer still writes the snippet where that host reads it, or says plainly that the host will not see it. [paraphrase]
  Errors: a host that reads `CLAUDE.md` is unchanged.
- **R10:** When memory is enabled but not initialized, plan's memory scan says so in one plain line instead of printing that the scan failed. [paraphrase]
  Errors: a real scan failure still reports as a failure.

## Boundaries

- No review rubric change. [inferred]
- No change to the other CLI backends' timeout handling; they kill only the direct child today and that is left as it is. [inferred]
- No `criteria.include` list or user-level criteria layer. [paraphrase]

## Decision Context

One small spec instead of separate issues: the items are each a few lines and share the same few areas. They were found while building and auditing 9.17.0 and the Antigravity host, and the maintainer's rule is that the next release waits until found things that need fixing are fixed, so this spec ships before it. R6 to R8 come from the 9.17.0 final audit's minor findings; R9 and R10 were found while building the Antigravity host.

## Parked unknowns

- A narrower whole-branch lens for the completion review, limited to the diff the reviewer already reads. The tested lens caught cross-task duplication 3 of 3 against 0 of 3 but cost 1.30 times the tokens against a 1.20 bar. Resolved by its own pre-registered round; not part of this spec's build.
