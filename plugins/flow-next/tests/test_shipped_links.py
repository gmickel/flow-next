"""fn-257 R12: relative markdown links in shipped prose resolve in the plugin.

The plugin root (plugins/flow-next/) is what a host installs, so a link from a
skill, agent, command, reference or template must land on a file inside it.
docs/ pages double as the GitHub docs tree and may also link repo-level files
outside the plugin (sync-codex.sh rewrites those to absolute URLs); they only
need to exist. URLs, anchor-only links, placeholders (`<...>`, `{...}`, `$VAR`,
globs), `.flow/...` run-time destinations and fenced code are out of scope.

Run:
    python3 -m unittest plugins.flow-next.tests.test_shipped_links -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
DIRS = ("skills", "agents", "commands", "references", "templates", "docs")
LINK = re.compile(r"\]\(([^)\s]+)\)")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


def broken_links() -> list[str]:
    broken: list[str] = []
    for top in DIRS:
        for path in sorted((PLUGIN / top).rglob("*.md")):
            in_fence = False
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.lstrip().startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                for target in LINK.findall(line):
                    file_part = target.split("#", 1)[0]
                    if (
                        not file_part
                        or SCHEME.match(target)
                        or any(ch in file_part for ch in "<{$*")
                        or file_part.startswith(".flow/")
                    ):
                        continue
                    resolved = (path.parent / file_part).resolve()
                    inside = resolved.is_relative_to(PLUGIN)
                    if resolved.exists() and (inside or top == "docs"):
                        continue
                    where = path.relative_to(PLUGIN)
                    reason = "missing" if not resolved.exists() else "outside the plugin root"
                    broken.append(f"{where}:{number}: {target} ({reason})")
    return broken


class ShippedLinksTest(unittest.TestCase):
    def test_every_relative_link_resolves_in_the_plugin_layout(self) -> None:
        broken = broken_links()
        if broken:
            self.fail("broken shipped links:\n" + "\n".join(broken))


if __name__ == "__main__":
    unittest.main()
