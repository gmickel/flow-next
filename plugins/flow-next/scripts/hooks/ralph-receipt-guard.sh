#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${FLOW_RALPH:-}" && -z "${REVIEW_RECEIPT_PATH:-}" ]]; then
  exit 0
fi

if [[ -z "${REVIEW_RECEIPT_PATH:-}" ]]; then
  exit 0
fi

if [[ ! -f "$REVIEW_RECEIPT_PATH" ]]; then
  echo "Missing review receipt: $REVIEW_RECEIPT_PATH" >&2
  exit 2
fi

python3 - "$REVIEW_RECEIPT_PATH" <<'PY'
import json
import re
import sys
from pathlib import Path

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
except Exception as e:
    print(f"Invalid receipt JSON: {e}", file=sys.stderr)
    sys.exit(2)

if not isinstance(data, dict):
    print("Invalid receipt JSON: expected object", file=sys.stderr)
    sys.exit(2)

if not data.get("type") or not data.get("id"):
    print("Invalid receipt JSON: missing type/id", file=sys.stderr)
    sys.exit(2)

if data.get("verdict") not in ("SHIP", "NEEDS_WORK", "MAJOR_RETHINK"):
    print("Invalid receipt JSON: missing or invalid verdict", file=sys.stderr)
    sys.exit(2)

basename = Path(path).name
patterns = [
    (r"^plan-(fn-\d+(?:-[a-z0-9][a-z0-9-]*[a-z0-9]|-[a-z0-9]{1,3})?)\.json$", "plan_review"),
    (r"^impl-(fn-\d+(?:-[a-z0-9][a-z0-9-]*[a-z0-9]|-[a-z0-9]{1,3})?\.\d+)\.json$", "impl_review"),
    (r"^completion-(fn-\d+(?:-[a-z0-9][a-z0-9-]*[a-z0-9]|-[a-z0-9]{1,3})?)\.json$", "completion_review"),
]
for pattern, expected_type in patterns:
    match = re.match(pattern, basename)
    if match:
        if data.get("type") != expected_type or data.get("id") != match.group(1):
            print("Invalid receipt JSON: type/id do not match receipt filename", file=sys.stderr)
            sys.exit(2)
        break

sys.exit(0)
PY
