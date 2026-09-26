"""Projection and prepare preserve source content and transaction preconditions."""
import json
import os
import stat
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from test_tracker_facade import (F, FLOW_BODY, SPEC_ID, _linked, _write_flow,
                                 _noop_push_responses, fake_execute, gh_cfg)
from flowctl_tracker.facade import preparation as P
from flowctl_tracker.types import TrackerError


class Preparation(unittest.TestCase):
    def test_render_legacy_and_fenced_content(self):
        legacy = '# Old spec\n## Goal\nAll prose and `links` survive.\n'
        self.assertEqual(P.render_body(legacy), legacy)
        source = ('# Title\n<!-- Goal: 70% [user], 30% [inferred] -->\n'
                  '## Acceptance Criteria\n- **R1:** Ship it. [user]\n'
                  '```md\n- **R2:** literal\n<!-- scope: example -->\n```\n'
                  '## Other\nA whole section.\n')
        rendered = P.render_body(source)
        self.assertIn('- [ ] Ship it. [user] [R1]', rendered)
        self.assertIn('```md\n- **R2:** literal\n<!-- scope: example -->\n```', rendered)
        self.assertIn('## Other\nA whole section.', rendered)
        self.assertNotIn('70%', rendered)
        self.assertEqual(P.render_body(source), rendered)

    def test_push_without_files_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / '.flow'
            _write_flow(flow, gh_cfg(), tracker=_linked())
            for index in range(2):
                out = F.sync(flow, SPEC_ID, op='push', event='plan',
                             execute=fake_execute(_noop_push_responses()))
                self.assertNotIsInstance(out, TrackerError, out)
                self.assertEqual(out['steps']['sync_body']['kind'], 'seeded' if index == 0 else 'noop')

    def test_rendered_push_keeps_echo_fence_for_tracker_rewrites(self):
        # The tracker normalized the last push (Linear-style rewrite); neither side moved since.
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / '.flow'
            _write_flow(flow, gh_cfg(), tracker=_linked(mergeBaseFlow=FLOW_BODY,
                        mergeBaseTracker='TRACKER REWRITE OF THE LAST PUSH'))
            ex = fake_execute(_noop_push_responses('TRACKER REWRITE OF THE LAST PUSH'))
            out = F.sync(flow, SPEC_ID, op='push', event='plan', execute=ex)
            self.assertNotIsInstance(out, TrackerError, out)
            self.assertEqual(out['steps']['sync_body']['kind'], 'noop')
            self.assertFalse(any(c.op == 'wire-update' for c in ex.calls))

    def test_status_only_without_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / '.flow'
            _write_flow(flow, gh_cfg(), tracker=_linked())
            ex = fake_execute(_noop_push_responses())
            out = F.sync(flow, SPEC_ID, op='push', event='plan', status_only=True, execute=ex)
            self.assertNotIsInstance(out, TrackerError, out)
            self.assertFalse(any(c.op == 'sync-body-parent-read' for c in ex.calls))

    def test_preparation_classifies_and_keeps_complete_cas_comments(self):
        marker = '<!-- flow-next:sync issue=x spec=y evt=plan evidence=abc -->\nOur evidence.\n---'
        comments = [{'id': '1', 'body': marker}, {'id': '2', 'body': 'OUR  evidence.'},
                    {'id': '3', 'body': 'Human question'},
                    {'id': '4', 'body': '<!-- flow-next:answer id=q --> Answer'}]
        for flow_body, remote, kind in [(FLOW_BODY, FLOW_BODY, 'noop'),
                                      (FLOW_BODY+'new', FLOW_BODY, 'flow-only'),
                                      (FLOW_BODY, FLOW_BODY+'new', 'tracker-only'),
                                      (FLOW_BODY+'new', FLOW_BODY+'new', 'both-changed')]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp) / '.flow'
                _write_flow(flow, gh_cfg(), tracker=_linked(mergeBaseFlow=FLOW_BODY,
                            mergeBaseTracker=FLOW_BODY.rstrip('\n')), spec_md=flow_body)
                with patch.object(P, 'dispatch', side_effect=[{'body': remote}, {'comments': comments}]) as wire:
                    out = F.sync(flow, SPEC_ID, op='reconcile', event='plan', prepare=True)
                self.assertEqual(wire.call_count, 2)
                self.assertNotIsInstance(out, TrackerError, out)
                self.assertEqual(out['classification'], kind)
                self.assertEqual([c['id'] for c in out['genuine_comments']], ['3', '4'])
                for path in out['files'].values():
                    self.assertEqual(stat.S_IMODE(Path(path).stat().st_mode), 0o600)
                self.assertEqual(len(json.loads(Path(out['files']['comments_file']).read_text())), 4)
                ex = fake_execute(_noop_push_responses(flow_body))
                F.sync(flow, SPEC_ID, op='push', event='plan', status_only=True, execute=ex)
                self.assertFalse(any(Path(path).exists() for path in out['files'].values()))

    def test_expiry_and_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / '.flow'
            _write_flow(flow, gh_cfg(), tracker=_linked())
            with patch.object(P, 'dispatch', side_effect=[{'body': FLOW_BODY}, {'comments': [], 'truncated': True}]):
                out = F.sync(flow, SPEC_ID, op='pull', event='plan', prepare=True)
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.subtype, 'comments_truncated')
            with patch.object(P, 'dispatch', side_effect=[{'body': FLOW_BODY}, {'comments': []}]):
                out = F.sync(flow, SPEC_ID, op='pull', event='plan', prepare=True)
            self.assertNotIsInstance(out, TrackerError, out)
            self.assertEqual(out['classification'], 'no-base')
            directory = Path(out['files']['flow_file']).parent
            os.utime(directory, (time.time()-3601, time.time()-3601))
            P.cleanup(flow, SPEC_ID, expired_only=True)
            self.assertFalse(directory.exists())


class RelationBatch(unittest.TestCase):
    def test_shared_guard_parallel_probes_and_serial_writes(self):
        import threading
        from flowctl_tracker import relate as R
        from flowctl_tracker.types import CONCURRENCY_CAP
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / '.flow'
            _write_flow(flow, gh_cfg(), tracker=_linked())
            deps = [f'fn-{n}-dep' for n in range(2, 8)]
            for n, dep in enumerate(deps):
                _write_flow(flow, gh_cfg(), spec_id=dep,
                            tracker=_linked(id=f'I_{n}', identifier=f'#{n+43}'))
            lock = threading.Lock()
            active = 0
            maximum = 0
            observed = []

            def probe(*args, **kwargs):
                nonlocal active, maximum
                with lock:
                    active += 1
                    maximum = max(maximum, active)
                time.sleep(.01)
                with lock:
                    active -= 1
                return False

            def transaction(*args, **kwargs):
                self.assertEqual(active, 0)
                self.assertFalse(kwargs['prepared']['remote'])
                self.assertTrue(list((flow / 'create-first').glob('relate-*.json')))
                observed.append(kwargs['blocked_by'])
                return {'kind': 'applied'}

            with patch.object(R.P, 'display_durable_guard', return_value=None) as guard, \
                    patch.dict(R.P.PROBES, {'github': probe}), \
                    patch.object(R, '_relate_txn', side_effect=transaction), \
                    patch.object(R, 'read_config', wraps=R.read_config) as config:
                results = R.relate_many(flow, SPEC_ID, deps, event='plan', execute=lambda _: None)
            self.assertEqual(len(results), len(deps))
            self.assertEqual(observed, deps)
            self.assertEqual(guard.call_count, len(deps)+1)
            self.assertEqual(config.call_count, 1)
            self.assertGreater(maximum, 1)
            self.assertLessEqual(maximum, CONCURRENCY_CAP)
            self.assertFalse(list((flow / 'create-first').glob('relate-*.json')))

    def test_prepared_probe_preserves_foreign_relation_collision(self):
        from flowctl_tracker import relate as R
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / '.flow'
            dep = 'fn-2-dep'
            _write_flow(flow, gh_cfg(), tracker=_linked())
            _write_flow(flow, gh_cfg(), spec_id=dep,
                        tracker=_linked(id='I_dep', identifier='#43'))
            with patch.object(R.P, 'display_durable_guard', return_value=None), \
                    patch.dict(R.P.PROBES, {'github': lambda *a, **kw: True}):
                result = R.relate_many(flow, SPEC_ID, [dep], event='plan',
                                       execute=lambda _: self.fail('unexpected mutation'))
            self.assertEqual(result[0]['kind'], 'queued')
            saved = json.loads((flow / 'specs' / f'{SPEC_ID}.json').read_text())
            self.assertEqual(saved['tracker']['depRelations'], [])
