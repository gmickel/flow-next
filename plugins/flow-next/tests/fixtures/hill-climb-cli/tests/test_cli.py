"""Regression gate: behaviour every kept attempt must preserve."""

import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def mycli(*args):
    return subprocess.run([sys.executable, "-m", "mycli", *args], cwd=ROOT, capture_output=True, text=True)


class CliContract(unittest.TestCase):
    def test_version(self):
        result = mycli("--version")
        self.assertEqual((result.returncode, result.stdout), (0, "mycli 1.4.0\n"))

    def test_list_finds_the_bundled_plugin(self):
        result = mycli("list")
        self.assertEqual(result.returncode, 0)
        self.assertIn("hello", result.stdout.split())

    def test_stats(self):
        result = mycli("stats")
        self.assertEqual((result.returncode, result.stdout), (0, "primes: 216816\n"))


if __name__ == "__main__":
    unittest.main()
