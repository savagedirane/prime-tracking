"""
Server-side geocoding: resolves free-text locations ("Douala, Cameroon")
into latitude/longitude once, at write time, so the public map never has to
guess (the old approach was a hardcoded city dictionary in the browser).

Uses OpenStreetMap's Nominatim — free, no API key. We respect its usage
policy explicitly:
  * a descriptive User-Agent identifying the app (required by policy)
  * at most ~1 request/second (a lock + minimum spacing enforces this even
    when an import creates hundreds of shipments at once)
  * results cached forever per location string (cities don't move)

Set GEOCODE_ENABLED=false to disable outbound lookups entirely (air-gapped
installs / CI). Failures are graceful: the milestone/shipment simply keeps
working with null coordinates until the next write retries it.
"""
import os
import threading
import time
import urllib.parse
import urllib.request

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = os.environ.get(
    "GEOCODER_USER_AGENT", "prime-crest-tracking/1.0 (set GEOCODER_USER_AGENT with your contact email)"
)
ENABLED = os.environ.get("GEOCODE_ENABLED", "true").lower() not in ("0", "false", "no")
MIN_INTERVAL = 1.1  # seconds between outbound requests (Nominatim policy)

_cache: dict[str, tuple[float, float] | None] = {}
_lock = threading.Lock()
_last_request = 0.0


def lookup(location: str) -> tuple[float, float] | None:
    """Geocode a location string. Returns (lat, lng) or None on any failure.
    Thread-safe, cached, rate-limited."""
    global _last_request
    if not ENABLED or not location or not location.strip():
        return None

    key = location.strip().lower()
    with _lock:
        if key in _cache:
            return _cache[key]

    query = urllib.parse.urlencode({"q": location, "format": "json", "limit": 1})
    req = urllib.request.Request(
        f"{NOMINATIM_URL}?{query}", headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with _lock:
            # Global pacing: keep >= MIN_INTERVAL between outbound calls.
            wait = MIN_INTERVAL - (time.monotonic() - _last_request)
            if wait > 0:
                time.sleep(wait)
            _last_request = time.monotonic()
        with urllib.request.urlopen(req, timeout=6) as resp:
            import json

            results = json.loads(resp.read().decode("utf-8"))
        if not results:
            with _lock:
                _cache[key] = None
            return None
        coords = (float(results[0]["lat"]), float(results[0]["lon"]))
        with _lock:
            _cache[key] = coords
        return coords
    except Exception:
        # Network down / rate-limited / bad response — never break a write.
        return None


# ---------------------------------------------------------------------------
# Background tasks (wired from main.py via BackgroundTasks)
# ---------------------------------------------------------------------------

def _after_coordinates_change(tracking_number: str) -> None:
    """Coordinates changed: drop the cached read model and push live updates."""
    import cache as cache_mod
    import events
    from snapshots import shipment_snapshot_json

    cache_mod.invalidate(tracking_number)
    snapshot = shipment_snapshot_json(tracking_number)
    if snapshot:
        events.publish(tracking_number, snapshot)


def refresh_milestone_coordinates(milestone_id: int) -> None:
    """Background task: geocode one milestone's location and store it."""
    import models
    from database import SessionLocal

    db = SessionLocal()
    try:
        milestone = db.get(models.Milestone, milestone_id)
        if not milestone or milestone.lat is not None:
            return
        coords = lookup(milestone.location)
        if not coords:
            return
        milestone.lat, milestone.lng = coords
        tracking_number = milestone.shipment.tracking_number
        db.commit()
        _after_coordinates_change(tracking_number)
    except Exception:
        db.rollback()
    finally:
        db.close()


def refresh_shipment_coordinates(shipment_id: str) -> None:
    """Background task: geocode a shipment's origin + destination."""
    import models
    from database import SessionLocal

    db = SessionLocal()
    try:
        shipment = db.get(models.Shipment, shipment_id)
        if not shipment:
            return
        changed = False
        if shipment.origin_lat is None:
            coords = lookup(shipment.origin)
            if coords:
                shipment.origin_lat, shipment.origin_lng = coords
                changed = True
        if shipment.dest_lat is None:
            coords = lookup(shipment.destination)
            if coords:
                shipment.dest_lat, shipment.dest_lng = coords
                changed = True
        if not changed:
            return
        db.commit()
        _after_coordinates_change(shipment.tracking_number)
    except Exception:
        db.rollback()
    finally:
        db.close()
