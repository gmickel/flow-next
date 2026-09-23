# Jira bodies render as written: Markdown to wiki markup on the v2 wire

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 80% [paraphrase] (GitHub issue #465, reporter @flecamos), 20% [inferred] -->

Every spec pushed to Jira through tracker-sync renders wrong. flowctl writes spec and comment bodies as Markdown into Jira REST v2 text fields. Those fields never interpret Markdown. Under the Wiki Style Renderer the string is parsed as wiki markup, so `#` becomes a numbered list, `##` a nested one, and `**bold**` a stray asterisk plus bold. Under the Default Text Renderer the raw `##` and `**` show literally. No field configuration displays the current write correctly.

The failure is silent. The envelope reports `success: true`, no capability is reported as degraded, and the existing body-fidelity check passes. That check compares stored bytes, and stored bytes do round-trip exactly. What is wrong is the rendered result, which only shows in a browser.

The Jira transport doc makes the wrong assumption explicit: it states the body form for Cloud and Data Center as "normalized to Markdown", and it justifies API version 2 with the byte-exact round trip. The byte measurement is correct. The conclusion drawn from it is not.

The fix keeps REST v2 and converts in the Jira provider: Markdown to Jira wiki markup on every write, and wiki markup back to Markdown on every read, so flow-side comparisons keep working in Markdown.

## Architecture & Data Models
<!-- scope: technical -->

- A pair of pure, deterministic, standard-library-only text transforms in the Jira provider: Markdown to wiki markup, and wiki markup back to Markdown. They make no I/O and no model calls, hold no state, and need no configuration. [paraphrase]
- **Write boundary.** Every Jira body write converts just before the wire: issue create (in the lifecycle create path, whose acknowledged `bodyWritten` seeds the merge base), issue update, and comment add and update. Callers above the wire keep handing over Markdown. [paraphrase]
- **Read boundary: decode exactly once.** Jira description and comment bodies are decoded to Markdown at the single point where the provider extracts them from a read. Every consumer then sees Markdown: normalized reads, the echo fence, `trackerBodyForMerge`, pull, reconcile, and comment dedup, including the PR-link comment fallback. Raw payloads are not re-decoded further up. [inferred]
- **Merge bases.** The fn-140 paired-base contract is unchanged: `mergeBaseFlow` is the exact local body, and `mergeBaseTracker` is the decoded server readback. The two forms may differ, so stable canonical Markdown is enough; the source Markdown spelling does not need to survive. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- **Construct subset.** ATX headings, bold, italic, inline code, links, fenced code blocks, simple pipe tables, blockquotes, and nested bullet and numbered lists: the constructs flow-next specs actually use. Checklist markers (`[ ]`, `[x]`) stay literal inside list items. This is a bounded subset, not full Markdown grammar. [inferred]
- **Literal preservation.** Unicode (umlauts included), code-span and fenced-block content, wiki-special characters in prose (escaped on write), and syntax outside the subset are all preserved as literal text, locally, without disabling conversion of the rest of the body. Wiki fragments the encoder never emits (for example macros a Jira user added) decode unchanged. [inferred]
- **Sync markers.** The `<!-- flow-next:sync ... -->` and chart-rollup markers pass through both directions byte-exact. Wiki markup has no comment syntax, so the marker stays visible in Jira, as it is today. [inferred]
- **Already-linked issues.** Issues pushed before this change hold raw Markdown, and their tracker merge base is raw Markdown. Decoding that body as wiki markup can differ from the base (a `#` heading reads as a list), so the echo fence would see a remote edit that never happened. [inferred]
- **Renderer prerequisite.** Correct display requires the Wiki Style Renderer on the field. The Default Text Renderer shows the markup literally. This is documented, not detected. [inferred]
- **Deployment shapes.** Cloud and Data Center/Server both use v2 and wiki markup, so one converter serves both, given the renderer prerequisite. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Every Jira body write (issue create, issue update, comment add and update) converts Markdown to wiki markup over the construct subset. Issue #465's fixture stores as `h1. Branch deployment build-time optimizations`, `h2. Goal & Context` and `*a unit the change did not touch takes a published artifact.*`. Tests assert the stored wire form, not a byte round trip. [paraphrase] Errors: syntax outside the subset, and literal wiki-special characters, are preserved locally as literal text; an unexpected converter failure surfaces through the existing structured error boundary and never sends the unconverted body silently.
- **R2:** Jira description and comment reads are decoded once, at extraction, into stable canonical Markdown that preserves content and formatting semantics for every construct R1 emits. A fixture per construct, plus non-ASCII text, shows encode then decode yields equivalent canonical Markdown. [paraphrase] Errors: unknown wiki fragments pass through unchanged, locally.
- **R3:** A push followed at once by a reconcile, with no edit on either side, reports no divergence and no conflict. A genuine Jira-side edit is still detected. Sync markers and comment dedup, including the PR-link comment fallback, still match exactly. [inferred] Errors: no error surface beyond the existing reconcile conflict contract.
- **R4:** For an issue linked before this change, push and reconcile compare the raw current body against the recorded tracker base first, using existing normalization. Only a proven-unchanged body is converted automatically: the write bypasses no-op suppression when conversion changes the wire body, and the paired bases commit through the existing write and readback handling. Any other difference takes the normal edit or conflict path. Pull must not erase that evidence: when raw/base equality proves an unchanged legacy body and decoding would change it, pull returns a structured conflict asking for push or reconcile first, replacing neither base and writing nothing to Jira. Tests cover pull-before-conversion, then a successful push or reconcile. [inferred] Errors: no error surface beyond the existing transaction and conflict contracts.
- **R5:** The create path's acknowledged body, the readback and every comparison use the same representation, so a freshly created issue's merge base matches its next read without a false diff. [inferred] Errors: no error surface beyond R3.
- **R6:** The Jira transport doc stops claiming Markdown normalization. It says bodies are converted to wiki markup on write and decoded on read, that correct rendering requires the Wiki Style Renderer (the Default Text Renderer shows markup literally), and that v2 is kept with this conversion, not because of the byte round trip. `CHANGELOG.md` credits @flecamos for the report and references #465. [paraphrase] Errors: no error surface beyond doc and test drift checks.
- **R7:** The transforms use only the Python standard library and add no HTTP request, subprocess or model call to any sync operation. The cost is negligible next to a Jira round trip; no benchmark is needed. [paraphrase] Errors: no error surface beyond R1/R2.

## Boundaries
<!-- scope: business -->

- Moving Jira to REST v3 and ADF is out of scope; v2 stays the resolved API version. [paraphrase]
- Hiding sync markers in the rendered Jira view is out of scope. [inferred]
- Detecting the field renderer or reporting it as a capability is out of scope; the prerequisite is documented (R6). [inferred]
- Changing how GitHub, GitLab or Linear bodies are written is out of scope. [inferred]
- Round-tripping arbitrary wiki macros that humans add in Jira is out of scope beyond preserving them as literal text (R2). [inferred]

## Decision Context
<!-- scope: both — conditionally substructured -->

Three directions were weighed ([paraphrase], from issue #465 and the triage discussion). Converting on v2 was chosen. It fixes rendering, keeps the recorded v2 decision, and is a contained, deterministic transform, which fits the tracker-determinism rule that plumbing lives in `flowctl_tracker/` and judgment stays in the host [strategy:Tracker determinism]. Moving to v3 and ADF was rejected: Data Center has no ADF, so it would still need a wiki converter there, which is more work for the same result. Documenting only and flagging the capability as degraded was rejected because issues would stay unreadable. Renderer detection with a degraded-capability flag was also dropped after review: it diagnoses configuration without changing the write, and adds probes and state that can go stale. The prerequisite is documented instead.

## Strategy Alignment

- **Tracker determinism** — the fix is deterministic provider plumbing in the tracker package with no host judgment added, the pattern that track records. [strategy:Tracker determinism]
