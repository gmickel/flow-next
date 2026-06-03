---
title: Trackers auto-linkify issue-key substrings inside markers (even in HTML comments
date: "2026-06-03"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md
tags: [fn-52, tracker-sync, linear, marker, dedup, linkify, smoke-test]
problem_type: integration
symptoms: back-reference / dedup marker containing wor-N key comes back as <issue>…</issue> markup; literal match fails
root_cause: "Linear/GitHub auto-linkify issue-key substrings in body+comment markdown, even inside HTML comments"
resolution_type: fix
---

## Problem
Linear (verified live during the fn-52 tracker-sync smoke test) **auto-linkifies any tracker issue-key substring** (`WOR-17`, case-insensitive) that appears in issue/comment markdown — **even inside an HTML comment**. Pushing a back-reference marker `<!-- flow-next:spec wor-21-slug -->` to a tracker-first issue came back rewritten as `<!-- flow-next:spec <issue id="<uuid>" href=".../WOR-21">WOR-21</issue>-slug -->`. The literal marker is corrupted, so the dedup/back-reference exact-match (`spec=wor-21-slug`) fails. Flow-first markers (`fn-3-...`) are unaffected because `fn-N` is not a tracker key pattern. GitHub does the same with `#123` → `<a>#123</a>`.

## Solution
Two mitigations, both landed in `references/comments-sync.md` + `references/identity.md`:
1. **Write linkify-safe keys.** The comment dedup marker now keys on `issue=<issue-uuid>` (a UUID is never a linkify target), not on the tracker-key-bearing `spec=<id>`. Match on `issue + evt + evidence`.
2. **Normalize on read.** Before matching ANY marker, strip the tracker's mention markup back to bare text: `s/<issue [^>]*>([^<]*)<\/issue>/$1/g` (GitHub: same for `<a …>#NNN</a>`). Then even an older `spec=`-keyed marker re-matches.
3. The flow back-reference stays a **`flow:<id>` label** (label text is never linkified) — NOT a body/title-embedded `[<id>]` reference when `<id>` carries a tracker key.

## Prevention
Any literal marker / sentinel written into tracker body or comment text must avoid embedding a raw issue-key substring (`TEAMKEY-N`, case-insensitive) — trackers rewrite those into mention markup, including inside HTML comments. Key markers on a UUID, and always normalize-strip mention markup before string-matching a marker on read.
