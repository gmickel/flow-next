"""Plugin discovery: any `.py` file on the search path whose first line is `# mycli-plugin`."""

import os
import sys

MARKER = "# mycli-plugin"
PLUGIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins")


def _search_roots():
    return [PLUGIN_DIR] + [p for p in sys.path if p and os.path.isdir(p)]


def _is_plugin(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.readline().strip() == MARKER
    except OSError:
        return False


def discover():
    found = {}
    for root in _search_roots():
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                path = os.path.join(dirpath, name)
                if name.endswith(".py") and _is_plugin(path):
                    found.setdefault(name[:-3], path)
    return found


def validate(found):
    """Re-scan the search path to confirm every discovered plugin still exists."""
    again = discover()
    return {name: path for name, path in found.items() if again.get(name) == path}
