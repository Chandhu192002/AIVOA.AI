"""Seed a handful of demo HCPs so the search / history tools have data."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import HCP

SEED_HCPS = [
    {"name": "Dr. Smith", "specialty": "Oncology", "institution": "City General Hospital"},
    {"name": "Dr. John", "specialty": "Cardiology", "institution": "Heartcare Institute"},
    {"name": "Dr. Sharma", "specialty": "Oncology", "institution": "Apollo Medical Center"},
    {"name": "Dr. Patel", "specialty": "Neurology", "institution": "NeuroLife Clinic"},
    {"name": "Dr. Mehta", "specialty": "Endocrinology", "institution": "Sunrise Hospital"},
    {"name": "Dr. Gupta", "specialty": "Pulmonology", "institution": "Breathe Well Clinic"},
]


def seed_hcps(db: Session) -> None:
    existing = db.execute(select(HCP.id).limit(1)).first()
    if existing:
        return
    for row in SEED_HCPS:
        db.add(HCP(**row))
    db.commit()
