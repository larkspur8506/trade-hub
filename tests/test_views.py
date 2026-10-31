import unittest

from app.store import SnapshotStore
from app.upstream import normalize_hl, normalize_lt
from app.views import render_page

from . import fixtures
from .test_upstream import _cfg


def _store_with_both() -> SnapshotStore:
    st = SnapshotStore()
    st.put("hl", True, 1793432400.0, normalize_hl(fixtures.hl_status()))
    st.put("lt", True, 1793432641.0, normalize_lt(
        fixtures.lt_status(), fixtures.lt_positions(), fixtures.lt_stops(), fixtures.lt_symbols(), fixtures.lt_events()
    ))
    return st


class RenderTests(unittest.TestCase):
    def test_full_page_contains_blocks(self):
        cfg = _cfg()
        html = render_page(
            _store_with_both().summary(stale_after_s=180),
            cfg.hl_panel_url,
            cfg.lt_panel_url,
        )
        for needle in (
            "trade-hub",
            "Hyperliquid",
            "Lighter",
            "499.22",
            "496.45",
            "SOL 空",
            "三标的动态",
            "等密集（带宽未进门槛）",
            "打开 HL 面板",
            "打开 Lighter 面板",
            "ma.example/admin?k=hltok",
            "lt.example/?k=ltadmin",
            "实盘 6 笔",
            "API 剩 163 天",
        ):
            self.assertIn(needle, html, f"missing: {needle}")

    def test_self_contained_no_external_assets(self):
        cfg = _cfg()
        html = render_page(
            _store_with_both().summary(stale_after_s=180),
            cfg.hl_panel_url,
            cfg.lt_panel_url,
        )
        self.assertNotIn("<script src=", html)
        self.assertNotIn("@import", html)
        self.assertNotIn("<link ", html)
        self.assertNotIn("cdn.", html)
        # the only external URLs allowed are the two panel jump links
        external = [line for line in html.split("href=") if "http" in line.split(">")[0]]
        self.assertEqual(len(external), 2, external)

    def test_error_source_shows_banner(self):
        st = SnapshotStore()
        st.put("hl", False, 1793432400.0, {}, "HTTPError: 502")
        html = render_page(st.summary(stale_after_s=180), "https://a", "https://b")
        self.assertIn("不可用", html)
        self.assertIn("502", html)
        self.assertIn("等待第一轮拉取", html)  # lt never fetched

    def test_empty_store_renders_init(self):
        html = render_page(SnapshotStore().summary(stale_after_s=180), "https://a", "https://b")
        self.assertEqual(html.count("等待第一轮拉取"), 2)

    def test_kill_and_stale_banners(self):
        st = _store_with_both()
        hl = st.get("hl")
        hl["data"]["kill"] = True
        hl["data"]["kill_reason"] = "人工"
        st.put("hl", True, 0.0, hl["data"])  # as_of=0 -> stale
        html = render_page(st.summary(stale_after_s=180), "https://a", "https://b")
        self.assertIn("已 kill（人工）", html)
        self.assertIn("数据", html)
        self.assertIn("未刷新", html)

    def test_event_message_escaped(self):
        st = _store_with_both()
        hl = st.get("hl")
        hl["data"]["events"][0]["message"] = "<script>x</script>"
        html = render_page(st.summary(stale_after_s=180), "https://a", "https://b")
        self.assertNotIn("<script>x</script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
