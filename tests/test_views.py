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
        fixtures.lt_status(), fixtures.lt_positions(), fixtures.lt_stops(), fixtures.lt_symbols(), fixtures.lt_events(),
        records=fixtures.lt_records(),
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
            "距下轨",
            "打开 HL 面板",
            "打开 Lighter 面板",
            "ma.example/admin?k=hltok",
            "lt.example/?k=ltadmin",
            "实盘 6 笔",
            "API 剩 163 天",
        ):
            self.assertIn(needle, html, f"missing: {needle}")

    def test_unified_markers(self):
        """两卡的标记语言一致：状态行止损都有 ✔、持仓标记都有、子行结构同序。"""
        cfg = _cfg()
        html = render_page(
            _store_with_both().summary(stale_after_s=180),
            cfg.hl_panel_url,
            cfg.lt_panel_url,
        )
        # 止损 ✔ 只在状态行出现（仓位表只放裸价格，加标记会把行顶成两行）
        self.assertEqual(html.count("<span class='mark'>✔</span>"), 2)
        # 持仓标记：合并卡里两边同向（HL short + LT held_side=-1）去重为一处
        self.assertEqual(html.count("持仓空（HL·LT）"), 1)
        self.assertEqual(html.count("持仓中"), 0)  # HL 有距上/下轨时 verdict 不渲染
        self.assertEqual(html.count("距上轨"), 3)  # 三标的动态合并卡：每标的距离
        # 两卡子行都有 tick 新鲜度与止损位（tick 在止损标记之后：" · tick "）
        self.assertEqual(html.count("止损 <span class='mark'>✔</span>"), 2)
        self.assertEqual(html.count(" · tick "), 2)
        # 两卡权益行都带浮盈
        self.assertEqual(html.count("<span class=\"upnl\">浮盈 "), 2)

    def test_head_links_are_local_icons(self):
        cfg = _cfg()
        html = render_page(
            _store_with_both().summary(stale_after_s=180),
            cfg.hl_panel_url,
            cfg.lt_panel_url,
        )
        self.assertIn("<link rel='apple-touch-icon' href='/apple-touch-icon.png'>", html)
        self.assertIn("<link rel='icon' type='image/png' href='/favicon-32.png'>", html)
        self.assertIn("<link rel='manifest' href='/manifest.webmanifest'>", html)

    def test_self_contained_no_external_assets(self):
        cfg = _cfg()
        html = render_page(
            _store_with_both().summary(stale_after_s=180),
            cfg.hl_panel_url,
            cfg.lt_panel_url,
        )
        self.assertNotIn("<script src=", html)
        self.assertNotIn("@import", html)
        self.assertNotIn("cdn.", html)
        # <link> 允许，但必须全部指向本站（相对路径）——指外网的算外链资产
        import re

        link_hrefs = re.findall(r"<link[^>]*href='([^']*)'", html)
        self.assertTrue(link_hrefs)
        for href in link_hrefs:
            self.assertTrue(href.startswith("/"), f"external link asset: {href}")
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

    def test_symbols_card_falls_back_to_lt(self):
        """HL 不可用时，三标的动态整卡退回 LT 数据（verdict 文案 + 持仓标记）。"""
        st = SnapshotStore()
        st.put("lt", True, 1793432641.0, normalize_lt(
            fixtures.lt_status(), fixtures.lt_positions(), fixtures.lt_stops(), fixtures.lt_symbols(), fixtures.lt_events(),
            records=fixtures.lt_records(),
        ))
        html = render_page(st.summary(stale_after_s=180), "https://a", "https://b")
        self.assertEqual(html.count("三标的动态"), 1)
        self.assertIn("等密集（带宽未进门槛）", html)
        self.assertIn("持仓空（LT）", html)
        self.assertNotIn("距上轨", html)

    def test_symbols_card_hidden_without_both(self):
        st = SnapshotStore()
        st.put("hl", False, 1793432400.0, {}, "HTTPError: 502")
        html = render_page(st.summary(stale_after_s=180), "https://a", "https://b")
        self.assertNotIn("三标的动态", html)

    def test_fills_and_exit_price(self):
        """底部区是最近成交（带平仓盈亏），持仓表带离场价列；不再渲染运维事件。"""
        cfg = _cfg()
        html = render_page(
            _store_with_both().summary(stale_after_s=180),
            cfg.hl_panel_url,
            cfg.lt_panel_url,
        )
        # 成交行：HL 最新先是开空腿，再是带已实现盈亏的平空腿；LT 同构
        self.assertIn("SOL 开空 1.17 @ 99.45", html)
        self.assertIn("SOL 平空 1.13 @ 102.44（-3.24 U）", html)
        self.assertIn("SOL 开空 0.72 @ 95.60", html)
        self.assertIn("SOL 平多 1.19 @ 102.73（-3.64 U）", html)
        # 成交时间是北京时间（fixture ts 1793304200 = UTC 20:03 → 北京 04:03）
        self.assertIn(">04:03</span>SOL 开空 1.17 @ 99.45", html)
        # 止损列裸价格：有 <td>104.95</td>，不再带 ✔
        self.assertIn("<td>104.95</td>", html)
        self.assertNotIn("<td>104.95 <span", html)
        # 头部生成时间是北京时间，无 UTC 后缀
        self.assertNotIn(" UTC</span>", html)
        # 运维事件不再出现在底部区
        self.assertNotIn("executor 心跳", html)
        # 离场价：两表表头；HL 取 symbol_state SMA20、LT 取 exit_price，
        # fixtures 里两者恰好同为 99.19，所以单元格出现两处
        self.assertEqual(html.count("<th>离场</th>"), 2)
        # 列序：浮盈U 在离场前（用户拍板的对调）
        self.assertEqual(html.count("<th>浮盈U</th><th>离场</th>"), 2)
        self.assertEqual(html.count("<th>离场</th><th>浮盈U</th>"), 0)
        self.assertEqual(html.count("<td>99.19</td>"), 2)
        # 无成交兜底
        st = SnapshotStore()
        st.put("hl", True, 1793432400.0, normalize_hl({**fixtures.hl_status(), "fills": []}))
        html2 = render_page(st.summary(stale_after_s=180), cfg.hl_panel_url, cfg.lt_panel_url)
        self.assertIn("暂无成交", html2)

    def test_trade_symbol_escaped(self):
        st = _store_with_both()
        lt = st.get("lt")
        lt["data"]["trades"][0]["symbol"] = "<b>x</b>"
        html = render_page(st.summary(stale_after_s=180), "https://a", "https://b")
        self.assertNotIn("<b>x</b>", html)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)

    def test_event_message_escaped(self):
        """运维事件已不渲染；转义检查对象换成 HL 成交行的动态字段。"""
        st = _store_with_both()
        hl = st.get("hl")
        hl["data"]["fills"][0]["coin"] = "<script>x</script>"
        html = render_page(st.summary(stale_after_s=180), "https://a", "https://b")
        self.assertNotIn("<script>x</script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
