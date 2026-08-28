#!/usr/bin/env python3
"""Verify every in-repo markdown link that carries an #anchor resolves.

An anchor is a heading slug or an explicit `<a id="...">` target.

The repo's CI link check runs lychee `--offline`, which proves a file exists but
says nothing about the fragment after `#`. A heading reword therefore breaks
cross-references silently, and these docs cross-reference heavily.

Usage:
    python3 scripts/check_doc_anchors.py           # report, exit 1 on breakage
    python3 scripts/check_doc_anchors.py --fix     # repair anchors that differ
                                                   # only by hyphen runs
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOTS = ("plugins/flow-next/docs", "plugins/flow-next/skills", "agent_docs")
EXTRA_FILES = ("README.md", "CLAUDE.md", "CONTRIBUTING.md", "GLOSSARY.md", "STRATEGY.md")
SKIP_DIRS = {"codex", "node_modules", ".flow"}
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+\.md)#([^)\s]+)\)")
HEADING = re.compile(r"(?m)^(#{1,6})\s+(.+?)\s*$")
EXPLICIT = re.compile(r"""<a\s+(?:id|name)=["']([^"']+)["']""")


def slug(text: str) -> str:
    text = text.replace("`", "").lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text.strip())


def anchors_of(path: Path) -> set[str]:
    found: set[str] = set()
    in_fence = False
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING.match(line)
        if match:
            found.add(slug(match.group(2)))
        found.update(EXPLICIT.findall(line))
    return found


def sources() -> list[Path]:
    files: list[Path] = [Path(name) for name in EXTRA_FILES if Path(name).exists()]
    for root in ROOTS:
        base = Path(root)
        if not base.exists():
            continue
        for path in base.rglob("*.md"):
            if SKIP_DIRS & set(path.parts):
                continue
            files.append(path)
    return sorted(set(files))


def main() -> int:
    fix = "--fix" in sys.argv
    cache: dict[Path, set[str]] = {}
    broken: list[str] = []
    repaired = 0

    for path in sources():
        text = path.read_text(encoding="utf-8")
        original = text
        for target, anchor in LINK.findall(text):
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                continue  # file existence is lychee's job
            if resolved not in cache:
                cache[resolved] = anchors_of(resolved)
            known = cache[resolved]
            if anchor in known:
                continue
            candidates = [a for a in known if re.sub(r"-+", "-", a) == re.sub(r"-+", "-", anchor)]
            if len(candidates) == 1 and fix:
                text = text.replace(f"{target}#{anchor}", f"{target}#{candidates[0]}")
                repaired += 1
            elif len(candidates) == 1:
                broken.append(f"{path}: {target}#{anchor} -> should be #{candidates[0]}")
            else:
                broken.append(f"{path}: {target}#{anchor} (no such heading)")
        if fix and text != original:
            path.write_text(text, encoding="utf-8")

    if fix:
        print(f"repaired {repaired} anchor(s)")
    if broken:
        print(f"{len(broken)} unresolved anchor link(s):\n")
        for item in sorted(set(broken)):
            print("  " + item)
        return 1
    print("OK - every anchored markdown link resolves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
