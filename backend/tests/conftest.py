"""
Test configuration. Environment is pinned BEFORE the app modules import so
main.py/database.py pick up the test database and limits, not local defaults.
"""
import os
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix="pcl-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["JWT_SECRET"] = "test-secret-not-for-production"
os.environ["GEOCODE_ENABLED"] = "false"          # no outbound HTTP in tests
os.environ["SSE_HEARTBEAT_SECONDS"] = "0.5"      # fast disconnect detection
os.environ["TRACK_RATELIMIT"] = "1000/minute"    # don't trip limits in tests
os.environ["AUTH_RATELIMIT"] = "1000/minute"
os.environ.pop("NOTIFY_WEBHOOK_URL", None)       # capture in-test instead

from fastapi.testclient import TestClient  # noqa: E402

import auth as auth_mod  # noqa: E402
import cache as cache_mod  # noqa: E402
import main as main_module  # noqa: E402
import models  # noqa: E402
import notifications  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402

Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_state():
    """Fresh shipments per test; keep admin_users so fixtures stay cheap.
    Also clear the TTL cache so lookups always hit this test's data."""
    yield
    cache_mod._cache.clear()
    db = SessionLocal()
    try:
        db.query(models.Milestone).delete()
        db.query(models.Shipment).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(main_module.app)


def _ensure_user(username: str, role: str) -> None:
    db = SessionLocal()
    try:
        if not db.query(models.AdminUser).filter_by(username=username).first():
            db.add(
                models.AdminUser(
                    username=username,
                    password_hash=auth_mod.hash_password("pw123456"),
                    role=role,
                )
            )
            db.commit()
    finally:
        db.close()


def _login(client: TestClient, username: str) -> str:
    r = client.post("/api/v1/admin/login", json={"username": username, "password": "pw123456"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_token(client):
    _ensure_user("admin", "admin")
    return _login(client, "admin")


@pytest.fixture
def operator_token(client):
    _ensure_user("oper", "operator")
    return _login(client, "oper")


@pytest.fixture
def notifications_outbox(monkeypatch):
    """Captures everything the app would deliver to the webhook."""
    out = []
    monkeypatch.setattr(notifications, "notify_event", lambda payload: out.append(payload))
    return out


def make_shipment(client, token, **overrides):
    payload = {
        "origin": "Lagos, Nigeria",
        "destination": "Buea, Cameroon",
        "sender_name": "Lagos Traders Ltd",
        "recipient_name": "Buea Tech Hub",
    }
    payload.update(overrides)
    return client.post(
        "/api/v1/admin/shipments", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
