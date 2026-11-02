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
            "标的动态",
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
        # 持仓标记：合并卡里两边同向（HL short + LT held_side=-1）去重为一处；
        # 持仓标的的密集/触发线被面板置 NULL（不评估入场）→ 显示「持仓中」，
        # 只空仓的 BTC/ETH 才有密集数和距上/下轨
        self.assertEqual(html.count("持仓空（HL·LT）"), 1)
        self.assertEqual(html.count(" · 持仓中"), 1)
        self.assertEqual(html.count(" · 密集 "), 2)
        self.assertEqual(html.count("距上轨"), 2)
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
        self.assertEqual(html.count("标的动态"), 1)
        self.assertIn("等密集（带宽未进门槛）", html)
        self.assertIn("持仓空（LT）", html)
        self.assertNotIn("距上轨", html)
        # LT 独撑：空仓标的显示 verdict，持仓标的显示「持仓中」（verdict 不叠加）
        self.assertEqual(html.count("等密集（带宽未进门槛）"), 2)
        self.assertEqual(html.count(" · 持仓中"), 1)

    def test_symbols_card_hidden_without_both(self):
        st = SnapshotStore()
        st.put("hl", False, 1793432400.0, {}, "HTTPError: 502")
        html = render_page(st.summary(stale_after_s=180), "https://a", "https://b")
        self.assertNotIn("标的动态", html)

    def test_fills_and_exit_price(self):
        """底部区是最近成交（带平仓盈亏），持仓表带离场价列；不再渲染运维事件。"""
        cfg = _cfg()
        html = render_page(
            _store_with_both().summary(stale_after_s=180),
            cfg.hl_panel_url,
            cfg.lt_panel_url,
        )
        # 成交行：HL 最新先是开空腿，再是带已实现盈亏的平空腿；LT 同构。
        # LT 离场腿的 side_text 是成交方向（买入），渲染按被平仓位方向显示「平空」
        self.assertIn("SOL 开空 1.17 @ 99.45", html)
        self.assertIn("SOL 平空 1.13 @ 102.44（-3.24 U）", html)
        self.assertIn("SOL 开空 0.72 @ 95.60", html)
        self.assertIn("SOL 平空 1.19 @ 102.73（-3.64 U）", html)
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

    def _store_with_mr(self, *, enabled=True, holding=False):
        st = SnapshotStore()
        data = fixtures.hl_status()
        data["mr"] = {
            "enabled": enabled, "state": "holding" if holding else "flat",
            "recon": "ok", "mark": 694.09,
            "signal": {"rsi2": 8.48, "threshold": 10.0, "exit_line": 685.25,
                       "next_eval_et": "2026-11-03T16:00:00-05:00",
                       "phase": "in_window", "last_session_date": "2026-10-30"},
        }
        if holding:
            data["mr"]["pos"] = {"qty": 0.0088, "entry_price": 28580.0,
                                 "mark": 28780.0, "upnl": 1.76,
                                 "dist_to_exit_pct": -97.61,
                                 "exit_line": 685.25}
        st.put("hl", True, 1793432400.0, normalize_hl(data))
        return st

    def test_mr_line_rendered_once_from_hl(self):
        """超跌腿只渲染一份（两所同源），并标出来源；持仓时动态行只留状态
        （现价/浮盈/离场线都在仓位表那行，重复会被读成两份账——2026-11-02）。"""
        cfg = _cfg()
        html = render_page(self._store_with_mr(holding=True).summary(stale_after_s=180),
                           cfg.hl_panel_url, cfg.lt_panel_url)
        self.assertEqual(html.count("超跌腿·"), 1)
        self.assertIn("超跌腿·HL", html)
        self.assertIn("持仓中", html)
        self.assertNotIn("距入场", html)
        self.assertNotIn("离场线 685.25", html)      # 仓位表的离场列还在，动态行不再重复
        self.assertIn('QQQ <span class="v">持仓中', html)  # 持仓时动态行只剩状态

    def test_mr_line_empty_shows_entry_distance(self):
        """空仓时动态行的职责：离开仓有多远（现价 · RSI2/阈值）+ 在等什么。"""
        cfg = _cfg()
        html = render_page(self._store_with_mr(holding=False).summary(stale_after_s=180),
                           cfg.hl_panel_url, cfg.lt_panel_url)
        self.assertIn("现价 694.09", html)
        self.assertIn("RSI2 8.48 / 阈 10", html)
        self.assertIn("窗口内等成交", html)
        self.assertNotIn("离场线", html)

    def test_mr_line_absent_when_disabled(self):
        cfg = _cfg()
        html = render_page(self._store_with_mr(enabled=False).summary(stale_after_s=180),
                           cfg.hl_panel_url, cfg.lt_panel_url)
        self.assertNotIn("超跌腿·", html)


    def _store_with_mr_pos(self):
        st = SnapshotStore()
        data = fixtures.hl_status()
        data["positions"] = []            # 主 dex 空仓，QQQ 在 xyz 子账户
        data["mr"] = {"enabled": True, "state": "holding", "recon": "ok",
                      "signal": {"rsi2": 8.4, "threshold": 10.0, "exit_line": 29327.25,
                                 "phase": "holding"},
                      "pos": {"qty": 0.0087, "entry_price": 28579.9, "mark": 28780.1,
                              "upnl": 1.74, "notional": 248.65, "exit_line": 29327.25}}
        st.put("hl", True, 1793432400.0, normalize_hl(data))
        return st

    def test_hl_card_shows_mr_position_row(self):
        """HL 的 QQQ 在 xyz dex，主 dex positions[] 里没有 —— 聚合页要从 mr.pos 补一行。"""
        cfg = _cfg()
        html = render_page(self._store_with_mr_pos().summary(stale_after_s=180),
                           cfg.hl_panel_url, cfg.lt_panel_url)
        self.assertIn("QQQ", html)
        self.assertIn("多·MR", html)
        self.assertIn("28,580", html)   # 窄屏价格取整（≥1000 不留小数）
        self.assertNotIn("当前空仓", html)


if __name__ == "__main__":
    unittest.main()
