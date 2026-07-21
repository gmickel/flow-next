#!/usr/bin/env python3
"""Small, source-authoritative startup front end for the bundled flowctl CLI.

Only exact static commands use tracked fast-path data. Every other command
compiles ``flowctl.py`` from source in memory; ignored executable caches are
never read or written.
"""

import hashlib
import importlib.util
import os
import sys
import types
from pathlib import Path


MIN_PYTHON = (3, 11)
SOURCE_NAME = "flowctl.py"
HELP_NAME = "flowctl-help.txt"
SOURCE_SHA256 = "74013601ba3f6bcb0a697a01b11f12468f69c6eca140e6d2274d069e47cb0706"
HELP_SHA256 = "ad7c987b1f90e8dd12f1e22c6ec4163c72222c3bbf49111ce278337258f01d85"
USAGE_ERROR = (
    "No usage guide found (searched the plugin's templates/usage.md, then "
    ".flow/usage.md). Reinstall/update the flow-next plugin, or run "
    "/flow-next:setup."
)


def _runtime_error() -> int:
    found = ".".join(str(part) for part in sys.version_info[:3])
    print(
        "flowctl: Python 3.11 or newer is required "
        f"(selected interpreter is Python {found}).",
        file=sys.stderr,
    )
    print(
        "  Install a supported Python, or set PYTHON_BIN to its command name.",
        file=sys.stderr,
    )
    return 1


def _reconfigure_stdio_utf8() -> None:
    """Match flowctl's legacy-codepage-safe output contract."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def _repo_root() -> Path:
    """Mirror flowctl's success-only git-root lookup for the usage fast path."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, OSError):
        return Path.cwd()


def _usage_fast_path(source: Path) -> int:
    bundled = source.parent.parent / "templates" / "usage.md"
    try:
        if bundled.is_file():
            sys.stdout.write(bundled.read_text(encoding="utf-8"))
            return 0
    except OSError:
        pass

    local = _repo_root() / ".flow" / "usage.md"
    for candidate in (local,):
        try:
            if candidate.is_file():
                sys.stdout.write(candidate.read_text(encoding="utf-8"))
                return 0
        except OSError:
            continue
    print(f"Error: {USAGE_ERROR}", file=sys.stderr)
    return 1


def _load_flowctl(source: Path):
    source_bytes = source.read_bytes()
    code = compile(source_bytes, str(source), "exec")

    spec = importlib.util.spec_from_file_location("flowctl", source)
    module = types.ModuleType("flowctl")
    module.__file__ = str(source)
    module.__cached__ = None
    module.__loader__ = spec.loader if spec is not None else None
    module.__package__ = ""
    module.__spec__ = spec
    sys.modules["flowctl"] = module
    exec(code, module.__dict__)
    return module


def _root_help_fast_path(source: Path) -> bool:
    """Write authenticated static help, or decline safely to live argparse."""
    # argparse deliberately honors terminal width through COLUMNS. Static text
    # is valid only for the default layout captured in flowctl-help.txt.
    if "COLUMNS" in os.environ or getattr(sys.stdout, "isatty", lambda: False)():
        return False

    help_path = source.with_name(HELP_NAME)
    try:
        source_bytes = source.read_bytes()
        help_bytes = help_path.read_bytes()
        if hashlib.sha256(source_bytes).hexdigest() != SOURCE_SHA256:
            return False
        if hashlib.sha256(help_bytes).hexdigest() != HELP_SHA256:
            return False
        help_text = help_bytes.decode("utf-8")
    except (OSError, UnicodeError):
        return False

    sys.stdout.write(help_text)
    return True


def main() -> int:
    if sys.version_info < MIN_PYTHON:
        return _runtime_error()

    _reconfigure_stdio_utf8()

    source = Path(__file__).resolve().with_name(SOURCE_NAME)
    if sys.argv[1:] == ["usage"]:
        return _usage_fast_path(source)
    if sys.argv[1:] == ["--help"] and _root_help_fast_path(source):
        return 0

    sys.argv[0] = str(source)
    module = _load_flowctl(source)
    module.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
