from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey
)

from sqlalchemy.sql import func

from backend.database import Base


class Assignment(Base):

    __tablename__ = "assignments"

    assignment_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    patient_id = Column(
        String(20),
        ForeignKey("patients.patient_id")
    )

    bed_id = Column(
        String(20),
        ForeignKey("beds.bed_id")
    )

    staff_id = Column(
        String(20),
        ForeignKey("staff.staff_id")
    )

    equipment_id = Column(
        String(20),
        ForeignKey("equipment.equipment_id")
    )

    assigned_at = Column(
        DateTime,
        server_default=func.now()
    )