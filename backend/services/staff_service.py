from sqlalchemy.orm import Session

from backend.models.staff import Staff


def get_all_staff(db: Session):

    return db.query(Staff).all()


def get_staff_by_id(
    db: Session,
    staff_id: str
):

    return (
        db.query(Staff)
        .filter(
            Staff.staff_id == staff_id
        )
        .first()
    )


def get_available_staff(
    db: Session,
    role: str | None = None,
    department: str | None = None
):

    query = (
        db.query(Staff)
        .filter(
            Staff.status == "available"
        )
    )

    if role:
        query = query.filter(
            Staff.role == role
        )

    if department:
        query = query.filter(
            Staff.department == department
        )

    return query.all()