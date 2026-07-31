"""Committed flow-config JSON Schema + generator honesty (fn-138.1).

Run: python3 -m unittest discover -s plugins/flow-next/tests -p "test_flow_config_schema.py" -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
ARTIFACT = ROOT / "schema" / "flow-config.schema.json"
GENERATOR = REPO / "scripts" / "gen_flow_config_schema.py"
GITATTRIBUTES = REPO / ".gitattributes"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(REPO / "scripts"))
import flowctl  # noqa: E402
import gen_flow_config_schema  # noqa: E402
from flowctl_tracker.resolved_cache import SCOPES  # noqa: E402


def _default_leaves(obj: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        if not obj:
            out[prefix] = obj
            return out
        for key, val in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            out.update(_default_leaves(val, path))
        return out
    out[prefix] = obj
    return out


def _schema_default_paths(node: dict, prefix: str = "") -> set[str]:
    """Collect paths of properties nodes that carry a default.

    Walks ``properties`` only - does not descend into patternProperties /
    additionalProperties subschemas.
    """
    found: set[str] = set()
    props = node.get("properties")
    if not isinstance(props, dict):
        return found
    for key, child in props.items():
        if not isinstance(child, dict):
            continue
        path = f"{prefix}.{key}" if prefix else key
        if "default" in child:
            found.add(path)
        found |= _schema_default_paths(child, path)
    return found


def _assert_descriptions(testcase: unittest.TestCase, node: dict) -> None:
    """Every properties node has a non-empty description.

    Skips subschemas under patternProperties / additionalProperties / anyOf.
    """
    props = node.get("properties")
    if not isinstance(props, dict):
        return
    for key, child in props.items():
        testcase.assertIsInstance(child, dict, key)
        desc = child.get("description")
        testcase.assertIsInstance(desc, str, key)
        testcase.assertTrue(desc.strip(), f"empty description at {key}")
        _assert_descriptions(testcase, child)


class FlowConfigSchema(unittest.TestCase):
    def test_artifact_exists_and_declares_meta(self) -> None:
        self.assertTrue(ARTIFACT.is_file(), ARTIFACT)
        data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(
            data["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertEqual(
            data["$id"],
            "https://flow-next.dev/schema/flow-config.schema.json",
        )

    def test_byte_identity_regen(self) -> None:
        self.assertEqual(
            gen_flow_config_schema.render().encode("utf-8"),
            ARTIFACT.read_bytes(),
            "run scripts/gen_flow_config_schema.py",
        )

    def test_determinism(self) -> None:
        self.assertEqual(
            gen_flow_config_schema.render(),
            gen_flow_config_schema.render(),
        )

    def test_byte_hygiene(self) -> None:
        raw = ARTIFACT.read_bytes()
        self.assertTrue(raw.endswith(b"\n"), "missing trailing newline")
        self.assertFalse(raw.endswith(b"\n\n"), "double trailing newline")
        self.assertNotIn(b"\r", raw)

    def test_generator_check_mode_agrees(self) -> None:
        out = subprocess.run(
            [sys.executable, str(GENERATOR), "--check"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_defaults_honesty_both_directions(self) -> None:
        defaults = _default_leaves(flowctl.get_default_config())
        schema = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        for path, value in defaults.items():
            node: Any = schema
            for part in path.split("."):
                self.assertIn(
                    "properties",
                    node,
                    f"no properties while descending to {path}",
                )
                self.assertIn(part, node["properties"], path)
                node = node["properties"][part]
            self.assertIn("default", node, path)
            self.assertEqual(node["default"], value, path)
        schema_defaults = _schema_default_paths(schema)
        self.assertEqual(schema_defaults, set(defaults))

    def test_root_schema_property_and_closed(self) -> None:
        schema = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        props = schema["properties"]
        self.assertEqual(props["$schema"]["type"], "string")
        self.assertIs(schema["additionalProperties"], False)

    def test_tracker_resolved_contract(self) -> None:
        schema = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        tracker = schema["properties"]["tracker"]["properties"]
        resolved = tracker["resolved"]
        per_tracker = tracker["perTracker"]
        self.assertIs(resolved["additionalProperties"], True)
        self.assertIs(per_tracker["additionalProperties"], True)
        self.assertNotIn("required", resolved)
        self.assertNotIn("default", resolved)
        sra = resolved["properties"]["scopeResolvedAt"]
        self.assertEqual(list(sra["properties"]), list(SCOPES))
        self.assertIs(sra["additionalProperties"], False)

    def test_gitattributes_schema_lf(self) -> None:
        text = GITATTRIBUTES.read_text(encoding="utf-8")
        self.assertIn("*.schema.json text eol=lf", text)

    def test_every_property_has_description(self) -> None:
        schema = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        _assert_descriptions(self, schema)


if __name__ == "__main__":
    unittest.main()
