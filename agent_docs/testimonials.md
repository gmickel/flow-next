# Testimonials manifest (canonical, verified)

Canonical source for every testimonial / adopter quote that ships on any flow-next property (README, flow-next.dev, mickel.tech). Produced by fn-117.1 (R5 substrate). Rules, binding on all workstreams (fn-117 hard boundaries):

- Every published quote MUST link to a resolving public source. No unlinked quotes. No paraphrases.
- Quotes ship verbatim, including the author's own punctuation (third-party text is never restyled).
- Entries in the EXCLUDED section MUST NOT ship (linked or unlinked) until a real source URL is recovered and recorded here.
- Re-verify URLs at ship time for each property task; update the verified-date column when you do.

## Boundary gates (run before shipping any property copy)

Both gates are in the fn-117 spec Quick commands. Both MUST produce no output (grep exit 1 = clean).

```bash
# 1. PSVI / Velocity Index vocabulary (patent-pending, vault-private):
grep -ri "PSVI\|Velocity Index" ~/work/flow-next.dev/src ~/work/mickel.tech/app/apps/flow-next README.md plugins/flow-next/docs/

# 2. Client names (pattern list is PRIVATE, kept out of this public repo at ~/.claude/flow-next-client-names.txt):
grep -riwf ~/.claude/flow-next-client-names.txt ~/work/flow-next.dev/src ~/work/mickel.tech/app/apps/flow-next README.md plugins/flow-next/docs/
```

Gate log:

| Date | Gate | Result |
|---|---|---|
| 2026-07-19 | PSVI/Velocity Index | clean (no matches, exit 1) |
| 2026-07-19 | client names (6-name private list) | clean (no matches, exit 1) |

The client-name list deliberately lives outside this repo: embedding the names in a committed grep would itself leak them. Maintainer extends the private file as coaching engagements accrue; the gate command never changes.

## Verified pool (GitHub, link-backed) - ACTIVE proof set for R5

All URLs verified resolving 2026-07-19 via `gh issue view` / `gh api` (public, no auth edge cases).

### 1. Claire Novotny - LEAD quote (substantive adoption evidence)

- **Author:** Claire Novotny (GitHub `clairernovotny`; .NET Foundation / former Microsoft)
- **Source:** issue [#111 "Reduce Ralph review churn with task quality proof packets"](https://github.com/gmickel/flow-next/issues/111)
- **Context:** data-driven writeup of two ~18-hour production Ralph runs (35 iterations, real repo), arguing for keeping the review loop because it is the quality mechanism. This is adoption proof of the strongest kind: an experienced engineer instrumenting flow-next on real work.
- **Verbatim quotables:**
  - "Recent Ralph runs show that the expensive loop is also the reason output quality is high"
  - "The observed high-value review findings were mostly not cosmetic. They caught false confidence"
  - "This should not make hard tasks cheap. The expensive loop remains because it is the quality mechanism."
- **Verified:** 2026-07-19, gh issue view.

### 2. Patrick Michalina

- **Author:** GitHub `patrickmichalina`
- **Source:** [comment on issue #5](https://github.com/gmickel/flow-next/issues/5#issuecomment-3734228766)
- **Verbatim quote:** "I am enjoying your version of all these cool new plugins. So far yours has worked the best."
- **Verified:** 2026-07-19, gh api (comment html_url resolves).

### 3. possibilities (external contributor)

- **Author:** GitHub `possibilities`
- **Source:** PR [#95 "fix(flow-next): check depends_on_epics in cmd_ready"](https://github.com/gmickel/flow-next/pull/95)
- **Verbatim quote:** "Hello, really enjoying this project, thanks for making it and making it public (also huge compliments on your website!)"
- **Context bonus:** an external contributor shipping a correct kernel patch is itself adoption proof (uses flowctl CLI directly, outside Ralph).
- **Verified:** 2026-07-19, gh pr view.

### 4. raydocs

- **Author:** GitHub `raydocs`
- **Source:** issue [#4](https://github.com/gmickel/flow-next/issues/4)
- **Verbatim quote:** "thanks for building and open-sourcing **gmickel-claude-marketplace** — it’s been really useful in my workflow."
- **Note:** quote predates the repo rename; fine to ship with a "[flow-next]" editorial bracket or use the fragment "it’s been really useful in my workflow."
- **Verified:** 2026-07-19, gh issue view.

### 5. Rytis-J

- **Author:** GitHub `Rytis-J`
- **Source:** issue [#54 "Keeping track with the updates"](https://github.com/gmickel/flow-next/issues/54)
- **Verbatim quote (fragment):** "this project is well maintained and often updated"
- **Note:** weakest of the pool (praise is incidental to an update-lag question). Use only in aggregate strips, not as a standalone capsule.
- **Verified:** 2026-07-19, gh issue view.

### 6. awesome-list feature

- **Author:** GitHub `ithiria894`
- **Source:** issue [#96 "Featured in awesome-claude-code-workflows"](https://github.com/gmickel/flow-next/issues/96); listing confirmed live in [awesome-claude-code-workflows README](https://github.com/ithiria894/awesome-claude-code-workflows) (entry present, cites "Plan-first workflows (Flow-Next), Ralph autonomous mode ... receipt-based gating")
- **Use:** the "Mentioned in awesome" badge (issue includes the badge snippet). NOTE for fn-117.2: the listing links the old repo name `gmickel/gmickel-claude-marketplace`; consider a listing-correction PR upstream.
- **Verified:** 2026-07-19, gh issue view + raw README fetch.

## X/Twitter set (mickel.tech d7a4024) - EXCLUDED pending manual link recovery

The fn-117 spec assumed commit d7a4024 in mickel.tech held the original testimonials with correct status URLs. Recovery was performed and the array extracted, but verification shows **the status ids in d7a4024 are fabricated** (most likely hallucinated when the page was authored). Evidence, method per step:

1. **Snowflake decode:** all 7 status ids decode to 2025-01-17 .. 2025-02-12. The flow-next repo's first commit is 2025-12-26. Tweets praising flow-next ~10 months before it existed are impossible.
2. **Duplicate id:** two different entries (Lat3ntG3nius and 010110O0) carry the SAME status id `1882438011868553581`.
3. **Live check (2026-07-19, agent-browser, logged out):** all 7 status URLs render "Post Not Found - X | 404 Error"; control tweet `x.com/jack/status/20` renders normally, so logged-out 404 is meaningful.
4. **Handle check (same method):** 6 of 7 handles are real accounts with display names matching the array (Claire Novotny, Baran Güneysel, Tiago Freitas in founder mode, Ben, Mark Feighery, dailyreader). `Lat3ntG3nius` no longer exists (renamed or deleted).
5. **Mechanical recovery exhausted:** publish.twitter.com oEmbed and the syndication CDN endpoint are both dead (404) as of 2026-07; X search requires login; automated logged-in X access is off-limits (account-suspension risk per house policy); exact-quote web search does not surface the posts (X is no longer indexed usefully).

**Conclusion:** the people are real and the quotes are very likely real (they long predate this manifest and matched live display names), but no entry has a resolving source URL. Under the linked-testimonials-only boundary, **none of these may ship** - not even unlinked - until a human manually recovers the real status URL (a few minutes of logged-in X search per author, e.g. `from:<handle> flow-next`). Real posts are probably from Jan-Feb 2026 (one year after the fabricated ids, shortly before the d7a4024 commit of 2026-02-12).

| Name | Handle | Handle live? | Verbatim quote (from d7a4024) | Fabricated URL | Exclusion reason |
|---|---|---|---|---|---|
| Claire Novotny | @clairernovotny | yes | "I've found it generating production-quality code. Far far better than any of the other tools I've tried so far." | x.com/clairernovotny/status/1886200988044026046 | status 404; id decodes 2025-02-02 (pre-product). Author separately verified via GitHub #111 (see pool entry 1) |
| David P | @Lat3ntG3nius | **no (account gone)** | "Cross-model review is genius because it exploits model diversity as a feature, not a bug. Different models make different mistakes, so using them as mutual reviewers creates a safety net that single-model workflows can't match." | x.com/Lat3ntG3nius/status/1882438011868553581 | status 404; id duplicated with @010110O0's entry; handle no longer exists - lowest recovery odds |
| Baran Güneysel | @chnoblist | yes | "As a designer, I always felt a gap between prototyping and delivering production-ready code, but flow-next bridges that gap and empowers me to ship with confidence." | x.com/chnoblist/status/1889599966391750888 | status 404; id decodes 2025-02-12 (pre-product) |
| Tiago Freitas | @tiagoefreitas | yes | "Flow-next is simply the best coding flow not even close, and still a side project!" | x.com/tiagoefreitas/status/1883665283568869572 | status 404; id decodes 2025-01-26 (pre-product) |
| Ben | @BuildItWithBen | yes | "RepoPrompt + flow-next combo has been a force multiplier for me. Keep the updates flowing!" | x.com/BuildItWithBen/status/1881534375655604424 | status 404; id decodes 2025-01-21 (pre-product) |
| Mark Feighery | @MarkFeighery1 | yes | "Ok never mind I used it all and it's brilliant." | x.com/MarkFeighery1/status/1880331261099487684 | status 404; id decodes 2025-01-17 (pre-product) |
| dailyreader | @010110O0 | yes | "Been running flow-next for the last week and boy am I happy!" | x.com/010110O0/status/1882438011868553581 | status 404; id is a duplicate of the Lat3ntG3nius entry |

**Re-inclusion procedure:** paste the real status URL into the row, verify it renders logged-out (agent-browser title shows author + text), move the entry into the verified pool with date + method. Do not relax the bar to profile URLs; a profile link does not source a quote.

## Consequences for downstream tasks (R5)

- **Active proof strategy: GitHub-pool-only** (spec early-proof-point fallback, triggered). fn-117.2 (README), .4 (flow-next.dev), .7 (mickel.tech) render from the verified pool above.
- **flow-next.dev homepage and mickel.tech currently ship the X quotes** with mangled handles / profile-only links (mickel.tech current page even paraphrases the quotes and invents handles like @ben, @mfeighery, @dailyreader). Tasks .3 and .7 must replace these using this manifest, not merely re-link them.
- If the maintainer manually recovers real status URLs before .2/.4/.7 ship, the X set upgrades to the verified pool and the lead capsule choice reopens (Tiago Freitas was the historical lead).
