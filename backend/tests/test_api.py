"""End-to-end API tests: auth, roles, tracking, milestones, pagination,
soft delete, SSE live stream, notifications, and geocoding."""
import jwt as pyjwt
import pytest

import auth as auth_mod
import geocode
from conftest import make_shipment
from utils import is_valid_tracking_number


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def add_milestone(client, token, tn, **overrides):
    payload = {"status": "In Transit", "location": "Abuja hub, Nigeria"}
    payload.update(overrides)
    return client.post(
        f"/api/v1/admin/shipments/{tn}/milestones", json=payload, headers=auth(token)
    )


# ---------------------------------------------------------------------------
# Health & auth
# ---------------------------------------------------------------------------

def test_health(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_returns_token_with_role(client, admin_token):
    payload = auth_mod.decode_access_token(admin_token)
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"


def test_login_wrong_password_401(client):
    from conftest import _ensure_user
    _ensure_user("admin", "admin")
    r = client.post("/api/v1/admin/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


@pytest.mark.parametrize("headers", [None, {"Authorization": "Bearer not.a.token"}])
def test_admin_endpoints_require_valid_token(client, headers):
    r = client.get("/api/v1/admin/shipments", headers=headers)
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Shipment creation
# ---------------------------------------------------------------------------

def test_create_generates_luhn_valid_tracking_number(client, admin_token):
    r = make_shipment(client, admin_token)
    assert r.status_code == 201
    body = r.json()
    assert is_valid_tracking_number(body["tracking_number"])
    assert body["created_by"] == "admin"
    # first milestone auto-seeded, with audit
    assert body["milestones"][0]["status"] == "Order Registered"
    assert body["milestones"][0]["created_by"] == "admin"


def test_create_with_explicit_number_duplicate_conflict(client, admin_token):
    r = make_shipment(client, admin_token, tracking_number="PCL-IMPORT-001")
    assert r.status_code == 201
    r2 = make_shipment(client, admin_token, tracking_number="PCL-IMPORT-001")
    assert r2.status_code == 409


def test_create_invalid_tracking_number_rejected(client, admin_token):
    r = make_shipment(client, admin_token, tracking_number="bad number!!")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Public tracking
# ---------------------------------------------------------------------------

def test_track_unknown_404(client):
    assert client.get("/api/v1/shipments/track/PCL000000000000000").status_code == 404


def test_track_returns_shipment_with_milestones(client, admin_token):
    tn = make_shipment(client, admin_token).json()["tracking_number"]
    r = client.get(f"/api/v1/shipments/track/{tn}")
    assert r.status_code == 200
    body = r.json()
    assert body["tracking_number"] == tn
    assert len(body["milestones"]) == 1


def test_milestone_updates_headline_status_and_audit(client, admin_token):
    tn = make_shipment(client, admin_token).json()["tracking_number"]
    r = add_milestone(client, admin_token, tn)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "In Transit"
    latest = body["milestones"][-1]
    assert latest["created_by"] == "admin"
    assert client.get(f"/api/v1/shipments/track/{tn}").json()["status"] == "In Transit"


def test_milestone_invalid_status_422(client, admin_token):
    tn = make_shipment(client, admin_token).json()["tracking_number"]
    r = add_milestone(client, admin_token, tn, status="Teleported")
    assert r.status_code == 422


def test_patch_partial_update(client, admin_token):
    tn = make_shipment(client, admin_token).json()["tracking_number"]
    r = client.patch(
        f"/api/v1/admin/shipments/{tn}",
        json={"recipient_name": "Renamed Recipient", "weight_kg": 3.5},
        headers=auth(admin_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["recipient_name"] == "Renamed Recipient"
    assert body["weight_kg"] == 3.5
    assert body["origin"] == "Lagos, Nigeria"  # untouched


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

def test_operator_can_work_but_not_delete(client, operator_token):
    # operator does day-to-day work
    r = make_shipment(client, operator_token)
    assert r.status_code == 201
    tn = r.json()["tracking_number"]
    assert add_milestone(client, operator_token, tn).status_code == 200

    # ...but destructive actions are admin-only
    r = client.delete(f"/api/v1/admin/shipments/{tn}", headers=auth(operator_token))
    assert r.status_code == 403


def test_admin_can_delete_and_restore(client, admin_token):
    tn = make_shipment(client, admin_token).json()["tracking_number"]

    assert client.delete(f"/api/v1/admin/shipments/{tn}", headers=auth(admin_token)).status_code == 204
    assert client.get(f"/api/v1/shipments/track/{tn}").status_code == 404

    r = client.post(f"/api/v1/admin/shipments/{tn}/restore", headers=auth(admin_token))
    assert r.status_code == 200 and r.json()["deleted_at"] is None
    assert client.get(f"/api/v1/shipments/track/{tn}").status_code == 200

    # double restore conflicts; restoring unknown 404s
    assert client.post(f"/api/v1/admin/shipments/{tn}/restore", headers=auth(admin_token)).status_code == 409
    assert client.post("/api/v1/admin/shipments/PCL000000000000000/restore", headers=auth(admin_token)).status_code == 404


# ---------------------------------------------------------------------------
# Pagination / search / filter
# ---------------------------------------------------------------------------

def test_pagination_search_and_status_filter(client, admin_token):
    tns = [
        make_shipment(client, admin_token, recipient_name="Alice & Co").json()["tracking_number"],
        make_shipment(client, admin_token, recipient_name="Bob & Sons").json()["tracking_number"],
        make_shipment(client, admin_token, recipient_name="Carol Ltd").json()["tracking_number"],
    ]
    add_milestone(client, admin_token, tns[0])  # -> In Transit

    r = client.get("/api/v1/admin/shipments?page=1&page_size=2", headers=auth(admin_token)).json()
    assert r["total"] == 3 and len(r["items"]) == 2 and r["total_pages"] == 2

    r = client.get("/api/v1/admin/shipments?q=alice", headers=auth(admin_token)).json()
    assert r["total"] == 1 and r["items"][0]["tracking_number"] == tns[0]

    r = client.get("/api/v1/admin/shipments?status=In Transit", headers=auth(admin_token)).json()
    assert r["total"] == 1 and r["items"][0]["tracking_number"] == tns[0]

    r = client.get("/api/v1/admin/shipments?status=Bogus", headers=auth(admin_token))
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# SSE live stream
# ---------------------------------------------------------------------------

def test_sse_unknown_number_not_found(client):
    # NOTE: TestClient buffers streamed responses until they complete, so we
    # only assert on terminating streams here. The live-push path is covered
    # by the raw-ASGI test below.
    with client.stream("GET", "/api/v1/shipments/track/PCL999999999999999/events") as resp:
        buf = b""
        for chunk in resp.iter_bytes():
            buf += chunk
            if b"not_found" in buf:
                break
    assert b"event: not_found" in buf


def test_sse_stream_initial_and_live_push(client, admin_token):
    """Drive the ASGI app directly so we can read the SSE stream WHILE it is
    still open: assert the initial snapshot, then a milestone POST pushes a
    fresh snapshot to the watcher without any polling."""
    import asyncio
    import threading
    import time as time_mod

    import main as app_module

    tn = make_shipment(client, admin_token).json()["tracking_number"]

    sent: list = []
    got_initial = threading.Event()
    disconnect = threading.Event()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": f"/api/v1/shipments/track/{tn}/events",
        "raw_path": f"/api/v1/shipments/track/{tn}/events".encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"testserver")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive():
        while not disconnect.is_set():
            await asyncio.sleep(0.05)
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)
        if message["type"] == "http.response.body" and b"event: shipment" in message.get("body", b""):
            got_initial.set()

    def run_app():
        asyncio.run(app_module.app(scope, receive, send))

    t = threading.Thread(target=run_app, daemon=True)
    t.start()

    def body_so_far() -> bytes:
        return b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")

    try:
        assert got_initial.wait(10), "initial SSE snapshot never arrived"
        assert tn.encode() in body_so_far()

        # Trigger a write from a second "client" — the watcher must get it live.
        r = add_milestone(client, admin_token, tn, location="Live push checkpoint")
        assert r.status_code == 200

        deadline = time_mod.time() + 10
        while time_mod.time() < deadline:
            if b"Live push checkpoint" in body_so_far():
                break
            time_mod.sleep(0.1)
        else:
            pytest.fail("milestone update was never pushed over SSE")
    finally:
        disconnect.set()
        t.join(timeout=10)

    # content-type came through on the response.start message
    headers = dict((k.lower(), v) for m in sent if m["type"] == "http.response.start" for k, v in m["headers"])
    assert headers[b"content-type"].startswith(b"text/event-stream")
    assert not t.is_alive(), "SSE generator did not end after disconnect"


# ---------------------------------------------------------------------------
# Notifications (webhook outbox)
# ---------------------------------------------------------------------------

def test_notifications_fired_for_create_and_milestone(client, admin_token, notifications_outbox):
    tn = make_shipment(client, admin_token).json()["tracking_number"]
    add_milestone(client, admin_token, tn, location="Kumba checkpoint")

    events = [e["event"] for e in notifications_outbox]
    assert "shipment.created" in events
    assert "milestone.added" in events

    milestone_event = next(e for e in notifications_outbox if e["event"] == "milestone.added")
    assert milestone_event["tracking_number"] == tn
    assert milestone_event["location"] == "Kumba checkpoint"
    assert milestone_event["status"] == "In Transit"


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

def test_milestone_gets_geocoded(client, admin_token, monkeypatch):
    monkeypatch.setattr(geocode, "lookup", lambda location: (4.0511, 9.7679))
    tn = make_shipment(client, admin_token).json()["tracking_number"]
    add_milestone(client, admin_token, tn)

    body = client.get(f"/api/v1/shipments/track/{tn}").json()
    latest = body["milestones"][-1]
    assert latest["lat"] == pytest.approx(4.0511)
    assert latest["lng"] == pytest.approx(9.7679)


def test_shipment_endpoints_get_geocoded(client, admin_token, monkeypatch):
    coords = {"lagos, nigeria": (6.5244, 3.3792), "buea, cameroon": (4.1527, 9.241)}
    monkeypatch.setattr(geocode, "lookup", lambda location: coords.get(location.strip().lower()))
    tn = make_shipment(client, admin_token).json()["tracking_number"]

    body = client.get(f"/api/v1/shipments/track/{tn}").json()
    assert body["origin_lat"] == pytest.approx(6.5244)
    assert body["dest_lat"] == pytest.approx(4.1527)


def test_geocode_failure_is_graceful(client, admin_token, monkeypatch):
    monkeypatch.setattr(geocode, "lookup", lambda location: None)
    tn = make_shipment(client, admin_token).json()["tracking_number"]
    r = add_milestone(client, admin_token, tn)
    assert r.status_code == 200
    assert r.json()["milestones"][-1]["lat"] is None
