"""fn-259 rolling admission and contiguous task evidence contracts."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_done_block_ergonomics import _Repo, SPEC_ID, TASK_ID, flowctl


class AdmissionTests(unittest.TestCase):
    def task(self, tid, touches, deps=()):
        return dict(id=tid, touches=touches, depends_on=list(deps), transitive_depends_on=list(deps))

    def test_incremental_glob_overlap_missing_serial_cap(self):
        rows = [self.task('1', ['src/a/**']), self.task('2', ['src/a/new.py']),
                self.task('3', None), self.task('4', ['.flow/tasks/x.md']),
                self.task('5', ['src/b.py']), self.task('6', ['src/c.py'])]
        out = flowctl.ready_admission(rows, {t['id']: t for t in rows}, [], 2)
        self.assertEqual(out['admitted'], ['1', '5'])
        self.assertEqual([x['reason'] for x in out['held']],
                         ['touches-overlap:1', 'touches-missing', 'always-serial', 'cap'])

    def test_dependency_closure_cycles_and_inflight(self):
        rows = [self.task('1', ['a'], ['2']), self.task('2', ['b'], ['3']), self.task('3', ['c'], ['1'])]
        tasks = {t['id']: t for t in rows}
        self.assertEqual(flowctl.task_dependency_closure('1', tasks), ['1', '2', '3'])
        rows[0]['transitive_depends_on'] = ['2', '3']
        self.assertEqual(flowctl.ready_admission([rows[0]], tasks, ['3'], 3)['held'][0]['reason'], 'dependency:3')

    def test_touch_parser_and_safe_distinct_paths(self):
        self.assertEqual(flowctl.task_touches('**Touches:** [`src/a.py`, src/b/**]'), ['src/a.py', 'src/b/**'])
        self.assertIsNone(flowctl.task_touches('no declaration'))
        rows = [self.task('1', ['src/a.py']), self.task('2', ['src/ab.py'])]
        self.assertEqual(flowctl.ready_admission(rows, {t['id']: t for t in rows}, [], 3)['admitted'], ['1', '2'])


class CommandTests(_Repo):
    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, env=self.env, capture_output=True, text=True, check=True).stdout.strip()

    def seed_git(self):
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'user.name', 'Test')
        self.git('add', '.flow')
        self.git('commit', '-qm', 'base')
        base = self.git('rev-parse', 'HEAD')
        (self.root / 'code').write_text('one')
        self.git('add', 'code'); self.git('commit', '-qm', 'implementation')
        return base, self.git('rev-parse', 'HEAD')

    def test_done_range_tests_stdin(self):
        base, head = self.seed_git()
        self.run_ok('start', TASK_ID)
        result = subprocess.run([sys.executable, str(flowctl.__file__), 'done', TASK_ID,
                                 '--range', f'{base}..{head}', '--test', 'test one', '--test', 'test two',
                                 '--summary-file', '-', '--json'], cwd=self.root, env=self.env,
                                input='Implemented feature', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        show = json.loads(self.run_ok('show', TASK_ID, '--json').stdout)
        self.assertEqual(show['evidence']['base_commit'], base)
        self.assertEqual(show['evidence']['commits'], [head])
        self.assertEqual(show['evidence']['tests'], ['test one', 'test two'])
        self.assertIn('Implemented feature', self.task_md())

    def test_unreachable_range_names_sha(self):
        base, head = self.seed_git()
        self.git('checkout', '-qb', 'side', base)
        self.run_ok('start', TASK_ID)
        result = self.run_cli('done', TASK_ID, '--range', f'{base}..{head}', '--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(head, result.stdout + result.stderr)
        self.assertEqual(self.status(), 'in_progress')

    def test_ready_metadata_missing_touches_and_tier_task(self):
        out = json.loads(self.run_ok('ready', '--spec', SPEC_ID, '--admit', '--json').stdout)
        self.assertIsNone(out['ready'][0]['touches'])
        self.assertEqual(out['held'], [{'id': TASK_ID, 'reason': 'touches-missing'}])
        self.run_ok('config', 'set', 'judge.enabled', 'false')
        tier = json.loads(self.run_ok('judge', '--preset', 'tier', '--task', TASK_ID, '--json').stdout)
        self.assertIn('tier_line', tier)
        self.assertIsNone(tier['spawn_model'])
        self.assertNotEqual(self.run_cli('judge', '--preset', 'tier', '--task', SPEC_ID + '.99').returncode, 0)

    def test_sync_resolves_lifecycle_ops_and_inactive_empty(self):
        self.assertEqual(json.loads(self.run_ok('sync', 'active', '--json').stdout)['ops'], {})
        self.run_ok('config', 'set', 'tracker.enabled', 'true')
        self.run_ok('config', 'set', 'tracker.perEvent.work.firstClaim', 'reconcile')
        self.run_ok('config', 'set', 'tracker.perEvent.work.done', 'push')
        ops = json.loads(self.run_ok('sync', 'active', '--json').stdout)['ops']
        self.assertEqual(ops['work.firstClaim'], 'push')
        self.assertEqual(ops['work.done'], 'comment')
        self.assertEqual(ops['completionReview'], 'off')
