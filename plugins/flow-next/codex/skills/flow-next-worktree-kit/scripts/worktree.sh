#!/usr/bin/env bash
set -euo pipefail

cmd="${1:-}"
name="${2:-}"
base="${3:-}"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$repo_root" ]]; then
  echo "not a git repo" >&2
  exit 1
fi

worktrees_dir="$repo_root/.worktrees"

fail() { echo "$*" >&2; exit 1; }

assert_worktrees_dir() {
  if [[ -e "$worktrees_dir" && ! -d "$worktrees_dir" ]]; then
    fail ".worktrees exists but is not a directory: $worktrees_dir"
  fi
  if [[ -L "$worktrees_dir" ]]; then
    fail ".worktrees is a symlink; refusing for safety: $worktrees_dir"
  fi
}

assert_safe_worktree_path() {
  local rel="$1"
  local path="$worktrees_dir"
  local IFS='/'
  read -r -a parts <<< "$rel"
  for part in "${parts[@]}"; do
    [[ -n "$part" ]] || continue
    path="$path/$part"
    if [[ -L "$path" ]]; then
      fail "refusing symlink path: $path"
    fi
    if [[ -e "$path" && ! -d "$path" ]]; then
      fail "path exists but is not a directory: $path"
    fi
  done
}

has_origin() { git remote get-url origin >/dev/null 2>&1; }

default_base() {
  local b
  b="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@' || true)"
  if [[ -n "$b" ]]; then
    echo "$b"
    return
  fi
  b="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
  if [[ -n "$b" ]]; then
    echo "$b"
    return
  fi
  if git rev-parse --verify -q "main^{commit}" >/dev/null; then
    echo "main"
    return
  fi
  if git rev-parse --verify -q "master^{commit}" >/dev/null; then
    echo "master"
    return
  fi
  echo "main"
}

validate_name() {
  local n="$1"
  [[ -n "$n" ]] || fail "missing name"
  [[ "$n" != -* ]] || fail "invalid name (cannot start with '-')"
  [[ "$n" != *".."* ]] || fail "invalid name (cannot contain '..')"
  git check-ref-format --branch "$n" >/dev/null 2>&1 || fail "invalid branch name: $n"
}

validate_base() {
  local b="$1"
  [[ -n "$b" ]] || fail "missing base"
  [[ "$b" != -* ]] || fail "invalid base (cannot start with '-')"
  [[ "$b" != *:* ]] || fail "invalid base (refspec ':' not allowed)"
  if git check-ref-format --branch "$b" >/dev/null 2>&1; then
    return 0
  fi
  git rev-parse --verify -q "$b^{commit}" >/dev/null || fail "invalid base: $b"
}

ensure_dir() {
  assert_worktrees_dir
  mkdir -p "$worktrees_dir"
}

copy_env() {
  local target="$1"
  [[ -d "$target" ]] || fail "target does not exist: $target"
  [[ ! -L "$target" ]] || fail "target is a symlink; refusing for safety: $target"
  shopt -s nullglob
  for f in "$repo_root"/.env*; do
    [[ -f "$f" ]] || continue
    [[ -L "$f" ]] && continue
    cp -n "$f" "$target/" || true
  done
  shopt -u nullglob
}

worktree_exists() {
  local target="$1"
  git worktree list --porcelain | sed -n 's/^worktree //p' | grep -Fqx -- "$target"
}

case "$cmd" in
  create)
    [[ -n "$name" ]] || fail "usage: create <name> [base]"
    validate_name "$name"
    ensure_dir

    base="${base:-$(default_base)}"
    validate_base "$base"

    if has_origin && git check-ref-format --branch "$base" >/dev/null 2>&1; then
      git fetch --quiet origin "$base" || true
    fi

    assert_safe_worktree_path "$name"
    target="${worktrees_dir}/${name}"
    mkdir -p "$(dirname "$target")"

    if worktree_exists "$target"; then
      echo "worktree exists: $target"
      exit 0
    fi

    start_point="$base"
    if git rev-parse --verify -q "origin/$base^{commit}" >/dev/null; then
      start_point="origin/$base"
    fi
    git rev-parse --verify -q "$start_point^{commit}" >/dev/null || fail "base does not resolve: $start_point"

    if git show-ref --verify --quiet "refs/heads/$name"; then
      git worktree add -- "$target" "$name"
    else
      git worktree add -b "$name" -- "$target" "$start_point"
    fi

    copy_env "$target"
    echo "created: $target"
    ;;
  list)
    git worktree list
    ;;
  switch)
    [[ -n "$name" ]] || fail "usage: switch <name>"
    validate_name "$name"
    assert_worktrees_dir
    assert_safe_worktree_path "$name"
    target="${worktrees_dir}/${name}"
    [[ -d "$target" ]] || fail "no such worktree dir: $target"
    worktree_exists "$target" || fail "not a registered worktree: $target"
    echo "$target"
    ;;
  copy-env)
    [[ -n "$name" ]] || fail "usage: copy-env <name>"
    validate_name "$name"
    assert_worktrees_dir
    assert_safe_worktree_path "$name"
    target="${worktrees_dir}/${name}"
    worktree_exists "$target" || fail "not a registered worktree: $target"
    copy_env "$target"
    echo "copied env to $target"
    ;;
  cleanup)
    assert_worktrees_dir
    echo "all worktrees (only those under $worktrees_dir can be removed by name):"
    git worktree list

    echo "enter names to remove (space-separated), or empty to cancel:"
    read -r to_remove
    [[ -n "$to_remove" ]] || { echo "cancel"; exit 0; }
    IFS=' ' read -r -a remove_names <<< "$to_remove"

    echo "About to remove worktrees (no force, branches kept). Proceed? [y/N]"
    read -r confirm
    [[ "$confirm" == "y" || "$confirm" == "Y" ]] || { echo "cancel"; exit 0; }

    failed=0
    for n in "${remove_names[@]}"; do
      validate_name "$n"
      assert_safe_worktree_path "$n"
      target="${worktrees_dir}/${n}"
      if ! worktree_exists "$target"; then
        echo "skip (not a registered worktree): $target" >&2
        failed=1
        continue
      fi
      if ! git worktree remove -- "$target"; then
        echo "failed to remove: $target" >&2
        failed=1
      fi
    done
    exit "$failed"
    ;;
  *)
    fail "commands: create | list | switch | cleanup | copy-env"
    ;;
esac
