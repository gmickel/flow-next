"""#505: a SHIP plan review is due again when a file the spec cites changed since the reviewed commit.

Real git fixture repos; the SHIP is written by the real review-attempt recorder, so the
commit the check reads is the one plan review records.
"""
import json
import os
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import test_pilot_strikes as support
from test_pilot_strikes import _git, _run, flowctl as f

BODY = """# Drift fixture

## Goal & Context

Change `src/cited.py` and anything under `docs/guide/`. Notes live in `.flow/notes/n.md`.
Not paths: `jq`, `--json`, `origin/main`.

## Acceptance Criteria

- **R1:** It works.
"""


class PlanReviewDriftTests(unittest.TestCase):
    def tearDown(self):
        os.chdir(self._cwd)
        support.PilotStrikesTestCase.tearDown(self)

    def setUp(self):
        support.PilotStrikesTestCase.setUp(self)
        # Task runtime state resolves through the process's git dir, so in-process
        # route calls run from the fixture, as `flowctl` does.
        self._cwd = os.getcwd()
        os.chdir(self.repo)
        self.assertEqual(_run(self.repo, 'init', '--json').returncode, 0)
        created = _run(self.repo, 'spec', 'create', '--title', 'Drift fixture', '--json')
        self.assertEqual(created.returncode, 0, created.stderr)
        self.sid = json.loads(created.stdout)['id']
        self.assertEqual(_run(self.repo, 'spec', 'ready', self.sid).returncode, 0)
        (self.repo / '.flow' / 'specs' / f'{self.sid}.md').write_text(BODY, encoding='utf-8')
        for name in ('src/cited.py', 'src/other.py', 'docs/guide/a.md', '.flow/notes/n.md'):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('v1\n', encoding='utf-8')
        self.commit('fixture')
        self.ship()

    def commit(self, message):
        _git(self.repo, 'add', '-A')
        _git(self.repo, 'commit', '-qm', message)

    def change(self, name, message='change'):
        (self.repo / name).write_text('v2\n', encoding='utf-8')
        self.commit(message)

    def in_repo(self):
        return [patch.object(f, 'get_repo_root', return_value=self.repo),
                patch.object(f, 'get_flow_dir', return_value=self.repo / '.flow')]

    def ship(self):
        """Record a SHIP plan verdict at HEAD through the real reservation and recorder."""
        head = _git(self.repo, 'rev-parse', 'HEAD').stdout.strip()
        patches = self.in_repo()
        for p in patches:
            p.start()
        try:
            _, reservation = f.enforce_and_increment_review_cap(
                self.sid, 'plan', artifact_sha256='a' * 64, review_type='plan', return_reservation=True)
            f.record_review_attempt(
                self.sid, 'plan', backend='host', output='<verdict>SHIP</verdict>', verdict='SHIP',
                review_type='plan', reservation_id=reservation, finalize_status_kind='plan',
                reset_rounds_on_ship=True, reviewed_head_sha=head)
        finally:
            for p in patches:
                p.stop()
        self.commit('chore(flow): plan review')
        self.assertEqual(self.spec_json()['plan_review_status'], 'ship')

    def spec_json(self):
        return json.loads((self.repo / '.flow' / 'specs' / f'{self.sid}.json').read_text())

    def edit_spec_json(self, **fields):
        path = self.repo / '.flow' / 'specs' / f'{self.sid}.json'
        data = json.loads(path.read_text())
        data.update(fields)
        path.write_text(json.dumps(data), encoding='utf-8')

    def gh_shim(self):
        real_run = subprocess.run
        def run(command, *args, **kwargs):
            if command[0] == 'gh':
                return SimpleNamespace(returncode=0, stdout='[]', stderr='')
            return real_run(command, *args, **kwargs)
        return patch.object(f.subprocess, 'run', side_effect=run)

    def route(self):
        """The route judge (`flowctl judge --preset route --spec`)."""
        patches = [*self.in_repo(), self.gh_shim(), patch.dict(os.environ, TYPESAFE_API_KEY='')]
        for p in patches:
            p.start()
        try:
            return f.judge_route(f.judge_route_state({}, self.sid))['decision']
        finally:
            for p in patches:
                p.stop()

    def pilot_route(self):
        patches = [*self.in_repo(), self.gh_shim(), patch.dict(os.environ, TYPESAFE_API_KEY=''),
                   patch.object(f, '_pilot_strikes_ledger_path', return_value=self.ledger)]
        for p in patches:
            p.start()
        try:
            return f.pilot_snapshot(self.sid)['route']['decision']
        finally:
            for p in patches:
                p.stop()

    def show_drift(self):
        shown = _run(self.repo, 'show', self.sid, '--json')
        self.assertEqual(shown.returncode, 0, shown.stdout + shown.stderr)
        return json.loads(shown.stdout).get('plan_review_drift')

    def assert_drift(self, paths):
        decision = self.route()
        self.assertEqual(decision['value'], 'plan_review')
        self.assertEqual(decision['rule'],
                         'plan review predates changes to cited files: ' + ', '.join(paths))
        self.assertEqual(self.show_drift(), paths)
        # R5: the pilot snapshot routes the same spec the same way.
        self.assertEqual(self.pilot_route(), decision)

    def assert_no_drift(self, expected_route='work_no_plan_default'):
        decision = self.route()
        self.assertEqual(decision['value'], expected_route)
        self.assertEqual(self.show_drift(), [])
        self.assertEqual(self.pilot_route(), decision)

    def test_r1_cited_file_change_routes_to_plan_review(self):
        self.assert_no_drift()
        self.change('src/cited.py')
        self.assert_drift(['src/cited.py'])

    def test_r1_change_under_a_cited_directory(self):
        self.change('docs/guide/a.md')
        self.assert_drift(['docs/guide/'])

    def test_r1_deleted_cited_file_counts_as_changed(self):
        _git(self.repo, 'rm', '-q', 'src/cited.py')
        self.commit('delete')
        self.assert_drift(['src/cited.py'])

    def test_r1_renamed_cited_file_counts_as_changed(self):
        _git(self.repo, 'mv', 'src/cited.py', 'src/moved.py')
        self.commit('rename')
        self.assert_drift(['src/cited.py'])

    def test_r1_missing_or_unrecorded_commit_is_no_drift(self):
        self.change('src/cited.py')
        attempts = self.spec_json()['review_attempts']
        for head in ('0' * 40, None, '--output=x'):
            with self.subTest(head=head):
                rows = [dict(row) for row in attempts]
                rows[-1]['head_sha'] = head
                self.edit_spec_json(review_attempts=rows)
                self.assert_no_drift()

    def test_r2_uncited_and_flow_only_changes_leave_the_route(self):
        self.change('src/other.py')
        self.change('.flow/notes/n.md')
        self.assert_no_drift()

    def test_r3_new_ship_at_head_clears_drift(self):
        self.change('src/cited.py')
        self.assert_drift(['src/cited.py'])
        self.ship()
        self.assert_no_drift()

    def test_r4_started_task_is_unchanged(self):
        created = _run(self.repo, 'task', 'create', '--spec', self.sid, '--title', 'Build', '--json')
        self.assertEqual(created.returncode, 0, created.stderr)
        task = json.loads(created.stdout)['id']
        self.commit('task')
        self.change('src/cited.py')
        # Every task still todo: the check applies to a planned spec too.
        self.assert_drift(['src/cited.py'])
        started = _run(self.repo, 'start', task, '--json')
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        self.assert_no_drift('work_planned')

    def test_r4_status_other_than_ship_is_unchanged(self):
        self.change('src/cited.py')
        for status in ('needs_work', 'needs_human', 'unknown'):
            with self.subTest(status=status):
                self.edit_spec_json(plan_review_status=status)
                self.assert_no_drift()
        self.edit_spec_json(plan_review_status='stale')
        self.assertEqual(self.route()['rule'], 'plan review stale')
        self.assertEqual(self.show_drift(), [])


if __name__ == '__main__':
    unittest.main()
