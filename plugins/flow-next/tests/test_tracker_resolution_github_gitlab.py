"""GitHub + GitLab resolution and the GitLab tier probe (fn-139.4).

The fake transport is the injected executor seam from task .2 - every test
drives the real resolver code with recorded response shapes, no live API.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import resolved_cache as RC  # noqa: E402
from flowctl_tracker.providers import github as GH  # noqa: E402
from flowctl_tracker.providers import gitlab as GL  # noqa: E402
from flowctl_tracker.providers import resolver_for  # noqa: E402
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402


def ok(body: dict) -> Response:
    return Response(200, {}, json.dumps(body).encode(), 0.01)


def fake_execute(responses: dict):
    """Route by op; record every request for argv assertions."""
    calls = []

    def execute(request):
        calls.append(request)
        out = responses[request.op]
        return out(request) if callable(out) else out

    execute.calls = calls
    return execute


def gitlab_cfg(**resolved) -> dict:
    cfg = {"tracker": {"type": "gitlab",
                       "perTracker": {"project": "gmickel/flow-next-smoke",
                                      "host": None}}}
    if resolved:
        cfg["tracker"]["resolved"] = resolved
    return cfg


class Dispatch(unittest.TestCase):
    def test_shipped_providers_resolve(self) -> None:
        self.assertIs(resolver_for("github"), GH)
        self.assertIs(resolver_for("gitlab"), GL)

    def test_unknown_provider_raises_rather_than_half_resolving(self) -> None:
        for p in ("bogus", "gitea", ""):
            with self.subTest(provider=p), self.assertRaises(KeyError):
                resolver_for(p)


class GitHubDestination(unittest.TestCase):
    def test_resolves_owner_and_repo_from_gh(self) -> None:
        ex = fake_execute({"resolve-destination": ok(
            {"name": "airtest", "owner": {"login": "gmickel"}})})
        out = GH.resolve_destination({}, ex)
        self.assertEqual(out, {"owner": "gmickel", "repo": "airtest"})
        argv = ex.calls[0].url_or_argv
        self.assertEqual(argv[:3], ["gh", "repo", "view"])
        self.assertTrue(ex.calls[0].idempotent)

    def test_transport_error_propagates(self) -> None:
        ex = fake_execute({"resolve-destination": TrackerError(
            ErrorClass.AUTH, "bad token")})
        out = GH.resolve_destination({}, ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.AUTH)

    def test_missing_fields_are_unresolved_not_a_crash(self) -> None:
        ex = fake_execute({"resolve-destination": ok({"name": None, "owner": {}})})
        out = GH.resolve_destination({}, ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)

    def test_malformed_body_is_transport(self) -> None:
        ex = fake_execute({"resolve-destination": Response(200, {}, b"not json", 0.01)})
        out = GH.resolve_destination({}, ex)
        self.assertIsInstance(out, TrackerError)
        self.assertEqual(out.subtype, "malformed_body")


class GitHubCapabilities(unittest.TestCase):
    def test_matches_the_truth_table_exactly(self) -> None:
        self.assertEqual(GH.resolve_capabilities({}, None), {
            "attachments": False, "blockedBy": False,
            "subIssues": True, "deleteIssue": False})

    def test_is_static_and_never_touches_the_network(self) -> None:
        """`execute=None` would explode on any call - passing it IS the test."""
        GH.resolve_capabilities({}, None)

    def test_never_ttl_stale(self) -> None:
        cfg = {"tracker": {"type": "github", "resolved": {
            "scopeResolvedAt": {"capabilities": "2020-01-01T00:00:00Z"}}}}
        self.assertFalse(RC.capabilities_stale(cfg))


class GitLabDestination(unittest.TestCase):
    PROJECT = {"id": 84817009, "path_with_namespace": "gmickel/flow-next-smoke",
               "web_url": "https://gitlab.com/gmickel/flow-next-smoke",
               "namespace": {"id": 111, "kind": "user", "full_path": "gmickel"}}

    def test_resolves_every_architecture_table_field(self) -> None:
        ex = fake_execute({"resolve-destination": ok(self.PROJECT)})
        out = GL.resolve_destination(gitlab_cfg(), ex)
        self.assertEqual(out, {"projectId": 84817009,
                               "projectPath": "gmickel/flow-next-smoke",
                               "host": "gitlab.com", "namespaceId": 111})

    def test_project_path_is_url_encoded(self) -> None:
        ex = fake_execute({"resolve-destination": ok(self.PROJECT)})
        GL.resolve_destination(gitlab_cfg(), ex)
        endpoint = ex.calls[0].url_or_argv[2]
        self.assertEqual(endpoint, "projects/gmickel%2Fflow-next-smoke")

    def test_self_managed_host_rides_the_hostname_flag(self) -> None:
        cfg = gitlab_cfg()
        cfg["tracker"]["perTracker"]["host"] = "gitlab.example.com"
        ex = fake_execute({"resolve-destination": ok(self.PROJECT)})
        out = GL.resolve_destination(cfg, ex)
        self.assertIn("--hostname", ex.calls[0].url_or_argv)
        self.assertEqual(out["host"], "gitlab.example.com")

    def test_missing_project_config_is_unresolved(self) -> None:
        out = GL.resolve_destination({"tracker": {"perTracker": {}}},
                                     fake_execute({}))
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)

    def test_non_numeric_ids_are_unresolved(self) -> None:
        ex = fake_execute({"resolve-destination": ok(
            {"id": "84817009", "namespace": {"id": None}})})
        out = GL.resolve_destination(gitlab_cfg(), ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)


class GitLabTierProbe(unittest.TestCase):
    def _resolved_dest(self) -> dict:
        return {"destination": {"projectId": 84817009,
                                "projectPath": "gmickel/flow-next-smoke",
                                "host": "gitlab.com", "namespaceId": 111}}

    def test_reprobe_is_exactly_one_request_via_pinned_namespace_id(self) -> None:
        ex = fake_execute({"probe-plan": ok({"id": 111, "plan": "free"})})
        ok_, plan, reason = GL.probe_plan(gitlab_cfg(**self._resolved_dest()), ex)
        self.assertTrue(ok_)
        self.assertEqual(plan, "free")
        self.assertEqual(len(ex.calls), 1, "one request - namespaceId is pinned")
        self.assertEqual(ex.calls[0].url_or_argv[2], "namespaces/111")

    def test_group_trial_grants_blocked_by(self) -> None:
        """Ultimate group -> blockedBy true (verified live on dociq1)."""
        ex = fake_execute({"probe-plan": ok({"id": 222, "plan": "ultimate_trial"})})
        caps = GL.resolve_capabilities(gitlab_cfg(), ex, namespace_id=222)
        self.assertTrue(caps["blockedBy"])
        self.assertEqual(caps["_source"]["gitlabPlan"], "ultimate_trial")

    def test_personal_namespace_stays_free_during_a_group_trial(self) -> None:
        """The OTHER direction (verified live on the personal namespace): the
        same user's group being on trial changes nothing for a personal project."""
        ex = fake_execute({"probe-plan": ok({"id": 111, "plan": "free"})})
        caps = GL.resolve_capabilities(gitlab_cfg(), ex, namespace_id=111)
        self.assertFalse(caps["blockedBy"])
        self.assertEqual(caps["_source"]["gitlabPlan"], "free")

    def test_truth_table_static_rows_match(self) -> None:
        ex = fake_execute({"probe-plan": ok({"id": 111, "plan": "free"})})
        caps = GL.resolve_capabilities(gitlab_cfg(), ex, namespace_id=111)
        self.assertEqual({k: caps[k] for k in ("attachments", "subIssues", "deleteIssue")},
                         {"attachments": True, "subIssues": False, "deleteIssue": True})

    def test_fresh_capability_resolution_fails_rather_than_inventing_false(self) -> None:
        """No prior value exists at first resolve - a failed probe must be a
        failed resolve, never a silent blockedBy:false."""
        ex = fake_execute({"probe-plan": TrackerError(ErrorClass.AUTH, "403")})
        out = GL.resolve_capabilities(gitlab_cfg(), ex, namespace_id=111)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)

    def test_no_pinned_namespace_is_a_clean_failure(self) -> None:
        ok_, plan, reason = GL.probe_plan(gitlab_cfg(), fake_execute({}))
        self.assertFalse(ok_)
        self.assertIn("namespaceId", reason)

    def test_failed_ttl_reprobe_reports_probe_never_degraded(self) -> None:
        cfg = gitlab_cfg(**self._resolved_dest())
        cfg["tracker"]["resolved"]["capabilities"] = {
            "attachments": True, "blockedBy": True, "subIssues": False,
            "deleteIssue": True, "_source": {"gitlabPlan": "ultimate"}}
        cfg["tracker"]["resolved"]["scopeResolvedAt"] = {
            "capabilities": "2026-01-01T00:00:00Z"}
        ex = fake_execute({"probe-plan": TrackerError(ErrorClass.AUTH, "transient 403")})
        out = GL.ttl_reprobe(cfg, ex, now="2026-06-01T00:00:00Z")
        self.assertFalse(out["probe"]["ok"])
        self.assertIn("403", out["probe"]["reason"])
        self.assertIsNone(out["degraded"], "a failed probe is NEVER a degradation")
        caps = cfg["tracker"]["resolved"]["capabilities"]
        self.assertTrue(caps["blockedBy"], "prior capability intact")
        self.assertEqual(cfg["tracker"]["resolved"]["scopeResolvedAt"]["capabilities"],
                         "2026-01-01T00:00:00Z", "no re-stamp on failure")

    def test_successful_reprobe_downgrade_is_structured(self) -> None:
        cfg = gitlab_cfg(**self._resolved_dest())
        cfg["tracker"]["resolved"]["capabilities"] = {
            "attachments": True, "blockedBy": True, "subIssues": False,
            "deleteIssue": True, "_source": {"gitlabPlan": "ultimate_trial"}}
        ex = fake_execute({"probe-plan": ok({"id": 111, "plan": "free"})})
        out = GL.ttl_reprobe(cfg, ex)
        self.assertTrue(out["probe"]["ok"])
        self.assertEqual(out["degraded"],
                         {"capability": "blockedBy", "from": True, "to": False,
                          "reason": "gitlab plan is 'free'"})


class ScopedResolutionThroughTheTransaction(unittest.TestCase):
    """`--scope destination` / `--scope capabilities` semantics for both
    providers: the resolver output rides resolve_transaction and stamps only
    its own scope."""

    def _run(self, cfg: dict, scope: str, network) -> tuple:
        with tempfile.TemporaryDirectory() as td:
            flow = Path(td)
            (flow / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
            out = RC.resolve_transaction(flow, scope, network)
            on_disk = json.loads((flow / "config.json").read_text(encoding="utf-8"))
        return out, on_disk

    def test_github_destination_scope(self) -> None:
        ex = fake_execute({"resolve-destination": ok(
            {"name": "airtest", "owner": {"login": "gmickel"}})})
        cfg = {"tracker": {"type": "github", "perTracker": {}}}
        out, on_disk = self._run(cfg, "destination",
                                 lambda c: GH.resolve_destination(c, ex))
        self.assertIsInstance(out, dict)
        resolved = on_disk["tracker"]["resolved"]
        self.assertEqual(resolved["destination"], {"owner": "gmickel", "repo": "airtest"})
        self.assertIn("destination", resolved["scopeResolvedAt"])
        self.assertNotIn("capabilities", resolved["scopeResolvedAt"])
        self.assertIsNone(resolved["resolvedAt"], "capabilities still absent")

    def test_github_capabilities_scope_completes_the_block(self) -> None:
        cfg = {"tracker": {"type": "github", "perTracker": {}, "resolved": {
            "resolvedAt": None,
            "scopeResolvedAt": {"destination": "2026-01-01T00:00:00Z"},
            "destination": {"owner": "gmickel", "repo": "airtest"},
        }}}
        out, on_disk = self._run(cfg, "capabilities",
                                 lambda c: GH.resolve_capabilities(c, None))
        self.assertIsInstance(out, dict)
        resolved = on_disk["tracker"]["resolved"]
        self.assertEqual(resolved["capabilities"], GH.CAPABILITIES)
        self.assertEqual(resolved["scopeResolvedAt"]["destination"],
                         "2026-01-01T00:00:00Z", "destination not falsely freshened")
        self.assertIsNotNone(resolved["resolvedAt"], "both scopes now present")

    def test_gitlab_destination_scope(self) -> None:
        ex = fake_execute({"resolve-destination": ok(GitLabDestination.PROJECT)})
        out, on_disk = self._run(gitlab_cfg(), "destination",
                                 lambda c: GL.resolve_destination(c, ex))
        self.assertIsInstance(out, dict)
        dest = on_disk["tracker"]["resolved"]["destination"]
        self.assertEqual(dest["projectId"], 84817009)
        self.assertEqual(dest["namespaceId"], 111)

    def test_gitlab_capabilities_scope(self) -> None:
        cfg = gitlab_cfg()
        cfg["tracker"]["resolved"] = {
            "resolvedAt": None, "scopeResolvedAt": {"destination": "2026-01-01T00:00:00Z"},
            "destination": {"projectId": 84817009,
                            "projectPath": "gmickel/flow-next-smoke",
                            "host": "gitlab.com", "namespaceId": 111}}
        ex = fake_execute({"probe-plan": ok({"id": 111, "plan": "free"})})
        out, on_disk = self._run(cfg, "capabilities",
                                 lambda c: GL.resolve_capabilities(c, ex))
        self.assertIsInstance(out, dict)
        resolved = on_disk["tracker"]["resolved"]
        self.assertFalse(resolved["capabilities"]["blockedBy"])
        self.assertEqual(resolved["capabilities"]["_source"]["gitlabPlan"], "free")
        self.assertIsNotNone(resolved["resolvedAt"])

    def test_failed_gitlab_capability_resolve_writes_nothing(self) -> None:
        cfg = gitlab_cfg()
        ex = fake_execute({"probe-plan": TrackerError(ErrorClass.AUTH, "403")})
        out, on_disk = self._run(cfg, "capabilities",
                                 lambda c: GL.resolve_capabilities(c, ex))
        self.assertIsInstance(out, TrackerError)
        self.assertNotIn("resolved", on_disk["tracker"])


if __name__ == "__main__":
    unittest.main()


class GitLabHostDerivation(unittest.TestCase):
    """With perTracker.host unset, glab may have answered from a self-managed
    host resolved off the git remote - the persisted host must come from the
    RESPONSE, never from a gitlab.com default."""

    def test_host_unset_derives_from_web_url(self) -> None:
        project = dict(GitLabDestination.PROJECT)
        project["web_url"] = "https://gitlab.example.com/gmickel/flow-next-smoke"
        ex = fake_execute({"resolve-destination": ok(project)})
        out = GL.resolve_destination(gitlab_cfg(), ex)
        self.assertEqual(out["host"], "gitlab.example.com")

    def test_host_unset_and_no_web_url_is_unresolved_not_gitlab_com(self) -> None:
        project = {k: v for k, v in GitLabDestination.PROJECT.items()
                   if k != "web_url"}
        ex = fake_execute({"resolve-destination": ok(project)})
        out = GL.resolve_destination(gitlab_cfg(), ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)
        self.assertIn("host", out.message)

    def test_explicit_host_wins_over_web_url(self) -> None:
        cfg = gitlab_cfg()
        cfg["tracker"]["perTracker"]["host"] = "gitlab.example.com"
        ex = fake_execute({"resolve-destination": ok(GitLabDestination.PROJECT)})
        out = GL.resolve_destination(cfg, ex)
        self.assertEqual(out["host"], "gitlab.example.com")


class GitLabSubgroupBillingNamespace(unittest.TestCase):
    def _subgroup_project(self) -> dict:
        return {"id": 5, "path_with_namespace": "acme/platform/api",
                "web_url": "https://gitlab.com/acme/platform/api",
                "namespace": {"id": 333, "kind": "group", "full_path": "acme/platform"}}

    def test_subgroup_pins_the_root_billing_namespace(self) -> None:
        ex = fake_execute({
            "resolve-destination": ok(self._subgroup_project()),
            "resolve-billing-namespace": ok({"id": 300, "full_path": "acme",
                                             "plan": "premium"}),
        })
        out = GL.resolve_destination(gitlab_cfg(), ex)
        self.assertEqual(out["namespaceId"], 300, "root group, not the subgroup")
        self.assertEqual(ex.calls[1].url_or_argv[2], "namespaces/acme")

    def test_top_level_namespace_needs_no_second_lookup(self) -> None:
        ex = fake_execute({"resolve-destination": ok(GitLabDestination.PROJECT)})
        GL.resolve_destination(gitlab_cfg(), ex)
        self.assertEqual(len(ex.calls), 1)

    def test_failed_root_lookup_is_unresolved(self) -> None:
        ex = fake_execute({
            "resolve-destination": ok(self._subgroup_project()),
            "resolve-billing-namespace": ok({"id": None}),
        })
        out = GL.resolve_destination(gitlab_cfg(), ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)


class MissingPlanIsNotEvidence(unittest.TestCase):
    """A 200 whose plan is absent/unknown is a FAILED probe - subgroup and
    non-owner responses omit the billing field, and missing evidence must
    never become blockedBy: false."""

    def _cfg_with_prior(self) -> dict:
        cfg = gitlab_cfg()
        cfg["tracker"]["resolved"] = {
            "destination": {"projectId": 1, "projectPath": "a/b",
                            "host": "gitlab.com", "namespaceId": 111},
            "capabilities": {"attachments": True, "blockedBy": True,
                             "subIssues": False, "deleteIssue": True,
                             "_source": {"gitlabPlan": "ultimate"}},
            "scopeResolvedAt": {"capabilities": "2026-01-01T00:00:00Z"}}
        return cfg

    def test_absent_plan_fails_the_probe(self) -> None:
        for payload in ({"id": 111}, {"id": 111, "plan": None},
                        {"id": 111, "plan": 7}, {"id": 111, "plan": "mystery_tier"}):
            with self.subTest(payload=payload):
                ex = fake_execute({"probe-plan": ok(payload)})
                ok_, plan, reason = GL.probe_plan(gitlab_cfg(), ex, namespace_id=111)
                self.assertFalse(ok_)
                self.assertIn("plan", reason)

    def test_fresh_resolution_fails_on_missing_plan(self) -> None:
        ex = fake_execute({"probe-plan": ok({"id": 111})})
        out = GL.resolve_capabilities(gitlab_cfg(), ex, namespace_id=111)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)

    def test_ttl_probe_on_missing_plan_keeps_the_prior_capability(self) -> None:
        cfg = self._cfg_with_prior()
        ex = fake_execute({"probe-plan": ok({"id": 111})})
        out = GL.ttl_reprobe(cfg, ex, now="2026-06-01T00:00:00Z")
        self.assertFalse(out["probe"]["ok"])
        self.assertIsNone(out["degraded"])
        self.assertTrue(cfg["tracker"]["resolved"]["capabilities"]["blockedBy"])

    def test_every_known_plan_is_accepted(self) -> None:
        for plan in sorted(GL.KNOWN_PLANS):
            ex = fake_execute({"probe-plan": ok({"id": 111, "plan": plan})})
            ok_, got, _ = GL.probe_plan(gitlab_cfg(), ex, namespace_id=111)
            self.assertTrue(ok_, plan)
            self.assertEqual(got, plan)


class NestedShapeGuards(unittest.TestCase):
    """Malformed provider output returns TrackerError, never AttributeError."""

    def test_github_non_dict_owner(self) -> None:
        for owner in ("gmickel", 5, ["x"], None):
            with self.subTest(owner=owner):
                ex = fake_execute({"resolve-destination": ok(
                    {"name": "airtest", "owner": owner})})
                out = GH.resolve_destination({}, ex)
                self.assertIsInstance(out, TrackerError)

    def test_github_non_string_name(self) -> None:
        ex = fake_execute({"resolve-destination": ok(
            {"name": 7, "owner": {"login": "gmickel"}})})
        out = GH.resolve_destination({}, ex)
        self.assertIsInstance(out, TrackerError)

    def test_gitlab_non_dict_namespace(self) -> None:
        for ns in ("acme", 5, ["x"], None):
            with self.subTest(namespace=ns):
                ex = fake_execute({"resolve-destination": ok(
                    {"id": 1, "namespace": ns,
                     "web_url": "https://gitlab.com/a/b"})})
                out = GL.resolve_destination(gitlab_cfg(), ex)
                self.assertIsInstance(out, TrackerError)
