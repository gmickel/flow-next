"""Read-only setup snapshots preserve raw false and remembered declines."""
import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_review_findings_parser import FLOWCTL, REPO


class SetupStatusTest(unittest.TestCase):
    def snapshot(self, root):
        out = io.StringIO()
        with patch.object(FLOWCTL, 'get_repo_root', return_value=root), patch.object(FLOWCTL, 'tracker_sync_active', return_value=False), contextlib.redirect_stdout(out):
            FLOWCTL.cmd_setup_status(argparse.Namespace(json=True, platform='codex', plugin_root=str(REPO / 'plugins/flow-next')))
        return json.loads(out.getvalue())

    def test_missing_state_creates_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = self.snapshot(root)
            self.assertTrue(result['first_run'])
            self.assertEqual(result['optional_answers'], {})
            self.assertEqual(list(root.iterdir()), [])

    def test_raw_false_declines_and_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '.flow').mkdir()
            meta = root / '.flow/meta.json'
            config = root / '.flow/config.json'
            meta.write_text(json.dumps({'setup_version': '1', 'setup': {'optional_answers': {'criteria': 'Skip', 'star': 'No thanks'}}}))
            config.write_text(json.dumps({'artifacts': {'html': {'enabled': False}}}))
            before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in (meta, config)]
            result = self.snapshot(root)
            self.assertFalse(result['first_run'])
            self.assertIs(result['config']['artifacts.html.enabled'], False)
            self.assertIsNone(result['config']['review.backend'])
            self.assertEqual(result['optional_answers']['criteria'], 'Skip')
            self.assertEqual(before, [(p.read_bytes(), p.stat().st_mtime_ns) for p in (meta, config)])
            meta.write_text('invalid JSON')
            self.assertTrue(self.snapshot(root)['first_run'])

    def test_docs_and_distinct_spec_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            canonical = REPO / 'plugins/flow-next/skills/flow-next-setup/templates/agents-md-snippet.md'
            (root / 'AGENTS.md').write_bytes(canonical.read_bytes())
            (root / 'SPEC.md').write_text('custom')
            result = self.snapshot(root)
            self.assertEqual(result['docs']['AGENTS.md'], 'current')
            self.assertEqual(result['spec_files'], ['SPEC.md'])

    def test_legacy_inventory_comes_from_canonical_constant(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in FLOWCTL.LEGACY_COPY_ARTIFACTS:
                path = root / name
                if name.endswith("/"):
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.touch()
            self.assertEqual(self.snapshot(root)["legacy_artifacts"], FLOWCTL.LEGACY_COPY_ARTIFACTS)
