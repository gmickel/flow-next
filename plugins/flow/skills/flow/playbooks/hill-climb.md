# Hill Climb

Use this playbook when pushing one metric toward a stated target over repeated attempts. The target belongs to the person; never invent, relax, or reinterpret it. If no target is given, ask once (or stop when unattended).

First build a repeatable harness on a realistic workload, prove it measures what it claims—separating a known-worse and known-better probe and rejecting wrong output or new errors—and freeze it before the first attempt. Never change the harness mid-climb to make a number move; if the harness must change, invalidate earlier measurements and re-baseline.

Run one hypothesis, one change, and one measurement per attempt, recording each attempt's change, before-and-after median and spread, and whether it was kept or reverted. Keep a change only when it beats the current best outside noise with correctness intact; revert every worse or inconclusive attempt cleanly before the next one.

Stop when the target is met, when attempts stop paying after changing approach, or when the stated budget ends, and report the baseline, final number, attempt record, and any remaining gap honestly.
