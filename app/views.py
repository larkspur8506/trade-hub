"""Server-rendered mobile-first HTML. Self-contained: no CDN, no external assets.

Theme follows the system (dark default + prefers-color-scheme light), same
convention as the two source panels — no theme toggle by design.

The two system cards share one visual language: identical status-line order
(模式 · kill · 止损 · tick 新鲜度, then system-specific extras), identical
positions-table columns (stop column shows the bare price — a marker makes the
row wrap on mobile), so a glance compares the two systems without re-learning
the layout. All displayed times are Beijing time (UTC+8).
"""
from __future__ import annotations

import html
import math
import time

_STALE_WARN_S = 600  # data older than 10 min gets an amber banner even if ok

_CSS = """
:root{
  --bg:#0f1216; --card:#181d24; --line:#262e38; --fg:#e8ecf1; --dim:#8b97a5; --faint:#5f6b78;
  --ok:#3fb96f; --warn:#d9a13b; --bad:#e05555; --accent:#5b9dd9;
  --up:#2fbf71; --down:#ef5b5b; --up-bg:rgba(47,191,113,.13); --down-bg:rgba(239,91,91,.13);
  --font:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif;
  color-scheme: dark light;
}
@media (prefers-color-scheme: light){
  :root{ --bg:#f3f5f8; --card:#ffffff; --line:#e3e8ee; --fg:#1c2430; --dim:#62707f; --faint:#98a3af;
         --up:#16a35a; --down:#d93f3f; --up-bg:rgba(22,163,90,.10); --down-bg:rgba(217,63,63,.10); }
}
*{box-sizing:border-box}
html,body{max-width:100%;overflow-x:hidden}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 var(--font);padding:12px;overscroll-behavior-y:contain;
  font-variant-numeric:tabular-nums;-webkit-text-size-adjust:100%}
header{display:flex;justify-content:space-between;align-items:center;margin:2px 2px 12px}
header h1{font-size:17px;margin:0;font-weight:700;letter-spacing:.2px}
header .gen{font-size:12px;color:var(--dim);padding:3px 8px;border-radius:999px;border:1px solid var(--line);cursor:pointer}
header .gen.old{color:var(--warn);border-color:var(--warn)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px}
.card h2{font-size:15px;margin:0 0 4px;display:flex;align-items:center;gap:7px;font-weight:650}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:none}
.dot.ok{background:var(--ok);box-shadow:0 0 0 3px rgba(63,185,111,.18)}
.dot.warn{background:var(--warn);box-shadow:0 0 0 3px rgba(217,161,59,.18)}
.dot.bad{background:var(--bad);box-shadow:0 0 0 3px rgba(224,85,85,.18)}
.sub{font-size:12px;color:var(--dim);margin-bottom:8px}
.sub .mark{color:var(--accent)}
.big{display:flex;align-items:baseline;flex-wrap:wrap;gap:4px 10px;margin:6px 0 12px}
.big .eq{font-size:24px;font-weight:650;letter-spacing:-.3px}
.big .lbl{font-size:12px;color:var(--dim);font-weight:400;margin-right:4px;letter-spacing:0}
.big .u{font-size:13px;color:var(--dim);font-weight:400;margin-left:2px}
.upnl{font-size:13px;font-weight:600;padding:2px 8px;border-radius:999px;background:var(--line)}
.upnl.up{color:var(--up);background:var(--up-bg)} .upnl.down{color:var(--down);background:var(--down-bg)}
.up{color:var(--up)} .down{color:var(--down)}
.tbl{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}
.pos{width:100%;border-collapse:collapse;font-size:13px;margin:0 0 10px;table-layout:fixed}
.pos col.c0{width:21%} .pos col.c1{width:13%}
.pos th{color:var(--faint);font-weight:500;font-size:11.5px;text-align:right;padding:4px 3px 5px;border-bottom:1px solid var(--line);white-space:nowrap}
.pos td{text-align:right;padding:6px 3px;border-bottom:1px solid var(--line);white-space:nowrap}
.pos tr:last-child td{border-bottom:none}
.pos th:first-child,.pos td:first-child{text-align:left}
.pos th:first-child,.pos td:first-child{padding-left:0} .pos th:last-child,.pos td:last-child{padding-right:0}
.pos td:first-child{font-weight:600;letter-spacing:-0.4px}
.pos .mark{font-weight:500;font-size:.86em}
.pos .mark.long,.act.long{color:var(--up)} .pos .mark.short,.act.short{color:var(--down)}
.pos .miss{color:var(--bad)}
.sym{font-size:13px;padding:7px 0;border-bottom:1px solid var(--line);font-weight:600}
.sym:last-of-type{border-bottom:none}
.sym .v{color:var(--dim);font-weight:400}
.sym .mark{color:var(--accent)}
details.leg{margin-top:4px;padding-top:4px;border-top:1px dashed var(--line);font-size:11.5px;color:var(--dim)}
details.leg summary{cursor:pointer;color:var(--faint);user-select:none;padding:2px 0}
details.leg .lg{padding:4px 0 2px;line-height:1.55}
details.leg .lg b{color:var(--fg);font-weight:600}
.sec{font-size:11px;color:var(--faint);margin:4px 0 2px;letter-spacing:.3px}
.ev{display:flex;align-items:baseline;gap:8px;font-size:12.5px;color:var(--fg);padding:4px 0;border-top:1px dashed var(--line);white-space:nowrap}
.ev .t{color:var(--faint);flex:none;min-width:2.9em}
.ev .tx{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}
.ev .tx .q{color:var(--dim)}
.ev .pl{flex:none;font-weight:600}
.act{font-weight:600}
.perf{font-size:12px;color:var(--dim);margin-top:8px;padding-top:8px;border-top:1px solid var(--line)}
.banner{font-size:12px;border-radius:8px;padding:6px 9px;margin:6px 0}
.banner.err{background:rgba(224,85,85,.12);color:var(--bad)}
.banner.warn{background:rgba(217,161,59,.12);color:var(--warn)}
.links{display:flex;gap:10px;margin:14px 0 6px}
.links a{flex:1;text-align:center;background:transparent;border:1px solid var(--accent);border-radius:12px;padding:11px 0;color:var(--accent);text-decoration:none;font-size:14px;font-weight:600}
.links a:active{background:rgba(91,157,217,.12)}
.init{color:var(--dim);font-size:13px;padding:8px 0}
/* 窄屏（iPhone 竖屏）：7 列表格固定列宽在 390px 内放下，仍溢出就在卡内横滑，
   不让整页产生横向滚动（2026-11-02 用户反馈「破窗」）。 */
@media (max-width:480px){
  body{padding:8px;font-size:14px}
  .card{padding:12px 10px}
  .big .eq{font-size:22px}
  .pos{font-size:11px;letter-spacing:-0.3px}
  .pos th{padding:3px 1.5px 4px;font-size:10.5px;letter-spacing:0}
  .pos td{padding:5px 1.5px}
  .ev{font-size:12px;gap:6px}
  .sym{font-size:12px;letter-spacing:-0.2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
}
/* 更窄（iPhone SE/mini 360-375px）：再压一档，保证价格数字不溢出 */
@media (max-width:380px){
  .pos{font-size:10px;letter-spacing:-0.4px}
  .pos col.c0{width:21%} .pos col.c1{width:13%}
  .pos th{font-size:10px}
  .pos td{padding:5px 1px}
}
"""

_JS = (
    "try{if(location.search.indexOf('k=')>-1){history.replaceState(null,'',location.pathname)}}catch(e){}"
    # PWA 独立窗口无刷新按钮、iOS 禁用系统下拉刷新：
    # 1) 顶部下拉 >70px 或点「更新」胶囊 → fetch /api/fragment 局部替换卡片（复用连接，免整页 reload）
    # 2) 前台每 60s 自动静默刷新（与后台轮询同周期），切回前台且距上次 >45s 立即刷一次
    # 3) 页面超过 2 分钟未刷新，「更新」胶囊变琥珀提示
    ";(function(){var sy=0,pulling=false,busy=false,hint=document.querySelector('header .gen'),main=document.getElementById('cards');"
    "var ck=function(){if(!hint)return;var ts=+hint.dataset.ts||0;hint.classList.toggle('old',ts>0&&Date.now()/1000-ts>120);};"
    "var rf=function(manual){if(busy)return;busy=true;"
    "if(manual&&hint){hint.textContent='刷新中…';}"
    "fetch('/api/fragment'+location.search,{credentials:'same-origin',cache:'no-store'})"
    ".then(function(r){if(!r.ok)throw new Error(r.status);return r.json();})"
    ".then(function(d){if(main&&d.html){var open=[];main.querySelectorAll('details[open]').forEach(function(e,i){open.push(i);});"
    "main.innerHTML=d.html;main.querySelectorAll('details').forEach(function(e,i){if(open.indexOf(i)>-1)e.open=true;});}"
    "if(hint&&d.gen){hint.textContent='更新 '+d.gen;hint.dataset.t=hint.textContent;hint.dataset.ts=d.ts;ck();}busy=false;})"
    ".catch(function(){busy=false;if(manual)location.reload();});};"
    "document.addEventListener('touchstart',function(e){if(window.scrollY<=0){sy=e.touches[0].clientY;pulling=true;}},{passive:true});"
    "document.addEventListener('touchmove',function(e){if(!pulling)return;var dy=e.touches[0].clientY-sy;"
    "if(hint&&dy>40&&dy<=70){hint.textContent='松手刷新…';}"
    "if(dy>70&&window.scrollY<=0){pulling=false;rf(true);}},{passive:true});"
    "document.addEventListener('touchend',function(){pulling=false;if(hint&&!busy)hint.textContent=hint.dataset.t||hint.textContent;},{passive:true});"
    "if(hint){hint.dataset.t=hint.textContent;hint.addEventListener('click',function(){rf(true);});ck();"
    "setInterval(function(){ck();if(!document.hidden)rf(false);},60000);"
    "document.addEventListener('visibilitychange',function(){ck();if(!document.hidden&&hint&&Date.now()/1000-(+hint.dataset.ts||0)>45)rf(false);});}})();"
)

_HEAD_LINKS = (
    "<link rel='apple-touch-icon' href='/apple-touch-icon.png'>"
    "<link rel='icon' type='image/png' href='/favicon-32.png'>"
    "<link rel='manifest' href='/manifest.webmanifest'>"
)


def esc(v) -> str:
    return html.escape(str(v if v is not None else "—"))


def _fmt_money(v, nd: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.{nd}f}"
    except (TypeError, ValueError):
        return esc(v)


def _decimals_for_small(f: float, nd: int) -> int:
    """小数位不够时补位：0.0008 按 2 位会变成 0.00，看不出开了多少 / 亏了多少。

    只在「按 nd 位四舍五入后恰好为 0」时补到首个有效数字后两位（0.0008 → 4 位，
    0.00004 → 6 位），最多 10 位。正常大小的数以 nd 位原样显示，表格宽度不受影响。
    """
    if f == 0 or round(f, nd) != 0:
        return nd
    return min(int(-math.log10(abs(f))) + 2, 10)


def _fmt_num(f: float, nd: int) -> str:
    d = _decimals_for_small(f, nd)
    s = f"{f:,.{d}f}"
    return s.rstrip("0") if d > nd else s


def _fmt_signed(v, nd: int = 2, suffix: str = "") -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return esc(v)
    sign = "+" if f >= 0 else ""
    return f"{sign}{_fmt_num(f, nd)}{suffix}"


def _sign_cls(v) -> str:
    """盈亏着色：>0 up（绿）、<0 down（红）、0/缺数不着色。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    if f > 0:
        return "up"
    if f < 0:
        return "down"
    return ""


def _pnl_span(v, suffix: str = "") -> str:
    cls = _sign_cls(v)
    inner = _fmt_signed(v) + suffix
    return f'<span class="{cls}">{inner}</span>' if cls else inner


def _side_mark(side_text, extra: str = "") -> str:
    """持仓方向小标记：多绿空红（仓位方向，与成交行的开/平多空同色系）。"""
    t = str(side_text or "")
    cls = "long" if t.startswith("多") else ("short" if t.startswith("空") else "")
    return f"<span class='mark {cls}'>{esc(t)}{extra}</span>" if t else ""


def _fmt_pct(v, nd: int = 1) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v) * 100:.{nd}f}%"
    except (TypeError, ValueError):
        return esc(v)


def _fmt_time(ts, now_ts: float | None = None) -> str:
    if ts is None:
        return "—"
    try:
        t_bj = float(ts) + 8 * 3600
    except (TypeError, ValueError):
        return "—"
    hm = time.strftime("%H:%M", time.gmtime(t_bj))
    ref = float(now_ts) if now_ts is not None else time.time()
    day_diff = int((ref + 8 * 3600) // 86400) - int(t_bj // 86400)
    if day_diff == 0:
        return hm
    if day_diff == 1:
        return f"昨 {hm}"
    return time.strftime("%m-%d %H:%M", time.gmtime(t_bj))


def _fmt_age(age_s) -> str:
    if age_s is None:
        return ""
    try:
        s = float(age_s)
    except (TypeError, ValueError):
        return ""
    if s < 90:
        return f"{int(s)} 秒前"
    if s < 5400:
        return f"{int(s // 60)} 分钟前"
    return f"{s / 3600:.1f} 小时前"


def _dot_class(entry: dict | None) -> str:
    if entry is None:
        return "warn"
    if not entry.get("ok"):
        return "bad"
    if entry.get("stale"):
        return "warn"
    data = entry.get("data") or {}
    if data.get("kill"):
        return "warn"
    return "ok"


def _held_text(side) -> str | None:
    """持仓方向标记：HL position_side 用 "long"/"short"，LT held_side 用 1/-1。"""
    if side in (1, "1"):
        return "多"
    if side in (-1, "-1", "short"):
        return "空"
    if side == "long":
        return "多"
    return None


def _stop_cell(covered: bool, price) -> str:
    """止损列只放价格（加标记会把行顶成两行）；缺止损才红字提示。"""
    if covered:
        return _fmt_px(price)
    return "<span class='miss'>无</span>"


def _sub_line(bits: list[str]) -> str:
    parts = [b for b in bits if b]
    return f'<div class="sub">{" · ".join(parts)}</div>' if parts else ""


def _mr_upnl(entry: dict | None):
    """MR 腿（QQQ）的浮盈。只用于 HL 卡：HL 面板的 `account.unrealized_pnl`
    不含 xyz 子账户（实测 8.7645 == 主 dex 仓位和，缺 QQQ 的 -1.96）。
    LT 的 `/positions` 已含 QQQ 行（面板 PR #62 起），hub 端 sum 即正确，
    **不要再加这一笔**，否则重复计算。"""
    pos = ((entry or {}).get("data") or {}).get("mr") or {}
    return (pos.get("pos") or {}).get("upnl")


def _total_upnl(base, mr_upnl):
    """卡头浮盈 = 面板聚合 + MR 腿。两个来源都缺才不渲染。"""
    vals = [float(v) for v in (base, mr_upnl) if v is not None]
    try:
        return sum(vals) if vals else None
    except (TypeError, ValueError):
        return None


def _equity_line(equity, upnl) -> str:
    upnl_html = ""
    if upnl is not None:
        upnl_html = f'<span class="upnl {_sign_cls(upnl)}">浮盈 {_fmt_signed(upnl)} U</span>'
    return (f'<div class="big"><span class="eq"><span class="lbl">权益</span>{_fmt_money(equity)}'
            f'<span class="u">U</span></span>{upnl_html}</div>')


def _mr_position_row(entry: dict | None) -> str | None:
    """MR 腿（QQQ）的持仓行 —— 有仓才出现，止损列写「—」（这条腿按设计不挂止损）。

    HL 的 QQQ 在 xyz dex 子账户里，`positions[]`（主 dex）看不到它；聚合页此前因此
    显示「当前空仓」。数据取 `status.mr.pos`（两侧同名同义）。
    """
    mr = (entry or {}).get("mr") or {}
    pos = mr.get("pos") or {}
    if not pos:
        return None
    exit_px = pos.get("exit_line") or (mr.get("signal") or {}).get("exit_line")
    return (
        f"<tr><td>QQQ·NDX {_side_mark('多')}</td>"
        f"<td>{_fmt_qty(pos.get('qty'))}</td>"
        f"<td>{_fmt_px(pos.get('entry_price'))}</td>"
        f"<td>{_fmt_px(pos.get('mark'))}</td>"
        f"<td>{_pnl_span(pos.get('upnl'))}</td>"
        f"<td>{_fmt_px(exit_px)}</td>"
        "<td>—</td></tr>"
    )


def _fmt_qty(v) -> str:
    """数量：<1 保留 4 位（0.0087 显示成 0.01 会让人以为仓大了一倍）。

    再小到 4 位也只剩 0 的（QQQ 这类高价标的单笔只有 0.0008）按首个有效数字补位，
    否则成交行会出现「开多 0.00 @ 28,579.00」这种看不出开了多少的写法。
    """
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _fmt_money(v)
    return _fmt_num(f, 2 if abs(f) >= 1 else 4)


def _fmt_px(v) -> str:
    """仓位表里的价格：≥1000 只留整数位（28,579.90 → 28,580），窄屏靠这个把表压进一屏。

    只用于**表格显示**，不改任何计算值；<1000 的（BTC 跌到三位、SOL 等）仍保留两位小数。
    """
    f = None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _fmt_money(v)
    if f >= 1000:
        return f"{f:,.0f}"
    return _fmt_money(f)


_POS_HEAD = (
    '<div class="tbl"><table class="pos"><colgroup><col class="c0"><col class="c1"><col><col><col><col><col></colgroup>'
    "<tr><th>标的</th><th>数量</th><th>入场</th><th>现价</th><th>浮盈U</th><th>离场</th><th>止损</th></tr>"
)


def _positions_table(rows: list[str]) -> str:
    """两卡共用一张表结构：固定列宽（table-layout:fixed），上下两卡列对齐可竖着比。"""
    return _POS_HEAD + "".join(rows) + "</table></div>"


_positions_table_hl = _positions_table
_positions_table_lt = _positions_table


_HL_DIR = {
    "Open Short": "开空",
    "Close Short": "平空",
    "Open Long": "开多",
    "Close Long": "平多",
}


def _hl_fill_lines(fills: list, n: int = 3, now_ts: float | None = None) -> list[str]:
    lines = []
    for f in (fills or [])[:n]:
        act = _HL_DIR.get(f.get("dir") or "", f.get("dir") or "—")
        pnl = None
        if str(f.get("dir") or "").startswith("Close") and f.get("closed_pnl") is not None:
            pnl = f.get("closed_pnl")
        lines.append(_trade_line(f.get("ts"), f.get("coin"), act, f.get("sz"), f.get("px"), pnl, now_ts=now_ts))
    return _trades_block(lines)


def _trade_line(ts, sym, act: str, qty, px, pnl, now_ts: float | None = None) -> str:
    """成交行：时间 | 标的 + 开/平多空（多绿空红）+ 数量 @ 价 | 平仓腿盈亏右对齐着色。"""
    cls = "long" if act.endswith("多") else ("short" if act.endswith("空") else "")
    pl = ""
    if pnl is not None:
        pl = f'<span class="{("pl " + _sign_cls(pnl)).strip()}">{_fmt_signed(pnl)} U</span>'
    return (
        f'<div class="ev"><span class="t">{_fmt_time(ts, now_ts)}</span>'
        f'<span class="tx">{esc(sym)} <span class="act {cls}">{esc(act)}</span> '
        f'<span class="q">{_fmt_qty(qty)} @ {_fmt_money(px)}</span></span>{pl}</div>'
    )


def _trades_block(lines: list[str]) -> list[str]:
    head = '<div class="sec">最近成交</div>'
    return [head] + (lines or ['<div class="ev"><span class="tx">暂无成交</span></div>'])


def _lt_trade_lines(trades: list, n: int = 3, now_ts: float | None = None) -> list[str]:
    lines = []
    for t in (trades or [])[:n]:
        is_exit = t.get("kind_text") == "离场"
        # LT 的 side_text 是成交方向；离场腿显示的是被平的仓位方向（平空=买入），
        # 与 HL 的 "Close Short" 同语义，需取反
        side = t.get("side_text") or ""
        if is_exit:
            side = {"多": "空", "空": "多"}.get(side, side)
        act = ("平" if is_exit else "开") + str(side)
        pnl = None
        if is_exit and t.get("realized_pnl") is not None:
            pnl = t.get("realized_pnl")
        lines.append(_trade_line(t.get("ts"), t.get("symbol"), act, t.get("qty"), t.get("price"), pnl, now_ts=now_ts))
    return _trades_block(lines)


_LEGEND_HTML = (
    '<details class="leg"><summary>图例说明</summary><div class="lg">'
    "<div><b>K线密集 x/6</b>：近 6 根 4h K 线均线带宽达标的根数（满 6 根允许突破入场）</div>"
    "<div><b>轨道距离 / 越线</b>：现价距上/下突破触发线的百分比；已越过触发线显示为越线幅度</div>"
    "<div><b>RSI2 均值回归</b>：QQQ 日线超跌反弹独立策略（HL 仓位用 QQQ·NDX 纳指100指数口径）</div>"
    "</div></details>"
)


def _symbols_card(hl_entry: dict | None, lt_entry: dict | None) -> str:
    """三标的动态合并卡：两边策略同源，只渲染一份。

    整合两侧优点——价格/密集取较新的一边；距上/下轨是 HL 独有信息，优先展示；
    HL 缺数时退回 LT 的 verdict 文案；持仓标记两边合并、同向去重。
    """
    hl_ok = bool(hl_entry and hl_entry.get("ok"))
    lt_ok = bool(lt_entry and lt_entry.get("ok"))
    hl_syms = {
        s.get("coin"): s for s in ((hl_entry or {}).get("data") or {}).get("symbols") or []
    } if hl_ok else {}
    lt_syms = {
        str(s.get("symbol") or "").split("_")[0]: s
        for s in ((lt_entry or {}).get("data") or {}).get("symbols") or []
    } if lt_ok else {}
    order = list(hl_syms) + [c for c in lt_syms if c not in hl_syms]
    if hl_ok and lt_ok:
        base_is_hl = (hl_entry.get("as_of") or 0) >= (lt_entry.get("as_of") or 0)
    else:
        base_is_hl = hl_ok
    lines = []
    for coin in order:
        h, l = hl_syms.get(coin), lt_syms.get(coin)
        price = ((h if base_is_hl else l) or h or l).get("price")
        # 密集：基准侧有数就用，没有落到另一侧
        if h and h.get("dense_cnt") is not None:
            dense = f"{esc(h.get('dense_cnt'))}/6"
        elif l and l.get("dense_bars") is not None:
            dense = f"{esc(l.get('dense_bars'))}/{esc(l.get('min_dense_bars'))}"
        else:
            dense = "—/6"
        marks = []
        hh = _held_text(h.get("position_side")) if h else None
        lh = _held_text(l.get("held_side")) if l else None
        if hh and lh and hh == lh:
            marks.append(f"持仓{hh}（HL·LT）")
        else:
            if hh:
                marks.append(f"持仓{hh}（HL）")
            if lh:
                marks.append(f"持仓{lh}（LT）")
        # 持仓标的不评估入场，密集/触发线无意义（面板置 NULL）→ 显示「持仓中」
        held = bool(hh or lh)
        # verdict 已含「持仓」时不再显示，避免「持仓中 · 持仓空（HL·LT）」
        verdict = l.get("verdict") if l else None
        if verdict and ("持仓" in str(verdict)):
            verdict = None
        if held:
            dense_part = "持仓中"
        else:
            dense_part = f"密集 {dense}"
        if not held and h and h.get("long_trigger") is not None and h.get("short_trigger") is not None:
            tail = _format_breakout_track(h.get("price"), h.get("long_trigger"), h.get("short_trigger"))
        elif verdict:
            tail = f" · {esc(verdict)}"
        else:
            tail = ""
        held_html = "".join(f' · <span class="mark">{esc(m)}</span>' for m in marks)
        lines.append(
            f'<div class="sym">{esc(coin)} <span class="v">{_fmt_money(price)} · {dense_part}{tail}{held_html}</span></div>'
        )
    mr_line, _src = _mr_line(hl_entry, lt_entry)
    if not lines and not mr_line:
        return ""
    return ('<div class="card"><h2>标的动态</h2>'
            + "".join(lines) + mr_line + _LEGEND_HTML + "</div>")


def _mr_line(hl_entry: dict | None, lt_entry: dict | None) -> tuple[str, str | None]:
    """超跌腿（QQQ）一行：两所**同一信号口径** → 只渲染一份，HL 优先。

    为什么只渲染一份：两边跑的是同一个 RSI2 策略、同一个信号日，并排两行会让人
    以为抓到了两个仓位。取 HL 的理由是它的 MR tick 是 5 分钟一次（LT 是 30 分钟）。
    """
    for entry, src in ((hl_entry, "HL"), (lt_entry, "LT")):
        if not entry or not entry.get("ok"):
            continue
        mr = (entry.get("data") or {}).get("mr") or {}
        pos = mr.get("pos") or {}
        if not mr or (not mr.get("enabled") and not pos):
            continue
        return _render_mr(mr, src), src
    return "", None


def _render_mr(mr: dict, src: str) -> str:
    """MR 一行（标的动态）：空仓时回答「离开仓有多远」（现价 · RSI2/阈值 · 等什么）；
    持仓时只留状态——现价/浮盈/离场线/距离场都在仓位表那行，再渲染一遍会被读成两份账
    （2026-11-02 用户指出与仓位表重复）。"""
    pos = mr.get("pos") or {}
    sig = mr.get("signal") or {}
    holding = bool(pos)
    parts = []
    if str(mr.get("recon") or "") == "err":
        status = "对账不平"
    elif holding:
        status = "持仓中"
    elif not mr.get("enabled"):
        status = "停用"
    else:
        mark = mr.get("mark")
        if mark is not None:
            parts.append(f"现价 {_fmt_money(mark)}")
        rsi = sig.get("rsi2")
        thr = sig.get("threshold")
        if rsi is not None:
            try:
                ok = thr is not None and float(rsi) < float(thr)
                tail = f" / 阈 {float(thr):g}" if thr is not None else ""
                parts.append(f"RSI2 {float(rsi):.2f}{tail}{' ✔' if ok else ''}")
            except (TypeError, ValueError):
                parts.append(f"RSI2 {esc(rsi)}")
        phase = str(sig.get("phase") or "")
        status = {"in_window": "窗口内等成交", "signal_ready": "等开盘",
                  "expired": "窗口已过", "no_signal": "空仓"}.get(phase, "空仓")
    body = " · ".join(parts)
    if body:
        return (f'<div class="sym">QQQ <span class="v">{body} · {esc(status)}'
                f' · <span class="mark">超跌腿·{esc(src)}</span></span></div>')
    return (f'<div class="sym">QQQ <span class="v">{esc(status)}'
            f' · <span class="mark">超跌腿·{esc(src)}</span></span></div>')


def _card_head(title: str, entry: dict | None, body: str) -> str:
    return f'<div class="card"><h2><span class="dot {_dot_class(entry)}"></span>{title}</h2>{body}</div>'


def _init_card(title: str) -> str:
    return _card_head(title, None, '<div class="init">等待第一轮拉取…</div>')


def _error_card(title: str, entry: dict) -> str:
    return _card_head(
        title, entry, f'<div class="banner err">不可用：{esc(entry.get("error"))}</div>'
    )


def _stale_banner(entry: dict) -> str:
    if entry.get("stale"):
        return f'<div class="banner warn">数据 {_fmt_age(entry.get("age_s"))}未刷新</div>'
    return ""


def _dist_pct(price, trigger) -> float | None:
    try:
        p, t = float(price), float(trigger)
    except (TypeError, ValueError):
        return None
    if p == 0:
        return None
    return (t - p) / p


def _format_breakout_track(price, long_trigger, short_trigger) -> str:
    """按方案 A 格式化多空轨道距离（紧凑文案以保证手机窄屏单行不折行）：

    - 破位/越过：破上 +x.x% / 破下 -y.y%
    - 距离：距多 +x.x% / 距空 -y.y%
    """
    try:
        p = float(price)
        t_long = float(long_trigger)
        t_short = float(short_trigger)
    except (TypeError, ValueError):
        return ""
    if p == 0:
        return ""

    if p >= t_long:
        dl_str = f"破上 +{(p / t_long - 1) * 100:.1f}%"
    else:
        dl_str = f"距多 +{(t_long / p - 1) * 100:.1f}%"

    if p <= t_short:
        ds_str = f"破下 -{(1 - p / t_short) * 100:.1f}%"
    else:
        ds_str = f"距空 -{(1 - t_short / p) * 100:.1f}%"

    return f" · {dl_str} · {ds_str}"


def _hl_card(entry: dict | None, now_ts: float | None = None) -> str:
    if entry is None:
        return _init_card("Hyperliquid")
    if not entry.get("ok"):
        return _error_card("Hyperliquid", entry)
    d = entry.get("data") or {}
    body: list[str] = [_stale_banner(entry)]

    positions = d.get("positions") or []
    if positions:
        stops = (
            "<span class='mark'>✔</span>"
            if all(p.get("has_stop") for p in positions)
            else "<span class='miss'>⚠ 止损缺口</span>"
        )
    else:
        stops = ""
    fresh = _fmt_age(
        max(0.0, time.time() - float(d["last_event_ts"])) if d.get("last_event_ts") else None
    )
    bits = [f"模式 {esc(d.get('mode') or '—')}"]
    if d.get("kill"):
        bits.append(f'<span style="color:var(--bad)">已 kill（{esc(d.get("kill_reason"))}）</span>')
    if stops:
        bits.append(f"止损 {stops}")
    if fresh:
        bits.append(f"tick {fresh}")
    if d.get("agent_days_left") is not None:
        bits.append(f"API 剩 {esc(d['agent_days_left'])} 天")
    if d.get("feed_ok") is False:
        bits.append('<span style="color:var(--warn)">数据源异常</span>')
    body.append(_sub_line(bits))
    body.append(_equity_line(d.get("equity"),
                             _total_upnl(d.get("unrealized_pnl"), _mr_upnl(entry))))

    if positions:
        rows = []
        for p in positions:
            side = "多" if p.get("side") == 1 else ("空" if p.get("side") == -1 else "—")
            rows.append(
                f"<tr><td>{esc(p.get('coin'))} {_side_mark(side)}</td>"
                f"<td>{_fmt_qty(p.get('size'))}</td>"
                f"<td>{_fmt_px(p.get('entry_px'))}</td>"
                f"<td>{_fmt_px(p.get('mark_px'))}</td>"
                f"<td>{_pnl_span(p.get('unrealized_pnl'))}</td>"
                f"<td>{_fmt_px(p.get('exit_px'))}</td>"
                f"<td>{_stop_cell(bool(p.get('has_stop')), p.get('stop_px'))}</td></tr>"
            )
        mr_row = _mr_position_row(d)
        if mr_row:
            rows.append(mr_row)
        body.append(_positions_table_hl(rows))
    else:
        mr_row = _mr_position_row(d)
        if mr_row:
            body.append(_positions_table_hl([mr_row]))
        else:
            body.append('<div class="sub">当前空仓</div>')

    body += _hl_fill_lines(d.get("fills"), now_ts=now_ts)

    perf = d.get("perf") or {}
    if perf.get("n"):
        body.append(
            f'<div class="perf">实盘 {esc(perf.get("n"))} 笔 · 胜率 {_fmt_pct(perf.get("win_rate"))}'
            f' · 均R {_pnl_span(perf.get("avg_r"))} · 总R {_pnl_span(perf.get("total_r"))}</div>'
        )
    return _card_head("Hyperliquid", entry, "".join(body))


def _lt_card(entry: dict | None, now_ts: float | None = None) -> str:
    if entry is None:
        return _init_card("Lighter")
    if not entry.get("ok"):
        return _error_card("Lighter", entry)
    d = entry.get("data") or {}
    body: list[str] = [_stale_banner(entry)]

    positions = d.get("positions") or []
    if d.get("stops_all_protected") is True:
        stops = "<span class='mark'>✔</span>"
    elif d.get("stops_all_protected") is False:
        stops = "<span class='miss'>⚠ 止损未全覆盖</span>"
    else:
        stops = "<span class='miss'>⚠ 读数降级</span>"
    bits = [f"模式 {esc(d.get('mode') or '—')}"]
    if d.get("kill"):
        bits.append(f'<span style="color:var(--bad)">已 kill（{esc(d.get("kill_reason"))}）</span>')
    bits.append(f"止损 {stops}")
    fresh = _fmt_age(d.get("last_tick_age_s"))
    if fresh:
        bits.append(f"tick {fresh}")
    if d.get("dd") is not None:
        bits.append(f"回撤 {_fmt_pct(d.get('dd'))}")
    for part in d.get("degraded_parts") or []:
        bits.append(f'<span style="color:var(--warn)">⚠ {esc(part.split(":", 1)[0])}</span>')
    body.append(_sub_line(bits))

    upnl = None
    if positions:
        try:
            upnl = sum(float(p.get("upnl") or 0) for p in positions)
        except (TypeError, ValueError):
            upnl = None
    body.append(_equity_line(d.get("equity"), upnl))

    if positions:
        rows = []
        for p in positions:
            rows.append(
                f"<tr><td>{esc(p.get('symbol'))} {_side_mark(p.get('side_text'))}</td>"
                f"<td>{_fmt_qty(p.get('qty'))}</td>"
                f"<td>{_fmt_px(p.get('entry_price'))}</td>"
                f"<td>{_fmt_px(p.get('price'))}</td>"
                f"<td>{_pnl_span(p.get('upnl'))}</td>"
                f"<td>{_fmt_px(p.get('exit_price'))}</td>"
                f"<td>{'—' if p.get('no_stop') else _stop_cell(bool(p.get('stop_price')), p.get('stop_price'))}</td></tr>"
            )
        body.append(_positions_table_lt(rows))
    else:
        body.append('<div class="sub">当前空仓</div>')

    body += _lt_trade_lines(d.get("trades"), now_ts=now_ts)
    perf = d.get("perf") or {}
    if perf.get("n"):
        body.append(
            f'<div class="perf">结单 {esc(perf.get("n"))} 笔 · 胜率 {_fmt_pct(perf.get("win_rate"))}'
            f' · 累计平仓 {_pnl_span(perf.get("realized_total"), " U")}</div>'
        )
    return _card_head("Lighter", entry, "".join(body))


def render_cards_fragment(summary: dict) -> dict:
    """局部刷新接口返回的数据包：三张卡片 HTML 片段 + 头部时间文本与时间戳。"""
    now_ts = summary.get("generated_at", time.time())
    gen = time.strftime("%H:%M:%S", time.gmtime(now_ts + 8 * 3600))
    cards_html = (
        _hl_card(summary.get("hl"), now_ts=now_ts)
        + _lt_card(summary.get("lt"), now_ts=now_ts)
        + _symbols_card(summary.get("hl"), summary.get("lt"))
    )
    return {"ts": int(now_ts), "gen": gen, "html": cards_html}


def render_page(summary: dict, hl_panel_url: str, lt_panel_url: str) -> str:
    frag = render_cards_fragment(summary)
    return (
        "<!doctype html><html lang='zh'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='apple-mobile-web-app-capable' content='yes'>"
        "<meta name='apple-mobile-web-app-title' content='trade-hub'>"
        "<meta name='theme-color' content='#0f1216'>"
        "<title>trade-hub</title>"
        f"{_HEAD_LINKS}"
        f"<style>{_CSS}</style></head><body>"
        f"<header><h1>trade-hub</h1><span class='gen' data-ts='{frag['ts']}'>更新 {frag['gen']}</span></header>"
        f"<main id='cards'>{frag['html']}</main>"
        + f"<nav class='links'><a href='{html.escape(hl_panel_url, quote=True)}'>打开 HL 面板</a>"
        + f"<a href='{html.escape(lt_panel_url, quote=True)}'>打开 Lighter 面板</a></nav>"
        + f"<script>{_JS}</script></body></html>"
    )
