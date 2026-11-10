#!/usr/bin/env bash
# make-pr's merge requests on a GitLab origin. make-pr-preflight.sh runs this in
# place of gh for the same argv (`pr list --head <branch> --state all --json <keys>
# [--jq <expr>]`, `pr view --json <keys>`) and gets gh's JSON keys back: number,
# url, state (OPEN, MERGED, CLOSED) and baseRefName, whatever --json names.
# make-pr-create.sh runs `pr create` with gh's argv (`--title --body-file [--draft]
# --base --head`) and `pr edit <number> --body-file <file> [--ready]`; both print
# the merge request's URL.
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

# A JSON body on stdin, built by jq; GitLab rejects a JSON body without its Content-Type.
# A refused write prints GitLab's answer, so the caller can match it.
glab_write() {
  local out
  out=$(glab api --method "$1" -H 'Content-Type: application/json' --input - "$2") \
    || { printf '%s\n' "$out" >&2; fail "glab api --method $1 $2 failed on ${GITLAB_HOST:-?}"; }
  printf '%s' "${out#"${out%%[[{]*}"}" | jq -er '.web_url' || fail "no merge request URL in GitLab's answer"
}

if [[ "${1:-}" == api-scope ]]; then
  # A personal access token reads its own scopes. An OAuth login (glab auth login --web) is
  # refused there with GitLab's "requires token type to be a personal access token" answer
  # and reads them from the OAuth token info, which lives outside /api/v4.
  if ! TOKEN=$(glab api personal_access_tokens/self 2>&1); then
    [[ "$TOKEN" == *"requires token type to be a personal access token"* ]] \
      || fail "glab api personal_access_tokens/self failed on ${GITLAB_HOST:-?}"
    # glab may print a config warning first; the value is the last line.
    PROTOCOL=$(glab config get api_protocol --host "${GITLAB_HOST:-}" 2>/dev/null) || PROTOCOL=""
    PROTOCOL=${PROTOCOL##*$'\n'}
    # A login keyed by the bare hostname keeps the web port in its api_host.
    API_HOST=$(glab config get api_host --host "${GITLAB_HOST:-}" 2>/dev/null) || API_HOST=""
    API_HOST=${API_HOST##*$'\n'}
    TOKEN=$(glab_json "${PROTOCOL:-https}://${API_HOST:-${GITLAB_HOST:-}}/oauth/token/info")
  fi
  printf '%s' "${TOKEN#"${TOKEN%%[[{]*}"}" | jq -e '(.scopes | type) == "array" and any(.scopes[]; . == "api")' >/dev/null \
    || fail "the glab token for ${GITLAB_HOST:-?} lacks api scope"
  exit 0
fi

[[ "${1:-}" == pr && "${2:-}" =~ ^(list|view|create|edit)$ ]] || { echo "usage: make-pr-gitlab.sh pr list|view|create|edit ... | api-scope" >&2; exit 2; }
[[ -n "${ORIGIN_PROJECT:-}" ]] || fail "no origin project"
ENDPOINT="projects/$(jq -rn --arg v "$ORIGIN_PROJECT" '$v | @uri')/merge_requests"

if [[ "$2" == create ]]; then
  shift 2; TITLE=""; BODY_FILE=""; BASE=""; HEAD=""; DRAFT=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --title) TITLE=$2 ;; --body-file) BODY_FILE=$2 ;; --base) BASE=$2 ;; --head) HEAD=$2 ;;
      --draft) DRAFT="Draft: "; shift; continue ;;   # GitLab's draft is a title prefix
      *) echo "make-pr-gitlab.sh: unsupported argument $1" >&2; exit 2 ;;
    esac
    shift 2
  done
  [[ -n "$TITLE" && -f "$BODY_FILE" && -n "$BASE" && -n "$HEAD" ]] || fail "pr create needs --title, --body-file, --base and --head"
  jq -n --rawfile d "$BODY_FILE" --arg t "$DRAFT$TITLE" --arg s "$HEAD" --arg b "$BASE" \
    '{source_branch: $s, target_branch: $b, title: $t, description: $d}' | glab_write POST "$ENDPOINT"
  exit 0
fi

if [[ "$2" == edit ]]; then
  NUMBER=${3:-}; shift 3; BODY_FILE=""; READY=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --body-file) BODY_FILE=$2; shift ;;
      --ready) READY=1 ;;
      *) echo "make-pr-gitlab.sh: unsupported argument $1" >&2; exit 2 ;;
    esac
    shift
  done
  [[ "$NUMBER" =~ ^[0-9]+$ && -f "$BODY_FILE" ]] || fail "pr edit needs a merge request number and --body-file"
  FIELDS=$(jq -n --rawfile d "$BODY_FILE" '{description: $d}')
  # The draft state stays as it is unless --ready, which drops every draft marker GitLab reads.
  if [[ -n "$READY" ]]; then
    TITLE=$(glab_json "$ENDPOINT/$NUMBER" | jq -er '.title') || fail "unreadable merge request !$NUMBER"
    FIELDS=$(printf '%s' "$FIELDS" | jq -c --arg t "$TITLE" '. + {title: ($t | sub("^(\\s*(\\[draft\\]|\\(draft\\)|draft:))+\\s*"; ""; "i"))}')
  fi
  printf '%s' "$FIELDS" | glab_write PUT "$ENDPOINT/$NUMBER"
  exit 0
fi

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
[[ -n "$HEAD" ]] || fail "no branch to read"
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
  if all(.[]; type == "object" and (.iid | type) == "number" and (.web_url | type) == "string" and .web_url != ""
         and (.state | IN("opened", "locked", "merged", "closed")) and (.target_branch | type) == "string"
         and (.source_project_id | type) == "number" and (.project_id | type) == "number")
  then [.[] | select(.source_project_id == .project_id)
        | {number: .iid, url: .web_url, baseRefName: .target_branch,
           state: {opened: "OPEN", locked: "OPEN", merged: "MERGED", closed: "CLOSED"}[.state]}]
       | if $read == "view" then map(select(.state == "OPEN"))[0] // empty else . end
  else error("malformed merge-request row") end' | jq -rc "$FILTER" \
  || fail "malformed merge-request listing"
