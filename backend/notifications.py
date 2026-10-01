"""
Outbound notifications for shipment events (the roadmap's email/WhatsApp
hook), delivered through a GENERIC WEBHOOK so any provider works without
this codebase depending on one:

    NOTIFY_WEBHOOK_URL=https://hook.eu2.make.com/...        (Make / Zapier /
    https://chat.whatsapp.com/...      n8n / your own receiver -> email,
                                       WhatsApp, SMS, Slack, whatever)

Payload shape (JSON POST):
    {
      "event": "milestone.added",          # or "shipment.created"
      "tracking_number": "PCL...",
      "status": "In Transit",
      "location": "Abuja hub",
      "note": "...",                       # milestone events only
      "recipient_name": "...",
      "origin": "...", "destination": "...",
      "estimated_delivery": "2026-10-02T00:00:00Z" | null,
      "timestamp": "2026-09-30T20:15:00Z"
    }

Delivery runs as a FastAPI BackgroundTask (never blocks the admin's HTTP
request), with one retry and full error containment — a dead webhook can
never fail a shipment write. When you outgrow single-instance delivery
(guarantees, fan-out to many providers), graduate to arq/Celery + Redis and
keep this module as the worker's job body.
"""
import json
import logging
import os
import urllib.request
from datetime import datetime, timezone

log = logging.getLogger("notifications")

NOTIFY_WEBHOOK_URL = os.environ.get("NOTIFY_WEBHOOK_URL", "")
TIMEOUT_SECONDS = 6


def notify_event(payload: dict) -> None:
    """Send one event to the configured webhook. Fire-and-forget by design:
    logs problems, never raises."""
    if not NOTIFY_WEBHOOK_URL:
        # No webhook configured — log so the flow is still observable in dev.
        log.info("notification (no webhook configured): %s", json.dumps(payload))
        return

    body = json.dumps(payload).encode("utf-8")
    for attempt in (1, 2):  # one retry on failure
        try:
            req = urllib.request.Request(
                NOTIFY_WEBHOOK_URL,
                data=body,
                headers={"Content-Type": "application/json", "User-Agent": "prime-crest-notifier/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                if resp.status < 300:
                    return
                log.warning("webhook returned HTTP %s (attempt %s)", resp.status, attempt)
        except Exception as exc:  # noqa: BLE001 — containment is the point
            log.warning("webhook delivery failed (attempt %s): %s", attempt, exc)
    log.error("webhook delivery abandoned for event=%s tn=%s", payload.get("event"), payload.get("tracking_number"))


def milestone_payload(event: str, shipment, milestone) -> dict:
    return {
        "event": event,
        "tracking_number": shipment.tracking_number,
        "status": milestone.status,
        "location": milestone.location,
        "note": milestone.note,
        "recipient_name": shipment.recipient_name,
        "origin": shipment.origin,
        "destination": shipment.destination,
        "estimated_delivery": shipment.estimated_delivery.isoformat() if shipment.estimated_delivery else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def shipment_created_payload(shipment) -> dict:
    return {
        "event": "shipment.created",
        "tracking_number": shipment.tracking_number,
        "status": shipment.status,
        "location": shipment.origin,
        "recipient_name": shipment.recipient_name,
        "origin": shipment.origin,
        "destination": shipment.destination,
        "estimated_delivery": shipment.estimated_delivery.isoformat() if shipment.estimated_delivery else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
