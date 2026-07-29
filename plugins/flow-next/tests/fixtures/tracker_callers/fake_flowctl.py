#!/usr/bin/env python3
"""Instrumented flowctl used by the tracker caller execution harness."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


OP_INPUTS = {
    "push": {"--flow-file", "--body-file"},
    "pull": {"--flow-file", "--body-file", "--comments-file"},
    "reconcile": {
        "--flow-file",
        "--body-file",
        "--comments-file",
        "--source-body-file",
    },
    "comment": {"--body-file"},
}
ALL_INPUTS = {
    "--flow-file",
    "--body-file",
    "--comments-file",
    "--source-body-file",
}


def _record(argv: list[str]) -> None:
    with open(os.environ["CALL_LOG"], "a", encoding="utf-8") as handle:
        handle.write(json.dumps(argv, separators=(",", ":")) + "\n")


def _validate_facade(argv: list[str]) -> tuple[str, str]:
    if len(argv) < 7 or argv[3] != "--op" or argv[5] != "--event":
        raise SystemExit("invalid tracker sync prefix: " + repr(argv))
    op, event = argv[4], argv[6]
    if op not in OP_INPUTS:
        raise SystemExit("invalid tracker sync operation: " + repr(op))
    tail = argv[7:]
    status_only = "--status-only" in tail
    if status_only:
        if op != "push" or tail.count("--status-only") != 1:
            raise SystemExit("invalid --status-only modifier: " + repr(tail))
        tail = [arg for arg in tail if arg != "--status-only"]
    if len(tail) % 2:
        raise SystemExit("input flags require values: " + repr(tail))
    supplied = {}
    for index in range(0, len(tail), 2):
        flag, value = tail[index : index + 2]
        if flag not in ALL_INPUTS or flag in supplied:
            raise SystemExit("invalid or duplicate input flag: " + repr(flag))
        supplied[flag] = value
        if not Path(value).is_file():
            raise SystemExit("input file does not exist: " + repr(value))
    required = OP_INPUTS[op]
    if set(supplied) != required:
        raise SystemExit(
            f"{op} input mismatch: expected {sorted(required)}, "
            f"got {sorted(supplied)}"
        )
    return op, event


def main() -> int:
    argv = sys.argv[1:]
    _record(argv)
    if argv[:2] == ["config", "get"]:
        leaf = os.environ["TRACKER_LEAF"]
        if argv == ["config", "get", "--json"]:
            print(json.dumps({"value": {"tracker": {"perEvent": {"plan": leaf}}}}))
        else:
            print(json.dumps({"value": leaf}))
    elif argv[:2] == ["sync", "active"]:
        print(json.dumps({"active": os.environ["BRIDGE_ACTIVE"] == "true"}))
    elif argv[:2] == ["tracker", "sync"]:
        op, event = _validate_facade(argv)
        print(json.dumps({"success": True, "status": "noop", "op": op, "event": event}))
    else:
        raise SystemExit("unexpected fake flowctl argv: " + repr(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
