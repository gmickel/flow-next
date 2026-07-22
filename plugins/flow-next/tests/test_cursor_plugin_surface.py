"""Cursor marketplace + plugin surface drift guard (fn-123 R1/R2/R9/R11).

Validates:

  - root ``.cursor-plugin/marketplace.json`` imports ``plugins/flow-next`` as
    the sole plugin source (team-marketplace repo import; no public-marketplace
    submission metadata);
  - ``plugins/flow-next/.cursor-plugin/plugin.json`` declares explicit
    ``skills`` / ``agents`` / ``commands`` / ``rules`` component paths so a
    whole-repo marketplace import never discovers ``codex/`` or ``tests/`` as
    components;
  - every declared component path resolves under the plugin root;
  - every skill / agent / command has non-empty ``name`` and ``description``
    frontmatter (Cursor marketplace review checklist shape);
  - ``rules/flow-next.mdc`` is the Cursor guidance rail: proper .mdc frontmatter,
    ``.flow/bin/flowctl`` resolution, lifecycle + the two ``flowctl usage``
    pull directives.

Pure file/JSON checks — no Cursor install required.

Run:
    python3 -m unittest test_cursor_plugin_surface -q
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent           # plugins/flow-next
REPO_ROOT = PLUGIN_DIR.parent.parent      # repo root

MARKETPLACE = REPO_ROOT / ".cursor-plugin" / "marketplace.json"
PLUGIN_MANIFEST = PLUGIN_DIR / ".cursor-plugin" / "plugin.json"
RULE = PLUGIN_DIR / "rules" / "flow-next.mdc"

# Cursor schema (https://github.com/cursor/plugins schemas): marketplace
# pluginEntry allows only name/source/description; owner allows name/email.
MARKETPLACE_TOP_KEYS = frozenset({"name", "owner", "metadata", "plugins"})
PLUGIN_ENTRY_KEYS = frozenset({"name", "source", "description"})
OWNER_KEYS = frozenset({"name", "email"})
REQUIRED_COMPONENT_KEYS = ("skills", "agents", "commands", "rules")

# Declared paths must stay inside the canonical component trees — never codex/
# or tests/ (discovery stop; dirs may still exist on whole-repo import).
FORBIDDEN_PATH_FRAGMENTS = ("codex", "tests")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_frontmatter(text: str) -> dict[str, str] | None:
    """Minimal YAML frontmatter extractor for name/description/alwaysApply.

    Only handles simple ``key: value`` / ``key: "quoted"`` lines — enough for
    skill/agent/command/rule frontmatter without pulling PyYAML into the test.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    block = text[3:end]
    out: dict[str, str] = {}
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip("\"'")
        if key:
            out[key] = val
    return out


def _nonempty(val: str | None) -> bool:
    return bool(val and val.strip())


class TestCursorMarketplace(unittest.TestCase):
    def test_marketplace_exists_and_parses(self) -> None:
        self.assertTrue(
            MARKETPLACE.is_file(),
            f"missing root marketplace: {MARKETPLACE.relative_to(REPO_ROOT)}",
        )
        data = _load_json(MARKETPLACE)
        self.assertIsInstance(data, dict)
        self.assertEqual(set(data.keys()) - MARKETPLACE_TOP_KEYS, set())
        self.assertTrue(_nonempty(data.get("name")))
        self.assertIn("plugins", data)
        self.assertIsInstance(data["plugins"], list)
        self.assertEqual(len(data["plugins"]), 1, "sole plugin source must be flow-next")

    def test_marketplace_sole_source_is_plugins_flow_next(self) -> None:
        data = _load_json(MARKETPLACE)
        entry = data["plugins"][0]
        self.assertIsInstance(entry, dict)
        self.assertEqual(set(entry.keys()) - PLUGIN_ENTRY_KEYS, set())
        self.assertEqual(entry.get("name"), "flow-next")
        source = entry.get("source", "").replace("\\", "/")
        # Accept ./plugins/flow-next or plugins/flow-next
        self.assertIn(
            source.lstrip("./"),
            {"plugins/flow-next"},
            f"marketplace source must point at plugins/flow-next, got {source!r}",
        )
        self.assertTrue(_nonempty(entry.get("description")))

    def test_marketplace_owner_shape(self) -> None:
        data = _load_json(MARKETPLACE)
        owner = data.get("owner")
        self.assertIsInstance(owner, dict)
        self.assertEqual(set(owner.keys()) - OWNER_KEYS, set())
        self.assertTrue(_nonempty(owner.get("name")))

    def test_no_public_marketplace_submission_metadata(self) -> None:
        # Guard against accidentally shipping public-marketplace publisher
        # fields (rejected on terms). Team repo-import only needs name/source.
        text = MARKETPLACE.read_text(encoding="utf-8")
        for banned in ("publisherId", "submission", "anysphere", "publicMarketplace"):
            self.assertNotIn(banned, text)


class TestCursorPluginManifest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(PLUGIN_MANIFEST.is_file())
        self.data = _load_json(PLUGIN_MANIFEST)
        self.assertIsInstance(self.data, dict)

    def test_required_component_paths_declared(self) -> None:
        for key in REQUIRED_COMPONENT_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, self.data, f"plugin.json must declare '{key}'")
                self.assertTrue(
                    _nonempty(str(self.data[key])),
                    f"plugin.json '{key}' must be non-empty",
                )

    def test_component_paths_resolve_and_exclude_forbidden(self) -> None:
        for key in REQUIRED_COMPONENT_KEYS:
            raw = self.data[key]
            paths = raw if isinstance(raw, list) else [raw]
            for p in paths:
                with self.subTest(key=key, path=p):
                    rel = str(p).lstrip("./")
                    for frag in FORBIDDEN_PATH_FRAGMENTS:
                        self.assertNotIn(
                            frag,
                            Path(rel).parts,
                            f"{key} path {p!r} must not reference {frag}/",
                        )
                    target = (PLUGIN_DIR / rel).resolve()
                    self.assertTrue(
                        str(target).startswith(str(PLUGIN_DIR.resolve())),
                        f"{key} path {p!r} escapes plugin root",
                    )
                    self.assertTrue(
                        target.exists(),
                        f"{key} path {p!r} does not resolve under plugin root",
                    )

    def test_name_matches_marketplace_entry(self) -> None:
        market = _load_json(MARKETPLACE)
        self.assertEqual(self.data.get("name"), "flow-next")
        self.assertEqual(market["plugins"][0]["name"], self.data["name"])


class TestComponentFrontmatter(unittest.TestCase):
    """Every skill/agent/command needs non-empty name + description (R11)."""

    def test_skills_have_name_and_description(self) -> None:
        skills = sorted(
            p for p in (PLUGIN_DIR / "skills").iterdir()
            if p.is_dir() and (p / "SKILL.md").is_file()
        )
        self.assertGreater(len(skills), 0)
        for skill_dir in skills:
            path = skill_dir / "SKILL.md"
            with self.subTest(skill=skill_dir.name):
                fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
                self.assertIsNotNone(fm, f"{path.name}: missing frontmatter")
                assert fm is not None
                self.assertTrue(_nonempty(fm.get("name")), f"{skill_dir.name}: empty name")
                self.assertTrue(
                    _nonempty(fm.get("description")),
                    f"{skill_dir.name}: empty description",
                )

    def test_agents_have_name_and_description(self) -> None:
        agents = sorted((PLUGIN_DIR / "agents").glob("*.md"))
        self.assertGreater(len(agents), 0)
        for path in agents:
            with self.subTest(agent=path.name):
                fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
                self.assertIsNotNone(fm, f"{path.name}: missing frontmatter")
                assert fm is not None
                self.assertTrue(_nonempty(fm.get("name")), f"{path.name}: empty name")
                self.assertTrue(
                    _nonempty(fm.get("description")),
                    f"{path.name}: empty description",
                )

    def test_commands_have_description(self) -> None:
        # fn-124 flattened the shims out of the plugin-name-colliding nested
        # command directory to ``commands/*.md`` and dropped the
        # ``name:`` frontmatter (the basename governs the command name now), so
        # this checks the flat path and requires ``description`` only — no
        # ``name`` (see test_command_shim_flatten.py for the flatten guard).
        commands = sorted((PLUGIN_DIR / "commands").glob("*.md"))
        self.assertGreater(len(commands), 0)
        for path in commands:
            with self.subTest(command=path.name):
                fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
                self.assertIsNotNone(fm, f"{path.name}: missing frontmatter")
                assert fm is not None
                self.assertTrue(
                    _nonempty(fm.get("description")),
                    f"{path.name}: empty description",
                )


class TestFlowNextRule(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(RULE.is_file(), f"missing rule: {RULE.relative_to(REPO_ROOT)}")
        self.text = RULE.read_text(encoding="utf-8")
        self.fm = _parse_frontmatter(self.text)

    def test_mdc_frontmatter(self) -> None:
        self.assertIsNotNone(self.fm, "flow-next.mdc needs YAML frontmatter")
        assert self.fm is not None
        self.assertTrue(_nonempty(self.fm.get("description")))
        # alwaysApply MUST stay false: a plugin-shipped rule with alwaysApply:true
        # injects into EVERY workspace the user opens, including non-flow-next
        # repos (review finding, fn-123.1). Agent-decides via the trigger-shaped
        # description is the correct scope for a plugin rule.
        self.assertEqual(self.fm.get("alwaysApply"), "false")
        self.assertIn(".flow/", str(self.fm.get("description")))

    def test_flowctl_resolved_via_flow_bin(self) -> None:
        self.assertIn(".flow/bin/flowctl", self.text)
        # Must NOT assume plugin-root env vars or bare PATH flowctl as the primary.
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", self.text)
        self.assertNotIn("DROID_PLUGIN_ROOT", self.text)

    def test_lifecycle_commands(self) -> None:
        for token in ("list", "show", "start", "done"):
            self.assertRegex(
                self.text,
                rf"\b{token}\b",
                f"lifecycle token {token!r} missing from flow-next.mdc",
            )
        self.assertIn("summary-file", self.text)
        self.assertIn("evidence-json", self.text)

    def test_two_usage_pull_directives(self) -> None:
        # The two pull directives from the fn-121 slim snippet (Cursor analog).
        self.assertRegex(
            self.text,
            re.compile(
                r"BEFORE any other flowctl operation.*flowctl usage",
                re.IGNORECASE | re.DOTALL,
            ),
        )
        self.assertRegex(
            self.text,
            re.compile(
                r"BEFORE delegating.*flowctl usage",
                re.IGNORECASE | re.DOTALL,
            ),
        )
        self.assertIn("Orchestration & model steering", self.text)


if __name__ == "__main__":
    unittest.main()
