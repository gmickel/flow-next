"""Deterministic operation-count regressions for Prime classification."""

from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


FLOWCTL_PY = Path(__file__).resolve().parents[1] / "scripts" / "flowctl.py"


def _load_flowctl():
    spec = importlib.util.spec_from_file_location(
        "flowctl_prime_performance_under_test", FLOWCTL_PY
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


flowctl = _load_flowctl()


class CountingPath(str):
    lower_calls = 0

    def lower(self) -> str:
        type(self).lower_calls += 1
        return super().lower()


class PrimeAtomicPairPerformanceTest(unittest.TestCase):
    def test_pascal_heavy_inventory_lowercases_linearly(self) -> None:
        paths = []
        for index in range(300):
            paths.append(CountingPath(f"forms/Form{index}.PAS"))
            paths.append(CountingPath(f"forms/Form{index}.DFM"))
        paths.extend(CountingPath(f"src/Other{index}.py") for index in range(300))

        CountingPath.lower_calls = 0
        result, collector = flowctl._prime_collect_atomic_pairs(paths)

        self.assertEqual(result["candidate_count"], 300)
        self.assertEqual(collector.operations, len(paths))
        self.assertLessEqual(
            CountingPath.lower_calls,
            2 * len(paths),
            "tracked lowercase inventory must be built once, not once per .pas file",
        )


class PrimeContainmentCacheTest(unittest.TestCase):
    def setUp(self) -> None:
        flowctl._PRIME_ROOT_REAL_CACHE.clear()

    def test_real_root_resolves_once_but_each_target_stays_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            real_realpath = os.path.realpath
            with mock.patch.object(
                flowctl.os.path, "realpath", wraps=real_realpath
            ) as realpath:
                for index in range(200):
                    self.assertIsNotNone(
                        flowctl._prime_contained(root, f"src/file-{index}.py")
                    )
                self.assertIsNone(flowctl._prime_contained(root, "../escape"))

            # One root resolution + one target resolution per containment call.
            self.assertEqual(realpath.call_count, 202)

    def test_symlinked_root_is_never_sticky_when_retargeted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            first = base / "first"
            second = base / "second"
            first.mkdir()
            second.mkdir()
            link = base / "root"
            link.symlink_to(first, target_is_directory=True)
            self.assertEqual(flowctl._prime_root_real(link), str(first.resolve()))
            link.unlink()
            link.symlink_to(second, target_is_directory=True)
            self.assertEqual(flowctl._prime_root_real(link), str(second.resolve()))


class PrimeGitBatchTest(unittest.TestCase):
    def test_parallel_results_and_failures_preserve_input_order(self) -> None:
        barrier = threading.Barrier(4)

        def fake_git(root, args, collector, timeout=30):
            collector.op()
            barrier.wait(timeout=5)
            if args[0] == "bad":
                collector.fail("bad probe")
                return (1, "", "bad probe")
            return (0, args[0], "")

        collector = flowctl._PrimeCollector("batch", budget=4)
        commands = [["one"], ["bad"], ["three"], ["four"]]
        with mock.patch.object(flowctl, "_prime_git", side_effect=fake_git):
            results = flowctl._prime_git_many(Path("."), commands, collector)

        self.assertEqual([result[1] for result in results], ["one", "", "three", "four"])
        self.assertEqual(collector.operations, 4)
        self.assertEqual(collector.errors, ["bad probe"])
        self.assertEqual(collector.status, "error")

    def test_executor_start_failure_falls_back_in_order(self) -> None:
        calls = []

        def fake_git(root, args, collector, timeout=30):
            collector.op()
            calls.append(args[0])
            return (0, args[0], "")

        collector = flowctl._PrimeCollector("batch", budget=3)
        commands = [["one"], ["two"], ["three"]]
        with mock.patch(
            "concurrent.futures.ThreadPoolExecutor",
            side_effect=RuntimeError("can't start new thread"),
        ):
            with mock.patch.object(flowctl, "_prime_git", side_effect=fake_git):
                results = flowctl._prime_git_many(Path("."), commands, collector)

        self.assertEqual(calls, ["one", "two", "three"])
        self.assertEqual([result[1] for result in results], calls)
        self.assertEqual(collector.operations, 3)
        self.assertEqual(collector.status, "ok")


class PrimeInventoryProcessTest(unittest.TestCase):
    def test_streamed_git_inventory_closes_stdout(self) -> None:
        class FakeProcess:
            def __init__(self) -> None:
                self.stdout = io.BytesIO(
                    b"100644 abcdef 0\tfile.py\0"
                )

            def kill(self) -> None:
                pass

            def poll(self) -> int:
                return 0

            def wait(self, timeout=None) -> int:
                return 0

        process = FakeProcess()
        collector = flowctl._PrimeCollector("inventory")
        with mock.patch.object(flowctl.subprocess, "Popen", return_value=process):
            entries, truncated = flowctl._prime_parse_ls_files_staged(
                Path("."), collector
            )

        self.assertEqual(entries, [("abcdef", "file.py")])
        self.assertFalse(truncated)
        self.assertTrue(process.stdout.closed)


if __name__ == "__main__":
    unittest.main()
