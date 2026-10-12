#!/usr/bin/env python3
"""Build the Muse Code plugin bundle at install time (fn-293).

Invoked by scripts/install-muse.sh. Stdlib only (Python 3.11+). No committed
Muse tree: the bundle is a copy of the canonical plugin with three bundle-only
changes, installed by `muse plugins install` and then discarded.

  python3 muse_bundle.py <canonical-plugin-dir> <dest>

Pinned Muse Code behaviour (1.4.6, verified live 2026-10-12):

  - Agent `disallowedTools` must name Muse work tools only; any Claude tool
    name (Edit, Write, Task) or a mixed list makes the definition invalid at
    spawn time, after install and approval have succeeded. Translation:
      Edit -> edit_file, Write -> write_file, Bash -> bash, Task -> dropped
    (subagent_spawn is a session-control tool no definition may deny).
  - A `tools:` allowlist with Claude names makes the definition unavailable.
  - Plugin agents are selected as `subagent_type: "flow-next/<name>"`.

Fail closed (named error on stderr, non-zero exit) on:
  UNMAPPED_DISALLOWED_TOOL — token outside {Edit, Write, Bash, Task}
  UNSUPPORTED_TOOLS_KEY    — an agent declares a `tools:` allowlist
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path


# Canonical disallowedTools token -> Muse work-tool name (None: not deniable).
DISALLOWED_TO_MUSE: dict[str, str | None] = {
    "Edit": "edit_file",
    "Write": "write_file",
    "Bash": "bash",
    "Task": None,
}

# Host manifests, the Codex mirror and the test suite are not part of a Muse install.
EXCLUDED = shutil.ignore_patterns(
    "codex", ".codex-plugin", ".cursor-plugin", "tests", "__pycache__", "*.pyc"
)

# setup's host detection keys on this file at the plugin root.
MARKER = ".flow-next-muse-bundle"

HOST_NOTE = """
## Muse Code

On this host the shipped agents are spawned with `subagent_spawn` and
`subagent_type: "flow-next/<name>"` (for example `flow-next/worker`,
`flow-next/repo-scout`). Any spelling of a shipped agent in these skills
(`flow-next:repo-scout`, `repo-scout`, `worker`) means that `subagent_type`;
without it Muse runs its built-in general-purpose agent instead.
"""

_DISALLOWED_RE = re.compile(r"^disallowedTools:[ \t]*(.*)$", re.M)


class BundleError(Exception):
    """Named bundle failure. `name` is the stable identifier tests pin."""

    def __init__(self, name: str, detail: str) -> None:
        self.name = name
        super().__init__(f"{name}: {detail}")


def translate_agent(text: str, source: str) -> str:
    """Rewrite one agent file's frontmatter tool names for Muse."""
    if not text.startswith("---\n"):
        return text
    end = text.index("\n---", 4)
    front, body = text[:end], text[end:]
    if re.search(r"^tools:", front, re.M):
        raise BundleError("UNSUPPORTED_TOOLS_KEY", source)
    match = _DISALLOWED_RE.search(front)
    if match is None:
        return text
    muse_names = []
    for token in (t.strip() for t in match.group(1).split(",")):
        if not token:
            continue
        if token not in DISALLOWED_TO_MUSE:
            raise BundleError("UNMAPPED_DISALLOWED_TOOL", f"{source}: {token}")
        if DISALLOWED_TO_MUSE[token]:
            muse_names.append(DISALLOWED_TO_MUSE[token])
    if muse_names:
        line = "disallowedTools: " + ", ".join(muse_names)
        front = front[: match.start()] + line + front[match.end():]
    else:
        front = front[: match.start()] + front[match.end() + 1:]
    return front + body


def build(plugin: Path, dest: Path) -> None:
    shutil.copytree(plugin, dest, ignore=EXCLUDED)
    for agent in sorted((dest / "agents").glob("*.md")):
        agent.write_text(
            translate_agent(agent.read_text(encoding="utf-8"), agent.name),
            encoding="utf-8",
        )
    rules = dest / "references" / "working-rules.md"
    rules.write_text(rules.read_text(encoding="utf-8") + HOST_NOTE, encoding="utf-8")
    (dest / MARKER).write_text("flow-next Muse Code bundle\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: muse_bundle.py <canonical-plugin-dir> <dest>", file=sys.stderr)
        return 2
    try:
        build(Path(argv[0]), Path(argv[1]))
    except BundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
