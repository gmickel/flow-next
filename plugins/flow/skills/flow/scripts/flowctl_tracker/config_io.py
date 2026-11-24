"""Shared config reads: absence permits defaults; invalid files are reported."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

_config_read_warnings: set[str] = set()


def read_config_file(config_path: Path) -> Optional[dict]:
    """Return None only for a missing file; reject invalid persisted config."""
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise ValueError(f"{config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{config_path}: expected a JSON object")
    return data


def load_raw_config(config_path: Path) -> Optional[dict]:
    """Warn once on invalid content before readers use their defaults."""
    try:
        return read_config_file(config_path)
    except ValueError as exc:
        message = str(exc)
        if message not in _config_read_warnings:
            print(f"Warning: {message}", file=sys.stderr)
            _config_read_warnings.add(message)
        return {}
