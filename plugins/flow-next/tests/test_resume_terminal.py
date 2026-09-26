"""Completion checkpoint parity: durable decisions, receipt recovery, failure paths."""
import argparse
import contextlib
import io
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
_spec = importlib.util.spec_from_file_location('flowctl_resume_test', Path(__file__).resolve().parents[1] / 'scripts' / 'flowctl.py')
f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(f)


class ResumeTerminalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.flow = Path(self.temp.name) / '.flow'
        self.flow.mkdir()
        self.path = self.flow / 'spec.json'
        self.patchers = [
            patch.object(f, 'find_spec_json_path', return_value=self.path),
            patch.object(f, '_review_sidecar_lock', side_effect=lambda *a: contextlib.nullcontext()),
            patch.object(f, 'get_max_review_iterations', return_value=8),
        ]
        for p in self.patchers:
            p.start()
            self.addCleanup(p.stop)

    def run_state(self, outcome='verdict', verdict='SHIP', backend='rp', status='unknown', reviewed='', rounds=0, extra=None, receipt=None):
        attempt = {'scope': 'completion', 'outcome': outcome, 'verdict': verdict,
                   'backend': backend, 'timestamp': '2026-08-02T00:00:00Z', **(extra or {})}
        self.path.write_text(json.dumps({'id': 'fn-1', 'completion_review_status': status,
            'completion_reviewed_at': reviewed, 'plan_review_rounds': rounds,
            'review_attempts': [] if outcome is None else [attempt]}))
        return f._resume_completion_terminal(self.flow, 'fn-1', receipt)

    def test_decision_matrix(self):
        cases = [
            ({'outcome': None}, 'continue', 'unknown', 0),
            ({'outcome': None, 'status': 'not_required'}, 'continue', 'not_required', 0),
            ({'outcome': 'transport_failure', 'verdict': None}, 'continue', 'unknown', 0),
            ({}, 'ship', 'ship', 0),
            ({'verdict': 'NEEDS_WORK', 'rounds': 7}, 'continue', 'unknown', 0),
            ({'verdict': 'MAJOR_RETHINK', 'rounds': 8}, 'continue', 'unknown', 0),
            ({'verdict': 'NEEDS_WORK', 'rounds': 8}, 'escalate', 'needs_work', 4),
            ({'verdict': 'NEEDS_HUMAN'}, 'escalate', 'needs_human', 4),
            ({'extra': {'superseded_by': 'new'}}, 'superseded', 'unknown', 0),
            ({'reviewed': '2026-08-03T00:00:00Z'}, 'continue', 'unknown', 0),
            ({'status': 'ship', 'reviewed': '2026-08-03T00:00:00Z'}, 'ship', 'ship', 0),
            ({'backend': 'host'}, 'retry', 'unknown', 0),
            ({'extra': {'timestamp': ''}}, 'continue', 'unknown', 0),
            ({'status': 'not_required'}, 'ship', 'ship', 0),
            ({'reviewed': '2026-08-02T00:00:00Z'}, 'continue', 'unknown', 0),
        ]
        for kwargs, action, status, code in cases:
            with self.subTest(kwargs=kwargs):
                result = self.run_state(**kwargs)
                self.assertEqual(result, {'action': action, 'status': status, 'exit': code})

    def test_unknown_state_fails_closed(self):
        for kwargs in ({'status': 'mystery'}, {'outcome': 'mystery'}, {'verdict': 'mystery'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_state(**kwargs)

    def test_receipt_recovery_before_status_and_stale_optional_receipt(self):
        recovery = self.flow / 'tmp' / 'completion-review-receipt-recovery-fn-1.json'
        recovery.parent.mkdir()
        payload = {'type': 'completion_review', 'id': 'fn-1', 'verdict': 'SHIP',
                   'mode': 'codex', 'attempt_timestamp': '2026-08-02T00:00:00Z', 'review': 'full evidence'}
        recovery.write_text(json.dumps(payload))
        destination = self.flow / 'other' / 'receipt.json'
        self.assertEqual(self.run_state(backend='codex', receipt=str(destination))['action'], 'ship')
        self.assertEqual(json.loads(destination.read_text()), payload)
        self.assertFalse(recovery.exists())
        self.assertEqual(json.loads(self.path.read_text())['completion_review_status'], 'ship')
        recovery.write_text(json.dumps(payload))
        self.assertEqual(self.run_state(backend='rp')['action'], 'ship')
        self.assertFalse(recovery.exists())
        self.assertEqual(self.run_state(backend='rp', receipt=str(destination))['action'], 'retry')

    def test_status_write_failure_keeps_recovery(self):
        recovery = self.flow / 'tmp' / 'completion-review-receipt-recovery-fn-1.json'
        recovery.parent.mkdir()
        recovery.write_text(json.dumps({'type': 'completion_review', 'id': 'fn-1', 'verdict': 'SHIP',
            'mode': 'codex', 'attempt_timestamp': '2026-08-02T00:00:00Z'}))
        with patch.object(f, 'atomic_write_json', side_effect=OSError('disk unavailable')):
            self.assertEqual(self.run_state(backend='codex')['action'], 'retry')
        self.assertTrue(recovery.exists())
        self.assertEqual(json.loads(self.path.read_text())['completion_review_status'], 'unknown')

    def test_command_returns_exit_intent_in_envelope(self):
        self.run_state(verdict='NEEDS_HUMAN')
        output = io.StringIO()
        with patch.object(f, 'get_flow_dir', return_value=self.flow), patch.object(
            f, 'resolve_spec_id_arg', return_value='fn-1'
        ), patch.dict(f.os.environ, {'REVIEW_RECEIPT_PATH': ''}), contextlib.redirect_stdout(output):
            f.cmd_review_rounds_resume_terminal(argparse.Namespace(id='fn-1', json=True))
        result = json.loads(output.getvalue())
        self.assertEqual(result['action'], 'escalate')
        self.assertEqual(result['exit'], 4)

    def test_receipt_destination_failure_preserves_status_and_recovery(self):
        recovery = self.flow / 'tmp' / 'completion-review-receipt-recovery-fn-1.json'
        recovery.parent.mkdir()
        recovery.write_text(json.dumps({'type': 'completion_review', 'id': 'fn-1', 'verdict': 'SHIP',
            'mode': 'host', 'attempt_timestamp': '2026-08-02T00:00:00Z'}))
        obstruction = self.flow / 'not-directory'
        obstruction.write_text('occupied')
        self.assertEqual(self.run_state(backend='host', receipt=str(obstruction / 'receipt'))['action'], 'retry')
        self.assertTrue(recovery.exists())
        self.assertEqual(json.loads(self.path.read_text())['completion_review_status'], 'unknown')
