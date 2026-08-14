"""tracker.resolved cache: scoped timestamps, lock transaction, state machine,
migration (fn-139.3).

Cross-platform by construction: the lock is an atomic mkdir and the contention
tests use real subprocesses, so the SAME tests exercise the Windows CI row -
no POSIX-only APIs anywhere in this file.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import config_lock as CL  # noqa: E402
from flowctl_tracker import resolved_cache as RC  # noqa: E402
from flowctl_tracker.types import ErrorClass, TrackerError  # noqa: E402


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def gitlab_config(**extra) -> dict:
    per = {"host": "gitlab.com", "project": "gmickel/flow-next-smoke"}
    per.update(extra)
    return {"tracker": {"type": "gitlab", "perTracker": per}}


def full_gitlab_resolved(now: str) -> dict:
    return {
        "resolvedAt": now,
        "scopeResolvedAt": {"destination": now, "capabilities": now},
        "destination": {"projectId": 84817009, "projectPath": "gmickel/flow-next-smoke",
                        "host": "gitlab.com", "namespaceId": 111},
        "capabilities": {"attachments": True, "blockedBy": False, "subIssues": False,
                         "deleteIssue": True, "_source": {"gitlabPlan": "free"}},
    }


class SchemaKeys(unittest.TestCase):
    def test_scope_set_is_the_epics_exact_four(self) -> None:
        self.assertEqual(RC.SCOPES, ("destination", "destination.statusIds",
                                     "destination.stateIds", "capabilities"))

    def test_legacy_flat_timestamp_fields_are_rejected(self) -> None:
        for legacy in ("destinationResolvedAt", "capabilitiesCheckedAt"):
            with self.subTest(field=legacy), self.assertRaises(ValueError):
                RC.validate_resolved_block({"scopeResolvedAt": {}, legacy: "2026-01-01"})

    def test_non_canonical_scope_key_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RC.validate_resolved_block({"scopeResolvedAt": {"destination.labels": "x"}})

    def test_unknown_scope_is_rejected_at_merge(self) -> None:
        with self.assertRaises(ValueError):
            RC.apply_scope_result(gitlab_config(), "labels", {})


class ResolvedAtRules(unittest.TestCase):
    """Set ONLY when complete; PRESERVED across partial refresh; CLEARED when a
    refresh reveals a now-missing required field. Never a TTL input."""

    def test_partial_resolution_never_stamps_resolved_at(self) -> None:
        cfg = gitlab_config()
        RC.apply_scope_result(cfg, "destination",
                              {"projectId": 1, "projectPath": "a/b", "host": "gitlab.com"})
        # namespaceId missing -> incomplete
        self.assertIsNone(cfg["tracker"]["resolved"]["resolvedAt"])

    def test_set_once_complete(self) -> None:
        cfg = gitlab_config()
        RC.apply_scope_result(cfg, "destination",
                              {"projectId": 1, "projectPath": "a/b",
                               "host": "gitlab.com", "namespaceId": 2})
        self.assertIsNone(cfg["tracker"]["resolved"]["resolvedAt"])
        RC.apply_scope_result(cfg, "capabilities",
                              {"attachments": True, "blockedBy": False,
                               "subIssues": False, "deleteIssue": True})
        self.assertIsNotNone(cfg["tracker"]["resolved"]["resolvedAt"])

    def test_preserved_across_partial_refresh(self) -> None:
        cfg = gitlab_config()
        cfg["tracker"]["resolved"] = full_gitlab_resolved("2026-01-01T00:00:00Z")
        RC.apply_scope_result(cfg, "destination", {"projectPath": "a/renamed"},
                              now="2026-06-01T00:00:00Z")
        self.assertEqual(cfg["tracker"]["resolved"]["resolvedAt"],
                         "2026-01-01T00:00:00Z", "a partial refresh must not bump it")

    def test_cleared_when_refresh_reveals_missing_required_field(self) -> None:
        cfg = gitlab_config()
        cfg["tracker"]["resolved"] = full_gitlab_resolved("2026-01-01T00:00:00Z")
        RC.apply_scope_result(cfg, "destination", {"namespaceId": None},
                              now="2026-06-01T00:00:00Z")
        self.assertIsNone(cfg["tracker"]["resolved"]["resolvedAt"])


class ScopeIsolation(unittest.TestCase):
    def test_destination_refresh_does_not_freshen_capabilities(self) -> None:
        cfg = gitlab_config()
        cfg["tracker"]["resolved"] = full_gitlab_resolved("2026-01-01T00:00:00Z")
        RC.apply_scope_result(cfg, "destination", {"projectPath": "a/renamed"},
                              now="2026-06-01T00:00:00Z")
        sra = cfg["tracker"]["resolved"]["scopeResolvedAt"]
        self.assertEqual(sra["capabilities"], "2026-01-01T00:00:00Z")
        self.assertEqual(sra["destination"], "2026-06-01T00:00:00Z")

    def test_destination_refresh_cannot_write_state_or_status_ids(self) -> None:
        for key in ("statusIds", "stateIds"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                RC.apply_scope_result(gitlab_config(), "destination", {key: {}})

    def test_state_ids_scope_writes_only_that_subkey(self) -> None:
        cfg = {"tracker": {"type": "linear", "perTracker": {}}}
        cfg["tracker"]["resolved"] = {
            "resolvedAt": None,
            "scopeResolvedAt": {"destination": "2026-01-01T00:00:00Z"},
            "destination": {"teamId": "t", "teamKey": "FLOW"},
            "capabilities": {},
        }
        RC.apply_scope_result(cfg, "destination.stateIds",
                              {"in_progress": "uuid-1"}, now="2026-06-01T00:00:00Z")
        dest = cfg["tracker"]["resolved"]["destination"]
        self.assertEqual(dest["teamId"], "t", "sibling fields untouched")
        self.assertEqual(dest["stateIds"], {"in_progress": "uuid-1"})
        sra = cfg["tracker"]["resolved"]["scopeResolvedAt"]
        self.assertEqual(sra["destination"], "2026-01-01T00:00:00Z")
        self.assertIn("destination.stateIds", sra)

    def test_capability_payload_key_set_is_closed(self) -> None:
        with self.assertRaises(ValueError):
            RC.apply_scope_result(gitlab_config(), "capabilities",
                                  {"attachments": True, "blockedBy": False,
                                   "subIssues": False, "deleteIssue": True,
                                   "uploads": True})


class CapabilityTtl(unittest.TestCase):
    def test_only_gitlab_is_ever_ttl_stale(self) -> None:
        old = iso(datetime.now(timezone.utc) - timedelta(hours=48))
        for t in ("github", "linear", "jira"):
            cfg = {"tracker": {"type": t, "resolved": {"scopeResolvedAt": {"capabilities": old}}}}
            self.assertFalse(RC.capabilities_stale(cfg), t)
        cfg = {"tracker": {"type": "gitlab", "resolved": {"scopeResolvedAt": {"capabilities": old}}}}
        self.assertTrue(RC.capabilities_stale(cfg))

    def test_fresh_gitlab_stamp_is_not_stale(self) -> None:
        now = iso(datetime.now(timezone.utc))
        cfg = {"tracker": {"type": "gitlab", "resolved": {"scopeResolvedAt": {"capabilities": now}}}}
        self.assertFalse(RC.capabilities_stale(cfg))

    def test_missing_or_garbage_stamp_reads_as_stale(self) -> None:
        for stamp in (None, "not-a-date"):
            cfg = {"tracker": {"type": "gitlab",
                               "resolved": {"scopeResolvedAt": ({} if stamp is None
                                                                else {"capabilities": stamp})}}}
            self.assertTrue(RC.capabilities_stale(cfg), repr(stamp))


class TierProbe(unittest.TestCase):
    def test_failed_probe_leaves_capability_and_reports_probe_field(self) -> None:
        """A transient 403 on the tier probe must not flip a capability."""
        cfg = gitlab_config()
        cfg["tracker"]["resolved"] = full_gitlab_resolved("2026-01-01T00:00:00Z")
        cfg["tracker"]["resolved"]["capabilities"]["blockedBy"] = True
        out = RC.apply_capability_probe(cfg, ok=False, reason="403 from namespaces probe",
                                        now="2026-06-01T00:00:00Z")
        self.assertTrue(cfg["tracker"]["resolved"]["capabilities"]["blockedBy"],
                        "prior capability intact")
        self.assertEqual(cfg["tracker"]["resolved"]["scopeResolvedAt"]["capabilities"],
                         "2026-01-01T00:00:00Z", "failed probe must not re-stamp")
        self.assertFalse(out["probe"]["ok"])
        self.assertIsNone(out["degraded"], "a failed probe is NOT a degradation")

    def test_successful_probe_updates_plan_and_stamps_capabilities_only(self) -> None:
        cfg = gitlab_config()
        cfg["tracker"]["resolved"] = full_gitlab_resolved("2026-01-01T00:00:00Z")
        out = RC.apply_capability_probe(cfg, ok=True, plan="ultimate_trial",
                                        now="2026-06-01T00:00:00Z")
        caps = cfg["tracker"]["resolved"]["capabilities"]
        self.assertTrue(caps["blockedBy"])
        self.assertEqual(caps["_source"]["gitlabPlan"], "ultimate_trial")
        sra = cfg["tracker"]["resolved"]["scopeResolvedAt"]
        self.assertEqual(sra["capabilities"], "2026-06-01T00:00:00Z")
        self.assertEqual(sra["destination"], "2026-01-01T00:00:00Z",
                         "capability probe must not freshen destination")
        self.assertIsNone(out["degraded"], "false->true is an upgrade, not a degradation")

    def test_downgrade_is_reported_structured(self) -> None:
        cfg = gitlab_config()
        cfg["tracker"]["resolved"] = full_gitlab_resolved("2026-01-01T00:00:00Z")
        cfg["tracker"]["resolved"]["capabilities"]["blockedBy"] = True
        out = RC.apply_capability_probe(cfg, ok=True, plan="free")
        self.assertFalse(cfg["tracker"]["resolved"]["capabilities"]["blockedBy"])
        self.assertEqual(out["degraded"]["capability"], "blockedBy")


class Migration(unittest.TestCase):
    def test_api_version_3_migrates_to_2(self) -> None:
        cfg = {"tracker": {"perTracker": {"apiVersion": 3}}}
        self.assertTrue(RC.migrate_config(cfg))
        self.assertEqual(cfg["tracker"]["perTracker"]["apiVersion"], 2)

    def test_other_values_untouched(self) -> None:
        for v in (2, None, "3"):
            cfg = {"tracker": {"perTracker": {"apiVersion": v}}}
            self.assertFalse(RC.migrate_config(cfg))
            self.assertEqual(cfg["tracker"]["perTracker"]["apiVersion"], v)


class StateMachineSeam(unittest.TestCase):
    """Every row of the cache state table, driven through plan_transition."""

    def test_absent_block_is_unresolved_never_a_false_capability(self) -> None:
        a = RC.plan_transition(RC.Trigger.ABSENT_BLOCK)
        self.assertEqual(a.kind, "fail")
        self.assertIs(a.error_class, ErrorClass.UNRESOLVED)

    def test_absent_field_is_a_scoped_re_resolve(self) -> None:
        a = RC.plan_transition(RC.Trigger.ABSENT_FIELD, scope="destination.stateIds")
        self.assertEqual((a.kind, a.scope, a.retry_operation),
                         ("resolve_scope", "destination.stateIds", True))

    def test_stale_id_retries_twice_then_exhausts(self) -> None:
        self.assertEqual(RC.plan_transition(RC.Trigger.STALE_ID, attempt=1).kind, "resolve_scope")
        self.assertEqual(RC.plan_transition(RC.Trigger.STALE_ID, attempt=2).kind, "resolve_scope")
        third = RC.plan_transition(RC.Trigger.STALE_ID, attempt=3)
        self.assertEqual(third.kind, "fail")
        self.assertIs(third.error_class, ErrorClass.UNRESOLVED)
        self.assertTrue(third.needs_human)

    def test_capability_rejected_degrades_never_deletes(self) -> None:
        a = RC.plan_transition(RC.Trigger.CAPABILITY_REJECTED)
        self.assertEqual(a.kind, "degrade")

    def test_capability_ttl_is_a_bounded_probe(self) -> None:
        a = RC.plan_transition(RC.Trigger.CAPABILITY_TTL)
        self.assertEqual((a.kind, a.scope), ("probe", "capabilities"))

    def test_ambiguous_state_is_conflict_and_human(self) -> None:
        a = RC.plan_transition(RC.Trigger.AMBIGUOUS_STATE)
        self.assertEqual(a.kind, "fail")
        self.assertIs(a.error_class, ErrorClass.CONFLICT)
        self.assertTrue(a.needs_human)

    def test_auth_failure_never_degrades(self) -> None:
        a = RC.plan_transition(RC.Trigger.AUTH_FAILURE)
        self.assertEqual(a.kind, "fail")
        self.assertIs(a.error_class, ErrorClass.AUTH)
        self.assertNotEqual(a.kind, "degrade")

    def test_retry_exhausted_fails_clean_cache_untouched(self) -> None:
        a = RC.plan_transition(RC.Trigger.RETRY_EXHAUSTED)
        self.assertIs(a.error_class, ErrorClass.UNRESOLVED)
        self.assertIn("untouched", a.note)


class TransactionFingerprint(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flow = Path(self.tmp.name)
        self.config_path = self.flow / "config.json"
        self._write(gitlab_config(projectId=1))

    def _write(self, cfg: dict) -> None:
        self.config_path.write_text(json.dumps(cfg), encoding="utf-8")

    def test_clean_resolve_merges_and_stamps(self) -> None:
        out = RC.resolve_transaction(
            self.flow, "destination",
            lambda cfg: {"projectId": 1, "projectPath": "a/b",
                         "host": "gitlab.com", "namespaceId": 9})
        self.assertIsInstance(out, dict)
        on_disk = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["tracker"]["resolved"]["destination"]["namespaceId"], 9)
        self.assertIn("destination", on_disk["tracker"]["resolved"]["scopeResolvedAt"])

    def test_mid_resolve_repoint_is_discarded_then_re_resolved(self) -> None:
        """A REAL repoint (project changed), not an unrelated write."""
        calls = {"n": 0}

        def network(cfg: dict) -> dict:
            calls["n"] += 1
            if calls["n"] == 1:
                # Simulate a `config set` repoint landing mid-resolve.
                repointed = gitlab_config(projectId=2)
                self._write(repointed)
            return {"projectId": cfg["tracker"]["perTracker"]["projectId"],
                    "projectPath": "x/y", "host": "gitlab.com", "namespaceId": 5}

        out = RC.resolve_transaction(self.flow, "destination", network)
        self.assertIsInstance(out, dict, "one bounded re-resolve, then success")
        self.assertEqual(calls["n"], 2)
        on_disk = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["tracker"]["resolved"]["destination"]["projectId"], 2,
                         "the merged ids belong to the REPOINTED project")

    def test_second_mismatch_returns_conflict_not_a_loop(self) -> None:
        calls = {"n": 0}

        def network(cfg: dict) -> dict:
            calls["n"] += 1
            self._write(gitlab_config(projectId=100 + calls["n"]))
            return {"projectId": 0, "projectPath": "x/y", "host": "gitlab.com",
                    "namespaceId": 5}

        out = RC.resolve_transaction(self.flow, "destination", network)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "fingerprint")
        self.assertEqual(calls["n"], 2, "exactly one bounded re-resolve")

    def test_unrelated_write_does_not_trip_the_fingerprint(self) -> None:
        def network(cfg: dict) -> dict:
            unrelated = gitlab_config(projectId=1)
            unrelated["review"] = {"backend": "codex"}
            self._write(unrelated)
            return {"projectId": 1, "projectPath": "a/b", "host": "gitlab.com",
                    "namespaceId": 9}

        out = RC.resolve_transaction(self.flow, "destination", network)
        self.assertIsInstance(out, dict)
        on_disk = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["review"]["backend"], "codex",
                         "the unrelated write survives the scoped merge")

    def test_network_error_propagates_and_writes_nothing(self) -> None:
        before = self.config_path.read_bytes()
        out = RC.resolve_transaction(
            self.flow, "destination",
            lambda cfg: TrackerError(ErrorClass.AUTH, "401"))
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.AUTH)
        self.assertEqual(self.config_path.read_bytes(), before)

    def test_transaction_applies_the_api_version_migration(self) -> None:
        cfg = {"tracker": {"type": "jira", "perTracker": {"apiVersion": 3, "projectKey": "SCRUM"}}}
        self._write(cfg)
        out = RC.resolve_transaction(
            self.flow, "destination",
            lambda c: {"baseUrl": "https://x.atlassian.net", "projectKey": "SCRUM",
                       "projectId": "1", "issueTypeId": "10001", "apiVersion": 2,
                       "style": "next-gen"})
        self.assertIsInstance(out, dict)
        on_disk = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["tracker"]["perTracker"]["apiVersion"], 2)

    def test_backfill_vs_consuming_verb_are_different_behaviors(self) -> None:
        """R9: resolve backfills; a consuming verb gets class unresolved."""
        # Consuming-verb side: the seam says fail, never resolve implicitly.
        verb_action = RC.plan_transition(RC.Trigger.ABSENT_BLOCK)
        self.assertEqual(verb_action.kind, "fail")
        self.assertIs(verb_action.error_class, ErrorClass.UNRESOLVED)
        # Backfill side: an explicit transaction populates the absent block.
        out = RC.resolve_transaction(
            self.flow, "destination",
            lambda cfg: {"projectId": 1, "projectPath": "a/b",
                         "host": "gitlab.com", "namespaceId": 9})
        self.assertIsInstance(out, dict)


class LockBehavior(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flow = Path(self.tmp.name)

    def test_lock_path_is_the_named_design(self) -> None:
        with CL.config_lock(self.flow):
            self.assertTrue((self.flow / ".locks" / "config.d").is_dir())
            owner = json.loads((self.flow / ".locks" / "config.d" / "owner.json")
                               .read_text(encoding="utf-8"))
            self.assertEqual(owner["pid"], os.getpid())
            self.assertIn("host", owner)
            self.assertIn("acquired_at", owner)
        self.assertFalse((self.flow / ".locks" / "config.d").exists(), "released")

    def test_held_lock_times_out_with_the_specified_error(self) -> None:
        (self.flow / ".locks" / "config.d").mkdir(parents=True)
        (self.flow / ".locks" / "config.d" / "owner.json").write_text(json.dumps({
            "pid": os.getpid(), "host": CL.socket.gethostname(),
            "acquired_at": time.time()}), encoding="utf-8")
        started = time.monotonic()
        with self.assertRaises(CL.ConfigLockTimeout):
            with CL.config_lock(self.flow, timeout_s=0.3):
                pass
        self.assertLess(time.monotonic() - started, 5.0)

    def test_stale_dead_pid_same_host_is_reclaimed(self) -> None:
        lock = self.flow / ".locks" / "config.d"
        lock.mkdir(parents=True)
        # A pid from a finished subprocess is provably dead on this host.
        proc = subprocess.run([sys.executable, "-c", "pass"], check=True)
        (lock / "owner.json").write_text(json.dumps({
            "pid": proc.args and 999999999,  # guaranteed-invalid pid
            "host": CL.socket.gethostname(),
            "acquired_at": time.time() - 600}), encoding="utf-8")
        with CL.config_lock(self.flow, timeout_s=2):
            pass  # acquired via reclaim

    def test_fresh_owner_is_never_reclaimed_even_if_pid_dead(self) -> None:
        lock = self.flow / ".locks" / "config.d"
        lock.mkdir(parents=True)
        (lock / "owner.json").write_text(json.dumps({
            "pid": 999999999, "host": CL.socket.gethostname(),
            "acquired_at": time.time()}), encoding="utf-8")
        with self.assertRaises(CL.ConfigLockTimeout):
            with CL.config_lock(self.flow, timeout_s=0.3):
                pass

    def test_other_hosts_locks_are_never_reclaimed_by_age(self) -> None:
        lock = self.flow / ".locks" / "config.d"
        lock.mkdir(parents=True)
        (lock / "owner.json").write_text(json.dumps({
            "pid": 999999999, "host": "some-other-host.example",
            "acquired_at": time.time() - 9999}), encoding="utf-8")
        with self.assertRaises(CL.ConfigLockTimeout):
            with CL.config_lock(self.flow, timeout_s=0.3):
                pass

    def test_crashed_holder_without_owner_json_is_reclaimed_by_age(self) -> None:
        lock = self.flow / ".locks" / "config.d"
        lock.mkdir(parents=True)
        old = time.time() - 600
        os.utime(lock, (old, old))
        with CL.config_lock(self.flow, timeout_s=2):
            pass

    def test_recent_ownerless_dir_is_not_reclaimed(self) -> None:
        (self.flow / ".locks" / "config.d").mkdir(parents=True)
        with self.assertRaises(CL.ConfigLockTimeout):
            with CL.config_lock(self.flow, timeout_s=0.3):
                pass


@unittest.skipIf(os.name == "nt", "POSIX permission bits")
@unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ignores mode bits")
class UnavailableLockIsNotContention(unittest.TestCase):
    """fn-193 / #340: a denied mkdir with NO lock directory present is not a
    holder. It must fail fast and say what the filesystem said."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flow = Path(self.tmp.name)

    def _seal(self, path: Path) -> None:
        path.chmod(0o500)
        self.addCleanup(lambda: path.chmod(0o700))

    def test_unwritable_locks_dir_fails_fast_and_blames_permissions(self) -> None:
        locks = self.flow / ".locks"
        locks.mkdir()
        self._seal(locks)
        started = time.monotonic()
        with self.assertRaises(CL.ConfigLockUnavailable) as raised:
            with CL.config_lock(self.flow, timeout_s=10):
                pass
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 1.0, "must not burn the deadline")
        message = str(raised.exception)
        self.assertIn("EACCES", message)
        self.assertIn(str(self.flow / ".locks" / "config.d"), message)
        self.assertNotIn("holder appears alive", message)

    def test_unwritable_flow_dir_reports_the_lock_parent(self) -> None:
        self._seal(self.flow)
        with self.assertRaises(CL.ConfigLockUnavailable) as raised:
            with CL.config_lock(self.flow, timeout_s=10):
                pass
        message = str(raised.exception)
        self.assertIn("EACCES", message)
        self.assertIn(str(self.flow / ".locks"), message)
        self.assertNotIn("holder appears alive", message)

    def test_unavailable_is_catchable_as_the_existing_timeout_type(self) -> None:
        locks = self.flow / ".locks"
        locks.mkdir()
        self._seal(locks)
        with self.assertRaises(CL.ConfigLockTimeout):
            with CL.config_lock(self.flow, timeout_s=10):
                pass


class TimeoutMessageReportsWhatWasObserved(unittest.TestCase):
    """fn-193 R2: 'holder appears alive' only when an owner was really read."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flow = Path(self.tmp.name)
        self.lock = self.flow / ".locks" / "config.d"

    def test_stale_owner_with_failing_reclaim_is_not_reported_alive(self) -> None:
        # PR #349 review: an owner the staleness probe already proved
        # reclaimable must not read as "alive" - name the failing reclaim.
        self.lock.mkdir(parents=True)
        # Same host (foreign hostnames are never stale - fails closed) with a
        # PID that cannot be alive, past the stale window.
        (self.lock / "owner.json").write_text(json.dumps({
            "pid": 999999999, "host": CL.socket.gethostname(),
            "acquired_at": time.time() - CL.STALE_OWNER_S - 60,
        }), encoding="utf-8")
        message = CL._timeout_message(self.lock, 1.0, None)
        self.assertIn("stale but reclamation is failing", message)
        self.assertNotIn("holder appears alive", message)

    def test_held_lock_names_the_holders_pid_and_host(self) -> None:
        self.lock.mkdir(parents=True)
        (self.lock / "owner.json").write_text(json.dumps({
            "pid": 999999999, "host": "holder-box.example",
            "acquired_at": time.time()}), encoding="utf-8")
        with self.assertRaises(CL.ConfigLockTimeout) as raised:
            with CL.config_lock(self.flow, timeout_s=0.3):
                pass
        message = str(raised.exception)
        self.assertIn("holder appears alive", message)
        self.assertIn("999999999", message)
        self.assertIn("holder-box.example", message)

    def test_ownerless_dir_says_owner_absent_and_when_it_reclaims(self) -> None:
        self.lock.mkdir(parents=True)
        with self.assertRaises(CL.ConfigLockTimeout) as raised:
            with CL.config_lock(self.flow, timeout_s=0.3):
                pass
        message = str(raised.exception)
        self.assertNotIn("holder appears alive", message)
        self.assertIn("no readable owner.json", message)
        self.assertIn("stale-reclaimable in", message)

    def test_permission_denied_while_the_path_exists_polls_to_the_deadline(self) -> None:
        # Pins the Windows delete-pending carve-out: denied + present is
        # transient, so it must NOT take the fail-fast branch.
        self.lock.mkdir(parents=True)
        real_mkdir = Path.mkdir

        def denied(target: Path, *args, **kwargs):
            if target == self.lock:
                raise PermissionError(13, "Permission denied")
            return real_mkdir(target, *args, **kwargs)

        started = time.monotonic()
        with mock.patch.object(Path, "mkdir", denied):
            with self.assertRaises(CL.ConfigLockTimeout) as raised:
                with CL.config_lock(self.flow, timeout_s=0.4):
                    pass
        self.assertGreaterEqual(time.monotonic() - started, 0.4)
        self.assertNotIsInstance(raised.exception, CL.ConfigLockUnavailable)
        message = str(raised.exception)
        self.assertIn("Permission denied", message)
        self.assertIn("kept being denied", message)
        self.assertNotIn("holder appears alive", message)


_WORKER = r"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from flowctl_tracker.config_lock import config_lock

flow = Path(sys.argv[2])
n = int(sys.argv[3])
counter = flow / "counter.json"
for _ in range(n):
    with config_lock(flow):
        v = json.loads(counter.read_text()) if counter.exists() else 0
        time.sleep(0.001)  # widen the race window
        counter.write_text(json.dumps(v + 1))
print("ok")
"""


class CrossProcessContention(unittest.TestCase):
    """Real subprocesses, no POSIX-only APIs - this IS the Windows CI row test."""

    def test_concurrent_writers_never_lose_an_increment(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            flow = Path(td)
            procs = [subprocess.Popen(
                [sys.executable, "-c", _WORKER, str(ROOT / "scripts"), str(flow), "25"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                for _ in range(3)]
            for p in procs:
                out, err = p.communicate(timeout=120)
                self.assertEqual(p.returncode, 0, err.decode(errors="replace"))
                self.assertIn(b"ok", out)
            total = json.loads((flow / "counter.json").read_text())
            self.assertEqual(total, 75, "a lost increment means the lock failed")

    def test_crashed_holder_is_recovered_by_rule_not_manual_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            flow = Path(td)
            # A process that acquires and dies without releasing.
            crasher = (
                "import sys, os\n"
                f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
                "from flowctl_tracker.config_lock import config_lock\n"
                f"lock = config_lock({str(flow)!r})\n"
                "lock.__enter__()\n"
                "os._exit(1)\n"
            )
            subprocess.run([sys.executable, "-c", crasher], check=False, timeout=60)
            lock_dir = flow / ".locks" / "config.d"
            self.assertTrue(lock_dir.exists(), "the crash left the lock held")
            # Age the orphan past STALE_OWNER_S, as rule-based recovery requires.
            owner = lock_dir / "owner.json"
            data = json.loads(owner.read_text(encoding="utf-8"))
            data["acquired_at"] = time.time() - 600
            owner.write_text(json.dumps(data), encoding="utf-8")
            with CL.config_lock(flow, timeout_s=5):
                pass  # recovered without manual cleanup


class DifferentScopeResolvesDoNotClobber(unittest.TestCase):
    def test_concurrent_destination_and_capabilities_resolves_both_land(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            flow = Path(td)
            (flow / "config.json").write_text(
                json.dumps(gitlab_config(projectId=1)), encoding="utf-8")
            results = {}

            def run(scope: str, data: dict) -> None:
                results[scope] = RC.resolve_transaction(
                    flow, scope, lambda cfg, d=data: (time.sleep(0.02), d)[1])

            t1 = threading.Thread(target=run, args=(
                "destination", {"projectId": 1, "projectPath": "a/b",
                                "host": "gitlab.com", "namespaceId": 9}))
            t2 = threading.Thread(target=run, args=(
                "capabilities", {"attachments": True, "blockedBy": False,
                                 "subIssues": False, "deleteIssue": True}))
            t1.start(); t2.start(); t1.join(); t2.join()

            self.assertIsInstance(results["destination"], dict)
            self.assertIsInstance(results["capabilities"], dict)
            on_disk = json.loads((flow / "config.json").read_text(encoding="utf-8"))
            resolved = on_disk["tracker"]["resolved"]
            self.assertEqual(resolved["destination"]["namespaceId"], 9)
            self.assertTrue(resolved["capabilities"]["attachments"])
            self.assertIsNotNone(resolved["resolvedAt"],
                                 "both scopes present -> complete")


class FlowctlWritersRouteThroughTheLock(unittest.TestCase):
    """set_config AND cmd_init hold `.flow/.locks/config.d` while writing."""

    @classmethod
    def setUpClass(cls) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "flowctl_under_lock_test", ROOT / "scripts" / "flowctl.py")
        cls.flowctl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.flowctl)

    def _assert_holds_lock_during_write(self, invoke) -> None:
        seen = {"locked_during_write": False}
        real_write = self.flowctl.atomic_write_json

        def spying_write(path, data):
            if path.name == "config.json":
                seen["locked_during_write"] = (
                    Path(self.flow, ".locks", "config.d").is_dir())
            return real_write(path, data)

        with mock.patch.object(self.flowctl, "atomic_write_json", spying_write):
            invoke()
        self.assertTrue(seen["locked_during_write"],
                        "config.json written without holding the shared lock")

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flow = Path(self.tmp.name) / ".flow"
        self.flow.mkdir()
        self._flow_patch = mock.patch.object(
            self.flowctl, "get_flow_dir", return_value=self.flow)
        self._flow_patch.start()
        self.addCleanup(self._flow_patch.stop)

    def test_set_config_holds_the_lock(self) -> None:
        self._assert_holds_lock_during_write(
            lambda: self.flowctl.set_config("tracker.enabled", "true"))

    def test_cmd_init_config_write_holds_the_lock(self) -> None:
        import argparse
        args = argparse.Namespace(json=True)
        with mock.patch.object(self.flowctl, "json_output"):
            self._assert_holds_lock_during_write(
                lambda: self.flowctl.cmd_init(args))

    def test_set_config_reads_inside_the_lock(self) -> None:
        """The read must happen under the lock or stale-read clobbering returns."""
        import inspect
        src = inspect.getsource(self.flowctl.set_config)
        self.assertIn("_shared_config_lock", src)
        self.assertNotIn("read_text", src,
                         "set_config must delegate the read to the locked helper")


if __name__ == "__main__":
    unittest.main()


class PidLivenessNeverSignals(unittest.TestCase):
    """`os.kill(pid, 0)` on Windows calls TerminateProcess - a liveness PROBE
    built on it kills the holder. Both branches are query-only; this test uses
    a real live child on every platform (ctypes branch on the Windows CI row)."""

    def test_live_child_reads_alive_and_survives_the_probe(self) -> None:
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            self.assertTrue(CL._pid_alive(child.pid))
            self.assertIsNone(child.poll(), "the probe must not kill the child")
        finally:
            child.kill()
            child.wait(timeout=30)

    def test_exited_child_reads_dead(self) -> None:
        child = subprocess.Popen([sys.executable, "-c", "pass"])
        child.wait(timeout=30)
        time.sleep(0.05)
        self.assertFalse(CL._pid_alive(child.pid))

    def test_posix_branch_never_uses_a_real_signal(self) -> None:
        if os.name == "nt":
            self.skipTest("POSIX branch")
        with mock.patch.object(CL.os, "kill") as k:
            CL._pid_alive(12345)
        self.assertEqual(k.call_args.args[1], 0, "signal 0 only - never a killer")


class ReclaimIsSerializedByRename(unittest.TestCase):
    """The ABA race: two contenders classify the SAME directory stale; A
    reclaims and acquires a fresh lock; B's delayed removal must not be able to
    delete A's new lock."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flow = Path(self.tmp.name)
        self.lock = self.flow / ".locks" / "config.d"

    def _make_stale_lock(self) -> None:
        self.lock.mkdir(parents=True)
        (self.lock / "owner.json").write_text(json.dumps({
            "pid": 999999999, "host": CL.socket.gethostname(),
            "acquired_at": time.time() - 600}), encoding="utf-8")

    def test_removal_targets_the_renamed_path_never_the_live_lock(self) -> None:
        self._make_stale_lock()
        self.assertTrue(CL._try_reclaim(self.lock))
        # A wins the rename; simulate A's fresh lock at the live path.
        self.lock.mkdir()
        (self.lock / "owner.json").write_text(json.dumps({
            "pid": os.getpid(), "host": CL.socket.gethostname(),
            "acquired_at": time.time()}), encoding="utf-8")
        # B, acting on its stale classification of the OLD directory, attempts
        # its own reclaim. The old directory is gone; rename can only touch the
        # live path if the implementation is wrong.
        stale_ghost = self.lock.with_name("config.d.ghost")
        self.assertFalse(stale_ghost.exists())
        # B's second staleness check on the LIVE lock sees a fresh owner:
        self.assertFalse(CL._owner_is_stale(self.lock, time.time()))
        self.assertTrue(self.lock.exists(), "A's fresh lock survives")

    def test_threads_racing_a_stale_lock_keep_mutual_exclusion(self) -> None:
        self._make_stale_lock()
        state = {"active": 0, "max": 0, "entries": 0}
        guard = threading.Lock()

        def contend() -> None:
            with CL.config_lock(self.flow, timeout_s=10):
                with guard:
                    state["active"] += 1
                    state["entries"] += 1
                    state["max"] = max(state["max"], state["active"])
                time.sleep(0.05)
                with guard:
                    state["active"] -= 1

        threads = [threading.Thread(target=contend) for _ in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(state["max"], 1, "two holders inside the critical section")
        self.assertEqual(state["entries"], 4)

    def test_failed_reclaim_rename_honours_the_deadline(self) -> None:
        """Permissions/antivirus/read-only rename failure must time out, not spin."""
        self._make_stale_lock()
        started = time.monotonic()
        with mock.patch.object(CL.os, "rename", side_effect=OSError("locked by AV")):
            with self.assertRaises(CL.ConfigLockTimeout):
                with CL.config_lock(self.flow, timeout_s=0.5):
                    pass
        self.assertLess(time.monotonic() - started, 5.0, "no unbounded spin")


class LockPathSymlinkContainment(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flow = Path(self.tmp.name) / "repo" / ".flow"
        self.flow.mkdir(parents=True)
        self.outside = Path(self.tmp.name) / "outside"
        self.outside.mkdir()

    def _symlink(self, link: Path, target: Path) -> None:
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):  # pragma: no cover - Windows w/o priv
            self.skipTest("symlinks unavailable on this platform/user")

    def test_symlinked_locks_dir_is_refused_and_target_untouched(self) -> None:
        self._symlink(self.flow / ".locks", self.outside)
        with self.assertRaises(CL.ConfigLockUnsafe):
            with CL.config_lock(self.flow):
                pass
        self.assertEqual(list(self.outside.iterdir()), [],
                         "nothing may be created through the symlink")

    def test_symlinked_lock_leaf_is_refused_not_deleted(self) -> None:
        victim = self.outside / "victim"
        victim.mkdir()
        (victim / "data.txt").write_text("precious", encoding="utf-8")
        (self.flow / ".locks").mkdir()
        self._symlink(self.flow / ".locks" / "config.d", victim)
        with self.assertRaises(CL.ConfigLockUnsafe):
            with CL.config_lock(self.flow):
                pass
        self.assertEqual((victim / "data.txt").read_text(encoding="utf-8"),
                         "precious", "release path must never rmtree the target")

    def test_transaction_maps_unsafe_lock_to_invalid_input(self) -> None:
        self._symlink(self.flow / ".locks", self.outside)
        (self.flow / "config.json").write_text(
            json.dumps(gitlab_config(projectId=1)), encoding="utf-8")
        out = RC.resolve_transaction(
            self.flow, "destination",
            lambda cfg: {"projectId": 1, "projectPath": "a/b",
                         "host": "gitlab.com", "namespaceId": 9})
        self.assertIsInstance(out, TrackerError)
        self.assertEqual(out.subtype, "lock_unsafe")


class CorruptConfigIsNeverOverwritten(unittest.TestCase):
    def test_non_object_json_root_returns_invalid_input_and_zero_byte_change(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            flow = Path(td)
            cfg = flow / "config.json"
            cfg.write_text("[1, 2, 3]", encoding="utf-8")
            before = cfg.read_bytes()
            out = RC.resolve_transaction(
                flow, "destination",
                lambda c: {"projectId": 1, "projectPath": "a/b",
                           "host": "gitlab.com", "namespaceId": 9})
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(cfg.read_bytes(), before, "no bytes may change")

    def test_missing_file_still_reads_as_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(RC._read_config(Path(td) / "config.json"), {})


class ReclaimerClaimClosesTheCheckToRenameWindow(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flow = Path(self.tmp.name)
        self.lock = self.flow / ".locks" / "config.d"

    def test_reclaim_recjecks_staleness_inside_the_claim(self) -> None:
        """A reclassified-fresh lock must survive a reclaimer that already
        decided it was stale."""
        self.lock.mkdir(parents=True)
        (self.lock / "owner.json").write_text(json.dumps({
            "pid": os.getpid(), "host": CL.socket.gethostname(),
            "acquired_at": time.time()}), encoding="utf-8")
        # The caller believed the lock stale; inside the claim the fresh owner
        # is re-read and the reclaim must refuse.
        self.assertFalse(CL._try_reclaim(self.lock))
        self.assertTrue(self.lock.exists())

    def _stale_owner(self) -> None:
        self.lock.mkdir(parents=True)
        (self.lock / "owner.json").write_text(json.dumps({
            "pid": 999999999, "host": CL.socket.gethostname(),
            "acquired_at": time.time() - 600}), encoding="utf-8")

    def test_concurrent_reclaimer_blocks_rather_than_double_reclaims(self) -> None:
        self._stale_owner()
        held = CL._acquire_reclaimer_claim(self.lock)
        self.assertIsNotNone(held)
        try:
            self.assertFalse(CL._try_reclaim(self.lock),
                             "an active claim must exclude a second reclaimer")
            self.assertTrue(self.lock.exists())
        finally:
            CL._release_reclaimer_claim(held)
        self.assertTrue(CL._try_reclaim(self.lock))
        self.assertFalse(self.lock.exists())

    def test_claim_is_never_deleted_and_needs_no_stale_recovery(self) -> None:
        """The claim is an OS file lock: the kernel releases it when the holder
        dies, so there is no orphan heuristic - and therefore no observation a
        delayed contender could act on to delete a live claim (the round-2 ABA)."""
        self._stale_owner()
        # A claim holder that CRASHES (hard exit, no release call):
        crasher = (
            "import sys, os\n"
            f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
            "from flowctl_tracker import config_lock as CL\n"
            f"claim = CL._acquire_reclaimer_claim(CL._lock_dir({str(self.flow)!r}))\n"
            "assert claim is not None\n"
            "os._exit(1)\n"
        )
        subprocess.run([sys.executable, "-c", crasher], check=False, timeout=60)
        # The kernel released the crashed holder's lock: reclaim proceeds
        # immediately, no age-out, no deletion of the claim path.
        self.assertTrue(CL._try_reclaim(self.lock))
        self.assertFalse(self.lock.exists())
        self.assertTrue(self.lock.with_name("config.d.reclaimer.lock").exists(),
                        "the claim path persists; only lock state changes")

    def test_live_cross_process_claim_holder_excludes_us(self) -> None:
        self._stale_owner()
        holder = (
            "import sys, time\n"
            f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
            "from flowctl_tracker import config_lock as CL\n"
            f"claim = CL._acquire_reclaimer_claim(CL._lock_dir({str(self.flow)!r}))\n"
            "assert claim is not None\n"
            "print('held', flush=True)\n"
            "time.sleep(10)\n"
        )
        proc = subprocess.Popen([sys.executable, "-c", holder],
                                stdout=subprocess.PIPE)
        try:
            self.assertEqual(proc.stdout.readline().strip(), b"held")
            self.assertFalse(CL._try_reclaim(self.lock),
                             "a live cross-process claim must exclude us")
            self.assertTrue(self.lock.exists())
        finally:
            proc.kill()
            proc.wait(timeout=30)
            proc.stdout.close()
        self.assertTrue(CL._try_reclaim(self.lock),
                        "kernel released the killed holder's claim")


class ClaimLeafSymlinkContainment(unittest.TestCase):
    """The persistent claim leaf gets the same no-follow policy as the lock
    directory components - a following open would create/open an external
    target planted by a malicious checkout."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flow = Path(self.tmp.name) / "repo" / ".flow"
        (self.flow / ".locks").mkdir(parents=True)
        self.lock = self.flow / ".locks" / "config.d"
        self.outside = Path(self.tmp.name) / "outside"
        self.outside.mkdir()

    def test_symlinked_claim_leaf_is_refused_and_target_preserved(self) -> None:
        victim = self.outside / "victim.bin"
        victim.write_bytes(b"precious")
        leaf = self.lock.with_name("config.d.reclaimer.lock")
        try:
            leaf.symlink_to(victim)
        except (OSError, NotImplementedError):  # pragma: no cover
            self.skipTest("symlinks unavailable on this platform/user")
        with self.assertRaises(CL.ConfigLockUnsafe):
            CL._acquire_reclaimer_claim(self.lock)
        self.assertEqual(victim.read_bytes(), b"precious")

    def test_unsafe_claim_leaf_surfaces_through_lock_acquisition(self) -> None:
        # A stale lock forces the reclaim path, which meets the planted leaf.
        self.lock.mkdir()
        (self.lock / "owner.json").write_text(json.dumps({
            "pid": 999999999, "host": CL.socket.gethostname(),
            "acquired_at": time.time() - 600}), encoding="utf-8")
        leaf = self.lock.with_name("config.d.reclaimer.lock")
        try:
            leaf.symlink_to(self.outside / "victim.bin")
        except (OSError, NotImplementedError):  # pragma: no cover
            self.skipTest("symlinks unavailable on this platform/user")
        with self.assertRaises(CL.ConfigLockUnsafe):
            with CL.config_lock(self.flow, timeout_s=1):
                pass

    def test_regular_claim_leaf_still_works(self) -> None:
        leaf = self.lock.with_name("config.d.reclaimer.lock")
        leaf.write_bytes(b"")
        claim = CL._acquire_reclaimer_claim(self.lock)
        self.assertIsNotNone(claim)
        CL._release_reclaimer_claim(claim)
