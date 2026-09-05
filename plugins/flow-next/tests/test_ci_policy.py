"""Exercise CI selection, aggregate status and exact-release evidence contracts."""
import importlib.util
import json
import os
import sys
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/ci' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CIPolicy(unittest.TestCase):
    def test_ranges_and_conservative_fallback(self):
        mod = load('classify_changes')
        with tempfile.TemporaryDirectory() as temp:
            def git(*args):
                return subprocess.check_output(['git', '-C', temp, *args], text=True).strip()
            git('init', '-q')
            git('config', 'user.email', 'ci@example.test')
            git('config', 'user.name', 'CI')
            p = Path(temp) / 'file.md'
            p.write_text('one')
            git('add', '.')
            git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            p.write_text('two')
            git('commit', '-qam', 'head')
            head = git('rev-parse', 'HEAD')
            original_run = subprocess.run
            def run(*args, **kwargs):
                return original_run(*args, cwd=temp, **kwargs)
            with mock.patch.object(mod.subprocess, 'run', side_effect=run):
                for event in ('push', 'pull_request'):
                    self.assertEqual(mod.changed_paths(event, base, head), ['file.md'])
                    for bad_base in ('', '0' * 40, 'missing', head):
                        self.assertIsNone(mod.changed_paths(event, bad_base, head))
            with mock.patch.object(mod.subprocess, 'run', side_effect=OSError('unavailable')):
                self.assertIsNone(mod.changed_paths('push', base, head))

    def test_matrix_and_windows_backstop(self):
        mod = load('classify_changes')
        for event in ('push', 'pull_request'):
            for paths, count, smoke, stub in [
                (None, 3, True, True), ([], 3, True, True),
                (['agent_docs/project.md'], 1, False, False),
                (['.flow/tasks/fn-1.1.json'], 1, False, False),
                (['plugins/flow-next/tests/fixture.md'], 3, True, False),
                (['agent_docs/check.py'], 3, True, False),
                (['plugins/flow-next/scripts/flowctl.cmd'], 3, True, True),
                (['scripts/merge_codex_config.py'], 3, True, True),
            ]:
                with self.subTest(event=event, paths=paths):
                    result = mod.classify(event, paths)
                    self.assertEqual(len(result['units_matrix']), count)
                    self.assertEqual(result['run_smokes'], smoke)
                    self.assertEqual(result['run_windows_stub'], stub)
        self.assertTrue(mod.classify('schedule', None)['run_windows_stub'])
        self.assertEqual(mod.classify('schedule', None)['units_matrix'], mod.WEEKLY)
        self.assertEqual(mod.classify('workflow_dispatch', ['README.md'])['units_matrix'], mod.FULL)

    def test_aggregate_blocks_failures_and_unexpected_skips(self):
        workflow = (ROOT / '.github/workflows/test-flow-next.yml').read_text(encoding='utf-8')
        script = workflow.split("python3 - <<'PYTHON'\n", 1)[1].split('          PYTHON', 1)[0]
        script = '\n'.join(line[10:] for line in script.splitlines())
        names = ['changes', 'units', 'smokes', 'python-intermediate-smoke', 'windows-python3-stub']
        for selected in (True, False):
            needs = {name: {'result': 'success' if selected or name in names[:2] else 'skipped'} for name in names}
            needs['changes']['outputs'] = {'run_smokes': str(selected).lower(), 'run_windows_stub': str(selected).lower()}
            result = subprocess.run([sys.executable, '-c', script], env=dict(os.environ, NEEDS_JSON=json.dumps(needs)), capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in names:
                for bad in ('failure', 'cancelled', 'skipped'):
                    if bad == 'skipped' and not selected and name in names[2:]:
                        continue
                    broken = json.loads(json.dumps(needs))
                    broken[name]['result'] = bad
                    with self.subTest(name=name, result=bad, selected=selected):
                        result = subprocess.run([sys.executable, '-c', script], env=dict(os.environ, NEEDS_JSON=json.dumps(broken)), capture_output=True)
                        self.assertNotEqual(result.returncode, 0)
        self.assertIn('    if: always()\n    needs: [changes, units, smokes, python-intermediate-smoke, windows-python3-stub]', workflow)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", workflow)
        for block in re.split(r'^  [\w-]+:\n', workflow.split('jobs:\n')[1], flags=re.M)[1:]:
            self.assertRegex(block, r'(?m)^    timeout-minutes: [1-9][0-9]*$')

    def test_release_requires_latest_exact_main_push_and_aggregate(self):
        mod = load('require_release_ci')
        good = {'id': 1, 'head_sha': 'abc', 'event': 'push', 'head_branch': 'main', 'status': 'completed', 'conclusion': 'success'}
        job = {'name': 'CI', 'status': 'completed', 'conclusion': 'success'}
        cases = [([], [job], False), ([good], [job], True)]
        for field, value in [('head_sha', 'other'), ('event', 'workflow_dispatch'), ('head_branch', 'feature'), ('status', 'in_progress'), ('conclusion', 'failure')]:
            cases.append(([dict(good, **{field: value})], [job], False))
        cases.extend([([good, dict(good, id=2, conclusion='failure')], [job], False),
                      ([good], [], False), ([good], [dict(job, conclusion='skipped')], False)])
        for runs, jobs, allowed in cases:
            with self.subTest(runs=runs, jobs=jobs), mock.patch.object(mod, 'gh_pages', side_effect=[[{'workflow_runs': runs}], [{'jobs': jobs}]]):
                if allowed:
                    self.assertEqual(mod.require_ci('owner/repo', 'abc'), 1)
                else:
                    with self.assertRaises(ValueError):
                        mod.require_ci('owner/repo', 'abc')
        with mock.patch.object(mod, 'gh_pages', side_effect=[[{'workflow_runs': [good]}], subprocess.CalledProcessError(1, 'gh')]):
            with self.assertRaises(subprocess.CalledProcessError):
                mod.require_ci('owner/repo', 'abc')
        workflow = (ROOT / '.github/workflows/release.yml').read_text(encoding='utf-8')
        self.assertLess(workflow.index('python scripts/ci/require_release_ci.py'), workflow.index('uses: softprops/action-gh-release'))
