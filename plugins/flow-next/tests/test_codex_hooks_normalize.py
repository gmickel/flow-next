"""Regression tests for scripts/normalize_codex_hooks.py.

Guards the historical bug where a Codex config.toml carrying BOTH
`codex_hooks = true` (older install-codex.sh) AND `hooks = true` (Codex/setup)
ended up with a DUPLICATE `hooks` key after a naive sed migration — invalid TOML
that breaks Codex hook loading. The normalizer must always converge to exactly
one `hooks = true` under [features] and no `codex_hooks`, idempotently.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "normalize_codex_hooks.py"

# Load the module directly for in-process unit assertions on normalize().
_spec = importlib.util.spec_from_file_location("normalize_codex_hooks", SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
normalize = _mod.normalize


def _features_hooks(text: str):
    """Return the list of hooks/codex_hooks keys seen inside [features]."""
    in_feat = False
    hooks, codex_hooks = 0, 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            in_feat = s == "[features]"
            continue
        if in_feat:
            if s.startswith("hooks"):
                hooks += 1
            if s.startswith("codex_hooks"):
                codex_hooks += 1
    return hooks, codex_hooks


def _assert_normal(text: str):
    hooks, codex_hooks = _features_hooks(text)
    assert hooks == 1, f"expected exactly one hooks key, got {hooks}\n{text}"
    assert codex_hooks == 0, f"expected no codex_hooks key, got {codex_hooks}\n{text}"
    # Must be valid TOML if a parser is available (py3.11+ ships tomllib).
    try:
        import tomllib
    except ModuleNotFoundError:
        return
    data = tomllib.loads(text)
    assert data.get("features", {}).get("hooks") is True


def test_both_keys_dedup_to_one():
    """The exact bug: both codex_hooks and hooks present -> single hooks."""
    src = (
        'model = "gpt-5"\n'
        "[features]\n"
        "codex_hooks = true  # flow-next\n"
        "hooks = true\n"
        "shell_tool = true\n"
        "[agents]\n"
        "max_threads = 12\n"
    )
    out = normalize(src)
    _assert_normal(out)
    # Content outside [features] preserved.
    assert 'model = "gpt-5"' in out
    assert "shell_tool = true" in out
    assert "[agents]" in out and "max_threads = 12" in out


def test_only_deprecated_key_migrates():
    src = "[features]\ncodex_hooks = true  # flow-next\nshell_tool = true\n"
    out = normalize(src)
    _assert_normal(out)


def test_only_modern_key_is_noop_shape():
    src = "[features]\nhooks = true\nshell_tool = true\n"
    out = normalize(src)
    _assert_normal(out)


def test_features_without_hooks_gets_one():
    src = "[features]\nshell_tool = true\n"
    out = normalize(src)
    _assert_normal(out)


def test_no_features_section_appended():
    src = 'model = "gpt-5"\n[agents]\nmax_threads = 4\n'
    out = normalize(src)
    _assert_normal(out)
    assert 'model = "gpt-5"' in out
    assert "[agents]" in out


def test_multiple_duplicate_hooks_collapse():
    src = "[features]\nhooks = true\nhooks = true\ncodex_hooks = true\nshell_tool = true\n"
    out = normalize(src)
    _assert_normal(out)


def test_idempotent():
    src = "[features]\ncodex_hooks = true\nhooks = true\n"
    once = normalize(src)
    twice = normalize(once)
    assert once == twice
    _assert_normal(twice)


def test_empty_file_gets_features():
    out = normalize("")
    _assert_normal(out)


def test_cli_writes_in_place(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("[features]\ncodex_hooks = true  # flow-next\nhooks = true\n")
    rc = subprocess.run(
        [sys.executable, str(SCRIPT), str(cfg)], capture_output=True
    ).returncode
    assert rc == 0
    _assert_normal(cfg.read_text())


def test_cli_missing_arg_exit_2():
    rc = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True).returncode
    assert rc == 2
