"""
Populates the local database with sample shipments so the tracking flow can
be exercised end-to-end without the admin UI. Safe to re-run: it skips any
tracking number that already exists.
"""
from datetime import datetime, timedelta, timezone

from database import Base, engine, SessionLocal
import models

Base.metadata.create_all(bind=engine)


def _dt(days_ago: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


SAMPLE_SHIPMENTS = [
    {
        "tracking_number": "PCL085263034594XYZ",
        "origin": "Frankfurt, Germany",
        "destination": "Douala, Cameroon",
        "sender_name": "Muller Industrial Parts GmbH",
        "recipient_name": "Savage Tech Supplies",
        "carrier": "Prime Crest Logistics",
        "shipping_mode": "Air Express",
        "weight_kg": 18.50,
        "length_cm": 48,
        "width_cm": 35,
        "height_cm": 28,
        "estimated_delivery": _dt(-2),
        "milestones": [
            ("Order Registered", "Frankfurt, Germany", "Shipment created and registered in the system.", 6),
            ("Departed Origin", "Frankfurt Airport (FRA)", "Package handed to carrier and scanned for departure.", 5),
            ("In Transit", "Doha, Qatar", "In transit through international hub.", 3.5),
            ("Customs Clearance", "Douala, Cameroon", "Held for customs inspection and duty assessment.", 1),
        ],
    },
    {
        "tracking_number": "PCL994810238120ABC",
        "origin": "Paris, France",
        "destination": "Yaoundé, Cameroon",
        "sender_name": "Atelier Nord Distribution",
        "recipient_name": "Yaoundé Retail Group",
        "carrier": "Prime Crest Logistics",
        "shipping_mode": "Air Express",
        "weight_kg": 6.2,
        "length_cm": 30,
        "width_cm": 20,
        "height_cm": 15,
        "estimated_delivery": _dt(-1),
        "milestones": [
            ("Order Registered", "Paris, France", "Shipment created and registered in the system.", 3),
            ("Departed Origin", "Paris Charles de Gaulle (CDG)", "Package handed to carrier and scanned for departure.", 2.2),
            ("In Transit", "Casablanca, Morocco", "In transit through regional hub.", 1),
        ],
    },
]


def run():
    db = SessionLocal()
    try:
        for entry in SAMPLE_SHIPMENTS:
            existing = (
                db.query(models.Shipment)
                .filter(models.Shipment.tracking_number == entry["tracking_number"])
                .first()
            )
            if existing:
                print(f"Skipping {entry['tracking_number']} (already seeded)")
                continue

            milestones = entry.pop("milestones")
            shipment = models.Shipment(status=milestones[-1][0], **entry)
            db.add(shipment)
            db.flush()

            for status_, location, note, days_ago in milestones:
                db.add(
                    models.Milestone(
                        shipment_id=shipment.id,
                        status=status_,
                        location=location,
                        note=note,
                        timestamp=_dt(days_ago),
                    )
                )
            print(f"Seeded {shipment.tracking_number}")

        db.commit()
        print("\nDone. Try these tracking numbers in the app:")
        for entry in SAMPLE_SHIPMENTS:
            print(f"  - {entry['tracking_number']}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
