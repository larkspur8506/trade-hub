"""In-memory snapshot store: last good payload per source + freshness."""
from __future__ import annotations

import threading
import time


class SnapshotStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sources: dict[str, dict] = {}

    def put(self, name: str, ok: bool, as_of: float, data: dict, error: str = "") -> None:
        with self._lock:
            self._sources[name] = {"ok": ok, "as_of": as_of, "data": data, "error": error}

    def get(self, name: str) -> dict | None:
        with self._lock:
            return self._sources.get(name)

    def summary(self, stale_after_s: float) -> dict:
        """Shape consumed by views.render_page and /api/summary."""
        now = time.time()
        out: dict[str, dict | None] = {"generated_at": now}
        for name in ("hl", "lt"):
            snap = self.get(name)
            if snap is None:
                out[name] = None
                continue
            entry = dict(snap)
            entry["age_s"] = max(0.0, now - snap["as_of"])
            entry["stale"] = snap["ok"] and entry["age_s"] > stale_after_s
            out[name] = entry
        return out
