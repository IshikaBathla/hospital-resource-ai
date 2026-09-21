from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models.patient import Patient
from backend.models.bed import Bed
from backend.models.staff import Staff
from backend.models.equipment import Equipment

from backend.services.constraint_service import (
    get_reallocation_candidates
)

from backend.services.procedure_service import (
    refresh_expired_procedures
)


def get_available_bed(
    db: Session,
    ward: str
):

    return (
        db.query(Bed)
        .filter(
            Bed.ward == ward,
            Bed.status == "available"
        )
        .order_by(Bed.bed_id)
        .first()
    )


def get_future_beds(
    db: Session,
    ward: str
):

    now = datetime.now()

    return (
        db.query(Bed)
        .filter(
            Bed.ward == ward,
            Bed.status == "occupied",
            Bed.expected_release_at.isnot(None),
            Bed.expected_release_at > now
        )
        .order_by(
            Bed.expected_release_at
        )
        .all()
    )


def get_available_staff(
    db: Session,
    department: str
):

    return (
        db.query(Staff)
        .filter(
            Staff.department == department,
            Staff.status == "available"
        )
        .order_by(Staff.staff_id)
        .all()
    )


def get_available_equipment(
    db: Session,
    location: str
):

    return (
        db.query(Equipment)
        .filter(
            Equipment.location == location,
            Equipment.status == "available"
        )
        .order_by(Equipment.equipment_id)
        .all()
    )


def calculate_wait_minutes(
    release_time
):

    if not release_time:
        return None

    if release_time.tzinfo is None:

        now = datetime.now()

    else:

        now = datetime.now(
            timezone.utc
        )

    seconds = (
        release_time - now
    ).total_seconds()

    return max(
        0,
        round(seconds / 60)
    )


def generate_recommendation(
    db: Session,
    patient_id: str
):

    # Automatically release expired resources
    refresh_expired_procedures(db)

    patient = (
        db.query(Patient)
        .filter(
            Patient.patient_id == patient_id
        )
        .first()
    )

    if not patient:

        return {
            "status": "error",
            "message": "Patient not found"
        }

    emergency_level = (
        patient.emergency_level.lower()
    )

    # =====================================
    # CRITICAL / HIGH
    # =====================================

    if emergency_level in [
        "critical",
        "high"
    ]:

        # -----------------------------
        # ICU available now
        # -----------------------------

        icu_bed = get_available_bed(
            db,
            "ICU"
        )

        if icu_bed:

            return {
                "status": "success",
                "patient_id": patient_id,
                "recommendation_type":
                    "immediate_resource",

                "recommended_action": {
                    "type":
                        "assign_available_bed",

                    "bed_id":
                        icu_bed.bed_id,

                    "ward":
                        icu_bed.ward
                },

                "reason":
                    "An ICU bed is currently available.",

                "human_decision_required":
                    True
            }

        # -----------------------------
        # Future ICU
        # -----------------------------

        future_beds = get_future_beds(
            db,
            "ICU"
        )

        if future_beds:

            bed = future_beds[0]

            wait_minutes = (
                calculate_wait_minutes(
                    bed.expected_release_at
                )
            )

            return {
                "status": "success",
                "patient_id": patient_id,
                "recommendation_type":
                    "future_resource",

                "recommended_action": {
                    "type":
                        "wait_for_resource",

                    "bed_id":
                        bed.bed_id,

                    "ward":
                        bed.ward,

                    "expected_available_at":
                        bed.expected_release_at,

                    "expected_wait_minutes":
                        wait_minutes
                },

                "reason":
                    "No ICU bed is currently available. "
                    "The recommended bed has an expected "
                    "release time.",

                "human_decision_required":
                    True
            }

        # -----------------------------
        # Reallocation
        # -----------------------------

        general_bed = get_available_bed(
            db,
            "General"
        )

        if general_bed:

            candidates = (
                get_reallocation_candidates(
                    db,
                    patient_id
                )
            )

            allowed_candidates = [
                candidate
                for candidate in candidates
                if candidate["allowed"]
            ]

            if allowed_candidates:

                candidate = (
                    allowed_candidates[0]
                )

                return {
                    "status": "success",
                    "patient_id": patient_id,
                    "recommendation_type":
                        "reallocation",

                    "recommended_action": {
                        "type":
                            "reallocate_existing_patient",

                        "target_bed":
                            candidate["bed_id"],

                        "target_patient":
                            candidate["patient_id"],

                        "replacement_bed":
                            general_bed.bed_id
                    },

                    "reason":
                        "No ICU bed is currently available. "
                        "A feasible reallocation candidate "
                        "was identified.",

                    "human_decision_required":
                        True
                }

        # -----------------------------
        # General fallback
        # -----------------------------

        general_bed = get_available_bed(
            db,
            "General"
        )

        if general_bed:

            return {
                "status": "success",
                "patient_id": patient_id,
                "recommendation_type":
                    "fallback_resource",

                "recommended_action": {
                    "type":
                        "assign_general_bed",

                    "bed_id":
                        general_bed.bed_id,

                    "ward":
                        general_bed.ward
                },

                "reason":
                    "No ICU bed is currently available. "
                    "A General ward bed is available as "
                    "a fallback resource.",

                "human_decision_required":
                    True
            }

        # -----------------------------
        # No action
        # -----------------------------

        return {
            "status": "success",
            "patient_id": patient_id,
            "recommendation_type":
                "no_feasible_action",

            "recommended_action": None,

            "reason":
                "No feasible bed allocation action "
                "is currently available.",

            "human_decision_required":
                True
        }

    # =====================================
    # MEDIUM / LOW
    # =====================================

    general_bed = get_available_bed(
        db,
        "General"
    )

    if general_bed:

        return {
            "status": "success",
            "patient_id": patient_id,
            "recommendation_type":
                "immediate_resource",

            "recommended_action": {
                "type":
                    "assign_available_bed",

                "bed_id":
                    general_bed.bed_id,

                "ward":
                    general_bed.ward
            },

            "reason":
                "A General ward bed is currently available.",

            "human_decision_required":
                True
        }

    future_beds = get_future_beds(
        db,
        "General"
    )

    if future_beds:

        bed = future_beds[0]

        return {
            "status": "success",
            "patient_id": patient_id,
            "recommendation_type":
                "future_resource",

            "recommended_action": {
                "type":
                    "wait_for_resource",

                "bed_id":
                    bed.bed_id,

                "ward":
                    bed.ward,

                "expected_available_at":
                    bed.expected_release_at,

                "expected_wait_minutes":
                    calculate_wait_minutes(
                        bed.expected_release_at
                    )
            },

            "reason":
                "No General ward bed is currently "
                "available, but a bed is expected "
                "to be released.",

            "human_decision_required":
                True
        }

    return {
        "status": "success",
        "patient_id": patient_id,
        "recommendation_type":
            "no_feasible_action",

        "recommended_action": None,

        "reason":
            "No feasible bed allocation action "
            "is currently available.",

        "human_decision_required":
            True
    }
from backend.models.recommendation import Recommendation


def save_recommendation(
    db: Session,
    recommendation_data: dict
):
    """
    Save generated recommendation into database.
    """

    action = recommendation_data.get(
        "recommended_action"
    )

    if not action:
        action = {}

    recommended_bed_id = (
        action.get("bed_id")
        or action.get("replacement_bed")
    )

    recommended_staff_id = (
        action.get("staff_id")
    )

    recommended_equipment_id = (
        action.get("equipment_id")
    )

    recommendation = Recommendation(
        patient_id=recommendation_data[
            "patient_id"
        ],

        recommendation_type=
            recommendation_data[
                "recommendation_type"
            ],

        recommended_bed_id=
            recommended_bed_id,

        recommended_staff_id=
            recommended_staff_id,

        recommended_equipment_id=
            recommended_equipment_id,

        reason=
            recommendation_data[
                "reason"
            ],

        status="pending"
    )

    db.add(recommendation)

    db.commit()

    db.refresh(recommendation)

    return recommendation
from backend.models.patient import Patient
from backend.models.recommendation import Recommendation


def get_highest_priority_waiting_patient(db: Session):
    patients = (
        db.query(Patient)
        .filter(Patient.status == "waiting")
        .all()
    )

    priority = {
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4
    }

    patients.sort(
        key=lambda patient: (
            priority.get(
                patient.emergency_level.lower(),
                99
            ),
            patient.patient_id
        )
    )

    for patient in patients:

        pending = (
            db.query(Recommendation)
            .filter(
                Recommendation.patient_id == patient.patient_id,
                Recommendation.status == "pending"
            )
            .first()
        )

        if not pending:
            return patient

    return None


def generate_automatic_recommendation(
    db: Session,
    released_bed_id: str
):
    patient = get_highest_priority_waiting_patient(db)

    if not patient:
        return None

    pending_bed_recommendation = (
        db.query(Recommendation)
        .filter(
            Recommendation.recommended_bed_id == released_bed_id,
            Recommendation.status == "pending"
        )
        .first()
    )

    if pending_bed_recommendation:
        return None

    recommendation_data = generate_recommendation(
        db,
        patient.patient_id
    )

    if recommendation_data.get("status") == "error":
        return None

    recommendation = save_recommendation(
        db,
        recommendation_data
    )

    return recommendation