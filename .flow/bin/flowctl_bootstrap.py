#!/usr/bin/env python3
"""Source-first startup accelerator for the bundled flowctl CLI.

The launcher always reads and hashes ``flowctl.py`` before accepting cached
bytecode.  Cache files are interpreter-tagged, checked-hash ``.pyc`` files in
the standard ignored ``__pycache__`` directory.  Missing, stale, corrupt, or
unwritable cache state falls back to compiling the source in memory.
"""

import importlib.util
import marshal
import sys
import types
from pathlib import Path


MIN_PYTHON = (3, 11)
SOURCE_NAME = "flowctl.py"
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


def _checked_cache_code(source: Path, source_bytes: bytes) -> types.CodeType:
    """Load code only from a valid checked-hash cache for this exact source."""
    cache = Path(importlib.util.cache_from_source(str(source)))
    data = cache.read_bytes()
    if len(data) < 17 or data[:4] != importlib.util.MAGIC_NUMBER:
        raise ValueError("invalid bytecode header")
    flags = int.from_bytes(data[4:8], "little")
    if flags & 0b11 != 0b11:
        raise ValueError("cache is not checked-hash bytecode")
    if data[8:16] != importlib.util.source_hash(source_bytes):
        raise ValueError("source hash changed")
    code = marshal.loads(data[16:])
    if not isinstance(code, types.CodeType):
        raise ValueError("cache payload is not code")
    return code


def _source_code(source: Path, source_bytes: bytes) -> types.CodeType:
    """Refresh checked-hash bytecode best-effort, then fall back to source."""
    import py_compile

    try:
        py_compile.compile(
            str(source),
            cfile=importlib.util.cache_from_source(str(source)),
            doraise=True,
            invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH,
        )
        return _checked_cache_code(source, source_bytes)
    except (ImportError, OSError, EOFError, ValueError, py_compile.PyCompileError):
        return compile(source_bytes, str(source), "exec")


def _load_flowctl(source: Path):
    source_bytes = source.read_bytes()
    try:
        code = _checked_cache_code(source, source_bytes)
    except (ImportError, OSError, EOFError, ValueError):
        code = _source_code(source, source_bytes)

    spec = importlib.util.spec_from_file_location("flowctl", source)
    module = types.ModuleType("flowctl")
    module.__file__ = str(source)
    module.__cached__ = importlib.util.cache_from_source(str(source))
    module.__loader__ = spec.loader if spec is not None else None
    module.__package__ = ""
    module.__spec__ = spec
    sys.modules["flowctl"] = module
    exec(code, module.__dict__)
    return module


def main() -> int:
    if sys.version_info < MIN_PYTHON:
        return _runtime_error()

    source = Path(__file__).resolve().with_name(SOURCE_NAME)
    if sys.argv[1:] == ["usage"]:
        return _usage_fast_path(source)

    sys.argv[0] = str(source)
    module = _load_flowctl(source)
    module.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
