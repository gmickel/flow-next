"""fn-179 R4 (#305) — executable SPEC.md discovery HITS count.

Locks the SHIPPED Step-4a discovery formula (extracted from
flow-next-setup/workflow.md, not a copy) against the argument-echo bug:
`ls -1 SPEC.md spec.md | sort -u | wc -l` counts argument NAMES, so on a
case-insensitive filesystem (APFS, NTFS) a repo holding only SPEC.md counted 2
and took the HITS=2 branch, printing a both-files warning at a correct repo.
The formula counts distinct files by inode instead.

Pin shape: content + reachability — the fence is located by its own anchor
(the Step-4a discovery section), then EXECUTED, so a moved-but-live formula
still passes and a silently-reverted one fails.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_setup_spec_discovery_hits -q
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
PLUGIN = HERE.parent.parent
CANONICAL_WF = PLUGIN / "skills" / "flow-next-setup" / "workflow.md"

_BASH = shutil.which("bash")

# Reachability anchor: the discovery fence is the bash fence that assigns HITS.
_HITS_FENCE = re.compile(r"(?ms)^```bash\n((?:(?!^```).)*?\bHITS=.*?)^```\s*$")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _extract_hits_fence() -> str:
    text = _read(CANONICAL_WF)
    fences = _HITS_FENCE.findall(text)
    if len(fences) != 1:
        raise AssertionError(
            f"expected exactly one HITS-assigning bash fence in {CANONICAL_WF}, "
            f"found {len(fences)}"
        )
    return fences[0]


def _run_hits(fence: str, cwd: Path) -> str:
    script = f"set -eu\n{fence}\nprintf '%s\\n' \"$HITS\"\n"
    proc = subprocess.run(
        [_BASH, "-c", script],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"HITS bash failed (rc={proc.returncode}):\n"
            f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
        )
    return proc.stdout.strip()


def _fs_is_case_sensitive(d: Path) -> bool:
    probe = d / "CaseProbe.md"
    probe.write_text("x", encoding="utf-8")
    try:
        return not (d / "caseprobe.md").exists()
    finally:
        probe.unlink()


@unittest.skipUnless(_BASH, "bash required to execute the discovery fence")
class TestSpecDiscoveryHits(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not CANONICAL_WF.is_file():
            raise AssertionError(f"missing {CANONICAL_WF}")
        cls.fence = _extract_hits_fence()

    def test_fence_counts_inodes_not_argument_names(self) -> None:
        # Content pin: the shipped formula resolves file identity. A revert to
        # the `ls | sort -u` argument echo fails here before it fails a repro.
        self.assertIn("stat", self.fence)
        self.assertIn("%i", self.fence)

    def test_no_spec_file_is_zero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(_run_hits(self.fence, Path(td)), "0")

    def test_single_uppercase_spec_is_one(self) -> None:
        # #305: this returned 2 on APFS under the argument-echo formula.
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "SPEC.md").write_text("# spec\n", encoding="utf-8")
            self.assertEqual(_run_hits(self.fence, d), "1")

    def test_single_lowercase_spec_is_one(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "spec.md").write_text("# spec\n", encoding="utf-8")
            self.assertEqual(_run_hits(self.fence, d), "1")

    def test_unrelated_files_do_not_count(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "SPEC.md").write_text("# spec\n", encoding="utf-8")
            (d / "README.md").write_text("# readme\n", encoding="utf-8")
            self.assertEqual(_run_hits(self.fence, d), "1")

    def test_two_distinct_files_still_two(self) -> None:
        # Only expressible on a case-sensitive FS (ext4 in CI); on APFS the two
        # names ARE one file, which the case above already covers.
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            if not _fs_is_case_sensitive(d):
                self.skipTest("case-insensitive filesystem: two distinct files "
                              "cannot exist")
            (d / "SPEC.md").write_text("# upper\n", encoding="utf-8")
            (d / "spec.md").write_text("# lower\n", encoding="utf-8")
            self.assertEqual(_run_hits(self.fence, d), "2")


if __name__ == "__main__":
    unittest.main()
