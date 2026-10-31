"""FastAPI app: background poll loop + gated page/JSON + open /health."""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import logging
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from . import upstream
from .config import Config
from .store import SnapshotStore
from .views import render_page

logger = logging.getLogger("trade-hub")

_COOKIE = "hub_token"
_STALE_FALLBACK_S = 180.0
_STATIC = Path(__file__).resolve().parent / "static"


def _authorized(request: Request, cfg: Config, k: str) -> bool:
    given = k or request.cookies.get(_COOKIE, "")
    if not given:
        return False
    return hmac.compare_digest(given, cfg.token)


def _unauthorized() -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><meta charset='utf-8'><body style='font-family:sans-serif'>"
        "需要 token：用 ?k=<b>HUB_TOKEN</b> 链接打开本页。</body>",
        status_code=401,
    )


async def _poll_loop(cfg: Config, store: SnapshotStore) -> None:
    while True:
        try:
            hl, lt = await asyncio.gather(
                upstream.collect_hl(cfg), upstream.collect_lt(cfg)
            )
            store.put(
                "hl", hl.ok, hl.as_of, hl.data, hl.error
            )
            store.put(
                "lt", lt.ok, lt.as_of, lt.data, lt.error
            )
            if not hl.ok:
                logger.warning("HL fetch failed: %s", hl.error)
            if not lt.ok:
                logger.warning("LT fetch failed: %s", lt.error)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - the loop must survive anything
            logger.exception("poll iteration failed")
        await asyncio.sleep(cfg.poll_s)


def create_app(cfg: Config | None = None, store: SnapshotStore | None = None, run_poller: bool = True) -> FastAPI:
    if cfg is None:
        cfg = Config.from_env()
    app = FastAPI(title="trade-hub", docs_url=None, redoc_url=None, openapi_url=None)
    st = store if store is not None else SnapshotStore()
    app.state.store = st
    app.state.cfg = cfg

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "service": "trade-hub"}

    @app.get("/apple-touch-icon.png")
    async def icon_apple() -> FileResponse:
        return FileResponse(_STATIC / "apple-touch-icon.png", media_type="image/png")

    @app.get("/favicon-32.png")
    async def icon_32() -> FileResponse:
        return FileResponse(_STATIC / "favicon-32.png", media_type="image/png")

    @app.get("/favicon.ico")
    async def favicon() -> FileResponse:
        return FileResponse(_STATIC / "favicon-32.png", media_type="image/png")

    @app.get("/icon-192.png")
    async def icon_192() -> FileResponse:
        return FileResponse(_STATIC / "icon-192.png", media_type="image/png")

    @app.get("/icon-512.png")
    async def icon_512() -> FileResponse:
        return FileResponse(_STATIC / "icon-512.png", media_type="image/png")

    @app.get("/manifest.webmanifest")
    async def manifest() -> FileResponse:
        return FileResponse(
            _STATIC / "manifest.webmanifest", media_type="application/manifest+json"
        )

    @app.get("/api/summary")
    async def api_summary(request: Request, k: str = ""):
        if not _authorized(request, cfg, k):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return st.summary(stale_after_s=max(cfg.poll_s * 3, _STALE_FALLBACK_S))

    @app.get("/", response_class=HTMLResponse)
    async def page(request: Request, k: str = ""):
        if not _authorized(request, cfg, k):
            return _unauthorized()
        html = render_page(
            st.summary(stale_after_s=max(cfg.poll_s * 3, _STALE_FALLBACK_S)),
            cfg.hl_panel_url,
            cfg.lt_panel_url,
        )
        resp = HTMLResponse(html)
        if k and hmac.compare_digest(k, cfg.token):
            resp.set_cookie(
                _COOKIE, k, max_age=3600 * 24 * 365, httponly=True, samesite="lax"
            )
        return resp

    if run_poller and cfg.poll_s > 0:

        @app.on_event("startup")
        async def _start() -> None:
            app.state.poll_task = asyncio.create_task(_poll_loop(cfg, st))

        @app.on_event("shutdown")
        async def _stop() -> None:
            task = getattr(app.state, "poll_task", None)
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    return app


def main() -> None:  # pragma: no cover - manual entry point
    import uvicorn

    cfg = Config.from_env()
    uvicorn.run(create_app(cfg), host="127.0.0.1", port=8120, log_level="info")


if __name__ == "__main__":  # pragma: no cover
    main()
