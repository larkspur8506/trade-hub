import asyncio
import unittest

from app.config import Config
from app.upstream import collect_hl, collect_lt, normalize_hl, normalize_lt

from . import fixtures


def _cfg(**kw) -> Config:
    base = dict(
        token="hubtok",
        hl_token="hltok",
        lt_admin_token="ltadmin",
        hl_base="http://127.0.0.1:8100/",
        lt_base="http://127.0.0.1:8110",
        hl_panel_base="https://ma.example",
        lt_panel_base="https://lt.example",
        poll_s=60,
        request_timeout_s=5,
    )
    base.update(kw)
    return Config(**base)


class NormalizeHlTests(unittest.TestCase):
    def test_extracts_fields(self):
        d = normalize_hl(fixtures.hl_status())
        self.assertEqual(d["equity"], 499.22)
        self.assertEqual(d["unrealized_pnl"], 4.59)
        self.assertEqual(d["mode"], "live")
        self.assertFalse(d["kill"])
        self.assertEqual(len(d["positions"]), 1)
        p = d["positions"][0]
        self.assertEqual(p["coin"], "SOL")
        self.assertEqual(p["side"], -1)
        self.assertTrue(p["has_stop"])
        self.assertEqual(p["stop_px"], 104.95)
        self.assertEqual(len(d["symbols"]), 3)
        self.assertEqual(d["symbols"][0]["coin"], "BTC")
        self.assertEqual(d["agent_days_left"], 163)
        self.assertTrue(d["feed_ok"])
        self.assertEqual(len(d["events"]), 2)
        self.assertEqual(d["perf"]["n"], 6)

    def test_tolerates_missing_sections(self):
        d = normalize_hl({"mode": "off", "account": {"equity": 1.0}})
        self.assertEqual(d["equity"], 1.0)
        self.assertEqual(d["positions"], [])
        self.assertEqual(d["symbols"], [])
        self.assertIsNone(d["feed_ok"])
        self.assertIsNone(d["agent_days_left"])
        self.assertFalse(d["kill"])

    def test_feed_failure_reflected(self):
        status = fixtures.hl_status()
        for f in status["system"]["feed"]:
            f["ok"] = False
        self.assertFalse(normalize_hl(status)["feed_ok"])


class NormalizeLtTests(unittest.TestCase):
    def test_combines_and_filters_open(self):
        d = normalize_lt(
            fixtures.lt_status(),
            fixtures.lt_positions(),
            fixtures.lt_stops(),
            fixtures.lt_symbols(),
            fixtures.lt_events(),
        )
        self.assertEqual(d["equity"], 496.45)
        self.assertEqual(d["open_count"], 1)
        self.assertEqual(len(d["positions"]), 1)  # IDLE row filtered
        p = d["positions"][0]
        self.assertEqual(p["symbol"], "SOL")
        self.assertEqual(p["side_text"], "空")
        self.assertTrue(d["stops_all_protected"])
        self.assertEqual(d["stops_uncovered"], 0)
        self.assertAlmostEqual(d["dd"], 0.0071)
        self.assertEqual(d["symbols"][0]["verdict"], "等密集（带宽未进门槛）")
        self.assertEqual(len(d["events"]), 2)
        self.assertEqual(d["degraded_parts"], [])

    def test_missing_sections_yield_empty_lists(self):
        d = normalize_lt(fixtures.lt_status(), None, None, None, None)
        self.assertEqual(d["positions"], [])
        self.assertIsNone(d["stops_all_protected"])
        self.assertEqual(d["degraded_parts"], [])  # collector's job, not the normalizer's

    def test_collector_reports_all_missing_subparts(self):
        import asyncio

        from app.upstream import collect_lt

        def fake_fetch(url, timeout):
            if url.endswith("/status"):
                return fixtures.lt_status(), ""
            return None, "HTTPError: 500"

        src = asyncio.run(collect_lt(_cfg(), fetch=fake_fetch))
        self.assertTrue(src.ok)
        self.assertEqual(len(src.data["degraded_parts"]), 5)

    def test_uncovered_stops_counted(self):
        stops = fixtures.lt_stops()
        stops["all_protected"] = False
        stops["uncovered"] = [{"symbol": "ETH"}]
        d = normalize_lt(fixtures.lt_status(), fixtures.lt_positions(), stops, None, None)
        self.assertFalse(d["stops_all_protected"])
        self.assertEqual(d["stops_uncovered"], 1)

    def test_kill_flagged(self):
        st = fixtures.lt_status()
        st["kill"] = True
        st["kill_reason"] = "人工"
        d = normalize_lt(st, None, None, None, None)
        self.assertTrue(d["kill"])
        self.assertEqual(d["kill_reason"], "人工")


class CollectorTests(unittest.TestCase):
    def test_collect_hl_builds_url_and_normalizes(self):
        seen = {}

        def fake_fetch(url, timeout):
            seen["url"] = url
            seen["timeout"] = timeout
            return fixtures.hl_status(), ""

        src = asyncio.run(collect_hl(_cfg(), fetch=fake_fetch))
        self.assertTrue(src.ok)
        self.assertEqual(seen["url"], "http://127.0.0.1:8100/api/hl/status?k=hltok")
        self.assertEqual(seen["timeout"], 5)
        self.assertEqual(src.data["equity"], 499.22)

    def test_collect_hl_error_path(self):
        src = asyncio.run(collect_hl(_cfg(), fetch=lambda u, t: (None, "HTTPError: 502")))
        self.assertFalse(src.ok)
        self.assertIn("502", src.error)

    def test_collect_lt_all_parts(self):
        calls = []

        def fake_fetch(url, timeout):
            calls.append(url)
            if url.endswith("/status"):
                return fixtures.lt_status(), ""
            if url.endswith("/positions"):
                return fixtures.lt_positions(), ""
            if url.endswith("/stops"):
                return fixtures.lt_stops(), ""
            if url.endswith("/events?limit=5"):
                return fixtures.lt_events(), ""
            if url.endswith("/api/records"):
                return fixtures.lt_records(), ""
            if url.endswith("/symbols"):
                return fixtures.lt_symbols(), ""
            return None, "no fixture for " + url

        src = asyncio.run(collect_lt(_cfg(), fetch=fake_fetch))
        self.assertTrue(src.ok)
        self.assertEqual(len(calls), 6)
        self.assertTrue(any("/api/records" in u for u in calls))
        self.assertEqual(src.data["open_count"], 1)
        self.assertEqual(len(src.data["trades"]), 2)

    def test_collect_lt_status_failure_fails_whole_source(self):
        def fake_fetch(url, timeout):
            if url.endswith("/status"):
                return None, "HTTPError: 500"
            return {}, ""

        src = asyncio.run(collect_lt(_cfg(), fetch=fake_fetch))
        self.assertFalse(src.ok)
        self.assertIn("500", src.error)

    def test_collect_lt_subpart_failure_degrades(self):
        def fake_fetch(url, timeout):
            if url.endswith("/symbols"):
                return None, "TimeoutError: x"
            if url.endswith("/status"):
                return fixtures.lt_status(), ""
            if url.endswith("/positions"):
                return fixtures.lt_positions(), ""
            if url.endswith("/stops"):
                return fixtures.lt_stops(), ""
            if url.endswith("/events?limit=5"):
                return fixtures.lt_events(), ""
            if url.endswith("/api/records"):
                return fixtures.lt_records(), ""
            return None, "no fixture for " + url

        src = asyncio.run(collect_lt(_cfg(), fetch=fake_fetch))
        self.assertTrue(src.ok)
        self.assertEqual(len(src.data["degraded_parts"]), 1)
        self.assertIn("symbols", src.data["degraded_parts"][0])


if __name__ == "__main__":
    unittest.main()
