"""Planning bundle, coverage and additive bulk authoring behavior (fn-259)."""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
import unittest
from contextlib import redirect_stdout
from unittest import mock

from test_task_bulk_create import TaskBulkCreateTestCase as _BulkFixture


class PlanningPreflight(unittest.TestCase):
    setUp = _BulkFixture.setUp
    tearDown = _BulkFixture.tearDown
    _call = _BulkFixture._call
    _write = _BulkFixture._write
    _bulk = _BulkFixture._bulk
    _bulk_from_path = _BulkFixture._bulk_from_path

    def test_bulk_collects_invalid_items_and_writes_nothing(self):
        path = self._write('bad.json', json.dumps([
            {'title': ''}, {'title': 'good', 'surprise': 1},
            {'title': 'files', 'description_file': 'missing.md'}, 42,
        ]))
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            self.flowctl.cmd_task_create(argparse.Namespace(
                spec=self.spec_id, json=True, from_json=path))
        result = json.loads(out.getvalue())
        self.assertEqual(len(result['errors']), 4)
        self.assertIn('touches', result['allowed_keys'])
        self.assertIn('description_file', result['allowed_keys'])
        self.assertEqual(list(self.tasks_dir.glob('*.*')), [])

    def test_relative_files_and_touches(self):
        nested = self.tmpdir / 'authoring'
        nested.mkdir()
        (nested / 'description.md').write_text('## Description\nDetailed approach\n')
        (nested / 'acceptance.md').write_text('## Acceptance\n- Works\n')
        payload = nested / 'tasks.json'
        payload.write_text(json.dumps([{
            'title': 'File input', 'description_file': 'description.md',
            'acceptance_file': 'acceptance.md', 'touches': 'src/a.py, tests/a.py',
            'satisfies': ['R1'],
        }]))
        result = self._bulk_from_path(str(payload))
        text = (self.tasks_dir / (result['tasks'][0]['id'] + '.md')).read_text()
        self.assertIn('Touches: src/a.py, tests/a.py', text)
        self.assertIn('Detailed approach', text)
        self.assertEqual(text.count('## Acceptance'), 1)
        self.assertIn('- Works', text)

    def test_coverage_uses_allocated_ids_and_warns_only(self):
        spec = self.tmpdir / '.flow' / 'specs' / (self.spec_id + '.md')
        spec.write_text('# Coverage\n\n## Acceptance Criteria\n- **R1:** One\n- **R2:** Two\n')
        self._bulk([{'title': 'Earlier'}])
        result = self._bulk([{'title': 'Owner', 'satisfies': ['R1', 'R99']}])
        owner = result['tasks'][0]['id']
        output = self._call(func=self.flowctl.cmd_validate, spec=self.spec_id, all=False, coverage=True)
        self.assertTrue(output['valid'])
        self.assertIn('R99', '\n'.join(output['warnings']))
        self.assertIn('uncovered R-IDs: R2', '\n'.join(output['warnings']))
        self.assertIn(f'| R1 | One | {owner} |', output['requirement_coverage'])
        self.assertIn('| R2 | Two | — | Uncovered |', output['requirement_coverage'])

    def test_preflight_matches_probes_and_isolates_failure(self):
        expected = self._call(func=self.flowctl.cmd_config_get)
        strategy = self._call(func=self.flowctl.cmd_strategy_status)
        with mock.patch.object(self.flowctl, 'cmd_glossary_list', side_effect=OSError('unreadable')):
            result = self._call(func=self.flowctl.cmd_preflight)
        self.assertEqual(result['value'], expected['value'])
        self.assertEqual(result['probes']['strategy']['value'], strategy)
        self.assertEqual(result['probes']['glossary']['status'], 'error')
        self.assertEqual(result['probes']['tracker']['status'], 'ok')
        self.assertEqual(result['probes']['review_backend']['status'], 'ok')

    def test_preflight_counts_active_decisions(self):
        def decisions(args):
            self.assertEqual((args.track, args.category), ('knowledge', 'decisions'))
            self.flowctl.json_output({'entries': [{'id': 'one'}, {'id': 'two'}]})
        with mock.patch.object(self.flowctl, 'cmd_memory_list', side_effect=decisions):
            result = self._call(func=self.flowctl.cmd_preflight)
        self.assertEqual(result['probes']['decisions']['value'], {'entry_count': 2})

    def test_refine_gate_preserves_fail_open_and_explicit_off(self):
        if not shutil.which("bash") or not shutil.which("jq"):
            self.skipTest("bash and jq required for executable skill gate")
        skill = Path(__file__).resolve().parents[1] / "skills/flow-next-refine/SKILL.md"
        fence = next(f for f in re.findall(r"```bash\n(.*?)\n```", skill.read_text(), re.S)
                     if "# One preflight bundle" in f)
        fake = self.tmpdir / "preflight"
        fake.write_text('#!/bin/sh\ncat "$PREFLIGHT_PAYLOAD"\n')
        fake.chmod(0o755)
        for status, forced, expected in (("ok", "", "0:0"), ("error", "", "1:1"),
                                         ("error", "off", "0:0")):
            payload = {"probes": {
                "glossary": {"status": status, "value": {"total_terms": 0}},
                "decisions": {"status": status, "value": {"entry_count": 0}},
                "strategy": {"status": status, "value": {"sections_filled": 0}},
            }}
            path = self._write("preflight.json", json.dumps(payload))
            env = {**os.environ, "FLOWCTL": str(fake), "PREFLIGHT_PAYLOAD": path,
                   "TMPDIR": str(self.tmpdir), "DOC_AWARE_FORCE": forced,
                   "STRATEGY_AWARE_FORCE": forced}
            run = subprocess.run(["bash", "-c", fence + '\nprintf "%s:%s" "$DOC_AWARE" "$STRATEGY_AWARE"'],
                                 env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(run.stdout.endswith(expected), run.stdout)


del _BulkFixture

if __name__ == '__main__':
    unittest.main()
