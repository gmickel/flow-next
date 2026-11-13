#!/usr/bin/env bash
# make-pr's pull requests on a Bitbucket Cloud origin. make-pr-preflight.sh runs this in
# place of gh for the same argv (`pr list --head <branch> --state all --json <keys>
# [--jq <expr>]`, `pr view --json <keys> [--jq <expr>]`) and gets gh's JSON keys back:
# number, url, state (OPEN, MERGED, CLOSED), baseRefName, createdAt and headRefOid (Bitbucket's
# short hash), whatever --json names.
# make-pr-create.sh runs `pr create` with gh's argv (`--title --body-file [--draft]
# --base --head`) and `pr edit <number> --body-file <file> [--ready]`; both print
# the pull request's URL. `pr create` refuses a branch that already has an open pull
# request: Bitbucket would answer that create with the open one, overwritten.
# `login` exits 0 when bkt holds a Bitbucket Cloud login that reads the origin repository.
# Environment: ORIGIN_PROJECT (origin path, <workspace>/<repository>).
# Exit 0 is a complete answer; a failed, partial or malformed read exits nonzero,
# never an empty "no pull request".
set -euo pipefail
# Windows jq.exe ends lines with CRLF; drop the CR so counts and values compare equal (#541).
jq() { command jq "$@" | tr -d '\r'; return "${PIPESTATUS[0]}"; }
fail() { echo "make-pr-bitbucket.sh: $*" >&2; exit 1; }
API=https://api.bitbucket.org/2.0

[[ "${ORIGIN_PROJECT:-}" =~ ^[^/[:space:]?#%]+/[^/[:space:]?#%]+$ ]] || fail "no origin repository (<workspace>/<repository>)"
REPO="/repositories/$ORIGIN_PROJECT"
# bkt finds its host only through a context; take a Bitbucket Cloud one, the active one first.
CONTEXT=$(bkt context list --json 2>/dev/null | jq -r '[.contexts // [] | .[] | select(.host == "api.bitbucket.org")]
  | sort_by(.active != true) | .[0].name // empty') || CONTEXT=""
[[ -n "$CONTEXT" ]] || fail "bkt has no Bitbucket Cloud context"

bkt_json() {
  bkt --context "$CONTEXT" api "$@" || fail "bkt api $1 failed"
}

# A refused write prints Bitbucket's answer, so the caller can match it.
bkt_write() {
  local out
  out=$(bkt --context "$CONTEXT" api "$2" -X "$1" -d "$3" 2>&1) || { printf '%s\n' "$out" >&2; fail "bkt api -X $1 $2 failed"; }
  printf '%s' "$out" | jq -er '.links.html.href' || fail "no pull request URL in Bitbucket's answer"
}

if [[ "${1:-}" == login ]]; then
  bkt_json "$REPO" | jq -e '.full_name | type == "string"' >/dev/null || fail "unreadable origin repository"
  exit 0
fi

[[ "${1:-}" == pr && "${2:-}" =~ ^(list|view|create|edit)$ ]] || { echo "usage: make-pr-bitbucket.sh pr list|view|create|edit ... | login" >&2; exit 2; }

if [[ "$2" == create ]]; then
  SELF=$0; shift 2; TITLE=""; BODY_FILE=""; BASE=""; HEAD=""; DRAFT=false
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --title) TITLE=$2 ;; --body-file) BODY_FILE=$2 ;; --base) BASE=$2 ;; --head) HEAD=$2 ;;
      --draft) DRAFT=true; shift; continue ;;
      *) echo "make-pr-bitbucket.sh: unsupported argument $1" >&2; exit 2 ;;
    esac
    shift 2
  done
  [[ -n "$TITLE" && -f "$BODY_FILE" && -n "$BASE" && -n "$HEAD" ]] || fail "pr create needs --title, --body-file, --base and --head"
  OPEN=$("$SELF" pr list --head "$HEAD" --state all --json url --jq 'map(select(.state == "OPEN"))[0].url // empty') \
    || fail "cannot read the pull requests of $HEAD; nothing created"
  [[ -z "$OPEN" ]] || fail "branch $HEAD already has an OPEN pull request: $OPEN; use --update"
  bkt_write POST "$REPO/pullrequests" "$(jq -cn --rawfile d "$BODY_FILE" --arg t "$TITLE" --arg s "$HEAD" --arg b "$BASE" \
    --argjson draft "$DRAFT" '{title: $t, description: $d} + (if $draft then {draft: true} else {} end)
      + {source: {branch: {name: $s}}, destination: {branch: {name: $b}}}')"
  exit 0
fi

if [[ "$2" == edit ]]; then
  NUMBER=${3:-}; shift 3; BODY_FILE=""; READY=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --body-file) BODY_FILE=$2; shift ;;
      --ready) READY=1 ;;
      *) echo "make-pr-bitbucket.sh: unsupported argument $1" >&2; exit 2 ;;
    esac
    shift
  done
  [[ "$NUMBER" =~ ^[0-9]+$ && -f "$BODY_FILE" ]] || fail "pr edit needs a pull request number and --body-file"
  # The draft state stays as it is unless --ready.
  bkt_write PUT "$REPO/pullrequests/$NUMBER" "$(jq -cn --rawfile d "$BODY_FILE" --arg ready "$READY" \
    '{description: $d} + (if $ready == "" then {} else {draft: false} end)')"
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
    *) echo "make-pr-bitbucket.sh: unsupported argument $1" >&2; exit 2 ;;
  esac
  shift 2
done
[[ "$READ" == list ]] || HEAD=$(git branch --show-current)
[[ -n "$HEAD" ]] || fail "no branch to read"
# A branch name may hold a double quote; Bitbucket's query language escapes it with a backslash.
Q=$(jq -rn --arg v "$HEAD" '"source.branch.name=\"" + ($v | gsub("\\\\"; "\\\\") | gsub("\""; "\\\"")) + "\"" | @uri')
NEXT="$REPO/pullrequests?state=OPEN&state=MERGED&state=DECLINED&state=SUPERSEDED&q=$Q&pagelen=50&page=1"
ROWS='[]'
while [[ -n "$NEXT" ]]; do
  PAGE=$(bkt_json "$NEXT")
  # Exactly one listing page; empty or other output is unreadable, never an empty listing.
  ROWS=$(printf '%s\n%s' "$ROWS" "$PAGE" | jq -cs 'if length == 2 and (.[1] | type) == "object" and (.[1].values | type) == "array"
    then .[0] + .[1].values else error("not a listing") end') || fail "unreadable pull request listing"
  NEXT=$(printf '%s' "$PAGE" | jq -r --arg api "$API" 'if .next == null then ""
    elif (.next | type) == "string" and (.next | startswith($api + "/")) then .next[($api | length):]
    else error("unexpected next page") end') || fail "unreadable pull request listing"
  if [[ -z "$NEXT" ]] && ! printf '%s\n%s' "$PAGE" "$ROWS" | jq -se '(.[0].size | type) != "number" or .[0].size == (.[1] | length)' >/dev/null; then
    fail "the pull request listing changed while it was read"
  fi
done
# A fork's pull request can share the branch name; only the origin repository's count.
printf '%s' "$ROWS" | jq -c --arg read "$READ" '
  if all(.[]; type == "object" and (.id | type) == "number" and (.links.html.href | type) == "string" and .links.html.href != ""
         and (.state | IN("OPEN", "MERGED", "DECLINED", "SUPERSEDED")) and (.destination.branch.name | type) == "string"
         and (.destination.repository.full_name | type) == "string" and (.created_on | type) == "string"
         and (.source.commit.hash | type) == "string"
         and (.source | has("repository")) and (.source.repository == null or (.source.repository.full_name | type) == "string"))
  then [.[] | select(((.source.repository.full_name // "") | ascii_downcase) == (.destination.repository.full_name | ascii_downcase))
        | {number: .id, url: .links.html.href, baseRefName: .destination.branch.name, createdAt: .created_on,
           headRefOid: .source.commit.hash,
           state: {OPEN: "OPEN", MERGED: "MERGED", DECLINED: "CLOSED", SUPERSEDED: "CLOSED"}[.state]}]
       | if $read == "view" then map(select(.state == "OPEN"))[0] // empty else . end
  else error("malformed pull request row") end' | jq -rc "$FILTER" \
  || fail "malformed pull request listing"
