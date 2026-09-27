"""Harness: cold-start wall time of `mycli --version`, with an output check.

Usage: python3 bench.py --runs N --warmup W DIR [DIR ...]
Runs are interleaved across the directories so drift hits every side alike.
Prints one line per directory: median, min and max in milliseconds.
Exits 1 when any run fails the output check.
"""

import argparse
import statistics
import subprocess
import sys
import time

EXPECTED = "mycli 1.4.0\n"


def one_run(directory):
    start = time.perf_counter()
    result = subprocess.run([sys.executable, "-m", "mycli", "--version"], cwd=directory, capture_output=True, text=True)
    elapsed = (time.perf_counter() - start) * 1000
    if result.returncode != 0 or result.stdout != EXPECTED:
        sys.exit(f"OUTPUT CHECK FAILED in {directory}: rc={result.returncode} stdout={result.stdout!r}")
    return elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--warmup", type=int, required=True)
    parser.add_argument("dirs", nargs="+")
    args = parser.parse_args()
    samples = {directory: [] for directory in args.dirs}
    for index in range(args.warmup + args.runs):
        for directory in args.dirs:
            elapsed = one_run(directory)
            if index >= args.warmup:
                samples[directory].append(elapsed)
    for directory, values in samples.items():
        print(f"{directory}: median {statistics.median(values):.0f} ms, range {min(values):.0f}-{max(values):.0f} ms")


if __name__ == "__main__":
    main()
