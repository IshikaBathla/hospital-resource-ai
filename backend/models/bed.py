from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey
)

from backend.database import Base


class Bed(Base):

    __tablename__ = "beds"

    bed_id = Column(
        String(20),
        primary_key=True
    )

    ward = Column(
        String(50),
        nullable=False
    )

    status = Column(
        String(20),
        nullable=False
    )

    patient_id = Column(
        String(20),
        ForeignKey("patients.patient_id")
    )

    expected_release_at = Column(
        DateTime,
        nullable=True
    )