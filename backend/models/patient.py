from sqlalchemy import Column, String, Integer

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