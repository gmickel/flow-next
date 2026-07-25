"""Every flowctl subcommand referenced in canonical skill prose must exist.

Hardened gate (fn-122 audit outcome, 2026-07-25) graduated from
.flow/memory/bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10:
skill workflows repeatedly invented or misremembered flowctl surfaces, and the
lesson was re-taught by four separate specs (fn-59, fn-68, fn-82, fn-122) in
six weeks. This test makes the subcommand half of that class impossible: it
extracts every ``$FLOWCTL <subcommand>`` invocation from the canonical skill
tree and asserts the first token is a registered top-level subcommand.

Scope is deliberately the deterministic half only. Field names, enum values,
and flag semantics stay judgment (the memory entry remains on disk as the
pointer explaining this gate). The codex mirror is excluded: it is generated,
and sync-codex.sh carries its own guards.
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "plugins" / "flow-next" / "skills"
FLOWCTL_PY = REPO_ROOT / "plugins" / "flow-next" / "scripts" / "flowctl.py"

# `$FLOWCTL <token>` / `"$FLOWCTL" <token>` / `${FLOWCTL} <token>`.
# The token must start with a lowercase letter, so flags (`--help`) never
# match; an inline-code mention like ``` `$FLOWCTL` is the CLI ``` never
# matches either because a backtick, not whitespace, follows the variable.
_INVOCATION = re.compile(
    r'(?:"\$\{?FLOWCTL\}?"|\$\{?FLOWCTL\}?)\s+([a-z][a-z0-9-]*)'
)


def registered_subcommands() -> frozenset[str]:
    """The real top-level subcommand set, from flowctl's own argparse help."""
    result = subprocess.run(
        [sys.executable, str(FLOWCTL_PY), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    match = re.search(r"\{([a-z0-9_,\-]+)\}", result.stdout + result.stderr)
    if not match:
        raise AssertionError(
            "could not parse the subcommand set from `flowctl --help` output"
        )
    return frozenset(match.group(1).split(","))


def referenced_subcommands(root: Path) -> list[tuple[str, int, str]]:
    """(file, line, token) for every $FLOWCTL invocation under root."""
    hits: list[tuple[str, int, str]] = []
    for path in sorted(root.rglob("*.md")):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for match in _INVOCATION.finditer(line):
                hits.append(
                    (str(path.relative_to(REPO_ROOT)), lineno, match.group(1))
                )
    return hits


class TestSkillProseFlowctlSurface(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = registered_subcommands()
        cls.hits = referenced_subcommands(SKILLS_DIR)

    def test_prose_actually_references_flowctl(self) -> None:
        # Guard the gate itself: if extraction ever silently matches nothing,
        # the main assertion would pass vacuously.
        self.assertGreater(
            len(self.hits),
            20,
            "extraction found implausibly few $FLOWCTL invocations - the "
            "regex or the skills path has drifted; fix the gate, not the prose",
        )

    def test_skill_prose_references_real_flowctl_subcommands(self) -> None:
        unknown = [
            f"{path}:{lineno}: $FLOWCTL {token}"
            for path, lineno, token in self.hits
            if token not in self.registry
        ]
        self.assertEqual(
            unknown,
            [],
            "skill prose references flowctl subcommands that do not exist "
            "(invented or renamed surface - fix the prose or register the "
            "subcommand):\n" + "\n".join(unknown),
        )

    def test_gate_fires_on_bogus_subcommand(self) -> None:
        # Negative self-test: prove the checker detects the defect class it
        # exists for, so a refactor cannot silently neuter it.
        sample = 'run `"$FLOWCTL" frobnicate-specs fn-1 --json` before commit'
        tokens = [m.group(1) for m in _INVOCATION.finditer(sample)]
        self.assertEqual(tokens, ["frobnicate-specs"])
        self.assertNotIn("frobnicate-specs", self.registry)


if __name__ == "__main__":
    unittest.main()
