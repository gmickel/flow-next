"""Reached-path routing tests for tracker-sync (fake transports only)."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
HARNESS = REPO_ROOT / "optimization" / "reached-path"
SKILL = (
    REPO_ROOT
    / "plugins"
    / "flow-next"
    / "skills"
    / "flow-next-tracker-sync"
    / "SKILL.md"
)
B1_TRACKER = HARNESS / "fixtures" / "b1" / "tracker"


def _load_module() -> Any:
    path = HARNESS / "tracker_routes.py"
    spec = importlib.util.spec_from_file_location("tracker_routes_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


routes = _load_module()


class SelectedAdapterRouteTestCase(unittest.TestCase):
    def test_inactive_and_unknown_load_no_adapter(self) -> None:
        for active, provider in ((False, None), (None, "github"), (True, "bogus")):
            route = routes.resolve_route(active=active, provider=provider)
            self.assertEqual((), route.adapter_reads)
            self.assertTrue(route.safe_stop)
            self.assertEqual(routes.ALL_ADAPTER_REFS, frozenset(route.forbidden_reads))

    def test_each_provider_loads_only_its_adapter(self) -> None:
        cases = {
            "github": {"active": True, "provider": "github"},
            "gitlab": {"active": True, "provider": "gitlab"},
            "jira": {"active": True, "provider": "jira"},
            "linear-mcp": {
                "active": True,
                "provider": "linear",
                "linear_mcp": True,
                "linear_api_key": True,
            },
            "linear-graphql": {
                "active": True,
                "provider": "linear",
                "linear_api_key": True,
            },
            "linear-none": {"active": True, "provider": "linear"},
        }
        for expected, kwargs in cases.items():
            with self.subTest(route=expected):
                route = routes.resolve_route(**kwargs)
                self.assertEqual(expected, route.state)
                self.assertEqual(routes.ADAPTER_REFS[expected], route.adapter_reads)
                self.assertFalse(set(route.adapter_reads) & set(route.forbidden_reads))
                routes.assert_production_form(REPO_ROOT, route)

    def test_linear_mcp_wins_and_unreached_rung_stays_cold(self) -> None:
        route = routes.resolve_route(
            active=True,
            provider="linear",
            linear_mcp=True,
            linear_api_key=True,
        )
        self.assertIn("references/linear-mcp.md", route.adapter_reads[-1])
        self.assertTrue(
            any(path.endswith("linear-graphql.md") for path in route.forbidden_reads)
        )

    def test_prompt_contains_fail_closed_router_contract(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for marker in (
            "Reached-path loading — common rules + one selected adapter",
            "read **exactly one** adapter path",
            "ROUTE_STATE=unknown",
            "linear|github|gitlab|jira",
            "do not guess a provider",
            "do not mutate sync state",
        ):
            self.assertIn(marker, text)

    def test_common_path_retains_reconciliation_contracts(self) -> None:
        texts = {
            path: (REPO_ROOT / path).read_text(encoding="utf-8")
            for path in routes.COMMON_REFS
        }
        combined = "\n".join(texts.values())
        for marker in (
            "Create-if-unlinked",
            "threeWayMergeBody",
            "who-wins",
            "sync defer",
            "projectDepRelations",
            "list-open",
            "list-relations",
            "question <spec-id | tracker-id>",
            "sync receipt",
            "lastSyncedAt",
        ):
            self.assertIn(marker, combined)


class FrozenFixtureCoverageTestCase(unittest.TestCase):
    def test_all_frozen_tracker_branches_are_covered(self) -> None:
        fixture_ids = {
            json.loads(path.read_text(encoding="utf-8"))["fixture_id"]
            for path in B1_TRACKER.glob("*.json")
        }
        expected = {
            "tracker.inactive",
            "tracker.malformed-config",
            "tracker.linear-mcp",
            "tracker.linear-graphql",
            "tracker.github",
            "tracker.gitlab",
            "tracker.jira",
            "tracker.op-push",
            "tracker.op-pull",
            "tracker.op-reconcile",
            "tracker.op-create-if-unlinked",
            "tracker.conflict-body",
            "tracker.conflict-status",
            "tracker.conflict-comments",
            "tracker.conflict-dependency",
        }
        self.assertEqual(expected, fixture_ids)


class FakeTransportTraceTestCase(unittest.TestCase):
    def test_production_shapes_are_recorded_without_external_writes(self) -> None:
        cases = {
            "github": {"active": True, "provider": "github"},
            "gitlab": {"active": True, "provider": "gitlab"},
            "jira": {"active": True, "provider": "jira"},
            "linear-mcp": {
                "active": True,
                "provider": "linear",
                "linear_mcp": True,
            },
            "linear-graphql": {
                "active": True,
                "provider": "linear",
                "linear_api_key": True,
            },
        }
        for expected, kwargs in cases.items():
            with self.subTest(route=expected):
                route = routes.resolve_route(**kwargs)
                fake = routes.FakeTransport(route)
                trace = fake.call(
                    "writeIssue",
                    {"issue": {"id": "fake-1", "body": "sanitized fixture"}},
                )
                self.assertTrue(trace["fake"])
                self.assertEqual(0, trace["external_writes"])
                self.assertIsNotNone(trace["wire_form"])
                self.assertEqual("updated", trace["receipt_status"])
                self.assertEqual(expected, route.state)
                routes.assert_production_form(REPO_ROOT, route)

    def test_operation_and_conflict_matrix_stays_on_normalized_interface(self) -> None:
        route = routes.resolve_route(active=True, provider="github")
        fake = routes.FakeTransport(route)
        operations = (
            "create-if-unlinked",
            "push",
            "pull",
            "reconcile",
            "conflict-body-defer",
            "conflict-status-defer",
            "conflict-comments-defer",
            "conflict-dependency-defer",
        )
        for operation in operations:
            trace = fake.call(
                operation,
                {"issue": {"id": "fake-1"}, "event": "manual"},
            )
            self.assertEqual(0, trace["external_writes"])
            self.assertEqual("fake-1", trace["normalized_request"]["issue"]["id"])
            if operation.startswith("conflict-"):
                self.assertEqual("queued", trace["receipt_status"])
            else:
                self.assertEqual("updated", trace["receipt_status"])
        self.assertEqual(list(operations), [call["operation"] for call in fake.calls])

    def test_auth_unavailable_degrades_each_provider_to_noop(self) -> None:
        cases = (
            {"active": True, "provider": "github"},
            {"active": True, "provider": "gitlab"},
            {"active": True, "provider": "jira"},
            {"active": True, "provider": "linear", "linear_mcp": True},
            {"active": True, "provider": "linear", "linear_api_key": True},
        )
        for kwargs in cases:
            with self.subTest(route=kwargs):
                route = routes.resolve_route(**kwargs)
                trace = routes.FakeTransport(route, available=False).call(
                    "writeIssue", {"issue": {"id": "fake-1"}}
                )
                self.assertEqual("none", trace["transport"])
                self.assertEqual("noop", trace["receipt_status"])
                self.assertIsNone(trace["wire_form"])
                self.assertEqual(0, trace["external_writes"])

    def test_no_transport_and_malformed_are_noop(self) -> None:
        cases = (
            routes.resolve_route(active=True, provider="linear"),
            routes.resolve_route(active=True, provider="unknown"),
        )
        for route in cases:
            trace = routes.FakeTransport(route).call("writeIssue", {"issue": {}})
            self.assertEqual("none", trace["transport"])
            self.assertEqual("noop", trace["receipt_status"])
            self.assertEqual(0, trace["external_writes"])
            self.assertIsNone(trace["wire_form"])


if __name__ == "__main__":
    unittest.main()
