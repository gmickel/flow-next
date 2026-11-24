"""`wire list-open --any-lane / --unlinked` (fn-314 R2-R5, R7).

Fake transports for every provider: the any-lane query, the compact row shape,
the local-only link check, the unchanged default output, and backlog mode's
tracker-only set.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[1] / "plugins" / "flow"
sys.path.insert(0, str(ROOT / "skills" / "flow" / "scripts"))
sys.path.insert(0, str(TESTS))

from flowctl_tracker import wire as W  # noqa: E402
from flowctl_tracker.types import ErrorClass, TrackerError  # noqa: E402
from test_tracker_conformance import (  # noqa: E402
    GH_ISSUE, GH_NODE, GL_ID, GL_ISSUE, JR_ID, JR_ISSUE, LN_ISSUE, LN_UUID,
    cli_endpoint, fake_execute, gh_cfg, gl_cfg, jr_cfg, ln_cfg, ok,
)

COMPACT_KEYS = {"id", "identifier", "title", "url", "labels", "excerpt"}
LONG_BODY = "x" * 900


def _second(issue: dict, **changes) -> dict:
    return {**issue, **changes}


# Two open issues per provider; the first is the one a spec links in tests.
GH_TWO = [GH_ISSUE, _second(GH_ISSUE, id=999002, node_id="I_kwDOTestNode2",
                            number=43, body=LONG_BODY)]
GL_TWO = [GL_ISSUE, _second(GL_ISSUE, id=GL_ID + 1, iid=13, description=LONG_BODY)]
LN_TWO = [LN_ISSUE, _second(LN_ISSUE, id="ffffffff-0000-0000-0000-000000000002",
                            identifier="WOR-18", description=LONG_BODY)]
JR_TWO = [JR_ISSUE, {"id": "10043", "key": "SCRUM-2",
                     "fields": {"summary": "T2", "description": LONG_BODY,
                                "labels": []}}]

CASES = [
    ("github", gh_cfg, ok(GH_TWO), GH_NODE, "I_kwDOTestNode2"),
    ("gitlab", gl_cfg, ok(GL_TWO), str(GL_ID), str(GL_ID + 1)),
    ("linear", ln_cfg, ok({"data": {"issues": {"nodes": LN_TWO}}}),
     LN_UUID, "ffffffff-0000-0000-0000-000000000002"),
    ("jira", jr_cfg, ok({"issues": JR_TWO}), JR_ID, "10043"),
]


def _unset_ready(cfg: dict) -> dict:
    cfg["tracker"].pop("readyState", None)
    return cfg


def _flow_with_link(tmp: str, durable: str) -> Path:
    flow = Path(tmp)
    (flow / "specs").mkdir()
    (flow / "specs" / "fn-1-linked.md").write_text(
        f"---\nid: fn-1-linked\ntitle: Linked\ntracker:\n  id: {json.dumps(durable)}\n  identifier: \"x\"\n---\n",
        encoding="utf-8")
    (flow / "specs" / "fn-2-unlinked.md").write_text(
        "---\nid: fn-2-unlinked\ntitle: Unlinked\n---\n", encoding="utf-8")
    return flow


def _lane_filter(provider: str, request) -> object:
    """The lane part of the one list request a provider issued."""
    if provider in ("github", "gitlab"):
        params = parse_qs(urlparse(cli_endpoint(request)).query)
        return params.get("labels"), params["state"]
    if provider == "linear":
        return json.loads(request.body)["variables"]["filter"]["state"]
    if request.method == "POST":
        return [json.loads(request.body)["jql"]]
    return parse_qs(urlparse(str(request.url_or_argv)).query)["jql"]


class AnyLaneTests(unittest.TestCase):
    def test_any_lane_lists_every_open_issue_with_ready_state_unset(self) -> None:
        expected_lane = {
            "github": (None, ["open"]),
            "gitlab": (None, ["opened"]),
            "linear": {"type": {"nin": ["completed", "canceled", "duplicate"]}},
            "jira": ["project = SCRUM AND statusCategory != Done"],
        }
        for provider, cfg_fn, response, first, second in CASES:
            with self.subTest(provider=provider):
                ex = fake_execute({"wire-list-open": response})
                out = W.dispatch("list-open", _unset_ready(cfg_fn()),
                                 execute=ex, any_lane=True)
                self.assertNotIsInstance(out, TrackerError, out)
                self.assertEqual([r["id"] for r in out["issues"]], [first, second])
                self.assertFalse(out["truncated"])
                self.assertEqual(len(ex.calls), 1)
                self.assertEqual(_lane_filter(provider, ex.calls[0]),
                                 expected_lane[provider])

    def test_any_lane_ignores_a_set_ready_state(self) -> None:
        for provider, cfg_fn, response, _first, _second in CASES:
            with self.subTest(provider=provider):
                ex = fake_execute({"wire-list-open": response})
                W.dispatch("list-open", cfg_fn(), execute=ex, any_lane=True)
                lane = json.dumps(_lane_filter(provider, ex.calls[0]))
                self.assertNotIn("Ready", lane)

    def test_compact_rows_drop_raw_and_cut_the_body(self) -> None:
        for provider, cfg_fn, response, _first, _second in CASES:
            with self.subTest(provider=provider):
                ex = fake_execute({"wire-list-open": response})
                out = W.dispatch("list-open", _unset_ready(cfg_fn()),
                                 execute=ex, any_lane=True)
                first, second = out["issues"]
                self.assertEqual(set(first), COMPACT_KEYS)
                self.assertEqual(first["labels"], ["bug"])
                self.assertEqual(first["excerpt"], "B")
                self.assertEqual(second["excerpt"], "x" * 500)
                self.assertTrue(first["url"], first)

    def test_jira_compact_row_carries_the_browse_url(self) -> None:
        ex = fake_execute({"wire-list-open": ok({"issues": [JR_ISSUE]})})
        out = W.dispatch("list-open", jr_cfg(), execute=ex, any_lane=True)
        self.assertEqual(out["issues"][0]["url"],
                         "https://ex.atlassian.net/browse/SCRUM-1")

    def test_linear_compact_listing_selects_labels(self) -> None:
        # A fixture returns whatever it holds; the query must ask for labels.
        for flags in ({"any_lane": True}, {"unlinked": True}):
            with self.subTest(**flags), tempfile.TemporaryDirectory() as tmp:
                ex = fake_execute({"wire-list-open": ok(
                    {"data": {"issues": {"nodes": [LN_ISSUE]}}})})
                W.dispatch("list-open", ln_cfg(), execute=ex,
                           flow_dir=_flow_with_link(tmp, "none"), **flags)
                self.assertIn("labels { nodes { name } }",
                              json.loads(ex.calls[0].body)["query"])

    def test_jira_cloud_v2_lists_through_search_jql(self) -> None:
        # Cloud answers 410 Gone on GET /rest/api/2/search (measured 2026-11-15).
        for flags in ({}, {"any_lane": True}):
            with self.subTest(flags=flags):
                ex = fake_execute({"wire-list-open": ok(
                    {"issues": [JR_ISSUE], "isLast": True})})
                out = W.dispatch("list-open", jr_cfg(), execute=ex, **flags)
                self.assertNotIsInstance(out, TrackerError, out)
                self.assertEqual(out["issues"][0]["id"], JR_ID)
                request = ex.calls[0]
                self.assertEqual(request.method, "POST")
                self.assertTrue(str(request.url_or_argv).endswith(
                    "/rest/api/2/search/jql"))

    def test_jira_data_center_keeps_classic_search(self) -> None:
        cfg = jr_cfg()
        cfg["tracker"]["perTracker"]["authScheme"] = "bearer-pat"
        ex = fake_execute({"wire-list-open": ok({"issues": [JR_ISSUE], "total": 1})})
        W.dispatch("list-open", cfg, execute=ex, any_lane=True)
        self.assertEqual(ex.calls[0].method, "GET")
        self.assertIn("/rest/api/2/search?", str(ex.calls[0].url_or_argv))

    def test_page_cap_reports_truncated(self) -> None:
        full_page = [_second(GH_ISSUE, node_id=f"I_n{i}", number=i)
                     for i in range(W._PAGE_SIZE)]
        ex = fake_execute({"wire-list-open": lambda _r: ok(full_page)})
        out = W.dispatch("list-open", _unset_ready(gh_cfg()), execute=ex,
                         any_lane=True)
        self.assertTrue(out["truncated"])
        self.assertEqual(len(ex.calls), W._MAX_PAGES)

    def test_unreachable_transport_is_the_existing_error_envelope(self) -> None:
        down = TrackerError(ErrorClass.TRANSPORT, "connection refused",
                            subtype="network")
        for provider, cfg_fn, _response, _first, _second in CASES:
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp)
                (flow / "config.json").write_text(
                    json.dumps(_unset_ready(cfg_fn())), encoding="utf-8")
                ex = fake_execute({"wire-list-open": down})
                payload, code = W.run(flow, "list-open", any_lane=True,
                                      unlinked=True, execute=ex)
                data = json.loads(payload)
                self.assertFalse(data["success"])
                self.assertEqual(data["class"], ErrorClass.TRANSPORT.value)
                self.assertNotEqual(code, 0)


class UnlinkedTests(unittest.TestCase):
    def test_unlinked_omits_issues_a_spec_links_without_an_extra_call(self) -> None:
        for provider, cfg_fn, response, first, second in CASES:
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = _flow_with_link(tmp, first)
                ex = fake_execute({"wire-list-open": response})
                out = W.dispatch("list-open", _unset_ready(cfg_fn()),
                                 execute=ex, any_lane=True, unlinked=True,
                                 flow_dir=flow)
                self.assertEqual([r["id"] for r in out["issues"]], [second])
                self.assertEqual(set(out["issues"][0]), COMPACT_KEYS)
                self.assertEqual({c.op for c in ex.calls}, {"wire-list-open"})
                self.assertEqual(len(ex.calls), 1)

    def test_unlinked_alone_reads_the_ready_lane(self) -> None:
        ready_lane = {
            "github": (["Ready"], ["open"]),
            "gitlab": (["Ready"], ["opened"]),
            "linear": {"name": {"eqIgnoreCase": "Ready"}},
            "jira": ['project = SCRUM AND status = "Ready for Work"'],
        }
        for provider, cfg_fn, response, first, second in CASES:
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = _flow_with_link(tmp, first)
                ex = fake_execute({"wire-list-open": response})
                out = W.dispatch("list-open", cfg_fn(), execute=ex,
                                 unlinked=True, flow_dir=flow)
                self.assertEqual([r["id"] for r in out["issues"]], [second])
                self.assertEqual(_lane_filter(provider, ex.calls[0]),
                                 ready_lane[provider])

    def test_unlinked_alone_keeps_the_unset_ready_state_floor(self) -> None:
        for provider, cfg_fn, _response, _first, _second in CASES:
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = _flow_with_link(tmp, "none")
                ex = fake_execute({})
                out = W.dispatch("list-open", _unset_ready(cfg_fn()),
                                 execute=ex, unlinked=True, flow_dir=flow)
                if provider == "linear":
                    self.assertIsInstance(out, TrackerError)
                    self.assertEqual(out.subtype, "ready_state")
                else:
                    self.assertEqual(out, {"issues": [], "truncated": False})
                self.assertEqual(ex.calls, [])


class DefaultOutputTests(unittest.TestCase):
    def test_no_flags_returns_compact_rows(self) -> None:
        for provider, cfg_fn, response, _first, _second in CASES:
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = _flow_with_link(tmp, _first)
                ex = fake_execute({"wire-list-open": response})
                out = W.dispatch("list-open", cfg_fn(), execute=ex,
                                 flow_dir=flow)
                self.assertEqual(len(out["issues"]), 2)
                self.assertEqual(set(out["issues"][0]), COMPACT_KEYS)
                self.assertEqual(out["issues"][0]["excerpt"], "B")
                self.assertEqual(out["issues"][1]["excerpt"], "x" * 500)
                self.assertNotIn("raw", out["issues"][0])
                self.assertNotIn("body", out["issues"][0])

    def test_linear_default_query_selects_labels_for_compact_rows(self) -> None:
        ex = fake_execute({"wire-list-open": ok(
            {"data": {"issues": {"nodes": LN_TWO}}})})
        W.dispatch("list-open", ln_cfg(), execute=ex)
        self.assertIn("labels { nodes { name } }",
                      json.loads(ex.calls[0].body)["query"])


class BacklogTrackerOnlySetTests(unittest.TestCase):
    """R5: the tracker-only set from `--unlinked` equals the prose de-dup."""

    def test_unlinked_equals_the_prose_dedup_on_a_fixture_backlog(self) -> None:
        from flowctl_tracker import spec_store  # noqa: PLC0415
        for provider, cfg_fn, response, first, _second in CASES:
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = _flow_with_link(tmp, first)
                full = W.dispatch("list-open", cfg_fn(),
                                  execute=fake_execute({"wire-list-open": response}))
                linked = {tr.get("id") for _sid, tr in spec_store.iter_spec_trackers(flow)
                          if tr.get("id")}
                prose = [r["identifier"] for r in full["issues"]
                         if r["id"] not in linked]
                new = W.dispatch("list-open", cfg_fn(), unlinked=True,
                                 flow_dir=flow,
                                 execute=fake_execute({"wire-list-open": response}))
                self.assertEqual([r["identifier"] for r in new["issues"]], prose)


class CliFlagTests(unittest.TestCase):
    def test_cli_accepts_both_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            flow.mkdir()
            (flow / "config.json").write_text("{}", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "skills" / "flow" / "scripts" / "edge.py"), "tracker",
                 "wire", "list-open", "--any-lane", "--unlinked", "--json"],
                cwd=tmp, capture_output=True, text=True)
            self.assertNotIn("unrecognized arguments", proc.stderr)
            self.assertIn("inactive", proc.stdout)


if __name__ == "__main__":
    unittest.main()
