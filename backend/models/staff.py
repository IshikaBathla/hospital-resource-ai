from sqlalchemy import Column, String

from backend.database import Base


class Staff(Base):

    __tablename__ = "staff"

    staff_id = Column(
        String(20),
        primary_key=True
    )

    name = Column(
        String(100),
        nullable=False
    )

    role = Column(
        String(30),
        nullable=False
    )

    department = Column(
        String(50)
    )

    status = Column(
        String(20),
        nullable=False
    )