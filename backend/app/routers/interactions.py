"""Read-only REST endpoints (HCP directory, logged data) used by the UI/demo."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import HCP, Interaction, ScheduledFollowUp
from ..schemas import HCPOut

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/hcps", response_model=list[HCPOut])
def list_hcps(db: Session = Depends(get_db)):
    return db.execute(select(HCP).order_by(HCP.name)).scalars().all()


@router.get("/interactions")
def list_interactions(hcp_name: str | None = None, limit: int = 20,
                      db: Session = Depends(get_db)):
    stmt = select(Interaction).order_by(Interaction.id.desc()).limit(max(1, min(limit, 100)))
    if hcp_name:
        stmt = (
            select(Interaction)
            .where(Interaction.hcp_name.ilike(f"%{hcp_name}%"))
            .order_by(Interaction.id.desc())
            .limit(max(1, min(limit, 100)))
        )
    rows = db.execute(stmt).scalars().all()
    return [r.to_dict() for r in rows]


@router.get("/followups")
def list_followups(db: Session = Depends(get_db)):
    rows = (
        db.execute(select(ScheduledFollowUp).order_by(ScheduledFollowUp.id.desc()))
        .scalars()
        .all()
    )
    return [r.to_dict() for r in rows]
