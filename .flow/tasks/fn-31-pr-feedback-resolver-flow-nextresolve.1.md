# fn-31-pr-feedback-resolver.1 GraphQL scripts

## Description

Bash scripts that wrap `gh api` GraphQL calls. Four scripts: fetch, thread-lookup, reply, resolve. Zero deps beyond `gh` + `jq`.

**Size:** M

**Files:**
- `plugins/flow-next/skills/flow-next-resolve-pr/scripts/get-pr-comments`
- `plugins/flow-next/skills/flow-next-resolve-pr/scripts/get-thread-for-comment`
- `plugins/flow-next/skills/flow-next-resolve-pr/scripts/reply-to-pr-thread`
- `plugins/flow-next/skills/flow-next-resolve-pr/scripts/resolve-pr-thread`

All scripts must be executable (`chmod +x`). Use `#!/usr/bin/env bash` + `set -euo pipefail`.

## `get-pr-comments`

```bash
#!/usr/bin/env bash
set -euo pipefail

PR_NUMBER="${1:?Usage: $0 PR_NUMBER}"
OWNER_REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
OWNER="${OWNER_REPO%/*}"
REPO="${OWNER_REPO#*/}"

# Fetch unresolved review threads, PR comments, review bodies in one GraphQL call
# Also fetch last N resolved threads for cross-invocation signal
gh api graphql -F owner="$OWNER" -F repo="$REPO" -F pr="$PR_NUMBER" -f query='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      author { login }
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          originalLine
          startLine
          originalStartLine
          comments(first: 50) {
            nodes {
              id
              author { login }
              body
              createdAt
            }
          }
        }
      }
      comments(first: 100) {
        nodes {
          id
          author { login }
          body
          createdAt
        }
      }
      reviews(first: 50) {
        nodes {
          id
          author { login }
          body
          state
          submittedAt
        }
      }
    }
  }
}' | jq --arg pr "$PR_NUMBER" '
  .data.repository.pullRequest as $p
  | ($p.author.login) as $author
  | {
      pr_number: ($pr | tonumber),
      review_threads: [
        $p.reviewThreads.nodes[]
        | select(.isResolved == false)
        | {id, isOutdated, path, line, originalLine, startLine, originalStartLine, comments: .comments.nodes}
      ],
      pr_comments: [
        $p.comments.nodes[]
        | select(.author.login != $author)
        | select(.body != null and .body != "")
        | {id, author: .author.login, body, createdAt}
      ],
      review_bodies: [
        $p.reviews.nodes[]
        | select(.author.login != $author)
        | select(.body != null and .body != "")
        | {id, author: .author.login, body, state, submittedAt}
      ],
      cross_invocation: {
        signal: ([$p.reviewThreads.nodes[] | select(.isResolved == true)] | length > 0),
        resolved_threads: [
          $p.reviewThreads.nodes[]
          | select(.isResolved == true)
          | {id, path, line: (.line // .originalLine)}
        ]
      }
    }
'
```

Filters: excludes PR author's own comments (already the feedback subject). Excludes empty review bodies (approvals with no text).

## `get-thread-for-comment`

```bash
#!/usr/bin/env bash
set -euo pipefail

PR_NUMBER="${1:?Usage: $0 PR_NUMBER COMMENT_NODE_ID [OWNER/REPO]}"
COMMENT_NODE_ID="${2:?Usage: $0 PR_NUMBER COMMENT_NODE_ID [OWNER/REPO]}"
OWNER_REPO="${3:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
OWNER="${OWNER_REPO%/*}"
REPO="${OWNER_REPO#*/}"

# Minimal thread listing (IDs + first comment IDs only, no bodies) to find matching thread
gh api graphql -F owner="$OWNER" -F repo="$REPO" -F pr="$PR_NUMBER" -f query='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          path
          line
          originalLine
          comments(first: 50) { nodes { id } }
        }
      }
    }
  }
}' | jq --arg cid "$COMMENT_NODE_ID" '
  .data.repository.pullRequest.reviewThreads.nodes[]
  | select(.comments.nodes | map(.id) | index($cid))
  | {id, path, line: (.line // .originalLine), isResolved}
'
```

If no match: prints nothing, exits 0. Caller checks emptiness.

## `reply-to-pr-thread`

```bash
#!/usr/bin/env bash
set -euo pipefail

THREAD_ID="${1:?Usage: echo REPLY_TEXT | $0 THREAD_ID}"
REPLY_TEXT=$(cat)

if [ -z "$REPLY_TEXT" ]; then
  echo "Empty reply text on stdin; aborting" >&2
  exit 1
fi

gh api graphql -F threadId="$THREAD_ID" -F body="$REPLY_TEXT" -f query='
mutation($threadId: ID!, $body: String!) {
  addPullRequestReviewThreadReply(input: {pullRequestReviewThreadId: $threadId, body: $body}) {
    comment { id url }
  }
}'
```

## `resolve-pr-thread`

```bash
#!/usr/bin/env bash
set -euo pipefail

THREAD_ID="${1:?Usage: $0 THREAD_ID}"

gh api graphql -F threadId="$THREAD_ID" -f query='
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread { id isResolved }
  }
}'
```

## Acceptance

- **AC1:** All four scripts exist at `plugins/flow-next/skills/flow-next-resolve-pr/scripts/` and are executable.
- **AC2:** `get-pr-comments <PR>` returns JSON object with `review_threads`, `pr_comments`, `review_bodies`, `cross_invocation` keys on a real PR.
- **AC3:** `get-pr-comments` excludes the PR author's own comments.
- **AC4:** `get-thread-for-comment` resolves a comment node ID to its thread ID.
- **AC5:** `reply-to-pr-thread` posts via GraphQL (verify on test PR).
- **AC6:** `resolve-pr-thread` sets thread's `isResolved: true` (verify on test PR).
- **AC7:** All scripts fail loudly (`set -euo pipefail`) on bad input or gh failures.
- **AC8:** Scripts are auditable — no external commands beyond `gh`, `jq`, standard POSIX utilities.

## Dependencies

None — foundational task for the epic.

## Done summary
Added four bash GraphQL scripts under `plugins/flow-next/skills/flow-next-resolve-pr/scripts/` (`get-pr-comments`, `get-thread-for-comment`, `reply-to-pr-thread`, `resolve-pr-thread`) wrapping `gh api` + `jq`, with `set -euo pipefail`, executable mode, and no deps beyond gh/jq/POSIX. Smoke-tested against live PRs #85 (author filter), #107 (cross-invocation signal), #113 (unresolved thread + review body), plus GraphQL schema introspection confirming reply/resolve mutation shapes.
## Evidence
- Commits: be36e53ee983211c0d8a1db3f21eec5d3af82ce1
- Tests: usage-error smoke, all 4 scripts, scripts/get-pr-comments 113 (keys + populated thread + excludes author), scripts/get-pr-comments 85 (author-filter verified), scripts/get-pr-comments 107 (cross_invocation.signal=true with 3 resolved_threads), scripts/get-thread-for-comment 113 real+bogus (returns thread / empty), GraphQL schema introspection: mutation input shapes match, bogus thread id reaches API (NOT_FOUND), empty stdin guard in reply-to-pr-thread, command-surface audit: only gh, jq, cat, echo, POSIX
- PRs: