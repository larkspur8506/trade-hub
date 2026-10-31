"""Server-rendered mobile-first HTML. Self-contained: no CDN, no external assets.

Theme follows the system (dark default + prefers-color-scheme light), same
convention as the two source panels — no theme toggle by design.
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
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Noto Sans CJK SC",sans-serif;padding:12px}
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
.sym{font-size:13px;padding:5px 0;border-bottom:1px solid var(--line)}
.sym:last-child{border-bottom:none}
.sym .v{color:var(--dim)}
.ev{font-size:12px;color:var(--dim);padding:3px 0;overflow-wrap:anywhere}
.ev .t{font-family:var(--mono);margin-right:6px}
.banner{font-size:12px;border-radius:6px;padding:6px 8px;margin:6px 0}
.banner.err{background:rgba(224,85,85,.12);color:var(--bad)}
.banner.warn{background:rgba(217,161,59,.12);color:var(--warn)}
.links{display:flex;gap:10px;margin:14px 0}
.links a{flex:1;text-align:center;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px 0;color:var(--fg);text-decoration:none;font-size:14px}
.init{color:var(--dim);font-size:13px;padding:8px 0}
"""

_JS = "try{if(location.search.indexOf('k=')>-1){history.replaceState(null,'',location.pathname)}}catch(e){}"


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
        return time.strftime("%H:%M", time.gmtime(float(ts)))
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


def _hl_card(entry: dict | None) -> str:
    head = '<div class="card"><h2><span class="dot {cls}"></span>Hyperliquid</h2>{body}</div>'
    if entry is None:
        return head.format(cls="warn", body='<div class="init">等待第一轮拉取…</div>')
    if not entry.get("ok"):
        return head.format(
            cls="bad",
            body=f'<div class="banner err">不可用：{esc(entry.get("error"))}</div>',
        )
    d = entry.get("data") or {}
    body: list[str] = []
    if entry.get("stale"):
        body.append(f'<div class="banner warn">数据 {_fmt_age(entry.get("age_s"))}未刷新</div>')
    bits = [f"模式 {esc(d.get('mode') or '—')}"]
    if d.get("kill"):
        bits.append(f'<span style="color:var(--bad)">已 kill（{esc(d.get("kill_reason"))}）</span>')
    if d.get("feed_ok") is False:
        bits.append('<span style="color:var(--warn)">数据源异常</span>')
    if d.get("agent_days_left") is not None:
        bits.append(f"API 剩 {esc(d['agent_days_left'])} 天")
    body.append(f'<div class="sub">{" · ".join(bits)}</div>')
    body.append(
        f'<div class="big">权益 {_fmt_money(d.get("equity"))} U'
        f'<span class="upnl">浮盈 {_fmt_signed(d.get("unrealized_pnl"))} U</span></div>'
    )
    if d.get("positions"):
        rows = []
        for p in d["positions"]:
            side = "多" if p.get("side") == 1 else ("空" if p.get("side") == -1 else "—")
            stop = f'{_fmt_money(p.get("stop_px"))} ✔' if p.get("has_stop") else '<span style="color:var(--bad)">无</span>'
            rows.append(
                f"<tr><td>{esc(p.get('coin'))} {side} ×{esc(p.get('leverage'))}</td>"
                f"<td>{_fmt_money(p.get('size'))}</td>"
                f"<td>{_fmt_money(p.get('entry_px'))}</td>"
                f"<td>{_fmt_money(p.get('mark_px'))}</td>"
                f"<td>{_fmt_signed(p.get('unrealized_pnl'))}</td>"
                f"<td>{stop}</td></tr>"
            )
        body.append(
            '<table class="pos"><tr><th>标的</th><th>数量</th><th>入场</th><th>现价</th><th>浮盈U</th><th>止损</th></tr>'
            + "".join(rows)
            + "</table>"
        )
    else:
        body.append('<div class="sub">当前空仓</div>')
    body.append('<div class="sub" style="margin:2px 0 4px">三标的动态</div>')
    for s in d.get("symbols") or []:
        price = _fmt_money(s.get("price"))
        dense = esc(s.get("dense_cnt"))
        dist_l = _fmt_pct(_dist_pct(s.get("price"), s.get("long_trigger")))
        dist_s = _fmt_pct(_dist_pct(s.get("price"), s.get("short_trigger")))
        _held = {"long": "多", "short": "空"}.get(s.get("position_side"))
        held = f" · 持仓{_held}" if _held else ""
        body.append(
            f'<div class="sym">{esc(s.get("coin"))} <span class="v">{price} · 密集 {dense}/6 · 距上轨 {dist_l} · 距下轨 {dist_s}{held}</span></div>'
        )
    for e in (d.get("events") or [])[:3]:
        body.append(f'<div class="ev"><span class="t">{_fmt_time(e.get("ts"))}</span>{esc(e.get("message"))}</div>')
    perf = d.get("perf") or {}
    if perf.get("n"):
        body.append(
            f'<div class="sub" style="margin-top:6px">实盘 {esc(perf.get("n"))} 笔 · 胜率 {_fmt_pct(perf.get("win_rate"))} · 均R {_fmt_signed(perf.get("avg_r"))} · 总R {_fmt_signed(perf.get("total_r"))}</div>'
        )
    return head.format(cls=_dot_class(entry), body="".join(body))


def _dist_pct(price, trigger) -> float | None:
    try:
        p, t = float(price), float(trigger)
    except (TypeError, ValueError):
        return None
    if p == 0:
        return None
    return (t - p) / p


def _lt_card(entry: dict | None) -> str:
    head = '<div class="card"><h2><span class="dot {cls}"></span>Lighter</h2>{body}</div>'
    if entry is None:
        return head.format(cls="warn", body='<div class="init">等待第一轮拉取…</div>')
    if not entry.get("ok"):
        return head.format(
            cls="bad",
            body=f'<div class="banner err">不可用：{esc(entry.get("error"))}</div>',
        )
    d = entry.get("data") or {}
    body: list[str] = []
    if entry.get("stale"):
        body.append(f'<div class="banner warn">数据 {_fmt_age(entry.get("age_s"))}未刷新</div>')
    bits = [f"模式 {esc(d.get('mode') or '—')}"]
    if d.get("kill"):
        bits.append(f'<span style="color:var(--bad)">已 kill（{esc(d.get("kill_reason"))}）</span>')
    if d.get("dd") is not None:
        bits.append(f"回撤 {_fmt_pct(d.get('dd'))}")
    if d.get("stops_all_protected") is False:
        bits.append('<span style="color:var(--bad)">止损未全覆盖</span>')
    elif d.get("stops_degraded"):
        bits.append('<span style="color:var(--warn)">止损读数降级</span>')
    for part in d.get("degraded_parts") or []:
        bits.append(f'<span style="color:var(--warn)">⚠ {esc(part.split(":", 1)[0])}</span>')
    tick = d.get("last_tick_age_s")
    if tick is not None:
        bits.append(f"tick {_fmt_age(tick)}")
    body.append(f'<div class="sub">{" · ".join(bits)}</div>')
    body.append(
        f'<div class="big">权益 {_fmt_money(d.get("equity"))} U</div>'
    )
    if d.get("positions"):
        rows = []
        for p in d["positions"]:
            stop = _fmt_money(p.get("stop_price")) if p.get("stop_price") else '<span style="color:var(--bad)">无</span>'
            rows.append(
                f"<tr><td>{esc(p.get('symbol'))} {esc(p.get('side_text'))}</td>"
                f"<td>{_fmt_money(p.get('qty'))}</td>"
                f"<td>{_fmt_money(p.get('entry_price'))}</td>"
                f"<td>{_fmt_money(p.get('price'))}</td>"
                f"<td>{_fmt_signed(p.get('upnl'))}</td>"
                f"<td>{stop}</td></tr>"
            )
        body.append(
            '<table class="pos"><tr><th>标的</th><th>数量</th><th>入场</th><th>现价</th><th>浮盈U</th><th>止损</th></tr>'
            + "".join(rows)
            + "</table>"
        )
    else:
        body.append('<div class="sub">当前空仓</div>')
    body.append('<div class="sub" style="margin:2px 0 4px">三标的动态</div>')
    for s in d.get("symbols") or []:
        price = _fmt_money(s.get("price"))
        dense = f'{esc(s.get("dense_bars"))}/{esc(s.get("min_dense_bars"))}'
        body.append(
            f'<div class="sym">{esc(s.get("symbol"))} <span class="v">{price} · 密集 {dense} · {esc(s.get("verdict"))}</span></div>'
        )
    for e in (d.get("events") or [])[:3]:
        body.append(f'<div class="ev"><span class="t">{_fmt_time(e.get("ts"))}</span>{esc(e.get("message"))}</div>')
    return head.format(cls=_dot_class(entry), body="".join(body))


def render_page(summary: dict, hl_panel_url: str, lt_panel_url: str) -> str:
    gen = time.strftime("%H:%M:%S", time.gmtime(summary.get("generated_at", time.time())))
    return (
        "<!doctype html><html lang='zh'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='apple-mobile-web-app-capable' content='yes'>"
        "<title>trade-hub</title>"
        f"<style>{_CSS}</style></head><body>"
        f"<header><h1>trade-hub</h1><span class='gen'>更新 {gen} UTC</span></header>"
        + _hl_card(summary.get("hl"))
        + _lt_card(summary.get("lt"))
        + f"<nav class='links'><a href='{html.escape(hl_panel_url, quote=True)}'>打开 HL 面板</a>"
        + f"<a href='{html.escape(lt_panel_url, quote=True)}'>打开 Lighter 面板</a></nav>"
        + f"<script>{_JS}</script></body></html>"
    )
