from sqlalchemy.orm import Session

from backend.models.equipment import Equipment


def get_all_equipment(db: Session):

    return db.query(Equipment).all()


def get_equipment_by_id(
    db: Session,
    equipment_id: str
):

    return (
        db.query(Equipment)
        .filter(
            Equipment.equipment_id == equipment_id
        )
        .first()
    )


def get_available_equipment(
    db: Session,
    equipment_type: str | None = None,
    location: str | None = None
):

    query = (
        db.query(Equipment)
        .filter(
            Equipment.status == "available"
        )
    )

    if equipment_type:
        query = query.filter(
            Equipment.equipment_type == equipment_type
        )

    if location:
        query = query.filter(
            Equipment.location == location
        )

    return query.all()