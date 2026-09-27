from sqlalchemy.orm import Session

from backend.models.patient import Patient
from backend.models.bed import Bed


def can_reallocate_patient(
    db: Session,
    patient_id: str
):
    """
    Check whether an admitted patient can be considered
    for reallocation.

    This function only validates the constraint.
    It does NOT perform any reallocation.
    """

    patient = (
        db.query(Patient)
        .filter(
            Patient.patient_id == patient_id
        )
        .first()
    )

    if not patient:
        return (
            False,
            "Patient not found"
        )

    if patient.status.lower() != "admitted":
        return (
            False,
            "Patient is not currently admitted"
        )

    if patient.emergency_level.lower() == "critical":
        return (
            False,
            "Critical patient cannot be reallocated"
        )

    return (
        True,
        "Patient can be considered for reallocation"
    )


def get_reallocation_candidates(
    db: Session,
    target_patient_id: str
):
    """
    Find occupied ICU beds whose patients can potentially
    be reallocated.

    The target patient itself is excluded.

    No database state is modified.
    """

    candidates = []

    beds = (
        db.query(Bed)
        .filter(
            Bed.ward == "ICU",
            Bed.status == "occupied"
        )
        .order_by(Bed.bed_id)
        .all()
    )

    for bed in beds:

        if not bed.patient_id:
            continue

        # Do not consider the target patient itself.
        if bed.patient_id == target_patient_id:
            continue

        allowed, reason = can_reallocate_patient(
            db,
            bed.patient_id
        )

        candidates.append({
            "bed_id": bed.bed_id,
            "patient_id": bed.patient_id,
            "allowed": allowed,
            "reason": reason
        })

    return candidates