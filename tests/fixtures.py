"""Synthetic upstream fixtures.

Shapes mirror the real payloads captured from the live panels (2026-10-31);
all numbers/addresses are fake. If an upstream payload shape changes, capture
a fresh real sample and update these builders — that is the contract.
"""
from __future__ import annotations


def hl_status() -> dict:
    return {
        "ts": 1793432400.0,
        "schema_version": 1,
        "mode": "live",
        "kill": False,
        "kill_reason": None,
        "account": {
            "address": "0x" + "ab" * 20,
            "equity": 499.22,
            "perp_equity": 27.84,
            "spot_usdc": 499.22,
            "spot_hold": 27.84,
            "spot_ok": True,
            "unified": True,
            "withdrawable": 0.0,
            "margin_used": 27.84,
            "notional": 111.76,
            "unrealized_pnl": 4.59,
            "today_realized": 0.0,
            "total_realized": -6.33,
            "fees_total": 1.73,
            "funding_total": 0.03,
        },
        "positions": [
            {
                "coin": "SOL",
                "side": -1,
                "size": 1.17,
                "entry_px": 99.446,
                "mark_px": 95.5205,
                "unrealized_pnl": 4.59,
                "has_stop": True,
                "stop_px": 104.95,
                "leverage": 5,
                "isolated": True,
                "position_id": 1,
                "stop_dist_pct": 0.055,
                "stop_unknown": False,
                "r_unrealized": 0.5,
                "liq_px": 118.0,
                "margin_used": 22.35,
                "position_value": 111.76,
                "funding_income": 0.0,
                "signal_bar_ms": 1793404800000,
            }
        ],
        "orders_open": [
            {
                "coin": "SOL",
                "oid": 123,
                "is_buy": True,
                "is_trigger": True,
                "limit_px": 104.95,
                "trigger_px": 104.95,
                "reduce_only": True,
                "sz": 1.17,
                "timestamp": 1793404900000,
            }
        ],
        "orders_recent": [],
        "fills": [],
        "signals": [],
        "symbol_state": [
            {
                "symbol": "BTC_USDT",
                "coin": "BTC",
                "price": 77351.0,
                "sma20": 79537.5,
                "sma200": 82522.25,
                "long_trigger": 81502.63,
                "short_trigger": 78930.17,
                "dense_cnt": 0,
                "updated_at": 1793431983.0,
                "position_side": None,
            },
            {
                "symbol": "ETH_USDT",
                "coin": "ETH",
                "price": 2238.3,
                "sma20": 2302.1,
                "sma200": 2495.75,
                "long_trigger": 2402.54,
                "short_trigger": 2289.08,
                "dense_cnt": 2,
                "updated_at": 1793431983.0,
                "position_side": None,
            },
            {
                "symbol": "SOL_USDT",
                "coin": "SOL",
                "price": 95.52,
                "sma20": 99.19,
                "sma200": 103.0,
                "long_trigger": 100.5,
                "short_trigger": 96.8,
                "dense_cnt": 4,
                "updated_at": 1793431983.0,
                "position_side": "short",
            },
        ],
        "events": [
            {"ts": 1793432400.7, "kind": "heartbeat", "symbol": None, "message": "executor 心跳（equity 499.18）"},
            {"ts": 1793432000.0, "kind": "reconcile", "symbol": "SOL", "message": "对账一致"},
        ],
        "perf": {"n": 6, "long": 1, "short": 5, "wins": 1, "avg_r": -0.35, "win_rate": 0.1667, "total_r": -2.11},
        "agent": {"days_left": 163, "level": "ok", "cleanup": "none"},
        "network": {"reachable": True, "latency_ms": 120, "testnet": False},
        "system": {
            "executor_last_event_at": 1793432400.7,
            "feed": [
                {"symbol": "BTC_USDT", "coin": "BTC", "source": "hl-candle", "ok": True, "last_error": "", "error_at": None, "last_ok_at": 1793431982.0},
                {"symbol": "ETH_USDT", "coin": "ETH", "source": "hl-candle", "ok": True, "last_error": "", "error_at": None, "last_ok_at": 1793431982.0},
                {"symbol": "SOL_USDT", "coin": "SOL", "source": "hl-candle", "ok": True, "last_error": "", "error_at": None, "last_ok_at": 1793431982.0},
            ],
            "last_bar": {},
            "mismatch": [],
            "stuck_orders": [],
        },
        "curve": {"meta": {}, "pnl": [], "twr": []},
    }


def lt_status() -> dict:
    return {
        "as_of": 1793432641.5,
        "mode": "live",
        "ok": True,
        "level": "ok",
        "state": "正常",
        "reasons": [],
        "equity": 496.45,
        "equity_known": True,
        "equity_source": "provider",
        "open_count": 1,
        "max_positions": 3,
        "kill": False,
        "kill_known": True,
        "kill_reason": "",
        "kill_by": "",
        "last_tick_ts": 1793432009.7,
        "last_tick_age_s": 631.8,
        "last_tick_text": "11 分钟前",
        "data_source": {"ok": True, "name": "bar", "age_s": 13441.0, "last_ts": 1793419200.0, "detail": "ok"},
        "credentials": {"known": True, "configured": True, "missing": [], "live_gate": {"enabled": True, "declared_account": 123456, "ok": True, "detail": ""}},
        "dd": {"index": 0.9929, "peak": 1.0, "drawdown": 0.0071, "action": "ok", "warn": 0.25, "kill": 0.3, "source": "dd_state", "available": True, "degraded": False},
        "warnings": [],
        "degraded": False,
        "block": "status",
    }


def lt_positions() -> dict:
    return {
        "as_of": 1793432803.8,
        "positions": [
            {
                "symbol": "SOL",
                "side": -1,
                "side_text": "空",
                "state": "OPEN",
                "status": "持仓中",
                "entry_price": 95.601,
                "price": 95.5365,
                "price_source": "mark",
                "upnl": 0.147,
                "upnl_pct": 0.00067,
                "qty": 0.717,
                "stop_price": 104.807,
                "dist_to_stop_pct": 0.097,
                "exit_price": 99.19,
                "dist_to_exit_pct": 0.038,
                "funding_rate": 9.6e-05,
                "funding_rate_cash": 0.0066,
                "funding_rate_exchange": "lighter",
                "funding_paid": 0.0226,
                "notional": 68.65,
                "margin": 13.73,
                "liq_price": 112.70,
                "opened_at": 1793410000.0,
                "holding_s": 22000.0,
                "holding_text": "6 小时",
                "position_id": 3,
                "warnings": [],
            },
            {
                "symbol": "BTC",
                "side": 0,
                "side_text": "—",
                "state": "IDLE",
                "status": "等待开仓",
                "entry_price": 0.0,
                "price": 77129.7,
                "upnl": 0.0,
                "qty": 0.0,
                "stop_price": 0.0,
                "warnings": [],
            },
        ],
        "open_count": 1,
        "symbols": [],
        "warnings": [],
        "degraded": False,
        "block": "positions",
    }


def lt_stops() -> dict:
    return {
        "as_of": 1793432641.6,
        "stops": [
            {
                "symbol": "SOL",
                "position_id": 3,
                "side": -1,
                "stop_price": 104.807,
                "qty": 0.717,
                "order_qty": 0.717,
                "order_id": "coi:123",
                "exchange_status": "present",
                "protected": True,
                "checked_at": 1793432641.6,
                "note": "已覆盖",
                "expires_at": 1795748627.5,
                "days_left": 26.8,
            }
        ],
        "orders_known": True,
        "uncovered": [],
        "not_on_exchange": [],
        "all_protected": True,
        "warnings": [],
        "degraded": False,
        "block": "stops",
    }


def lt_symbols() -> dict:
    return {
        "as_of": 1793432706.0,
        "symbols": [
            {
                "symbol": "BTC",
                "price": 77129.7,
                "band_pct": 0.0315,
                "threshold_pct": 0.0157,
                "dense_bars": 0,
                "min_dense_bars": 6,
                "sma20": 79531.45,
                "sma200": 82517.96,
                "verdict": "等密集（带宽未进门槛）",
                "reason": "均线不密集",
                "blocked_by": "squeeze",
                "fired": False,
                "side": 0,
                "held_side": 0,
                "warnings": [],
            },
            {
                "symbol": "ETH",
                "price": 2238.29,
                "dense_bars": 0,
                "min_dense_bars": 6,
                "verdict": "等密集（带宽未进门槛）",
                "reason": "均线不密集",
                "blocked_by": "squeeze",
                "fired": False,
                "side": 0,
                "held_side": 0,
                "warnings": [],
            },
            {
                "symbol": "SOL",
                "price": 95.54,
                "dense_bars": 3,
                "min_dense_bars": 6,
                "verdict": "持仓中",
                "reason": "",
                "blocked_by": "",
                "fired": False,
                "side": 0,
                "held_side": -1,
                "warnings": [],
            },
        ],
        "warnings": [],
        "degraded": False,
        "block": "symbols",
    }


def lt_events() -> dict:
    return {
        "as_of": 1793432641.6,
        "events": [
            {"id": 930, "ts": 1793432009.7, "kind": "heartbeat", "symbol": None, "message": "tick heartbeat from scheduler", "action": "心跳", "skipped": False, "alert": False, "data": {}},
            {"id": 929, "ts": 1793432009.5, "kind": "hold", "symbol": "SOL", "message": "SOL hold: no exit trigger", "action": "其他", "skipped": False, "alert": False, "data": {}},
        ],
        "count": 2,
        "skipped_count": 0,
        "limit": 5,
        "warnings": [],
        "degraded": False,
        "block": "events",
    }
