from sqlalchemy import Column, String

from backend.database import Base


class Equipment(Base):

    __tablename__ = "equipment"

    equipment_id = Column(
        String(20),
        primary_key=True
    )

    equipment_type = Column(
        String(50),
        nullable=False
    )

    status = Column(
        String(20),
        nullable=False
    )

    location = Column(
        String(100)
    )