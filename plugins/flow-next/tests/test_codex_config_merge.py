"""Config merge regression: ownership, duplicate recovery, atomicity and scope."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('merge_codex_config', ROOT / 'scripts/merge_codex_config.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SOURCE = ROOT / 'plugins/flow-next/codex/agents'
ROLE = '[agents.agents_md_scout]\ndescription = "old"\nconfig_file = "agents/agents-md-scout.toml"\n'


class ConfigMergeTests(unittest.TestCase):
    def test_utf8_config_and_roles_under_legacy_locale(self):
        original_open = Path.open
        original_fdopen = os.fdopen
        def locale_open(path, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
            return original_open(path, mode, buffering, ('cp1252' if encoding in (None, 'locale') and 'b' not in mode else encoding), errors, newline)
        def locale_fdopen(fd, mode='r', buffering=-1, encoding=None, **kwargs):
            return original_fdopen(fd, mode, buffering, encoding=encoding or 'cp1252', **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'roles'
            source.mkdir()
            (source / 'scout.toml').write_text('description = "Unicode \u2192 \u201d"\n', encoding='utf-8')
            config = root / 'config.toml'
            user = '[custom]\nnote = "\u65e5\u672c"\n'
            config.write_text(user, encoding='utf-8')
            original_bytes = config.read_bytes()
            with mock.patch.object(Path, 'open', locale_open), mock.patch.object(os, 'fdopen', locale_fdopen):
                mod.update(config, source, 12)
                mod.update(config, source, 12)
            data = tomllib.loads(config.read_text(encoding='utf-8'))
            self.assertEqual(data['custom']['note'], '\u65e5\u672c')
            self.assertEqual(data['agents']['scout']['description'], 'Unicode \u2192 \u201d')
            self.assertEqual(next(root.glob('config.toml.pre-flow-next-*')).read_bytes(), original_bytes)

    def test_unmarked_duplicate_recovery_and_scope(self):
        text = '[agents]\nenabled = true\nmax_concurrent_threads_per_session = 12\n' + ROLE
        text += mod.END + '\n' + mod.BEGIN + '\nmax_threads = 12\n' + ROLE + mod.END + '\n'
        result = mod.merge(text, SOURCE, 12)
        data = tomllib.loads(result)
        self.assertEqual(data['agents']['max_threads'], 12)
        self.assertTrue(data['agents']['enabled'])
        self.assertNotIn('max_concurrent_threads_per_session', data['agents'])
        self.assertNotIn('max_threads', data['agents']['agents_md_scout'])
        self.assertEqual(mod.merge(result, SOURCE, 12), result)

    def test_user_tables_and_role_overrides_preserved(self):
        user = '[mcp_servers.mine]\ncommand = "my-command"\n[agents.private]\nconfig_file = "private.toml"\nmax_threads = 3\n'
        result = mod.merge('[agents]\nmax_threads = 7\n' + user + ROLE + 'model = "custom"\n', SOURCE, 9)
        data = tomllib.loads(result)
        self.assertIn(user, result)
        self.assertEqual(data['agents']['max_threads'], 9)
        self.assertEqual(data['agents']['private']['max_threads'], 3)
        self.assertEqual(data['agents']['agents_md_scout']['model'], 'custom')

    def test_markers_do_not_authorize_deleting_unrelated_tables(self):
        user = '[agents.private]\nconfig_file = "private.toml"\n'
        out = mod.merge(mod.BEGIN + '\n' + user + ROLE + mod.END + '\n', SOURCE, 12)
        self.assertIn(user, out)

    def test_skill_config_array_tables_preserved(self):
        text = '[[skills.config]]\npath = "/skills/one"\nenabled = false\n[[skills.config]]\npath = "/skills/two"\nenabled = true\n'
        out = mod.merge(text, SOURCE, 12)
        self.assertEqual(tomllib.loads(out)['skills'], tomllib.loads(text)['skills'])
        self.assertEqual(mod.merge(out, SOURCE, 12), out)

    def test_marker_inside_user_string_cannot_silently_change(self):
        text = '[custom]\nnote = """\n' + mod.END + '\n"""\n'
        with self.assertRaises(ValueError):
            mod.merge(text, SOURCE, 12)

    def test_owned_name_with_other_path_refused(self):
        with self.assertRaises(ValueError):
            mod.merge(ROLE.replace('agents/agents-md-scout.toml', 'my-scout.toml'), SOURCE, 12)

    def test_conflicting_overrides_refused(self):
        with self.assertRaises(ValueError):
            mod.merge(ROLE + 'model = "one"\n' + ROLE + 'model = "two"\n', SOURCE, 12)

    def test_invalid_unrelated_toml_preserved_without_backup_or_write(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'config.toml'
            p.write_text('model = "one"\nmodel = "two"\n')
            original = p.read_bytes()
            with self.assertRaises(ValueError):
                mod.update(p, SOURCE, 12)
            self.assertEqual(p.read_bytes(), original)
            self.assertEqual(list(Path(temp).iterdir()), [p])

    def test_backup_permissions_and_noop(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'config.toml'
            p.write_text('model = "private-model"\n')
            original = p.read_bytes()
            p.chmod(0o600)
            mod.update(p, SOURCE, 12, check=True)
            self.assertEqual(p.read_bytes(), original)
            mod.update(p, SOURCE, 12)
            backups = list(Path(temp).glob('config.toml.pre-flow-next-*'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), original)
            if os.name != 'nt':
                self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
                self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            mod.update(p, SOURCE, 12)
            self.assertEqual(list(Path(temp).glob('config.toml.pre-flow-next-*')), backups)

    def test_empty_and_hooks_migration(self):
        for text in ['', '[features]\nhooks = true\nhooks = true\n', '[features]\ncodex_hooks = true\nhooks = true\n', '[features]\nhooks = true\n# --- flow-next features ---\n[features]\ncodex_hooks = true\n# --- end flow-next features ---\n']:
            with self.subTest(text=text):
                out = mod.merge(text, SOURCE, 12)
                data = tomllib.loads(out)
                self.assertTrue(data['features']['hooks'])
                self.assertEqual(data['agents']['max_threads'], 12)
                self.assertEqual(mod.merge(out, SOURCE, 12), out)

    @unittest.skipIf(sys.platform == 'win32', 'Native Windows bash is a WSL stub')
    def test_installer_preflight_refuses_before_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / '.codex'
            dest.mkdir()
            p = dest / 'config.toml'
            p.write_text(ROLE.replace('agents/agents-md-scout.toml', 'private.toml'))
            original = p.read_bytes()
            env = dict(os.environ, HOME=temp, CODEX_HOME=str(dest))
            run = subprocess.run(['bash', str(ROOT / 'scripts/install-codex.sh')], env=env, capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(p.read_bytes(), original)
            self.assertEqual(list(dest.iterdir()), [p])

    @unittest.skipIf(sys.platform == 'win32', 'Native Windows bash is a WSL stub')
    def test_real_installer_recovers_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            dest = home / 'work codex'
            dest.mkdir()
            p = dest / 'config.toml'
            p.write_text('[agents]\nenabled = true\n' + ROLE + mod.END + '\n' + mod.BEGIN + '\nmax_threads = 12\n' + ROLE + mod.END + '\n')
            env = dict(os.environ, HOME=str(home), CODEX_HOME=str(dest), CODEX_MAX_THREADS='12')
            first = None
            for _ in range(2):
                run = subprocess.run(['bash', str(ROOT / 'scripts/install-codex.sh')], env=env, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                data = tomllib.loads(p.read_text())
                self.assertEqual(data['agents']['max_threads'], 12)
                if first is not None:
                    self.assertEqual(p.read_bytes(), first)
                first = p.read_bytes()
            self.assertTrue((dest / 'agents/agents-md-scout.toml').exists())


if __name__ == '__main__':
    unittest.main()
