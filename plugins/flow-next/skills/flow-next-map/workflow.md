# /flow-next:map workflow

Execute these phases in order. Each gates on the prior. Stop on user-blocking error — never plow through with bad state.

## Preamble

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CLAWPATCH_DIR="$REPO_ROOT/.clawpatch"
```

The skill uses pure POSIX shell plus `clawpatch` invocations.

---

## Ralph-block — runs first, before everything else

Already gated in SKILL.md. Re-check defensively in case the workflow is loaded standalone:

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
  if [[ -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
    TRIGGER="REVIEW_RECEIPT_PATH"
  else
    TRIGGER="FLOW_RALPH"
  fi
  echo "Error: /flow-next:map declines under Ralph ($TRIGGER set); rerun interactively." >&2
  exit 2
fi
```

The skill MUST NOT write to `$REVIEW_RECEIPT_PATH` — that's the upstream review caller's receipt; corrupting it is worse than declining.

---

## Phase 0: Argument parsing + config-state echo (R12)

### 0.1 — Parse arguments

Default `SOURCE` is `heuristic` (provider-free, deterministic). The `--` terminator splits skill-handled flags from passthrough.

**Passthrough boundary.** The slash-command host delivers `$ARGUMENTS` as a single string; the skill word-splits on whitespace to tokenize. That means **passthrough is token-level (whitespace-separated), not verbatim shell** — arguments containing literal spaces, embedded quotes, or shell metacharacters cannot survive intact. We mitigate by disabling glob expansion (`set -f`) so `*` and `?` reach `clawpatch` unmolested; tokens like `src/foo` or `--paths=src/foo` flow through cleanly. Users needing complex quoting should run `clawpatch map` directly.

```bash
SOURCE="heuristic"
EXTRA_PASSTHROUGH=()
seen_dashdash=0

# Disable globbing so passthrough tokens like `*.py` or `src/?` reach
# clawpatch verbatim instead of being expanded against $PWD. We do NOT
# claim full shell-verbatim passthrough — tokens are whitespace-split
# (see "Passthrough boundary" above).
set -f
# shellcheck disable=SC2086
set -- $ARGUMENTS
set +f
while [[ $# -gt 0 ]]; do
  if [[ "$seen_dashdash" == "1" ]]; then
    EXTRA_PASSTHROUGH+=("$1")
    shift
    continue
  fi
  case "$1" in
    --) seen_dashdash=1 ;;
    --source)
      # Guard against `--source` at end-of-args or followed by the
      # passthrough terminator. Without this, `shift` past end-of-args
      # crashes under `set -e` with a cryptic shell error.
      if [[ $# -lt 2 || "$2" == "--" ]]; then
        echo "Error: --source requires a value (one of: heuristic, auto, agent)" >&2
        exit 2
      fi
      SOURCE="$2"
      shift
      ;;
    --source=*) SOURCE="${1#--source=}" ;;
    *) EXTRA_PASSTHROUGH+=("$1") ;;
  esac
  shift
done

case "$SOURCE" in
  heuristic|auto|agent) ;;
  *)
    echo "Error: --source must be one of: heuristic, auto, agent (got: $SOURCE)" >&2
    exit 2
    ;;
esac
```

### 0.2 — Config-state echo (R12)

Emit one four-line block before any work runs. This is the user's "what am I about to do?" anchor:

```bash
# clawpatch version (or "not installed")
if command -v clawpatch >/dev/null 2>&1; then
  CP_VER="$(clawpatch --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1)"
  CP_VER="${CP_VER:-unknown}"
else
  CP_VER="not installed"
fi

# CLAWPATCH_PROVIDER env var (orthogonal to flow-next review backend)
CP_PROVIDER="${CLAWPATCH_PROVIDER:-none}"

# flow-next review backend (informational only — not proxied to clawpatch).
# Must pass --json: text mode prints `review.backend: <value>`, NOT JSON, so
# the previous "value":"..." grep returned empty and the field always
# defaulted to "none" — false config state regardless of what the user set.
FN_REVIEW_BACKEND="$($FLOWCTL config get review.backend --json 2>/dev/null | grep -oE '"value":[[:space:]]*"[^"]*"' | sed -E 's/.*"value":[[:space:]]*"([^"]*)".*/\1/' || echo "none")"
FN_REVIEW_BACKEND="${FN_REVIEW_BACKEND:-none}"

# .clawpatch/ last-mapped timestamp (mtime of features/ dir, or "absent")
if [[ -d "$CLAWPATCH_DIR/features" ]]; then
  if [[ "$(uname)" == "Darwin" ]]; then
    CP_LAST_MAPPED="$(stat -f '%Sm' -t '%Y-%m-%dT%H:%M:%SZ' "$CLAWPATCH_DIR/features" 2>/dev/null || echo unknown)"
  else
    CP_LAST_MAPPED="$(stat -c '%y' "$CLAWPATCH_DIR/features" 2>/dev/null | cut -d. -f1 || echo unknown)"
  fi
else
  CP_LAST_MAPPED="absent"
fi

cat <<EOF
clawpatch: $CP_VER (--source $SOURCE)
CLAWPATCH_PROVIDER: $CP_PROVIDER
flow-next review backend: $FN_REVIEW_BACKEND (informational; not proxied)
.clawpatch/ last-mapped: $CP_LAST_MAPPED
EOF
```

The four-line block ordering matches R12 spec wording: clawpatch version + `--source`, `CLAWPATCH_PROVIDER`, flow-next review backend, `.clawpatch/` last-mapped.

---

## Phase 1: Install detection (R1, R11)

### 1.1 — Hard requirement: `clawpatch` on PATH

```bash
if ! command -v clawpatch >/dev/null 2>&1; then
  cat >&2 <<'EOF'
clawpatch is not installed.

Install (requires Node 22+):

    pnpm add -g clawpatch

Then re-run /flow-next:map.
EOF

  # R11 — PNPM_HOME divergence hint. Conditional framing: this branch fires
  # whenever pnpm is available, BEFORE we know whether the user has actually
  # installed clawpatch. So phrase it as "if you already installed and still
  # see this" rather than asserting an install happened — and avoid the
  # pnpm-v11-specific claim (the PNPM_HOME/PATH wiring step applies to pnpm 10
  # too; the user's global bin may be ~/.local/share/pnpm, not $PNPM_HOME/bin).
  if command -v pnpm >/dev/null 2>&1 && pnpm bin -g >/dev/null 2>&1; then
    PNPM_GLOBAL_BIN="$(pnpm bin -g 2>/dev/null)"
    cat >&2 <<EOF

Hint: pnpm is available — your pnpm global bin is at: $PNPM_GLOBAL_BIN

If you already ran \`pnpm add -g clawpatch\` and still see this, that directory
is likely not on your PATH. pnpm installs global binaries under \$PNPM_HOME and
needs a one-time \`pnpm setup\` to wire PATH. Run:

    pnpm setup
    # then re-source your shell rc (e.g. source ~/.zshrc) or open a new shell

…and re-run /flow-next:map.
EOF
  fi
  exit 1
fi
```

**No auto-install.** The skill detects and instructs; users install with their own permission. Global npm installs are user-consent territory.

### 1.2 — Capture version for the range guard

```bash
CP_VER_RAW="$(clawpatch --version 2>/dev/null || true)"
CP_VER="$(printf '%s' "$CP_VER_RAW" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1)"

if [[ -z "$CP_VER" ]]; then
  echo "Warning: could not parse clawpatch version from '$CP_VER_RAW'. Continuing with degraded checks." >&2
fi
```

Tolerant `(\d+\.\d+\.\d+)` regex — matches `0.4.0`, `clawpatch 0.4.0`, `clawpatch/0.4.0 (node 22)`, etc.

---

## Phase 2: Version-range guard (R10)

`SUPPORTED_CLAWPATCH=">=0.4.0 <0.5.0"` — single source defined in SKILL.md prose. Implementation:

```bash
SUPPORTED_MIN="0.4.0"
SUPPORTED_MAX_EXCL="0.5.0"

# Compare semver triples lexicographically after zero-padding each segment.
# Tolerant: missing patch → assume .0; unparseable → skip the check.
ver_cmp() {
  # ver_cmp <a> <b> → prints -1 / 0 / 1
  local a="$1" b="$2"
  if [[ -z "$a" || -z "$b" ]]; then echo 0; return; fi
  local IFS=.
  # shellcheck disable=SC2206
  local A=($a) B=($b)
  for i in 0 1 2; do
    local ai="${A[$i]:-0}" bi="${B[$i]:-0}"
    if (( 10#$ai > 10#$bi )); then echo 1; return; fi
    if (( 10#$ai < 10#$bi )); then echo -1; return; fi
  done
  echo 0
}

if [[ -n "$CP_VER" ]]; then
  cmp_min="$(ver_cmp "$CP_VER" "$SUPPORTED_MIN")"
  cmp_max="$(ver_cmp "$CP_VER" "$SUPPORTED_MAX_EXCL")"
  if [[ "$cmp_min" == "-1" || "$cmp_max" != "-1" ]]; then
    echo "Warning: clawpatch $CP_VER outside supported range >=$SUPPORTED_MIN <$SUPPORTED_MAX_EXCL — continuing (degraded; behavior may differ)." >&2
  fi
fi
```

**Outside-range → warn one line and continue. Never block.** clawpatch is pre-1.0 — strict pinning would create friction every minor release.

---

## Phase 3: Init when `.clawpatch/` absent (R2)

```bash
if [[ ! -d "$CLAWPATCH_DIR" ]]; then
  echo "No .clawpatch/ found — running 'clawpatch init' first." >&2
  if ! clawpatch init; then
    echo "Error: 'clawpatch init' failed. See output above." >&2
    exit 1
  fi
fi
```

`clawpatch init` is fully deterministic (App.ts: detects git remote / branch / project name / languages / frameworks; writes `.clawpatch/project.json` + `.clawpatch/config.json`; no provider contacts). Safe to call automatically.

### 3.1 — Write `.clawpatch/.gitignore` skeleton (decision lock-in #1)

The skeleton lives **self-contained inside `.clawpatch/`** so deleting that directory removes both data and ignore rules in one step. We do NOT append to the repo `.gitignore`.

The skill owns this write — STRATEGY zero-dep means flowctl never references clawpatch (no `_ensure_clawpatch_gitignore` helper in flowctl.py).

```bash
GITIGNORE_PATH="$CLAWPATCH_DIR/.gitignore"
if [[ ! -f "$GITIGNORE_PATH" ]]; then
  cat > "$GITIGNORE_PATH" <<'EOF'
# Auto-managed by /flow-next:map — patterns scoped to .clawpatch/.
# Delete this directory entire to remove data + ignore rules together.
#
# Ignore EVERYTHING under .clawpatch/ — features/*.json, project.json,
# config.json, .cache/, *.log, *.tmp, patches/*.tmp — except this
# .gitignore file itself. The persisted index is reproducible from
# `clawpatch map`; checking it into git would create review noise and
# couple PRs to mapper-output drift. Per the spec edge case
# "`.clawpatch/` ignored at directory level", this self-contained
# pattern delivers that contract without touching the repo `.gitignore`.
*
!.gitignore
EOF
fi
```

Idempotent — only writes when the file doesn't exist. If clawpatch's own future init starts shipping `.gitignore`, we defer to it (leave the upstream file in place).

Verify the contract with `git check-ignore` from inside the repo:

```bash
git check-ignore -v .clawpatch/features/foo.json   # → .clawpatch/.gitignore:N:*  .clawpatch/features/foo.json
git check-ignore -v .clawpatch/.gitignore          # → no output, exit 1 (NOT ignored — the negation is intentional)
```

---

## Phase 4: Map invocation (R1)

```bash
echo "Running: clawpatch map --source $SOURCE${EXTRA_PASSTHROUGH[*]:+ ${EXTRA_PASSTHROUGH[*]}}" >&2
# Disable errexit around the call so we can capture the real exit code
# in MAP_EXIT — under `set -euo pipefail` (script preamble), a non-zero
# `clawpatch map` would exit the shell before line 5 runs, making the
# diagnostic + propagated exit code unreachable.
set +e
clawpatch map --source "$SOURCE" "${EXTRA_PASSTHROUGH[@]}"
MAP_EXIT=$?
set -e

if [[ "$MAP_EXIT" -ne 0 ]]; then
  echo "Error: 'clawpatch map' exited with code $MAP_EXIT." >&2
  exit "$MAP_EXIT"
fi
```

**Default `--source heuristic` is always passed explicitly.** Upstream's default is also `heuristic` today (cli.ts:1925) but explicit pass guards against the default flipping in a future minor.

clawpatch streams stdout live during the filesystem walk; we don't buffer. Ctrl+C kills cleanly via subprocess group (no skill-side timeout — large-repo maps can take a minute).

For `--source auto` / `--source agent`, clawpatch enforces its own `CLAWPATCH_PROVIDER` requirement. If unconfigured, clawpatch's own error surfaces; the skill propagates it verbatim.

---

## Phase 5: Result summary

```bash
FEATURES_DIR="$CLAWPATCH_DIR/features"
if [[ -d "$FEATURES_DIR" ]]; then
  COUNT=$(find "$FEATURES_DIR" -maxdepth 1 -name '*.json' -type f 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$(uname)" == "Darwin" ]]; then
    LAST="$(stat -f '%Sm' -t '%Y-%m-%dT%H:%M:%SZ' "$FEATURES_DIR" 2>/dev/null || echo unknown)"
  else
    LAST="$(stat -c '%y' "$FEATURES_DIR" 2>/dev/null | cut -d. -f1 || echo unknown)"
  fi
  cat <<EOF

Mapped: $COUNT feature(s) at $FEATURES_DIR
Last-mapped: $LAST
EOF

  # Zero-features-on-heuristic hint. clawpatch's heuristic mapper targets
  # conventional app/framework layouts (npm bins, Next.js routes, Python
  # packages, Rails/Laravel/Django, Go/Rust services, JVM, .NET, SwiftPM,
  # Phoenix). Repos that don't match — CLI tools, plugins, markdown/docs-heavy,
  # non-standard monorepos — get 0 features and clawpatch flags coverage as
  # weak (`weak=true`, `agent-skip reason=heuristic` in the map output above).
  # Surface the next step rather than leaving the user with a silent empty map.
  if [[ "$COUNT" -eq 0 && "$SOURCE" == "heuristic" ]]; then
    cat >&2 <<'EOF'

Note: heuristic mapping found 0 features. clawpatch's deterministic mapper
targets conventional app/framework layouts; if this repo is a CLI tool,
plugin, or has a non-standard structure, the heuristic detectors may not
match it (clawpatch flags this as "weak" coverage above). For richer,
LLM-backed mapping:

    /flow-next:map --source=auto    # heuristic first, provider only if weak
    /flow-next:map --source=agent   # always provider-backed

Both require a clawpatch provider configured (CLAWPATCH_PROVIDER, e.g. codex)
and spend provider tokens — orthogonal to flow-next's review backend.
EOF
  fi

  cat <<EOF

Next steps:
  - flowctl repo-map list
  - /flow-next:plan <spec-id>       (scouts read the index when present)
  - /flow-next:capture              (scouts read the index when present)
EOF
else
  echo "Warning: clawpatch map exited 0 but .clawpatch/features/ is missing. Inspect $CLAWPATCH_DIR directly." >&2
fi
```

---

## Forbidden behaviors

- **Touching the repo `.gitignore`.** The `.clawpatch/.gitignore` skeleton stays inside `.clawpatch/`.
- **Auto-installing clawpatch.** Phase 1 detects + instructs; never runs `pnpm add`.
- **Writing to `$REVIEW_RECEIPT_PATH`.** The Ralph-block is decline-to-run only.
- **Proxying flow-next's review backend into `CLAWPATCH_PROVIDER`.** Orthogonal matrices. The config-state echo (Phase 0.2) lists the flow-next backend for informational context only.
- **Buffering `clawpatch map` stdout.** Stream live so users see progress on large-repo maps.
- **Blocking on outside-range version.** Phase 2 warns and continues. clawpatch is pre-1.0; strict pinning would create churn every minor.
