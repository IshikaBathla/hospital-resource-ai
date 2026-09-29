from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from backend.database import Base


class RecommendationOutcome(Base):
    __tablename__ = "recommendation_outcomes"

    outcome_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    recommendation_id = Column(
        Integer,
        nullable=False
    )

    patient_id = Column(
        String(20),
        nullable=False
    )

    decision = Column(
        String(20),
        nullable=False
    )

    recommended_bed_id = Column(
        String(20),
        nullable=True
    )

    actual_bed_id = Column(
        String(20),
        nullable=True
    )

    recommended_staff_id = Column(
        String(20),
        nullable=True
    )

    actual_staff_id = Column(
        String(20),
        nullable=True
    )

    recommended_equipment_id = Column(
        String(20),
        nullable=True
    )

    actual_equipment_id = Column(
        String(20),
        nullable=True
    )

    outcome_status = Column(
        String(30),
        nullable=False
    )

    notes = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.now
    )