from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)

from sqlalchemy.sql import func

from backend.database import Base


class Recommendation(Base):

    __tablename__ = "recommendations"

    recommendation_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    patient_id = Column(
        String(20),
        ForeignKey("patients.patient_id"),
        nullable=False
    )

    recommendation_type = Column(
        String(50),
        nullable=False
    )

    recommended_bed_id = Column(
        String(20)
    )

    recommended_staff_id = Column(
        String(20)
    )

    recommended_equipment_id = Column(
        String(20)
    )

    # -----------------------------------------------------
    # REALLOCATION SUPPORT
    # -----------------------------------------------------

    affected_patient_id = Column(
        String(20),
        ForeignKey("patients.patient_id"),
        nullable=True
    )

    affected_patient_current_bed_id = Column(
        String(20),
        nullable=True
    )

    affected_patient_replacement_bed_id = Column(
        String(20),
        nullable=True
    )

    reason = Column(
        Text,
        nullable=False
    )

    status = Column(
        String(20),
        default="pending"
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )