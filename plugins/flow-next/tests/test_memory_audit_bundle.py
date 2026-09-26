"""Mechanical audit and overlap planning behavior (fn-259 R27/R28)."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from flowctl_test_support import FLOWCTL_CMD, MemoryRepoTemplate


class MemoryAuditBundleTests(MemoryRepoTemplate, unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.memory = self.init_repo(self.root)

    def run_cli(self, *args, rc=0):
        result = subprocess.run([*FLOWCTL_CMD, *args, '--json'], cwd=self.root,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, rc, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def add(self, title='A recurrent crash'):
        return self.run_cli('memory', 'add', '--track', 'bug', '--category',
                            'runtime-errors', '--title', title, '--module', 'src.py')

    def apply(self, entries, rc=0):
        plan = self.root / 'plan.json'
        plan.write_text(json.dumps({'entries': entries}))
        return self.run_cli('memory', 'apply', '--plan', str(plan), rc=rc)

    def test_overlap_has_no_mutation_even_with_update(self):
        entry = self.add()
        before = {p: p.read_bytes() for p in self.memory.rglob('*') if p.is_file()}
        out = self.run_cli('memory', 'add', '--track', 'bug', '--category',
                           'runtime-errors', '--title', 'A recurrent crash',
                           '--module', 'src.py', '--check-overlap', '--update', entry['entry_id'])
        self.assertEqual(out['matches'][0]['id'], entry['entry_id'])
        self.assertEqual(before, {p: p.read_bytes() for p in self.memory.rglob('*') if p.is_file()})

    def test_scan_reports_invalid_and_mechanical_evidence(self):
        entry = self.add()
        self.apply([{'id': entry['entry_id'], 'set': {'hardened_into': 'rules.md#RULE -- reason'},
                     'body': '## Update one\n\n## Update two\n'}])
        (self.root / 'rules.md').write_text('RULE')
        (self.memory / 'bug/runtime-errors/bad-2026-01-01.md').write_text('broken')
        rows = self.run_cli('memory', 'audit-scan')['entries']
        valid = next(row for row in rows if row['id'] == entry['entry_id'])
        self.assertEqual(valid['recurrence']['updates'], 2)
        self.assertFalse(valid['module_exists'])
        self.assertTrue(valid['hardened_rule_present'])
        self.assertTrue(next(row for row in rows if 'bad-' in row['id'])['schema_errors'])

    def test_partial_plan_and_move_repoints_references(self):
        entry = self.add()
        other = self.add('Separate failure')
        self.apply([{'id': other['entry_id'], 'set': {'related_to': [entry['entry_id']]}}])
        moved = entry['entry_id'].replace('runtime-errors', 'integration')
        out = self.apply([{'id': 'bug/runtime-errors/missing'},
                          {'id': entry['entry_id'], 'move': moved, 'stamp': True}], rc=1)
        self.assertEqual(len(out['applied']), 1)
        self.assertEqual(len(out['errors']), 1)
        self.assertFalse((self.memory / (entry['entry_id'] + '.md')).exists())
        self.assertIn(moved, Path(other['path']).read_text())
        self.assertIn('last_audited:', (self.memory / (moved + '.md')).read_text())

    def test_invalid_entry_does_not_partially_mutate(self):
        entry = self.add()
        path = Path(entry['path'])
        before = path.read_bytes()
        self.apply([{'id': entry['entry_id'], 'stamp': True, 'set': {'status': 'nonsense'}}], rc=1)
        self.assertEqual(path.read_bytes(), before)
        self.apply([{'id': entry['entry_id'], 'move': '../../outside'}], rc=1)
        self.assertEqual(path.read_bytes(), before)

    def test_removal_repoints_and_canonical_drops_self_reference(self):
        old = self.add()
        canonical = self.add('Canonical crash')
        self.apply([{'id': canonical['entry_id'], 'set': {'related_to': [old['entry_id']]}}])
        self.apply([{'id': old['entry_id'], 'remove': True, 'replacement': canonical['entry_id']}])
        self.assertFalse(Path(old['path']).exists())
        text = Path(canonical['path']).read_text()
        self.assertNotIn(old['entry_id'], text)
        self.assertNotIn(canonical['entry_id'], text)

    def test_scan_substantive_history_ignores_audit_stamp(self):
        for args in [('init', '-q'), ('config', 'user.name', 'test'),
                     ('config', 'user.email', 'test@example.com')]:
            subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True)
        entry = self.add()
        def commit():
            subprocess.run(['git', 'add', '-A'], cwd=self.root, check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-qm', 'checkpoint'], cwd=self.root, check=True, capture_output=True)
        commit()
        self.apply([{'id': entry['entry_id'], 'stamp': True}])
        commit()
        moved = entry['entry_id'].replace('runtime-errors', 'integration')
        self.apply([{'id': entry['entry_id'], 'move': moved}])
        commit()
        row = self.run_cli('memory', 'audit-scan')['entries'][0]
        # Creation plus category edit on move, but no audit-stamp count.
        self.assertEqual(row['recurrence']['commits'], 2)
