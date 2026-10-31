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
import time

_STALE_WARN_S = 600  # data older than 10 min gets an amber banner even if ok

_CSS = """
:root{
  --bg:#12151a; --card:#1a1f27; --line:#2a323d; --fg:#e8ecf1; --dim:#8b97a5;
  --ok:#3fb96f; --warn:#d9a13b; --bad:#e05555; --accent:#5b9dd9; --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  color-scheme: dark light;
}
@media (prefers-color-scheme: light){
  :root{ --bg:#f5f7fa; --card:#ffffff; --line:#dde3ea; --fg:#1c2430; --dim:#62707f; }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Noto Sans CJK SC",sans-serif;padding:12px;overscroll-behavior-y:contain}
header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px}
header h1{font-size:17px;margin:0}
header .gen{font-size:12px;color:var(--dim)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:12px}
.card h2{font-size:15px;margin:0 0 6px;display:flex;align-items:center;gap:7px}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block;flex:none}
.dot.ok{background:var(--ok)} .dot.warn{background:var(--warn)} .dot.bad{background:var(--bad)}
.sub{font-size:12px;color:var(--dim);margin-bottom:8px}
.big{font-family:var(--mono);font-size:19px;margin:2px 0 10px}
.big .upnl{font-size:13px;margin-left:8px}
.pos{width:100%;border-collapse:collapse;font-size:13px;margin:6px 0 10px}
.pos th{color:var(--dim);font-weight:500;text-align:right;padding:3px 4px;border-bottom:1px solid var(--line)}
.pos td{text-align:right;padding:4px;font-family:var(--mono);border-bottom:1px solid var(--line)}
.pos th:first-child,.pos td:first-child{text-align:left}
.pos td:first-child{font-family:inherit}
.pos .mark{color:var(--ok)}
.pos .miss{color:var(--bad)}
.sym{font-size:13px;padding:5px 0;border-bottom:1px solid var(--line)}
.sym:last-child{border-bottom:none}
.sym .v{color:var(--dim)}
.sym .mark{color:var(--accent)}
.ev{font-size:12px;color:var(--dim);padding:3px 0;overflow-wrap:anywhere}
.ev .t{font-family:var(--mono);margin-right:6px}
.banner{font-size:12px;border-radius:6px;padding:6px 8px;margin:6px 0}
.banner.err{background:rgba(224,85,85,.12);color:var(--bad)}
.banner.warn{background:rgba(217,161,59,.12);color:var(--warn)}
.links{display:flex;gap:10px;margin:14px 0}
.links a{flex:1;text-align:center;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px 0;color:var(--fg);text-decoration:none;font-size:14px}
.init{color:var(--dim);font-size:13px;padding:8px 0}
"""

_JS = (
    "try{if(location.search.indexOf('k=')>-1){history.replaceState(null,'',location.pathname)}}catch(e){}"
    # PWA 独立窗口没有刷新按钮、iOS 禁用系统下拉刷新——自己实现：顶部下拉 >70px 重新加载，
    # 点「更新」时间也能刷新
    ";(function(){var sy=0,pulling=false,hint=document.querySelector('header .gen');"
    "document.addEventListener('touchstart',function(e){if(window.scrollY<=0){sy=e.touches[0].clientY;pulling=true;}},{passive:true});"
    "document.addEventListener('touchmove',function(e){if(!pulling)return;var dy=e.touches[0].clientY-sy;"
    "if(hint&&dy>40&&dy<=70){hint.textContent='松手刷新…';}"
    "if(dy>70&&window.scrollY<=0){pulling=false;location.reload();}},{passive:true});"
    "document.addEventListener('touchend',function(){pulling=false;if(hint)hint.textContent=hint.dataset.t||hint.textContent;},{passive:true});"
    "if(hint){hint.dataset.t=hint.textContent;hint.addEventListener('click',function(){location.reload();});}})();"
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


def _fmt_signed(v, nd: int = 2, suffix: str = "") -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return esc(v)
    sign = "+" if f >= 0 else ""
    return f"{sign}{f:,.{nd}f}{suffix}"


def _fmt_pct(v, nd: int = 1) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v) * 100:.{nd}f}%"
    except (TypeError, ValueError):
        return esc(v)


def _fmt_time(ts) -> str:
    if ts is None:
        return "—"
    try:
        return time.strftime("%H:%M", time.gmtime(float(ts) + 8 * 3600))
    except (TypeError, ValueError):
        return "—"


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
        return _fmt_money(price)
    return "<span class='miss'>无</span>"


def _sub_line(bits: list[str]) -> str:
    parts = [b for b in bits if b]
    return f'<div class="sub">{" · ".join(parts)}</div>' if parts else ""


def _equity_line(equity, upnl) -> str:
    upnl_html = ""
    if upnl is not None:
        upnl_html = f'<span class="upnl">浮盈 {_fmt_signed(upnl)} U</span>'
    return f'<div class="big">权益 {_fmt_money(equity)} U{upnl_html}</div>'


def _positions_table_hl(rows: list[str]) -> str:
    return (
        '<table class="pos"><tr><th>标的</th><th>数量</th><th>入场</th><th>现价</th><th>浮盈U</th><th>离场</th><th>止损</th></tr>'
        + "".join(rows)
        + "</table>"
    )


def _positions_table_lt(rows: list[str]) -> str:
    return (
        '<table class="pos"><tr><th>标的</th><th>数量</th><th>入场</th><th>现价</th><th>浮盈U</th><th>离场</th><th>止损</th></tr>'
        + "".join(rows)
        + "</table>"
    )


_HL_DIR = {
    "Open Short": "开空",
    "Close Short": "平空",
    "Open Long": "开多",
    "Close Long": "平多",
}


def _hl_fill_lines(fills: list, n: int = 3) -> list[str]:
    lines = []
    for f in (fills or [])[:n]:
        act = _HL_DIR.get(f.get("dir") or "", f.get("dir") or "—")
        pnl = ""
        if str(f.get("dir") or "").startswith("Close") and f.get("closed_pnl") is not None:
            pnl = f"（{_fmt_signed(f.get('closed_pnl'))} U）"
        lines.append(
            f'<div class="ev"><span class="t">{_fmt_time(f.get("ts"))}</span>'
            f"{esc(f.get('coin'))} {esc(act)} {_fmt_money(f.get('sz'))} @ {_fmt_money(f.get('px'))}{pnl}</div>"
        )
    return lines or ['<div class="ev">暂无成交</div>']


def _lt_trade_lines(trades: list, n: int = 3) -> list[str]:
    lines = []
    for t in (trades or [])[:n]:
        is_exit = t.get("kind_text") == "离场"
        # LT 的 side_text 是成交方向；离场腿显示的是被平的仓位方向（平空=买入），
        # 与 HL 的 "Close Short" 同语义，需取反
        side = t.get("side_text") or ""
        if is_exit:
            side = {"多": "空", "空": "多"}.get(side, side)
        act = ("平" if is_exit else "开") + esc(side)
        pnl = ""
        if t.get("kind_text") == "离场" and t.get("realized_pnl") is not None:
            pnl = f"（{_fmt_signed(t.get('realized_pnl'))} U）"
        lines.append(
            f'<div class="ev"><span class="t">{_fmt_time(t.get("ts"))}</span>'
            f"{esc(t.get('symbol'))} {act} {_fmt_money(t.get('qty'))} @ {_fmt_money(t.get('price'))}{pnl}</div>"
        )
    return lines or ['<div class="ev">暂无成交</div>']


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
    if not order:
        return ""
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
            dl = _fmt_pct(_dist_pct(h.get("price"), h.get("long_trigger")))
            ds = _fmt_pct(_dist_pct(h.get("price"), h.get("short_trigger")))
            tail = f" · 距上轨 {dl} · 距下轨 {ds}"
        elif verdict:
            tail = f" · {esc(verdict)}"
        else:
            tail = ""
        held_html = "".join(f' · <span class="mark">{esc(m)}</span>' for m in marks)
        lines.append(
            f'<div class="sym">{esc(coin)} <span class="v">{_fmt_money(price)} · {dense_part}{tail}{held_html}</span></div>'
        )
    return '<div class="card"><h2>三标的动态</h2>' + "".join(lines) + "</div>"


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


def _hl_card(entry: dict | None) -> str:
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
    body.append(_equity_line(d.get("equity"), d.get("unrealized_pnl")))

    if positions:
        rows = []
        for p in positions:
            side = "多" if p.get("side") == 1 else ("空" if p.get("side") == -1 else "—")
            rows.append(
                f"<tr><td>{esc(p.get('coin'))} {side}</td>"
                f"<td>{_fmt_money(p.get('size'))}</td>"
                f"<td>{_fmt_money(p.get('entry_px'))}</td>"
                f"<td>{_fmt_money(p.get('mark_px'))}</td>"
                f"<td>{_fmt_signed(p.get('unrealized_pnl'))}</td>"
                f"<td>{_fmt_money(p.get('exit_px'))}</td>"
                f"<td>{_stop_cell(bool(p.get('has_stop')), p.get('stop_px'))}</td></tr>"
            )
        body.append(_positions_table_hl(rows))
    else:
        body.append('<div class="sub">当前空仓</div>')

    body += _hl_fill_lines(d.get("fills"))

    perf = d.get("perf") or {}
    if perf.get("n"):
        body.append(
            f'<div class="sub" style="margin-top:6px">实盘 {esc(perf.get("n"))} 笔 · 胜率 {_fmt_pct(perf.get("win_rate"))} · 均R {_fmt_signed(perf.get("avg_r"))} · 总R {_fmt_signed(perf.get("total_r"))}</div>'
        )
    return _card_head("Hyperliquid", entry, "".join(body))


def _lt_card(entry: dict | None) -> str:
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
                f"<tr><td>{esc(p.get('symbol'))} {esc(p.get('side_text'))}</td>"
                f"<td>{_fmt_money(p.get('qty'))}</td>"
                f"<td>{_fmt_money(p.get('entry_price'))}</td>"
                f"<td>{_fmt_money(p.get('price'))}</td>"
                f"<td>{_fmt_signed(p.get('upnl'))}</td>"
                f"<td>{_fmt_money(p.get('exit_price'))}</td>"
                f"<td>{_stop_cell(bool(p.get('stop_price')), p.get('stop_price'))}</td></tr>"
            )
        body.append(_positions_table_lt(rows))
    else:
        body.append('<div class="sub">当前空仓</div>')

    body += _lt_trade_lines(d.get("trades"))
    return _card_head("Lighter", entry, "".join(body))


def render_page(summary: dict, hl_panel_url: str, lt_panel_url: str) -> str:
    gen = time.strftime("%H:%M:%S", time.gmtime(summary.get("generated_at", time.time()) + 8 * 3600))
    return (
        "<!doctype html><html lang='zh'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='apple-mobile-web-app-capable' content='yes'>"
        "<meta name='apple-mobile-web-app-title' content='trade-hub'>"
        "<meta name='theme-color' content='#12151a'>"
        "<title>trade-hub</title>"
        f"{_HEAD_LINKS}"
        f"<style>{_CSS}</style></head><body>"
        f"<header><h1>trade-hub</h1><span class='gen'>更新 {gen}</span></header>"
        + _hl_card(summary.get("hl"))
        + _lt_card(summary.get("lt"))
        + _symbols_card(summary.get("hl"), summary.get("lt"))
        + f"<nav class='links'><a href='{html.escape(hl_panel_url, quote=True)}'>打开 HL 面板</a>"
        + f"<a href='{html.escape(lt_panel_url, quote=True)}'>打开 Lighter 面板</a></nav>"
        + f"<script>{_JS}</script></body></html>"
    )
