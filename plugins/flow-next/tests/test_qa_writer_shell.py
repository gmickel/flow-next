"""Execute the shipped QA receipt writer through its real shell/CLI boundary."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PLUGIN = Path(__file__).resolve().parents[1]
WORKFLOWS = [
    PLUGIN / 'skills/flow-next-qa/workflow.md',
    PLUGIN / 'codex/skills/flow-next-qa/workflow.md',
]
SHELLS = [shell for name in ('bash', 'zsh') if (shell := shutil.which(name))]


@unittest.skipIf(os.name == 'nt' or not SHELLS, 'requires a POSIX shell')
class QaWriterShellTest(unittest.TestCase):
    def test_coverage_survives_the_actual_receipt_writer(self):
        coverage = {'covered': 1, 'total': 1, 'rids': [{'id': 'R1', 'coverage': 'live'}]}
        for workflow in WORKFLOWS:
            section = workflow.read_text().split('### 6.3 —', 1)[1]
            block = section.split('```bash\n', 1)[1].split('\n```', 1)[0]
            for shell in SHELLS:
                for value in (None, '', json.dumps(coverage)):
                    with self.subTest(workflow=workflow, shell=shell, value=value):
                        with tempfile.TemporaryDirectory() as tmp:
                            root = Path(tmp)
                            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
                            subprocess.run(['git', '-c', 'user.name=QA test', '-c', 'user.email=qa@example.test',
                                            '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                                            'commit', '--allow-empty', '-qm', 'baseline'], cwd=root, check=True)
                            env = dict(os.environ)
                            for key in ('RID_COVERAGE', 'REVIEW_RECEIPT_PATH', 'QA_RECEIPT_OVERRIDE', 'FLOW_STATE_DIR'):
                                env.pop(key, None)
                            env.update(REPO_ROOT=str(root), SPEC_ID='fn-1-smoke', QA_OUTCOME='NA',
                                       NA_REASON='CLI "quoted"\n雪', FLOWCTL=str(PLUGIN / 'scripts/flowctl'),
                                       PYTHON_BIN=sys.executable, TMPDIR=str(root),
                                       QA_FINDINGS='[]', OPEN_P0P1='[]')
                            if value is not None:
                                env['RID_COVERAGE'] = value
                            subprocess.run([sys.executable, str(PLUGIN / 'scripts/flowctl.py'), 'init'],
                                           cwd=root, env=env, check=True, capture_output=True)
                            result = subprocess.run([shell, '-c', 'set -e\n' + block], cwd=root,
                                                    env=env, capture_output=True, text=True)
                            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                            receipt = json.loads((root / '.flow/review-receipts/qa-fn-1-smoke.json').read_text())
                            self.assertEqual(receipt['rid_coverage'], coverage if value else {})
                            self.assertEqual(receipt['qa_outcome'], 'NA')
                            self.assertEqual(receipt['verdict'], 'SHIP')
                            self.assertEqual(receipt['na_reason'], env['NA_REASON'])


if __name__ == '__main__':
    unittest.main()
