# Tracker rejections say why, and idea text reads clean

## Goal & Context

When Jira or GitLab rejects a request, flow-next reports `rejected (400)` and drops the tracker's own explanation. A person who names the wrong parent for a new issue, for example a story as the parent of a story, sees that an error happened and not which one. Jira's answer said exactly what was wrong, and it was thrown away. Parent issues at creation shipped in 9.13.0 with the promise that a rejected parent comes back as the tracker's own error, so this closes a gap in that release.

Separately, ideas read from Jira Product Discovery carry Jira's colour markup. The idea template wraps its placeholder prompts in colour tags, so every idea read includes `{color:#97a0af}` noise in the text an agent uses to judge whether the idea has real content.

The users are developers and product people who use flow-next with Jira or GitLab, and anyone who starts flow from a discovery idea.

<!-- Source: 60% user / 30% [paraphrase] / 10% [inferred] -->

## Architecture & Data Models

**Rejection reason.** The tracker package classifies every HTTP answer in one place. A client-error answer that is no special case becomes an invalid-input error whose message holds the status only. Linear already carries the provider's text there, redacted and bounded. Jira and GitLab get the same treatment: the classifier reads the reason from the response body and appends it after the status. The error's class and subtype do not change, so every caller that branches on them behaves as before.

Jira puts its reasons in `errorMessages` (a list of strings) and `errors` (a map from field name to text). GitLab puts them in `message` or `error`, each of which can be a string, a list or a map of lists.

**Idea text.** The idea read is the one place the cleanup applies. Ideas are never written back, so removing colour tags there cannot lose anything. The ordinary issue read and every write are left alone, because a linked issue's body is read, merged and pushed back, and stripping markup on read would remove a person's formatting from the tracker on the next push.

<!-- Source: 20% user / 20% [paraphrase] / 60% [inferred] -->

## API Contracts

The message keeps its current start, so anything that matches on the status keeps working:

```text
rejected (400): parent: Please select valid parent issue.; parentId: Please select valid parent issue.
rejected (400): title is missing
rejected (400)
```

The first line is what Jira Cloud answered on 2026-11-18 for a story given as the parent of a story: two `errors` entries, each rendered as `field: text` and joined with `; `. An `errorMessages` entry is rendered as its text alone, before the field entries. The second line is a GitLab `error` string. The third is today's message, kept when the body holds no reason. The reason is redacted the way Linear's provider text already is, because a tracker can echo a credential back, and it is cut to the same length bound.

The idea read returns `text` for a body or comment that held `{color:#97a0af}text{color}`.

<!-- Source: 10% user / 20% [paraphrase] / 70% [inferred] -->

## Edge Cases & Constraints

- **No reason in the body.** An empty body, a body that is not JSON, a JSON value that is not an object, or an object without the reason fields gives today's message unchanged.
- **Special cases keep their own messages.** Authentication and permission answers, not-found, rate limiting, Jira's missing-token 404 and GitLab's licence 403 are classified as today.
- **Callers that read the message.** The GitHub single-parent path looks for the status code in the message. GitHub's messages do not change in this spec, and the status stays in the same position for the trackers that do change.
- **Untrusted text.** The reason is provider text. It is redacted and bounded before it becomes a message, and it never widens what the envelope prints beyond that message.
- **Unbalanced colour tags.** An opening tag with no closing tag, or the reverse, is removed and the surrounding text kept.
- **Colour tags outside the idea read.** The ordinary issue read returns them as today.

<!-- Source: 10% user / 20% [paraphrase] / 70% [inferred] -->

## Acceptance Criteria

- **R1:** On Jira, a rejected request's error message carries Jira's own reasons after the status, taken from `errorMessages` and from `errors` as `field: text`, redacted and bounded. The error's class and subtype are the ones 9.13.0 returns. Errors: a body with no reason, an unparseable body or a non-object body gives the 9.13.0 message unchanged. [paraphrase]
- **R2:** On GitLab, a rejected request's error message carries GitLab's own reason after the status, taken from `message` or `error` whether each is a string, a list or a map of lists, redacted and bounded, with class and subtype unchanged. Errors: as R1. [inferred]
- **R3:** Every other classification is unchanged: authentication and permission answers, not-found, rate limiting, server errors, Jira's missing-token 404, GitLab's licence 403, and all Linear and GitHub classifications. No error surface. [inferred]
- **R4:** A message that gains a reason still starts with `rejected (<status>)`, so a caller that matches on the status behaves as in 9.13.0. No error surface. [inferred]
- **R5:** `flowctl tracker idea read` returns an idea's body and comments with Jira colour tags removed and their inner text kept. The ordinary issue read and every write are byte-identical to 9.13.0 for the same input. Errors: an unbalanced tag is removed and the text kept. [paraphrase]
- **R6:** No always-loaded skill file changes. No error surface. [inferred]

Tests assert class and subtype exactly as existing tests do, and add cases for each reason shape, the no-reason fallbacks, redaction of an echoed credential, and the colour cases (G2). A test that pinned the bare message for a Jira or GitLab rejection is updated to the new message; no other existing assertion changes. A live check before release creates an issue under a wrong-level parent on Jira Cloud and shows Jira's reason in the message, shows a GitLab rejection's reason the same way, and reads a template idea with no colour tags in the output. The maintainer's test sites and credential lookups are in the gitignored notes file `.flow/tmp/tracker-live-checks.md`. Docs updated in the same change: the changelog under Unreleased, and the tracker-sync reference where it describes what a rejected parent returns. [inferred]

## Boundaries

- No change to GitHub's or Linear's error messages. [inferred]
- No reason added to authentication, not-found or rate-limit errors. [inferred]
- No removal of colour or any other markup from linked issue bodies or comments, on read or on write. [inferred]
- No change to how idea content is judged. An idea that holds only its template's prompt text is still the "no requirement text" case the idea reference describes. [inferred]

## Decision Context

The reason is appended to the existing message instead of replacing it, because one caller already matches on the status inside the message, and because a status with a reason reads better than either alone.

Colour is removed only where the text is read and never written back. The Jira adapter converts bodies between Markdown and wiki markup in both directions for linked issues, and a tag it does not model passes through unchanged today, which is what keeps a person's formatting intact across a push. Cleaning the idea read gets the benefit with none of that risk.

GitLab is included with Jira because 9.13.0 makes the same promise for a rejected epic as for a rejected Jira parent. GitHub is left out because nothing shipped there depends on it.

<!-- Source: 10% user / 20% [paraphrase] / 70% [inferred] -->

## Strategy Alignment

- Tracker determinism: turning a tracker's answer into a readable, bounded, redacted message is mechanical and belongs in the tracker package's one classifier. [strategy:Tracker determinism]
