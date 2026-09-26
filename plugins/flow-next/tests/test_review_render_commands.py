"""Shared host review rendering and atomic publication command regressions."""
import argparse
import contextlib
import io
import json
from unittest import mock

from test_review_convergence_journal import _JournalReplayBase, flowctl


class TestReviewRenderCommands(_JournalReplayBase):
    def test_record_attach_publishes_one_json_and_consumes_once(self):
        rid = self._reserve()
        output = self.root / 'output.md'
        output.write_text('<verdict>NEEDS_WORK</verdict>')
        payload = self.root / 'payload.json'
        payload.write_text(json.dumps(self._payload()))
        target = self.root / 'receipt.json'
        code, out, err = self._run_cli(
            'review-rounds', 'record', self.spec_id, '--kind', 'plan',
            '--review-type', 'plan', '--reservation-id', rid,
            '--output-file', str(output), '--receipt-target', str(target),
            '--receipt-payload-file', str(payload), '--attach', '--json',
        )
        self.assertEqual(code, 0, err + out)
        self.assertTrue(json.loads(out)['published_from_journal'])
        self.assertEqual(json.loads(target.read_text())['review'], output.read_text())
        self.assertEqual(len(self._data()['review_attempts']), 1)
        self.assertFalse(self._journal_path(rid).exists())

    def test_increment_range_identity_matches_backend_blob(self):
        args = argparse.Namespace(id=self.spec_id, kind='impl', task=self.spec_id+'.1',
                                  base='a'*40, head='b'*40, json=True,
                                  review_type='impl')
        with mock.patch.object(flowctl, '_resolve_review_rounds_args', return_value=(self.spec_id, args.task)), \
             mock.patch.object(flowctl, '_gather_review_identity_diff', return_value='the diff'), \
             mock.patch.object(flowctl, 'enforce_and_increment_review_cap', return_value=(1, 'rid')) as reserve, \
             contextlib.redirect_stdout(io.StringIO()):
            flowctl.cmd_review_rounds_increment(args)
        self.assertEqual(reserve.call_args.kwargs['artifact_sha256'],
                         flowctl._review_artifact_sha256(flowctl.build_impl_review_artifact_blob('the diff')))

    def test_completion_increment_range_identity_includes_specs_and_criteria(self):
        criteria = self.root / '.flow/criteria.md'
        criteria.write_text('global criteria')
        args = argparse.Namespace(id=self.spec_id, kind='plan', task=None,
                                  base='a'*40, head='b'*40, json=True,
                                  review_type='completion')
        with mock.patch.object(flowctl, '_resolve_review_rounds_args', return_value=(self.spec_id, None)), \
             mock.patch.object(flowctl, '_gather_review_identity_diff', return_value='the diff'), \
             mock.patch.object(flowctl, '_load_epic_and_task_specs', return_value=(None, None, 'spec', 'tasks', [])), \
             mock.patch.object(flowctl, 'get_criteria_path', return_value=criteria), \
             mock.patch.object(flowctl, 'enforce_and_increment_review_cap', return_value=(1, 'rid')) as reserve, \
             contextlib.redirect_stdout(io.StringIO()):
            flowctl.cmd_review_rounds_increment(args)
        self.assertEqual(reserve.call_args.kwargs['artifact_sha256'],
                         flowctl._review_artifact_sha256(flowctl.build_completion_review_artifact_blob('spec', 'tasks', 'the diff', 'global criteria')))

    def test_impl_prompt_matches_codex_builder(self):
        task = self.root / '.flow/tasks' / (self.spec_id+'.1.md')
        task.write_text('# Task\n')
        target = self.root / 'prompt.md'
        args = argparse.Namespace(kind='impl', id=self.spec_id+'.1', base='main',
                                  head=None, axis='correctness', focus=None,
                                  receipt=str(self.root/'absent.json'), out=str(target), json=True)
        with mock.patch.object(flowctl, 'get_repo_root', return_value=self.root), \
             mock.patch.object(flowctl, '_capture_review_snapshot', return_value=('a'*40, 'b'*40)), \
             mock.patch.object(flowctl, '_gather_review_scope', return_value='1\t0\tfile.py'), \
             mock.patch.object(flowctl, 'gather_context_hints', return_value='hints'), \
             contextlib.redirect_stdout(io.StringIO()):
            flowctl.cmd_review_prompt(args)
        expected = flowctl.build_review_persona_override() + flowctl.build_review_prompt(
            'impl', context_hints='hints', review_scope='1\t0\tfile.py',
            diff_range='a'*40+'..'+'b'*40, spec_path=task.relative_to(self.root).as_posix(), axis='correctness')
        self.assertEqual(target.read_text(), expected)

    def test_plan_prompt_matches_backend_paths_and_rubric(self):
        spec = self.root / '.flow/specs' / (self.spec_id+'.md')
        spec.write_text('# Demo\n')
        task = self.root / '.flow/tasks' / (self.spec_id+'.1.md')
        task.write_text('# Task\n')
        target = self.root / 'prompt.md'
        args = argparse.Namespace(kind='plan', id=self.spec_id, base='main',
                                  head=None, axis=None, focus=None,
                                  receipt=str(self.root/'absent.json'), out=str(target), json=True)
        with mock.patch.object(flowctl, 'get_repo_root', return_value=self.root), \
             mock.patch.object(flowctl, '_capture_review_snapshot', return_value=('a'*40, 'b'*40)), \
             mock.patch.object(flowctl, 'gather_context_hints', return_value='hints'), \
             contextlib.redirect_stdout(io.StringIO()):
            flowctl.cmd_review_prompt(args)
        expected = flowctl.build_review_persona_override() + flowctl.build_review_prompt(
            'plan', context_hints='hints', spec_path=spec.relative_to(self.root).as_posix(),
            task_spec_paths=[task.relative_to(self.root).as_posix()])
        self.assertEqual(target.read_text(), expected)
