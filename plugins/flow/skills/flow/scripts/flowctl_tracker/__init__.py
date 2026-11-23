"""Deterministic tracker transport for flowctl (fn-139 spec A).

WHY THIS IS A PACKAGE, AND WHY THE NAME IS NAMESPACED.

flowctl ships as *named files*, not a package, so a package only reaches a
user when the distribution paths copy it. The Codex, Cursor and OpenCode
installers copy this package and verify it against its manifest
(`scripts/lib/verify_tracker_manifest.py`); Claude Code installs the whole plugin.

The name is `flowctl_tracker`, never a bare `tracker`: the launcher runs
`flowctl_bootstrap.py` as a script, so `sys.path[0]` is that file's directory
and this package sits directly on `sys.path`. A generic top-level name there
would collide with anything else a user happens to have installed.

Adapters land in `providers/` in later tasks; this module holds no transport
logic and imports nothing from flowctl, so the dependency runs one way only.
"""

# Deliberately no __version__ here. An earlier draft carried one claiming to
# track the flow-next release while hardcoding a value the manifests contradict.
# Nothing consumes it yet, and distribution/version wiring is task .5 - a field
# that lies is worse than an absent one.

__all__: list[str] = []
