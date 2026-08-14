"""Reader-schema drift test + fixture validation (fn-138.2, R2+R4).

Sibling of test_flow_config_schema.py (keeps modules under ~500 lines).
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
ARTIFACT = ROOT / "schema" / "flow-config.schema.json"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(REPO / "scripts"))
import flowctl  # noqa: E402
from flowctl_tracker.resolved_cache import SCOPES  # noqa: E402
from gen_flow_config_schema import _default_leaves  # noqa: E402

# fn-138.3: the ONE flowctl constant carries the published URL; tests
# reference it rather than re-embedding the string.
SCHEMA_URL = flowctl.FLOW_CONFIG_SCHEMA_URL

# (b) Annotated allowlist: dotted keys the schema declares that have NO
# get_default_config() leaf. Union semantics with (a) - a key may move
# between the defaults tree and this list without breaking the comparator.
ALLOWLIST: dict[str, str] = {
    "$schema": "stamped by /flow-next:setup; inert to flowctl (R3 in fn-138.3)",
    "tracker.perTracker.repo": (
        "machine-written GitHub linkage (discovery ceremony); not seeded"
    ),
    "tracker.resolved.destination.statusIds": (
        "machine-written by flowctl tracker resolve"
    ),
    "tracker.resolved.destination.stateIds": (
        "machine-written by flowctl tracker resolve (Linear)"
    ),
    "tracker.resolved.capabilities": (
        "machine-written provider capability cache"
    ),
    "tracker.resolved.scopeResolvedAt": (
        "machine-written; property names are the four canonical scopes "
        "(contain dots - terminal container)"
    ),
    "tracker.resolved.resolvedAt": "machine-written resolve completion stamp",
    # Dict-read keys: consumed by flowctl_tracker through parsed config dicts
    # (per.get/transport.get), invisible to the four-helper call-site guard -
    # inventoried here manually; the guard cannot see dict navigation.
    "tracker.perTracker.owner": "dynamic per.get via _FINGERPRINT_KEYS (resolved_cache.py)",
    "tracker.perTracker.authScheme": "dict-read (resolve_verb.py)",
    "tracker.perTracker.issueType": "dict-read (providers/jira.py)",
    "tracker.perTracker.blocksLinkType": "dict-read (relate/providers.py)",
    "tracker.perTracker.preferredTransport": "dict-read (facade/helpers.py)",
    "tracker.perTracker.transport": "dict-read legacy alias (facade/helpers.py)",
    "tracker.transport.timeoutS": "dict-read (resolve_verb.py)",
    "tracker.transport.maxRetries": "dict-read (resolve_verb.py)",
    "tracker.transport.backoffCapS": "dict-read (resolve_verb.py)",
    "tracker.transport.concurrency": "dict-read (resolve_verb.py)",
    "makePr.derivedPaths": (
        "validated-only reader key (make-pr export rules); never seeded"
    ),
}

# Containers the schema-key walk must NOT descend into: their property
# names are not dotted-path segments (scope keys contain literal dots).
TERMINAL_CONTAINERS = frozenset({
    "tracker.resolved.scopeResolvedAt",
    # capabilities carries boolean flags PLUS the machine-written _source
    # provenance object (GitLab resolver) - one canonical leaf, not per-key.
    "tracker.resolved.capabilities",
})

# Both quote styles: flowctl.py carries at least one single-quoted read
# (get_config('tracker.type') inside an f-string) - a double-quote-only
# regex would let future single-quoted call sites slip past the guard.
_CALL_RE = re.compile(
    r"(?:\bget_config|\b_get_config_from_file|\b_tree_probe"
    r"|\b_walk_config_value)"
    r"\(\s*(f?)(['\"])([^'\"]+)\2"
)

_ANNOTATION_KEYS = {"$schema", "$id", "title", "description", "default"}
_VALIDATION_KEYS = {
    "type",
    "enum",
    # fn-168 (PR #295 bot r3): the review-round cap's runtime contract is >= 1,
    # and a schema that accepts 0 lets an editor bless a value flowctl then
    # silently replaces with the default. The published artifact has to carry the
    # bound, so the checker learns the keyword rather than the artifact dropping
    # a real constraint.
    "minimum",
    "properties",
    "additionalProperties",
    "patternProperties",
    "anyOf",
    "pattern",
    "items",
}
_SUPPORTED_KEYS = _ANNOTATION_KEYS | _VALIDATION_KEYS


def _canonical_keys() -> set[str]:
    return set(_default_leaves(flowctl.get_default_config())) | set(ALLOWLIST)


def _schema_leaf_paths(schema: dict, prefix: str = "") -> set[str]:
    """Walk nested properties; terminal / no-properties nodes are leaves."""
    found: set[str] = set()
    props = schema.get("properties")
    if not isinstance(props, dict):
        return found
    for key, child in props.items():
        if not isinstance(child, dict):
            continue
        path = f"{prefix}.{key}" if prefix else key
        child_props = child.get("properties")
        if path in TERMINAL_CONTAINERS or not isinstance(child_props, dict):
            found.add(path)
        else:
            found |= _schema_leaf_paths(child, path)
    return found


def _literal_accounted(text: str, canonical: set[str], *, fstr: bool) -> bool:
    """Return True iff a config-read literal is covered by canonical keys."""
    if not fstr:
        return text in canonical
    prefix = text.split("{", 1)[0]
    if not prefix or not prefix.endswith("."):
        return False
    return any(
        k.startswith(prefix) or (k + ".") == prefix for k in canonical
    )


def _inventory_files() -> list[Path]:
    base = ROOT / "scripts"
    files = [base / "flowctl.py"]
    tracker = base / "flowctl_tracker"
    files.extend(sorted(tracker.rglob("*.py")))
    return files


class SchemaError(Exception):
    """Raised when the schema itself is malformed / uses unsupported keywords."""


def _matches_type(instance: Any, type_name: str) -> bool:
    if type_name == "object":
        return isinstance(instance, dict)
    if type_name == "array":
        return isinstance(instance, list)
    if type_name == "string":
        return isinstance(instance, str)
    if type_name == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if type_name == "number":
        return (
            isinstance(instance, (int, float))
            and not isinstance(instance, bool)
        )
    if type_name == "boolean":
        return isinstance(instance, bool)
    if type_name == "null":
        return instance is None
    raise SchemaError(f"unknown type name {type_name!r}")


def validate(instance: Any, schema: Any, path: str = "$") -> list[str]:
    """Minimal draft-2020-12 subset; fail closed on unsupported keywords."""
    if not isinstance(schema, dict):
        raise SchemaError(f"schema node at {path} is not a dict")
    unknown = set(schema) - _SUPPORTED_KEYS
    if unknown:
        raise SchemaError(
            f"unsupported keyword(s) at {path}: {sorted(unknown)}"
        )

    errors: list[str] = []

    if "type" in schema:
        raw = schema["type"]
        type_names = [raw] if isinstance(raw, str) else list(raw)
        if not type_names or not all(isinstance(t, str) for t in type_names):
            raise SchemaError(f"malformed type at {path}")
        if not any(_matches_type(instance, t) for t in type_names):
            errors.append(
                f"{path}: type mismatch (want {type_names}, got "
                f"{type(instance).__name__})"
            )

    if "enum" in schema:
        enum = schema["enum"]
        ok = any(
            isinstance(instance, bool) == isinstance(e, bool) and instance == e
            for e in enum
        )
        if not ok:
            errors.append(f"{path}: value not in enum")

    if "minimum" in schema:
        bound = schema["minimum"]
        if isinstance(bound, bool) or not isinstance(bound, (int, float)):
            raise SchemaError(f"malformed minimum at {path}")
        # bools are ints in Python; a bool instance is a type error, not a bound
        # comparison, and `type` already reported it.
        if (
            isinstance(instance, (int, float))
            and not isinstance(instance, bool)
            and instance < bound
        ):
            errors.append(f"{path}: {instance} is below minimum {bound}")

    if "pattern" in schema and isinstance(instance, str):
        if not re.search(schema["pattern"], instance):
            errors.append(f"{path}: does not match pattern")

    if isinstance(instance, dict):
        props = schema.get("properties")
        if not isinstance(props, dict):
            props = {}
        patterns = schema.get("patternProperties")
        if not isinstance(patterns, dict):
            patterns = {}
        addl = schema.get("additionalProperties")
        for key, val in instance.items():
            covered = False
            child_path = f"{path}.{key}"
            if key in props:
                covered = True
                errors.extend(validate(val, props[key], child_path))
            for pat, sub in patterns.items():
                if re.search(pat, key):
                    covered = True
                    errors.extend(validate(val, sub, child_path))
            if not covered:
                if addl is False:
                    errors.append(
                        f"{child_path}: additional property {key!r} "
                        f"not allowed"
                    )
                elif isinstance(addl, dict):
                    errors.extend(validate(val, addl, child_path))

    if "items" in schema and isinstance(instance, list):
        for i, el in enumerate(instance):
            errors.extend(validate(el, schema["items"], f"{path}[{i}]"))

    if "anyOf" in schema:
        branches = schema["anyOf"]
        matched = False
        for branch in branches:
            # SchemaError from a malformed branch must propagate (fail closed).
            if not validate(instance, branch, path):
                matched = True
                break
        if not matched:
            errors.append(f"{path}: no anyOf branch matched")

    return errors


class ReaderSchemaDrift(unittest.TestCase):
    def test_schema_keys_match_reader_keys_both_directions(self) -> None:
        schema = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        schema_keys = _schema_leaf_paths(schema)
        reader_keys = _canonical_keys()
        schema_only = sorted(schema_keys - reader_keys)
        reader_only = sorted(reader_keys - schema_keys)
        self.assertEqual(
            schema_keys,
            reader_keys,
            f"schema_only={schema_only} reader_only={reader_only}",
        )

    def test_allowlist_not_assumed_disjoint(self) -> None:
        defaults = set(_default_leaves(flowctl.get_default_config()))
        # Overlap allowed; comparator is a union, never assumes disjoint.
        self.assertEqual(
            _canonical_keys(),
            defaults | set(ALLOWLIST),
        )

    def test_allowlist_entries_annotated(self) -> None:
        for key, note in ALLOWLIST.items():
            self.assertIsInstance(note, str, key)
            self.assertTrue(note.strip(), f"empty annotation for {key}")


class ConfigReadLiteralGuard(unittest.TestCase):
    def test_literals_accounted_for(self) -> None:
        canonical = _canonical_keys()
        violations: list[str] = []
        total = 0
        for path in _inventory_files():
            text = path.read_text(encoding="utf-8")
            for match in _CALL_RE.finditer(text):
                fprefix, lit = match.group(1), match.group(3)
                total += 1
                is_f = fprefix == "f"
                if not _literal_accounted(lit, canonical, fstr=is_f):
                    rel = path.relative_to(ROOT)
                    kind = "f-string" if is_f else "literal"
                    violations.append(f"{rel}: {kind} {lit!r}")
        self.assertGreaterEqual(
            total,
            8,
            "regex found too few call sites (may have silently rotted)",
        )
        self.assertEqual(
            violations,
            [],
            "unaccounted config-read literal(s); add to schema generator "
            "TABLE + ALLOWLIST/defaults: " + "; ".join(violations),
        )

    def test_regex_catches_both_quote_styles(self) -> None:
        src = (
            'x = get_config("memory.enabled")\n'
            "y = get_config('tracker.type')\n"
            'z = _get_config_from_file(f"tracker.perEvent.{event}")\n'
        )
        hits = [(m.group(1), m.group(3)) for m in _CALL_RE.finditer(src)]
        self.assertEqual(
            hits,
            [
                ("", "memory.enabled"),
                ("", "tracker.type"),
                ("f", "tracker.perEvent.{event}"),
            ],
        )

    def test_literal_helper_boundary_cases(self) -> None:
        canonical = _canonical_keys()
        self.assertFalse(
            _literal_accounted(
                "makePr.derivedPathsX", canonical, fstr=False
            )
        )
        self.assertFalse(
            _literal_accounted(
                "memory.enabledExtra", canonical, fstr=False
            )
        )
        self.assertTrue(
            _literal_accounted("memory.enabled", canonical, fstr=False)
        )
        self.assertTrue(
            _literal_accounted("tracker.perEvent.", canonical, fstr=True)
        )


class StructuralCheckerFailsClosed(unittest.TestCase):
    def test_non_dict_schema_raises(self) -> None:
        with self.assertRaises(SchemaError):
            validate("x", "not-a-dict")  # type: ignore[arg-type]

    def test_unknown_keyword_raises(self) -> None:
        with self.assertRaises(SchemaError):
            validate("ab", {"type": "string", "minLength": 3})

    def test_unknown_type_name_raises(self) -> None:
        with self.assertRaises(SchemaError):
            validate(1, {"type": "widget"})

    def test_enum_bool_int_strict(self) -> None:
        self.assertTrue(validate(True, {"enum": [1]}))
        self.assertTrue(validate(0, {"enum": [False]}))

    def test_bool_not_integer(self) -> None:
        self.assertTrue(validate(True, {"type": "integer"}))


class FixtureValidation(unittest.TestCase):
    schema: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    def _valid(self, cfg: dict) -> None:
        errs = validate(cfg, self.schema)
        self.assertEqual(errs, [], f"expected valid, got {errs}")

    def _invalid(self, cfg: dict) -> None:
        errs = validate(cfg, self.schema)
        self.assertTrue(errs, f"expected invalid for {cfg!r}")

    def test_init_persisted_defaults_plus_schema_validates(self) -> None:
        cfg = flowctl._init_persisted_defaults()
        cfg["$schema"] = SCHEMA_URL
        self._valid(cfg)

    def test_get_default_config_plus_schema_validates(self) -> None:
        cfg = flowctl.get_default_config()
        cfg["$schema"] = SCHEMA_URL
        self._valid(cfg)

    def test_valid_review_backends(self) -> None:
        self._valid({"review": {"backend": "codex"}})
        self._valid({"review": {"backend": "codex:gpt-5.4:high"}})
        self._valid({"review": {"backend": "codex:m:none"}})
        self._valid({"review": {"backend": "cursor:some-model"}})
        self._valid({"review": {"backend": None}})

    def test_valid_land_clean_pattern(self) -> None:
        self._valid({"land": {"cleanReviewCommentPattern": None}})
        self._valid({"land": {"cleanReviewCommentPattern": ""}})

    def test_valid_open_namespaces(self) -> None:
        self._valid({"tracker": {"perTracker": {"futureKey": 123}}})
        self._valid(
            {"tracker": {"resolved": {"someNewBlock": {"x": 1}}}}
        )

    def test_valid_scope_resolved_at(self) -> None:
        stamps = {scope: "2026-07-31T00:00:00Z" for scope in SCOPES}
        self._valid(
            {"tracker": {"resolved": {"scopeResolvedAt": stamps}}}
        )

    def test_valid_models_roles(self) -> None:
        self._valid(
            {
                "models": {
                    "roles": {
                        "review": {"codex": "gpt-5.6-sol:high"},
                    },
                },
            }
        )

    def test_valid_make_pr_derived_paths(self) -> None:
        self._valid(
            {
                "makePr": {
                    "derivedPaths": {
                        "dualCopy": [{"path": "a", "source": "b"}],
                        "state": [{"prefix": ".flow/"}],
                    },
                },
            }
        )

    def test_removed_work_namespace_is_invalid(self) -> None:
        # flow-98: the packaged-delegation keys are gone from the reader AND
        # the schema, so an editor flags a config that still carries them.
        # flowctl itself never fails on them - it prints one advisory line.
        self._invalid({"work": {"delegate": "codex"}})
        self._invalid({"work": {"delegateModel": "gpt-5.6-terra"}})
        self._invalid({"models": {"roles": {"delegate": {"codex": "m"}}}})

    def test_invalid_enums(self) -> None:
        self._invalid({"pipeline": {"qa": "yes"}})
        self._invalid({"tracker": {"conflictTiebreak": "flow"}})

    def test_invalid_backend_grammar(self) -> None:
        self._invalid({"review": {"backend": "copilot:m:none"}})
        self._invalid({"review": {"backend": "rp:some-model"}})
        self._invalid({"review": {"backend": "bogus"}})

    def test_invalid_unknown_keys(self) -> None:
        self._invalid({"nonsuch": {}})
        self._invalid({"memory": {"bogus": True}})

    def test_invalid_types(self) -> None:
        self._invalid({"memory": {"enabled": "yes"}})
        self._invalid({"land": {"patienceMinutes": True}})

    def test_invalid_models_roles_closed(self) -> None:
        self._invalid(
            {"models": {"roles": {"bogusRole": {"codex": "m"}}}}
        )
        self._invalid(
            {"models": {"roles": {"review": {"rp": "m"}}}}
        )

    def test_invalid_scope_map(self) -> None:
        self._invalid(
            {
                "tracker": {
                    "resolved": {
                        "scopeResolvedAt": {"bogus.scope": "t"},
                    },
                },
            }
        )

    def test_invalid_make_pr_rule_types(self) -> None:
        self._invalid(
            {
                "makePr": {
                    "derivedPaths": {"dualCopy": [{"path": 1}]},
                },
            }
        )

    def test_invalid_schema_url_type(self) -> None:
        self._invalid({"$schema": 42})


class TestArtifactKeywordsSupported(unittest.TestCase):
    """Every node of the committed artifact uses only checker-supported keywords.

    The checker's fail-closed guarantee is per-visited-node; this walk is
    instance-independent, so an unsupported keyword in a branch no fixture
    exercises still fails the suite (host review P3, fn-138.2)."""

    def test_every_schema_node_uses_supported_keys(self) -> None:
        def walk(node, path="$"):
            if isinstance(node, dict):
                unknown = set(node) - _SUPPORTED_KEYS - {"$id", "title"}
                # Property NAMES are not keywords - only walk keyword positions.
                for key, value in node.items():
                    if key in ("properties", "patternProperties"):
                        for name, sub in value.items():
                            walk(sub, f"{path}.{key}[{name}]")
                    elif key in ("items", "additionalProperties") and isinstance(value, dict):
                        walk(value, f"{path}.{key}")
                    elif key == "anyOf":
                        for i, sub in enumerate(value):
                            walk(sub, f"{path}.anyOf[{i}]")
                self.assertFalse(
                    unknown, f"unsupported schema keywords at {path}: {sorted(unknown)}"
                )

        walk(json.loads(ARTIFACT.read_text(encoding="utf-8")))


class TestDictReadGuard(unittest.TestCase):
    """Mechanical guard for dict-navigation config reads in flowctl_tracker.

    The four-helper call-site guard cannot see `per.get("key")` /
    `transport.get("key")` navigation - this test greps those literal forms
    across flowctl_tracker and asserts every read key has a schema entry, so
    a future `per.get("newSetting")` fails the suite instead of silently
    missing from the schema (PR #280 round 5)."""

    _PER_RE = re.compile(r"""\bper\.get\(\s*["']([A-Za-z]+)["']\s*\)""")
    _TRANSPORT_RE = re.compile(r"""\btransport\.get\(\s*["']([A-Za-z]+)["']\s*\)""")

    def test_dict_read_keys_have_schema_entries(self) -> None:
        schema = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        tracker_props = schema["properties"]["tracker"]["properties"]
        per_props = set(tracker_props["perTracker"]["properties"])
        transport_props = set(tracker_props["transport"]["properties"])
        tracker_dir = REPO / "plugins" / "flow-next" / "scripts" / "flowctl_tracker"
        missing = []
        for path in sorted(tracker_dir.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for key in self._PER_RE.findall(text):
                if key not in per_props:
                    missing.append(f"tracker.perTracker.{key} ({path.name})")
            for key in self._TRANSPORT_RE.findall(text):
                if key not in transport_props:
                    missing.append(f"tracker.transport.{key} ({path.name})")
        # Dynamic reads through the fingerprint registry (per.get(k) with k
        # from _FINGERPRINT_KEYS) are invisible to the literal grep - import
        # the registry itself so a new fingerprint key without a schema entry
        # fails here (PR #280 round 7). "type" lives on tracker, not perTracker.
        from flowctl_tracker import resolved_cache as _rc

        for key in _rc._FINGERPRINT_KEYS:
            if key == "type":
                continue
            if key not in per_props:
                missing.append(f"tracker.perTracker.{key} (_FINGERPRINT_KEYS)")
        self.assertFalse(
            missing,
            "dict-read config keys without schema entries: " + ", ".join(missing),
        )





class TestBackendGrammarMatchesParser(unittest.TestCase):
    """Exhaustive equivalence: the schema's review.backend grammar accepts a
    string iff BackendSpec.parse does, over every shape up to the parser's
    two-colon cap for every backend (77 cases). Ends the per-shape whack-a-mole
    permanently (PR #280 rounds 1-3).

    Deliberate boundary: whitespace-PADDED components (parse strips them, e.g.
    `codex: model : high `) are excluded from the equivalence contract - the
    schema lints toward the canonical unpadded form, and stricter-in-editor is
    the safe direction (accepted in the fn-138.1 host review and PR #280 r6;
    flowctl never rejects such configs at runtime)."""

    def test_schema_equals_parser_over_all_shapes(self) -> None:
        import contextlib
        import io

        schema = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        frag = schema["properties"]["review"]["properties"]["backend"]

        def schema_ok(v: str) -> bool:
            for alt in frag["anyOf"]:
                if "enum" in alt and v in alt["enum"]:
                    return True
                if alt.get("type") == "string" and "pattern" in alt and re.search(alt["pattern"], v):
                    return True
            return False

        cases = set()
        for b in sorted(flowctl.VALID_BACKENDS):
            cases.update({b, b + ":", b + "::"})
            for mdl in ("", "m1"):
                for eff in ("", "high", "none", "bogus"):
                    cases.add(f"{b}:{mdl}:{eff}")
                    if eff == "":
                        cases.add(f"{b}:{mdl}")
        for v in sorted(cases):
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    flowctl.BackendSpec.parse(v)
                runtime = True
            except Exception:
                runtime = False
            self.assertEqual(schema_ok(v), runtime, f"schema/parser disagree on {v!r}")


if __name__ == "__main__":
    unittest.main()
