"""Pilot hop facts and serialized strikes, with a real git/Flow fixture."""
import json
import os
import subprocess
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

import test_pilot_strikes as support
from test_pilot_strikes import _git, _run, flowctl as f


class PilotSnapshotTests(unittest.TestCase):
    tearDown = support.PilotStrikesTestCase.tearDown
    _read_ledger = support.PilotStrikesTestCase._read_ledger
    def setUp(self):
        support.PilotStrikesTestCase.setUp(self)
        init = _run(self.repo, 'init', '--json')
        self.assertEqual(init.returncode, 0, init.stderr)
        created = _run(self.repo, 'spec', 'create', '--title', 'Snapshot fixture', '--json')
        self.assertEqual(created.returncode, 0, created.stderr)
        self.sid = json.loads(created.stdout)['id']
        self.assertEqual(_run(self.repo, 'spec', 'ready', self.sid).returncode, 0)
        self.spec_path = self.repo / '.flow' / 'specs' / f'{self.sid}.json'
        # Sidecars use the metadata directory in current repos.
        if not self.spec_path.exists():
            self.spec_path = next((self.repo / '.flow').rglob(f'{self.sid}.json'))
        self.spec = json.loads(self.spec_path.read_text())
        self.branch = self.spec['branch_name']
        _git(self.repo, 'branch', self.branch)

    def snapshot(self, rows=None, failed=False):
        real_run = subprocess.run
        gh_calls = []
        def run(command, *args, **kwargs):
            if command[0] == 'gh':
                gh_calls.append(command)
                return SimpleNamespace(returncode=int(failed), stdout=json.dumps(rows or []))
            return real_run(command, *args, **kwargs)
        with patch.object(f, 'get_repo_root', return_value=self.repo), patch.object(f, 'get_flow_dir', return_value=self.repo / '.flow'), patch.object(f.subprocess, 'run', side_effect=run), patch.dict(os.environ, TYPESAFE_API_KEY=''), patch.object(f, '_pilot_strikes_ledger_path', return_value=self.ledger):
            result = f.pilot_snapshot(self.sid)
        self.assertEqual(len(gh_calls), 1)
        return result

    def test_snapshot_has_code_route_without_external_judge_and_is_read_only(self):
        before = _git(self.repo, 'status', '--porcelain').stdout
        result = self.snapshot()
        self.assertEqual(result['selected']['id'], self.sid)
        self.assertTrue(result['selected']['branch_exists'])
        self.assertEqual(result['selected']['tasks'], result['before_dispatch'])
        self.assertTrue(result['selected']['chain']['eligible'])
        self.assertFalse(result['route']['available'])
        self.assertEqual(result['route']['decision']['value'], 'work_no_plan_default')
        self.assertEqual(result['route']['reason'], 'no_key')
        self.assertFalse(result['guards']['dirty'])
        self.assertIn('pipeline', result['config'])
        self.assertIn('backend', result['review_backend'])
        self.assertFalse(self.ledger.exists())
        self.assertEqual(before, _git(self.repo, 'status', '--porcelain').stdout)

    def test_one_listing_preserves_open_merged_and_closed_observations(self):
        rows = [{'number': i, 'url': f'https://example.test/pr/{i}', 'state': state,
                 'headRefName': self.branch, 'headRefOid': str(i), 'mergedAt': '2026-01-01' if state == 'MERGED' else None}
                for i, state in enumerate(['OPEN', 'MERGED', 'CLOSED'], 1)]
        result = self.snapshot(rows)
        pr = result['selected']['pr']
        self.assertEqual(pr['open']['number'], 1)
        self.assertEqual(pr['merged_head'], '2')
        self.assertEqual(pr['closed'][0]['number'], 3)
        self.assertEqual(result['route']['decision']['value'], 'existing_pr_tail')
        self.assertEqual(result['route']['decision']['pr_ref']['number'], 1)

    def test_probe_failure_does_not_guess_lifecycle(self):
        result = self.snapshot(failed=True)
        self.assertTrue(result['selected']['pr']['probe_failed'])
        self.assertTrue(result['route']['pr_probe_failed'])
        self.assertNotIn('decision', result['route'])

    def test_qa_freshness_peels_only_bookkeeping_commits(self):
        head = _git(self.repo, 'rev-parse', self.branch).stdout.strip()
        receipt = self.repo / '.flow' / 'review-receipts' / f'qa-{self.sid}.json'
        receipt.parent.mkdir(exist_ok=True)
        receipt.write_text(json.dumps({'id': self.sid, 'head_sha': head, 'qa_outcome': 'SHIP'}))
        _git(self.repo, 'checkout', self.branch)
        _git(self.repo, 'add', '-A')
        _git(self.repo, 'commit', '-qm', f'chore(flow): qa verdict {self.sid}')
        self.assertTrue(self.snapshot()['selected']['qa_fresh'])
        _git(self.repo, 'commit', '--allow-empty', '-qm', 'feat: new code')
        self.assertFalse(self.snapshot()['selected']['qa_fresh'])

    def test_guards_ralph_only_and_dirty_outside_flow(self):
        for marker in ('FLOW_RALPH', 'REVIEW_RECEIPT_PATH', 'FLOW_AUTONOMOUS', 'AUTONOMOUS'):
            with patch.dict(os.environ, {'FLOW_RALPH': '', 'REVIEW_RECEIPT_PATH': '', marker: '1'}):
                self.assertEqual(self.snapshot()['guards']['nested'], marker in ('FLOW_RALPH', 'REVIEW_RECEIPT_PATH'))
        (self.repo / 'new-code.py').write_text('x = 1\n')
        self.assertTrue(self.snapshot()['guards']['dirty'])

    def test_record_cumulative_across_stages_and_clear_preserves_unready(self):
        for stage, count in [('plan', 1), ('work', 2)]:
            result = _run(self.repo, 'pilot', 'strikes', 'record', self.sid, '--stage', stage, '--reason', stage, '--json')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['count'], count)
            self.assertEqual(json.loads(result.stdout)['unreadied'], count >= 2)
        self.assertFalse(json.loads(self.spec_path.read_text())['ready'])
        self.assertEqual(self._read_ledger()[self.sid]['stage'], 'work')
        self.assertEqual(_run(self.repo, 'pilot', 'strikes', 'clear', self.sid).returncode, 0)
        self.assertFalse(json.loads(self.spec_path.read_text())['ready'])

    def test_concurrent_records_serialize(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda i: _run(self.repo, 'pilot', 'strikes', 'record', self.sid,
                                                  '--stage', 'work', '--reason', str(i), '--json'), range(4)))
        self.assertTrue(all(r.returncode == 0 for r in results), [(r.stdout, r.stderr) for r in results])
        self.assertEqual(self._read_ledger()[self.sid]['count'], 4)
        self.assertFalse(json.loads(self.spec_path.read_text())['ready'])

    def test_unknown_spec_record_does_not_write(self):
        result = _run(self.repo, 'pilot', 'strikes', 'record', 'fn-999', '--stage', 'work', '--reason', 'test', '--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.ledger.exists())


if __name__ == '__main__':
    unittest.main()
