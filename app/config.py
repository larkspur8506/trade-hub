"""Configuration read from environment variables; fail-closed on missing items."""
from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    token: str
    hl_token: str
    lt_base: str
    hl_base: str
    lt_admin_token: str
    hl_panel_base: str
    lt_panel_base: str
    poll_s: int
    request_timeout_s: float

    @property
    def hl_panel_url(self) -> str:
        return self.hl_panel_base.rstrip("/") + "/admin?k=" + self.hl_token

    @property
    def lt_panel_url(self) -> str:
        base = self.lt_panel_base.rstrip("/")
        if self.lt_admin_token:
            return base + "/?k=" + self.lt_admin_token
        return base

    @classmethod
    def from_env(cls, env: dict | None = None) -> "Config":
        env = os.environ if env is None else env

        def get(key: str, default: str = "") -> str:
            return (env.get(key) or default).strip()

        missing = [k for k in ("HUB_TOKEN", "HUB_HL_TOKEN") if not get(k)]
        if missing:
            raise ConfigError("缺少必需环境变量: " + ", ".join(missing))

        raw_poll = get("HUB_POLL_S", "60")
        try:
            poll_s = int(raw_poll)
        except ValueError as e:
            raise ConfigError(f"HUB_POLL_S 不是整数: {raw_poll!r}") from e
        if poll_s < 0:
            raise ConfigError(f"HUB_POLL_S 不能为负: {poll_s}")

        raw_timeout = get("HUB_REQUEST_TIMEOUT_S", "12")
        try:
            timeout = float(raw_timeout)
        except ValueError as e:
            raise ConfigError(f"HUB_REQUEST_TIMEOUT_S 不是数字: {raw_timeout!r}") from e
        if timeout <= 0:
            raise ConfigError(f"HUB_REQUEST_TIMEOUT_S 必须为正: {timeout}")

        return cls(
            token=get("HUB_TOKEN"),
            hl_token=get("HUB_HL_TOKEN"),
            lt_admin_token=get("HUB_LT_ADMIN_TOKEN"),
            hl_base=get("HUB_HL_BASE", "http://127.0.0.1:8100"),
            lt_base=get("HUB_LT_BASE", "http://127.0.0.1:8110"),
            hl_panel_base=get("HUB_HL_PANEL_BASE", "https://ma.222677.xyz"),
            lt_panel_base=get("HUB_LT_PANEL_BASE", "https://lt.222677.xyz"),
            poll_s=poll_s,
            request_timeout_s=timeout,
        )
