"""fn-201.3 / R5+R6 — OpenCode installer: command stubs, read-surface pin,
path-ownership, R2 layout, --uninstall, reinstall identity.

Generator command-stub tests drive opencode_generate.py against fixtures (no
live skill prose). Installer tests run scripts/install-opencode.sh via --dest
into tempdirs; skipped on native Windows.

Run:
    python3 -m unittest test_install_opencode -q
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))  # flowctl_tracker reachability (test_tracker_package_import guard)
HERE = Path(__file__).resolve()
PLUGIN = HERE.parent.parent
REPO = PLUGIN.parent.parent
INSTALLER = REPO / "scripts" / "install-opencode.sh"
GENERATOR = PLUGIN / "scripts" / "lib" / "opencode_generate.py"
SKILLS = PLUGIN / "skills"
FIXTURES = HERE.parent / "fixtures" / "opencode-install"
VERIFIER = PLUGIN / "scripts" / "lib" / "verify_tracker_manifest.py"
MANIFEST_NAME = ".flow-next-opencode-manifest"

INSTALLED_SUPPORT_DIRS = frozenset({"scripts", "templates", "references", "docs"})

# Named, reason-annotated exclusions (spec Architecture derivation rule).
READ_SURFACE_EXCLUSIONS = {
    ".claude-plugin": "host manifest, not a runtime read",
    ".cursor-plugin": "host manifest",
    ".codex-plugin": "host manifest",
    "codex": "committed Codex rewrite mirror (must not land at dest)",
    "skills": "installed separately (and minus flow-next-setup/)",
    "commit": "non-filesystem noise (URL fragment)",
    "..": "non-filesystem noise (../../../ matching ../../ then ..)",
}

_PLUGIN_ROOT_SEG = re.compile(r"\$\{PLUGIN_ROOT\}/([A-Za-z0-9._-]+)")
_DOTDOT_SEG = re.compile(r"\.\./\.\./([A-Za-z0-9._-]+)")
_SUPPORT_DIRS_RE = re.compile(r"^SUPPORT_DIRS=\(([^)]*)\)", re.M)


def _load_generate() -> Any:
    spec = importlib.util.spec_from_file_location(
        "opencode_generate_install_under_test", GENERATOR
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {GENERATOR}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _is_cruft(path: Path) -> bool:
    if path.suffix == ".pyc" or path.name == ".DS_Store":
        return True
    return any(part == "__pycache__" for part in path.parts)


def _tree(root: Path) -> dict[str, bytes | None]:
    out: dict[str, bytes | None] = {}
    for path in sorted(root.rglob("*")):
        if _is_cruft(path):
            continue
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            out[rel] = None
        elif path.is_file():
            out[rel] = path.read_bytes()
    return out


def _manifest_paths(dest: Path) -> list[str]:
    text = (dest / MANIFEST_NAME).read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line]


def _is_claimed(rel: str, owned: set[str]) -> bool:
    if rel in owned:
        return True
    prefix = rel + "/"
    return any(item.startswith(prefix) for item in owned)


def _derived_read_segments() -> set[str]:
    segs: set[str] = set()
    for path in SKILLS.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        segs.update(_PLUGIN_ROOT_SEG.findall(text))
        segs.update(_DOTDOT_SEG.findall(text))
    return segs


class TestOpencodeCommandStubs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gen = _load_generate()

    def test_skill_backed_stub_has_description_arguments_and_installed_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "dest"
            paths = Path(tmp) / "paths"
            buf = StringIO()
            with redirect_stdout(buf):
                rels = self.gen.generate_commands(
                    FIXTURES / "commands",
                    FIXTURES / "skills",
                    dest,
                    paths,
                )
            stub = dest / "commands" / "flow-next-plan.md"
            self.assertTrue(stub.is_file())
            self.assertIn("commands/flow-next-plan.md", rels)
            text = stub.read_text(encoding="utf-8")
            self.assertIn(
                "description: Fixture plan skill for OpenCode command stubs.",
                text,
            )
            self.assertIn("$ARGUMENTS", text)
            installed = dest.resolve() / "skills" / "flow-next-plan" / "SKILL.md"
            self.assertIn(str(installed), text)
            self.assertNotIn("flow-next-flow-next-plan.md", text)
            self.assertFalse((dest / "commands" / "flow-next-flow-next-plan.md").exists())

    def test_uninstall_is_copied_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "dest"
            paths = Path(tmp) / "paths"
            with redirect_stdout(StringIO()):
                self.gen.generate_commands(
                    FIXTURES / "commands",
                    FIXTURES / "skills",
                    dest,
                    paths,
                )
            got = (dest / "commands" / "flow-next-uninstall.md").read_bytes()
            expected = (FIXTURES / "commands" / "uninstall.md").read_bytes()
            self.assertEqual(got, expected)

    def test_setup_is_excluded_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "dest"
            paths = Path(tmp) / "paths"
            buf = StringIO()
            with redirect_stdout(buf):
                rels = self.gen.generate_commands(
                    FIXTURES / "commands",
                    FIXTURES / "skills",
                    dest,
                    paths,
                )
            self.assertIn(self.gen.SETUP_EXCLUSION_NOTE, buf.getvalue())
            self.assertFalse((dest / "commands" / "flow-next-setup.md").exists())
            self.assertFalse((dest / "commands" / "setup.md").exists())
            self.assertNotIn("commands/flow-next-setup.md", rels)

    def test_command_without_skill_dir_is_not_in_roster(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "dest"
            paths = Path(tmp) / "paths"
            with redirect_stdout(StringIO()):
                rels = self.gen.generate_commands(
                    FIXTURES / "commands",
                    FIXTURES / "skills",
                    dest,
                    paths,
                )
            self.assertFalse((dest / "commands" / "flow-next-orphan.md").exists())
            self.assertNotIn("commands/flow-next-orphan.md", rels)


class TestOpencodeReadSurfacePin(unittest.TestCase):
    """derived − exclusions == installed support dirs.

    A naive equality over the raw grep matches host manifests, the codex/
    mirror, sibling-skill ../../ links, and non-path noise. A NEW segment
    that is in neither the named exclusion list (plus skill-dir names) nor
    INSTALLED_SUPPORT_DIRS fails this test.
    """

    def test_installer_support_dirs_match_the_pinned_set(self) -> None:
        text = INSTALLER.read_text(encoding="utf-8")
        match = _SUPPORT_DIRS_RE.search(text)
        self.assertIsNotNone(match, "SUPPORT_DIRS=(...) missing from installer")
        self.assertEqual(set(match.group(1).split()), set(INSTALLED_SUPPORT_DIRS))

    def test_derived_minus_exclusions_equals_installed_support_dirs(self) -> None:
        derived = _derived_read_segments()
        self.assertTrue(derived, "grep of skills/ produced no PLUGIN_ROOT/ or ../../ segments")
        skill_names = {p.name for p in SKILLS.iterdir() if p.is_dir()}
        excluded: set[str] = set()
        unknown_exclusions: list[str] = []
        for seg in derived:
            if seg in READ_SURFACE_EXCLUSIONS:
                excluded.add(seg)
            elif seg in skill_names:
                excluded.add(seg)
            elif seg in INSTALLED_SUPPORT_DIRS:
                continue
            else:
                unknown_exclusions.append(seg)
        self.assertEqual(
            unknown_exclusions,
            [],
            "new unhandled plugin-root segment(s) in skills/ grep — add to "
            "INSTALLED_SUPPORT_DIRS (and the installer) or to "
            "READ_SURFACE_EXCLUSIONS with a reason: "
            + ", ".join(sorted(unknown_exclusions)),
        )
        support = derived - excluded
        self.assertEqual(
            support,
            set(INSTALLED_SUPPORT_DIRS),
            "derived − exclusions != installed support dirs "
            f"(derived={sorted(derived)} excluded={sorted(excluded)} "
            f"support={sorted(support)} installed={sorted(INSTALLED_SUPPORT_DIRS)})",
        )
        leftover_named = set(READ_SURFACE_EXCLUSIONS) - derived
        # Named reasons stay even if a grep currently misses them; they
        # document why those segments must never become support dirs.
        self.assertIn(".claude-plugin", leftover_named | derived)


@unittest.skipIf(
    sys.platform == "win32",
    "POSIX shell installer test; plain `bash` on Windows resolves to the WSL stub",
)
@unittest.skipIf(shutil.which("bash") is None, "bash not available")
class TestOpencodeInstaller(unittest.TestCase):
    def _run(
        self, dest: Path, extra: list[str] | None = None, home: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["HOME"] = str(home if home is not None else dest.parent / "home")
        env.pop("XDG_CONFIG_HOME", None)
        cmd = ["bash", str(INSTALLER), "--dest", str(dest)]
        if extra:
            cmd.extend(extra)
        return subprocess.run(
            cmd,
            cwd=str(REPO),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )

    def test_writes_stay_inside_manifest_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "opencode"
            sibling = dest / "user-notes.txt"
            dest.mkdir()
            sibling.write_text("keep me\n", encoding="utf-8")
            parent_sentinel = root / "outside.txt"
            parent_sentinel.write_text("parent stays\n", encoding="utf-8")
            home = root / "home"
            (home / ".claude").mkdir(parents=True)
            claude_sentinel = home / ".claude" / "keep.txt"
            claude_sentinel.write_text("claude stays\n", encoding="utf-8")

            result = self._run(dest, home=home)
            self.assertEqual(
                result.returncode, 0, f"{result.stdout}\n{result.stderr}"
            )

            owned = set(_manifest_paths(dest))
            self.assertTrue(owned, "manifest is empty")
            for rel in owned:
                self.assertFalse(
                    rel.startswith(("/", "..")) or "/../" in f"/{rel}/",
                    f"manifest lists an unsafe path: {rel}",
                )
                self.assertTrue(
                    (dest / rel).exists(), f"manifest path missing: {rel}"
                )
            extras: list[str] = []
            for rel in _tree(dest):
                if rel == MANIFEST_NAME:
                    continue
                if not _is_claimed(rel, owned):
                    extras.append(rel)
            self.assertEqual(
                extras,
                ["user-notes.txt"],
                f"installer wrote paths outside the ownership manifest: {extras}",
            )
            self.assertEqual(sibling.read_text(encoding="utf-8"), "keep me\n")
            self.assertEqual(
                parent_sentinel.read_text(encoding="utf-8"), "parent stays\n"
            )
            self.assertEqual(
                claude_sentinel.read_text(encoding="utf-8"), "claude stays\n"
            )
            self.assertFalse((home / ".config" / "opencode").exists())
            self.assertNotIn("user-notes.txt", owned)
            self.assertFalse(
                any("timestamp" in p or p.startswith("/") for p in owned)
            )

    def test_preflight_aborts_on_unclaimed_support_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "opencode"
            scripts = dest / "scripts"
            scripts.mkdir(parents=True)
            user = scripts / "mine.sh"
            user.write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
            result = self._run(dest)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("exists and is not claimed", result.stderr)
            self.assertIn(str(scripts), result.stderr)
            self.assertEqual(user.read_text(encoding="utf-8"), "#!/bin/sh\necho mine\n")
            self.assertFalse((dest / MANIFEST_NAME).exists())
            self.assertFalse((dest / "templates").exists())

    def test_force_overrides_unclaimed_support_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "opencode"
            scripts = dest / "scripts"
            scripts.mkdir(parents=True)
            user = scripts / "mine.sh"
            user.write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
            result = self._run(dest, extra=["--force"])
            self.assertEqual(
                result.returncode, 0, f"{result.stdout}\n{result.stderr}"
            )
            self.assertFalse(user.exists())
            self.assertTrue((dest / "scripts" / "flowctl").is_file())
            self.assertIn("scripts", _manifest_paths(dest))

    def test_unclaimed_sibling_dir_is_not_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "opencode"
            other = dest / "my-other-tool"
            other.mkdir(parents=True)
            keep = other / "cfg.json"
            keep.write_text("{}\n", encoding="utf-8")
            user_skill = dest / "skills" / "user-skill"
            user_skill.mkdir(parents=True)
            (user_skill / "SKILL.md").write_text("# mine\n", encoding="utf-8")
            result = self._run(dest)
            self.assertEqual(
                result.returncode, 0, f"{result.stdout}\n{result.stderr}"
            )
            self.assertEqual(keep.read_text(encoding="utf-8"), "{}\n")
            self.assertEqual(
                (user_skill / "SKILL.md").read_text(encoding="utf-8"), "# mine\n"
            )
            owned = set(_manifest_paths(dest))
            self.assertNotIn("my-other-tool", owned)
            self.assertNotIn("skills/user-skill", owned)
            self.assertFalse((dest / "skills" / "flow-next-setup").exists())

    def test_r2_layout_two_levels_up_flowctl_and_templates(self) -> None:
        # Self-referential on the pinned directory names (skills/, scripts/,
        # templates/). Host discovery of agents/commands is the R2 MANUAL
        # item and is never asserted here.
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "opencode"
            result = self._run(dest)
            self.assertEqual(
                result.returncode, 0, f"{result.stdout}\n{result.stderr}"
            )
            skill_mds = sorted(dest.glob("skills/*/SKILL.md"))
            self.assertTrue(skill_mds, "no installed skills/<name>/SKILL.md")
            for skill_md in skill_mds:
                flowctl = (skill_md.parent / "../../scripts/flowctl").resolve()
                spec = (skill_md.parent / "../../templates/spec.md").resolve()
                self.assertTrue(
                    flowctl.is_file(),
                    f"{skill_md}: ../../scripts/flowctl missing at {flowctl}",
                )
                self.assertTrue(
                    os.access(flowctl, os.X_OK),
                    f"{skill_md}: ../../scripts/flowctl is not executable",
                )
                self.assertTrue(
                    spec.is_file(),
                    f"{skill_md}: ../../templates/spec.md missing at {spec}",
                )
            verify = subprocess.run(
                [sys.executable, str(VERIFIER), str(dest / "scripts")],
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)

    def test_uninstall_removes_manifest_paths_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "opencode"
            dest.mkdir()
            sibling = dest / "user-notes.txt"
            sibling.write_text("keep me\n", encoding="utf-8")
            user_skill = dest / "skills" / "user-skill"
            user_skill.mkdir(parents=True)
            (user_skill / "SKILL.md").write_text("# mine\n", encoding="utf-8")
            result = self._run(dest)
            self.assertEqual(
                result.returncode, 0, f"{result.stdout}\n{result.stderr}"
            )
            owned = list(_manifest_paths(dest))
            self.assertTrue(owned)
            result = self._run(dest, extra=["--uninstall"])
            self.assertEqual(
                result.returncode, 0, f"{result.stdout}\n{result.stderr}"
            )
            self.assertFalse((dest / MANIFEST_NAME).exists())
            for rel in owned:
                target = dest / rel
                self.assertFalse(
                    target.exists(), f"uninstall left manifest path: {rel}"
                )
            self.assertEqual(sibling.read_text(encoding="utf-8"), "keep me\n")
            self.assertEqual(
                (user_skill / "SKILL.md").read_text(encoding="utf-8"), "# mine\n"
            )
            self.assertFalse((dest / "skills" / "flow-next-plan").exists())
            self.assertFalse((dest / "scripts" / "flowctl").exists())

    def test_uninstall_refuses_unsafe_relpath_and_removes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "opencode"
            dest.mkdir()
            keep = dest / "keep.txt"
            keep.write_text("in dest\n", encoding="utf-8")
            outside = root / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            (dest / MANIFEST_NAME).write_text(
                "keep.txt\n../outside.txt\n", encoding="utf-8"
            )
            result = self._run(dest, extra=["--uninstall"])
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("unsafe path", result.stderr)
            self.assertIn("../outside.txt", result.stderr)
            self.assertTrue((dest / MANIFEST_NAME).is_file())
            self.assertEqual(keep.read_text(encoding="utf-8"), "in dest\n")
            self.assertEqual(outside.read_text(encoding="utf-8"), "outside\n")

    def test_uninstall_without_manifest_guesses_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "opencode"
            dest.mkdir()
            keep = dest / "scripts"
            keep.mkdir()
            (keep / "mine.sh").write_text("stay\n", encoding="utf-8")
            result = self._run(dest, extra=["--uninstall"])
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("no ownership manifest", result.stderr)
            self.assertEqual((keep / "mine.sh").read_text(encoding="utf-8"), "stay\n")

    def test_rerun_drops_stale_manifest_paths_only(self) -> None:
        """The OLD_MANIFEST comm -23 branch: a path the previous manifest owned
        but this snapshot no longer ships is removed on re-run; an unclaimed
        sibling in the same tree survives."""
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "opencode"
            result = self._run(dest)
            self.assertEqual(
                result.returncode, 0, f"{result.stdout}\n{result.stderr}"
            )
            stale = dest / "skills" / "flow-next-retired" / "SKILL.md"
            stale.parent.mkdir(parents=True)
            stale.write_text("# retired upstream\n", encoding="utf-8")
            unclaimed = dest / "skills" / "user-own" / "SKILL.md"
            unclaimed.parent.mkdir(parents=True)
            unclaimed.write_text("# mine\n", encoding="utf-8")
            manifest = dest / MANIFEST_NAME
            lines = manifest.read_text(encoding="utf-8").splitlines()
            lines += [
                "skills/flow-next-retired",
                "skills/flow-next-retired/SKILL.md",
            ]
            manifest.write_text(
                "\n".join(sorted(set(lines))) + "\n", encoding="utf-8"
            )
            result = self._run(dest)
            self.assertEqual(
                result.returncode, 0, f"{result.stdout}\n{result.stderr}"
            )
            self.assertFalse(stale.parent.exists(), "stale owned path survived")
            self.assertTrue(unclaimed.exists(), "unclaimed sibling was deleted")
            self.assertNotIn(
                "skills/flow-next-retired",
                (dest / MANIFEST_NAME).read_text(encoding="utf-8"),
            )

    def test_reinstall_after_uninstall_is_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "opencode"
            first = self._run(dest)
            self.assertEqual(first.returncode, 0, f"{first.stdout}\n{first.stderr}")
            before = _tree(dest)
            self.assertIn(MANIFEST_NAME, before)
            uninstall = self._run(dest, extra=["--uninstall"])
            self.assertEqual(
                uninstall.returncode, 0, f"{uninstall.stdout}\n{uninstall.stderr}"
            )
            second = self._run(dest)
            self.assertEqual(
                second.returncode, 0, f"{second.stdout}\n{second.stderr}"
            )
            after = _tree(dest)
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
