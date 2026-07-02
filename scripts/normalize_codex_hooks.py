#!/usr/bin/env python3
"""Idempotent, dedup-safe normalization of the Codex hooks feature flag.

Ensures a Codex `config.toml` ends with EXACTLY ONE `hooks = true` under
`[features]` and NO deprecated `codex_hooks` key — regardless of the starting
state. Fixes the historical bug where a config carrying BOTH `codex_hooks = true`
(written by older install-codex.sh) AND `hooks = true` (written by Codex or by
setup) ended up with a duplicate `hooks` key after a naive sed migration, which
is invalid TOML and breaks Codex hook loading.

Rules (applied only inside the `[features]` table):
  - drop every `codex_hooks = ...` line (deprecated pre-2026 spelling)
  - keep the FIRST `hooks = ...` line, drop any later duplicates
  - if `[features]` exists but has no `hooks` key, insert `hooks = true` after
    the header
  - if there is no `[features]` table at all, append one with `hooks = true`
Everything outside `[features]` is preserved byte-for-byte. Re-running is a
no-op once normalized (idempotent).

Usage:
    python3 normalize_codex_hooks.py <path/to/config.toml>
Exit 0 on success (writes in place only when content changed); exit 2 on a
missing path argument. A missing file is created with a fresh `[features]`
block (matches install-codex.sh's "no config yet" behavior).
"""
from __future__ import annotations

import re
import sys

_HOOKS_LINE = "hooks = true  # flow-next"
# A section header like `[features]` or `[agents.foo]`. Leading whitespace tolerated.
_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_CODEX_HOOKS_RE = re.compile(r"^\s*codex_hooks\s*=")
_HOOKS_RE = re.compile(r"^\s*hooks\s*=")


def normalize(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    in_features = False
    features_seen = False
    hooks_kept_in_features = False

    for line in lines:
        m = _SECTION_RE.match(line)
        if m:
            # Leaving a [features] block without a hooks key → inject one before
            # the new section starts.
            if in_features and not hooks_kept_in_features:
                out.append(_HOOKS_LINE)
                hooks_kept_in_features = True
            in_features = m.group(1).strip() == "features"
            if in_features:
                features_seen = True
                hooks_kept_in_features = False
            out.append(line)
            continue

        if in_features:
            # Drop the deprecated key entirely.
            if _CODEX_HOOKS_RE.match(line):
                continue
            # Keep the first hooks line, drop later duplicates.
            if _HOOKS_RE.match(line):
                if hooks_kept_in_features:
                    continue
                hooks_kept_in_features = True
                out.append(line)
                continue

        out.append(line)

    # File ended while still inside [features] with no hooks key.
    if in_features and not hooks_kept_in_features:
        out.append(_HOOKS_LINE)
        hooks_kept_in_features = True

    # No [features] table anywhere → append one.
    if not features_seen:
        if out and out[-1].strip() != "":
            out.append("")
        out.append("[features]")
        out.append(_HOOKS_LINE)

    result = "\n".join(out)
    # Preserve a single trailing newline if the original had one (or add it).
    if text.endswith("\n") or not text.endswith("\n"):
        result = result.rstrip("\n") + "\n"
    return result


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write("usage: normalize_codex_hooks.py <config.toml>\n")
        return 2
    path = argv[1]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            original = fh.read()
    except FileNotFoundError:
        original = ""
    updated = normalize(original)
    if updated != original:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
