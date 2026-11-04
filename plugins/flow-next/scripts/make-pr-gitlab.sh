#!/usr/bin/env bash
# make-pr's pull-request reads on a GitLab origin. make-pr-preflight.sh runs this in
# place of gh for the same argv (`pr list --head <branch> --state all --json <keys>
# [--jq <expr>]`, `pr view --json <keys>`) and gets gh's JSON keys back: number,
# url, state (OPEN, MERGED, CLOSED) and baseRefName, whatever --json names.
# `api-scope` exits 0 when glab's token for the host has api scope.
# Environment: GITLAB_HOST (origin host[:port]) and ORIGIN_PROJECT (origin path).
# Exit 0 is a complete answer; a failed, partial or malformed read exits nonzero,
# never an empty "no merge request".
set -euo pipefail
# Windows jq.exe ends lines with CRLF; drop the CR so counts and values compare equal (#541).
jq() { command jq "$@" | tr -d '\r'; return "${PIPESTATUS[0]}"; }
fail() { echo "make-pr-gitlab.sh: $*" >&2; exit 1; }

glab_json() {
  local out
  out=$(glab api "$1") || fail "glab api $1 failed on ${GITLAB_HOST:-?}"
  # glab can print a config warning on stdout before the JSON (measured in fn-139).
  printf '%s' "${out#"${out%%[[{]*}"}"
}

if [[ "${1:-}" == api-scope ]]; then
  TOKEN=$(glab_json personal_access_tokens/self)
  printf '%s' "$TOKEN" | jq -e '.scopes | index("api") != null' >/dev/null \
    || fail "the glab token for ${GITLAB_HOST:-?} lacks api scope"
  exit 0
fi

[[ "${1:-} ${2:-}" == "pr list" || "${1:-} ${2:-}" == "pr view" ]] || { echo "usage: make-pr-gitlab.sh pr list|view ... | api-scope" >&2; exit 2; }
READ=$2; shift 2
HEAD=""; FILTER="."
while [[ $# -gt 0 ]]; do
  case "$1" in
    --head) HEAD=$2 ;;
    --state) [[ "$2" == all ]] || fail "only --state all is supported" ;;
    --json) ;;   # every read answers the same keys
    --jq) FILTER=$2 ;;
    *) echo "make-pr-gitlab.sh: unsupported argument $1" >&2; exit 2 ;;
  esac
  shift 2
done
[[ "$READ" == list ]] || HEAD=$(git branch --show-current)
[[ -n "$HEAD" && -n "${ORIGIN_PROJECT:-}" ]] || fail "no branch or origin project to read"

ENDPOINT="projects/$(jq -rn --arg v "$ORIGIN_PROJECT" '$v | @uri')/merge_requests"
BRANCH=$(jq -rn --arg v "$HEAD" '$v | @uri')
ROWS='[]'; PAGE=1
while :; do
  LISTED=$(glab_json "$ENDPOINT?state=all&source_branch=$BRANCH&per_page=100&page=$PAGE")
  # Exactly one JSON array: empty or other output is unreadable, never an empty listing.
  COUNT=$(printf '%s' "$LISTED" | jq -s 'if length == 1 and (.[0] | type) == "array" then .[0] | length else error("not a listing") end') \
    || fail "unreadable merge-request listing"
  ROWS=$(printf '%s\n%s' "$ROWS" "$LISTED" | jq -cs '.[0] + .[1]')
  [[ "$COUNT" -lt 100 ]] && break
  PAGE=$((PAGE + 1))
done
# A fork's merge request can share the branch name; only the origin project's count.
# A locked merge request is mid-merge and still open.
printf '%s' "$ROWS" | jq -c --arg read "$READ" '
  if all(.[]; type == "object" and (.iid | type) == "number" and (.web_url | type) == "string"
         and (.state | IN("opened", "locked", "merged", "closed")) and (.target_branch | type) == "string"
         and (.source_project_id | type) == "number" and (.project_id | type) == "number")
  then [.[] | select(.source_project_id == .project_id)
        | {number: .iid, url: .web_url, baseRefName: .target_branch,
           state: {opened: "OPEN", locked: "OPEN", merged: "MERGED", closed: "CLOSED"}[.state]}]
       | if $read == "view" then map(select(.state == "OPEN"))[0] // empty else . end
  else error("malformed merge-request row") end' | jq -rc "$FILTER" \
  || fail "malformed merge-request listing"
