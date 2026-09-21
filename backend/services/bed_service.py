from sqlalchemy.orm import Session

from backend.models.bed import Bed


def get_all_beds(db: Session):

    return db.query(Bed).all()


def get_bed_by_id(
    db: Session,
    bed_id: str
):

    return (
        db.query(Bed)
        .filter(
            Bed.bed_id == bed_id
        )
        .first()
    )


def get_available_beds(
    db: Session,
    ward: str | None = None
):

    query = (
        db.query(Bed)
        .filter(
            Bed.status == "available"
        )
    )

    if ward:
        query = query.filter(
            Bed.ward == ward
        )

    return query.all()


def update_bed(
    db: Session,
    bed_id: str,
    status: str,
    patient_id: str | None = None,
    expected_release_at=None
):

    bed = get_bed_by_id(
        db,
        bed_id
    )

    if not bed:
        return None

    bed.status = status
    bed.patient_id = patient_id
    bed.expected_release_at = expected_release_at

    if status == "available":
        bed.patient_id = None
        bed.expected_release_at = None

    db.commit()

    db.refresh(bed)

    return bed