from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text

from backend.database import Base


class Patient(Base):

    __tablename__ = "patients"

    patient_id = Column(
        String(20),
        primary_key=True
    )

    name = Column(
        String(100),
        nullable=False
    )

    age = Column(
        Integer,
        nullable=False
    )

    emergency_level = Column(
        String(20),
        nullable=False
    )

    status = Column(
        String(30),
        nullable=False
    )

    waiting_since = Column(
        DateTime,
        nullable=True
    )

    required_equipment_type = Column(
        String(50),
        nullable=True
    )

    # =========================================================
    # OPERATIONAL CARE STATUS
    # =========================================================

    care_status = Column(
        String(30),
        nullable=False,
        default="active"
    )

    transfer_ready = Column(
        Boolean,
        nullable=False,
        default=False
    )

    expected_release_at = Column(
        DateTime,
        nullable=True
    )

    staff_note = Column(
        Text,
        nullable=True
    )