import unittest

from fastapi.testclient import TestClient

from app.main import create_app
from app.store import SnapshotStore

from . import fixtures
from .test_upstream import _cfg


def _client():
    cfg = _cfg(poll_s=0)
    app = create_app(cfg, store=SnapshotStore(), run_poller=False)
    return TestClient(app), cfg


class HealthTests(unittest.TestCase):
    def test_health_open(self):
        client, _ = _client()
        r = client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])


class TokenGateTests(unittest.TestCase):
    def test_page_requires_token(self):
        client, _ = _client()
        self.assertEqual(client.get("/").status_code, 401)
        self.assertEqual(client.get("/?k=wrong").status_code, 401)
        self.assertEqual(client.get("/api/summary").status_code, 401)
        self.assertEqual(client.get("/api/summary?k=wrong").status_code, 401)

    def test_page_with_query_token_sets_cookie(self):
        client, _ = _client()
        r = client.get("/?k=hubtok")
        self.assertEqual(r.status_code, 200)
        self.assertIn("hub_token", r.cookies)

    def test_page_with_cookie_token(self):
        client, _ = _client()
        r = client.get("/", cookies={"hub_token": "hubtok"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("trade-hub", r.text)

    def test_summary_with_query_token(self):
        client, _ = _client()
        r = client.get("/api/summary?k=hubtok")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("hl", body)
        self.assertIn("lt", body)
        self.assertIsNone(body["hl"])


class SummaryShapeTests(unittest.TestCase):
    def test_summary_includes_populated_store(self):
        import time as _time

        from app.upstream import normalize_hl

        st = SnapshotStore()
        st.put("hl", True, _time.time(), normalize_hl(fixtures.hl_status()))
        app = create_app(_cfg(poll_s=0), store=st, run_poller=False)
        client = TestClient(app)
        r = client.get("/api/summary?k=hubtok")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["hl"]["data"]["equity"], 499.22)
        self.assertIn("age_s", body["hl"])
        self.assertFalse(body["hl"]["stale"])

    def test_stale_flag_set_when_old(self):
        from app.upstream import normalize_hl

        st = SnapshotStore()
        st.put("hl", True, 1.0, normalize_hl(fixtures.hl_status()))  # ancient as_of
        app = create_app(_cfg(poll_s=0), store=st, run_poller=False)
        client = TestClient(app)
        body = client.get("/api/summary?k=hubtok").json()
        self.assertTrue(body["hl"]["stale"])


class ConfigTests(unittest.TestCase):
    def test_missing_required_env_fails(self):
        from app.config import Config as C
        from app.config import ConfigError

        with self.assertRaises(ConfigError):
            C.from_env({"HUB_TOKEN": "t"})  # HUB_HL_TOKEN missing

    def test_from_env_missing_token(self):
        from app.config import ConfigError

        with self.assertRaises(ConfigError):
            _cfg().__class__.from_env({})

    def test_from_env_minimal(self):
        from app.config import Config as C

        cfg = C.from_env({"HUB_TOKEN": "t", "HUB_HL_TOKEN": "h"})
        self.assertEqual(cfg.token, "t")
        self.assertEqual(cfg.hl_base, "http://127.0.0.1:8100")
        self.assertEqual(cfg.lt_base, "http://127.0.0.1:8110")
        self.assertEqual(cfg.poll_s, 60)
        self.assertIn("/admin?k=h", cfg.hl_panel_url)
        self.assertEqual(cfg.lt_panel_url, "https://lt.222677.xyz")

    def test_from_env_bad_poll_s(self):
        from app.config import ConfigError

        with self.assertRaises(ConfigError):
            _cfg().__class__.from_env(
                {"HUB_TOKEN": "t", "HUB_HL_TOKEN": "h", "HUB_POLL_S": "abc"}
            )

    def test_lt_admin_token_adds_k_to_panel_link(self):
        cfg = _cfg()
        self.assertIn("?k=ltadmin", cfg.lt_panel_url)
