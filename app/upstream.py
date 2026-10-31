"""Fetch and normalize the two panels' JSON into one common summary shape.

Normalizers are pure functions, unit-tested against fixtures that mirror the
real upstream payloads (captured 2026-10-31 from the live panels). The fetch
layer is stdlib urllib run in a thread — same convention as the sibling repos
(no extra HTTP dependency on the trading hosts).
"""
from __future__ import annotations

import asyncio
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Source:
    ok: bool
    as_of: float
    error: str = ""
    data: dict = field(default_factory=dict)


def _fetch_json(url: str, timeout: float) -> tuple[Optional[dict], str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "trade-hub/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), ""
    except Exception as exc:  # noqa: BLE001 - degrade to an error string by design
        return None, f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------
# HL  (crypto-ma-alert, GET /api/hl/status?k=)
# --------------------------------------------------------------------------

def normalize_hl(status: dict) -> dict:
    acc = status.get("account") or {}
    sma20_by_coin = {
        s.get("coin"): s.get("sma20") for s in status.get("symbol_state") or []
    }
    positions = [
        {
            "coin": p.get("coin"),
            "side": p.get("side"),
            "size": p.get("size"),
            "entry_px": p.get("entry_px"),
            "mark_px": p.get("mark_px"),
            "unrealized_pnl": p.get("unrealized_pnl"),
            "has_stop": bool(p.get("has_stop")),
            "stop_px": p.get("stop_px"),
            "leverage": p.get("leverage"),
            # 离场线 = SMA20（与 HL 面板口径一致：收盘破线离场）
            "exit_px": sma20_by_coin.get(p.get("coin")),
        }
        for p in status.get("positions") or []
    ]
    symbols = [
        {
            "coin": s.get("coin"),
            "price": s.get("price"),
            "dense_cnt": s.get("dense_cnt"),
            "long_trigger": s.get("long_trigger"),
            "short_trigger": s.get("short_trigger"),
            "sma200": s.get("sma200"),
            "position_side": s.get("position_side"),
        }
        for s in status.get("symbol_state") or []
    ]
    events = [
        {"ts": e.get("ts"), "kind": e.get("kind"), "message": e.get("message")}
        for e in (status.get("events") or [])[:5]
    ]
    fills = [
        {
            "ts": f.get("ts"),
            "coin": f.get("coin"),
            "dir": f.get("dir"),
            "sz": f.get("sz"),
            "px": f.get("px"),
            "closed_pnl": f.get("closed_pnl"),
        }
        for f in (status.get("fills") or [])[:5]
    ]
    perf = status.get("perf") or {}
    feed = (status.get("system") or {}).get("feed") or []
    return {
        "equity": acc.get("equity"),
        "unrealized_pnl": acc.get("unrealized_pnl"),
        "notional": acc.get("notional"),
        "margin_used": acc.get("margin_used"),
        "today_realized": acc.get("today_realized"),
        "total_realized": acc.get("total_realized"),
        "mode": status.get("mode"),
        "kill": bool(status.get("kill")),
        "kill_reason": status.get("kill_reason") or "",
        "positions": positions,
        "symbols": symbols,
        "events": events,
        "fills": fills,
        "perf": {
            "n": perf.get("n"),
            "win_rate": perf.get("win_rate"),
            "avg_r": perf.get("avg_r"),
            "total_r": perf.get("total_r"),
        },
        "agent_days_left": (status.get("agent") or {}).get("days_left"),
        "agent_level": (status.get("agent") or {}).get("level"),
        "feed_ok": (all(f.get("ok") for f in feed) if feed else None),
        "mismatch": (status.get("system") or {}).get("mismatch"),
        "last_event_ts": (status.get("system") or {}).get("executor_last_event_at"),
        "panel_ts": status.get("ts"),
    }


# --------------------------------------------------------------------------
# Lighter  (lighter-ma-bot, GET /status /positions /stops /symbols /events)
# --------------------------------------------------------------------------

def normalize_lt(
    status: Optional[dict],
    positions: Optional[dict],
    stops: Optional[dict],
    symbols: Optional[dict],
    events: Optional[dict],
    records: Optional[dict] = None,
    degraded_parts: Optional[list] = None,
) -> dict:
    st = status or {}
    open_positions = [
        {
            "symbol": p.get("symbol"),
            "side_text": p.get("side_text"),
            "qty": p.get("qty"),
            "entry_price": p.get("entry_price"),
            "price": p.get("price"),
            "upnl": p.get("upnl"),
            "upnl_pct": p.get("upnl_pct"),
            "stop_price": p.get("stop_price"),
            "exit_price": p.get("exit_price"),
            "notional": p.get("notional"),
            "liq_price": p.get("liq_price"),
            "funding_rate": p.get("funding_rate"),
            "holding_text": p.get("holding_text"),
        }
        for p in (positions or {}).get("positions") or []
        if p.get("state") == "OPEN"
    ]
    trades = [
        {
            "ts": t.get("ts"),
            "symbol": t.get("symbol"),
            "kind_text": t.get("kind_text"),
            "side_text": t.get("side_text"),
            "qty": t.get("qty"),
            "price": t.get("price"),
            "realized_pnl": t.get("realized_pnl"),
        }
        for t in (records or {}).get("trades") or []
        if t.get("kind") in ("entry", "exit")
    ][:5]
    symbols_out = [
        {
            "symbol": s.get("symbol"),
            "price": s.get("price"),
            "dense_bars": s.get("dense_bars"),
            "min_dense_bars": s.get("min_dense_bars"),
            "verdict": s.get("verdict"),
            "reason": s.get("reason"),
            "held_side": s.get("held_side"),
        }
        for s in (symbols or {}).get("symbols") or []
    ]
    ev = (events or {}).get("events") or []
    dd = st.get("dd") or {}
    stops_doc = stops or {}
    return {
        "equity": st.get("equity"),
        "equity_source": st.get("equity_source"),
        "mode": st.get("mode"),
        "kill": bool(st.get("kill")),
        "kill_reason": st.get("kill_reason") or "",
        "dd": dd.get("drawdown"),
        "dd_action": dd.get("action"),
        "last_tick_age_s": st.get("last_tick_age_s"),
        "open_count": len(open_positions),
        "positions": open_positions,
        "stops_all_protected": stops_doc.get("all_protected"),
        "stops_uncovered": len(stops_doc.get("uncovered") or []),
        "stops_degraded": bool(stops_doc.get("degraded")),
        "symbols": symbols_out,
        "events": [
            {"ts": e.get("ts"), "kind": e.get("kind"), "message": e.get("message")}
            for e in ev[:5]
        ],
        "trades": trades,
        "degraded_parts": list(degraded_parts or []),
    }


# --------------------------------------------------------------------------
# Collectors (fetch + normalize; `fetch` injectable for tests)
# --------------------------------------------------------------------------

async def collect_hl(cfg, fetch: Callable | None = None) -> Source:
    do_fetch = fetch or _fetch_json
    url = cfg.hl_base.rstrip("/") + "/api/hl/status?k=" + urllib.parse.quote(cfg.hl_token)
    payload, err = await asyncio.to_thread(do_fetch, url, cfg.request_timeout_s)
    if payload is None:
        return Source(ok=False, as_of=time.time(), error=err or "empty response")
    return Source(ok=True, as_of=time.time(), data=normalize_hl(payload))


_LT_PARTS = ("/status", "/positions", "/stops", "/symbols", "/events?limit=5", "/api/records")


async def collect_lt(cfg, fetch: Callable | None = None) -> Source:
    do_fetch = fetch or _fetch_json
    base = cfg.lt_base.rstrip("/")

    async def one(path: str) -> tuple[str, Optional[dict], str]:
        payload, err = await asyncio.to_thread(
            do_fetch, base + path, cfg.request_timeout_s
        )
        return path, payload, err

    results = await asyncio.gather(*(one(p) for p in _LT_PARTS))
    by_path = {path: (payload, err) for path, payload, err in results}

    status_payload, status_err = by_path["/status"]
    if status_payload is None:
        return Source(ok=False, as_of=time.time(), error=status_err or "empty /status")

    degraded: list[str] = []
    positions_payload, positions_err = by_path["/positions"]
    stops_payload, stops_err = by_path["/stops"]
    symbols_payload, symbols_err = by_path["/symbols"]
    events_payload, events_err = by_path["/events?limit=5"]
    records_payload, records_err = by_path["/api/records"]
    for name, err in (
        ("positions", positions_err),
        ("stops", stops_err),
        ("symbols", symbols_err),
        ("events", events_err),
        ("records", records_err),
    ):
        if err:
            degraded.append(f"{name}: {err}")

    data = normalize_lt(
        status_payload, positions_payload, stops_payload, symbols_payload, events_payload,
        records=records_payload,
        degraded_parts=degraded,
    )
    return Source(ok=True, as_of=time.time(), data=data)
