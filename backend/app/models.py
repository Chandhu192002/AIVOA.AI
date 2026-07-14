"""ORM models for the HCP module."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class HCP(Base):
    """Healthcare Professional master record (seeded demo data)."""

    __tablename__ = "hcps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    specialty: Mapped[str] = mapped_column(String(120), default="")
    institution: Mapped[str] = mapped_column(String(160), default="")


class Interaction(Base):
    """A single logged interaction between a field rep and an HCP."""

    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hcp_name: Mapped[str] = mapped_column(String(120), index=True)
    interaction_type: Mapped[str] = mapped_column(String(40), default="Meeting")
    date: Mapped[str] = mapped_column(String(10), default="")   # YYYY-MM-DD
    time: Mapped[str] = mapped_column(String(5), default="")    # HH:MM (24h)
    attendees: Mapped[str] = mapped_column(Text, default="")
    topics_discussed: Mapped[str] = mapped_column(Text, default="")
    materials_shared: Mapped[list] = mapped_column(JSON, default=list)
    samples_distributed: Mapped[list] = mapped_column(JSON, default=list)
    sentiment: Mapped[str] = mapped_column(String(10), default="Neutral")
    outcomes: Mapped[str] = mapped_column(Text, default="")
    follow_up_actions: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hcp_name": self.hcp_name,
            "interaction_type": self.interaction_type,
            "date": self.date,
            "time": self.time,
            "attendees": self.attendees,
            "topics_discussed": self.topics_discussed,
            "materials_shared": self.materials_shared or [],
            "samples_distributed": self.samples_distributed or [],
            "sentiment": self.sentiment,
            "outcomes": self.outcomes,
            "follow_up_actions": self.follow_up_actions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ScheduledFollowUp(Base):
    """Follow-up task created by the `schedule_follow_up` agent tool."""

    __tablename__ = "scheduled_followups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("interactions.id"), nullable=True
    )
    hcp_name: Mapped[str] = mapped_column(String(120), index=True)
    due_date: Mapped[str] = mapped_column(String(10), default="")  # YYYY-MM-DD
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "interaction_id": self.interaction_id,
            "hcp_name": self.hcp_name,
            "due_date": self.due_date,
            "note": self.note,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
