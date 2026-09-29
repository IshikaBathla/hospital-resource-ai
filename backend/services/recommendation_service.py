from datetime import datetime

import pandas as pd

from sqlalchemy.orm import Session

from backend.models.patient import Patient
from backend.models.bed import Bed
from backend.models.staff import Staff
from backend.models.equipment import Equipment
from backend.models.recommendation import Recommendation

from backend.services.constraint_service import (
    get_reallocation_candidates
)

from backend.services.procedure_service import (
    refresh_expired_procedures
)

from backend.services.forecasting_service import (
    load_patient_arrivals,
    prepare_department_hourly_data,
    train_department_forecast_models,
    forecast_department_next_24_hours,
    get_forecast_pressure
)


# =========================================================
# BED HELPERS
# =========================================================

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
        .order_by(Bed.expected_release_at)
        .all()
    )


# =========================================================
# STAFF HELPERS
# =========================================================

def get_available_staff(
    db: Session,
    department: str | None = None
):
    query = (
        db.query(Staff)
        .filter(
            Staff.status == "available"
        )
    )

    if department:
        query = query.filter(
            Staff.department == department
        )

    return (
        query
        .order_by(Staff.staff_id)
        .all()
    )


def get_recommended_staff(
    db: Session,
    ward: str
):
    staff = get_available_staff(
        db,
        ward
    )

    if staff:
        return staff[0]

    return None


# =========================================================
# EQUIPMENT HELPERS
# =========================================================

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

    return (
        query
        .order_by(Equipment.equipment_id)
        .all()
    )


def get_recommended_equipment(
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

    return (
        query
        .order_by(Equipment.equipment_id)
        .first()
    )


# =========================================================
# WAIT TIME
# =========================================================

def calculate_wait_minutes(
    release_time
):
    if not release_time:
        return None

    now = datetime.now()

    difference = (
        release_time - now
    ).total_seconds() / 60

    return max(
        0,
        round(difference)
    )


# =========================================================
# BED ACTION
# =========================================================

def build_bed_action(
    db: Session,
    bed: Bed
):
    staff = get_recommended_staff(
        db,
        bed.ward
    )

    equipment = get_recommended_equipment(
        db,
        location=bed.ward
    )

    return {
        "type": "assign_available_bed",
        "bed_id": bed.bed_id,
        "ward": bed.ward,
        "staff_id": (
            staff.staff_id
            if staff
            else None
        ),
        "equipment_id": (
            equipment.equipment_id
            if equipment
            else None
        )
    }


# =========================================================
# GENERATE RECOMMENDATION
# =========================================================

def generate_recommendation(
    db: Session,
    patient_id: str
):

    # Refresh expired procedures
    refresh_expired_procedures(db)

    # -----------------------------------------------------
    # Find patient
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # ML forecast pressure
    # -----------------------------------------------------

    icu_pressure = get_department_pressure(
        db,
        "ICU"
    )

    general_pressure = get_department_pressure(
        db,
        "General"
    )

    # =====================================================
    # CRITICAL / HIGH PRIORITY
    # =====================================================

    if emergency_level in {
        "critical",
        "high"
    }:

        # -------------------------------------------------
        # 1. ICU BED AVAILABLE
        # -------------------------------------------------

        bed = get_available_bed(
            db,
            "ICU"
        )

        if bed:

            staff = get_recommended_staff(
                db,
                "ICU"
            )

            equipment = get_recommended_equipment(
                db,
                location="ICU"
            )

            return {
                "patient_id": patient_id,

                "priority": emergency_level,

                "recommended_action": {
                    "type": "immediate_resource",

                    "bed_id": bed.bed_id,

                    "ward": bed.ward,

                    "staff_id": (
                        staff.staff_id
                        if staff
                        else None
                    ),

                    "equipment_id": (
                        equipment.equipment_id
                        if equipment
                        else None
                    )
                },

                "reason": (
                    "An ICU bed is currently available."
                    + (
                        f" Forecast indicates ICU pressure with "
                        f"{icu_pressure['predicted_24h_arrivals']} "
                        f"predicted arrivals over the next 24 hours."
                        if icu_pressure
                        else ""
                    )
                ),

                "expected_wait_minutes": 0
            }

        # -------------------------------------------------
        # 2. FUTURE ICU BED
        # -------------------------------------------------

        future_beds = get_future_beds(
            db,
            "ICU"
        )

        if future_beds:

            future_bed = future_beds[0]

            staff = get_recommended_staff(
                db,
                "ICU"
            )

            equipment = get_recommended_equipment(
                db,
                location="ICU"
            )

            wait_minutes = calculate_wait_minutes(
                future_bed.expected_release_at
            )

            return {
                "patient_id": patient_id,

                "priority": emergency_level,

                "recommended_action": {
                    "type": "future_resource",

                    "bed_id": future_bed.bed_id,

                    "ward": future_bed.ward,

                    "expected_release_at":
                        future_bed.expected_release_at,

                    "staff_id": (
                        staff.staff_id
                        if staff
                        else None
                    ),

                    "equipment_id": (
                        equipment.equipment_id
                        if equipment
                        else None
                    )
                },

                "reason": (
                    "No ICU bed is currently available, "
                    "but an ICU bed is expected to be "
                    "released."
                    + (
                        f" ML forecast indicates ICU pressure with "
                        f"{icu_pressure['predicted_24h_arrivals']} "
                        f"predicted arrivals over the next 24 hours."
                        if icu_pressure
                        else ""
                    )
                ),

                "expected_wait_minutes":
                    wait_minutes
            }

        # -------------------------------------------------
        # 3. REALLOCATION
        # -------------------------------------------------

        candidates = get_reallocation_candidates(
            db,
            patient_id
        )

        allowed_candidates = [
            candidate
            for candidate in candidates
            if candidate["allowed"]
        ]

        if allowed_candidates:

            candidate = allowed_candidates[0]

            replacement_bed = get_available_bed(
                db,
                "General"
            )

            if replacement_bed:

                staff = get_recommended_staff(
                    db,
                    "ICU"
                )

                equipment = get_recommended_equipment(
                    db,
                    location="ICU"
                )

                return {
                    "patient_id": patient_id,

                    "priority": emergency_level,

                    "recommended_action": {
                        "type": "reallocation",

                        "replacement_bed":
                            replacement_bed.bed_id,

                        "target_bed":
                            candidate["bed_id"],

                        "target_patient_id":
                            candidate["patient_id"],

                        "staff_id": (
                            staff.staff_id
                            if staff
                            else None
                        ),

                        "equipment_id": (
                            equipment.equipment_id
                            if equipment
                            else None
                        )
                    },

                    "reason": (
                        "No ICU bed is currently available. "
                        "A feasible patient reallocation "
                        "can create ICU capacity."
                        + (
                            f" ML forecast indicates ICU pressure with "
                            f"{icu_pressure['predicted_24h_arrivals']} "
                            f"predicted arrivals over the next 24 hours."
                            if icu_pressure
                            else ""
                        )
                    ),

                    "expected_wait_minutes": 0
                }

        # -------------------------------------------------
        # 4. GENERAL FALLBACK
        # -------------------------------------------------

        general_bed = get_available_bed(
            db,
            "General"
        )

        if general_bed:

            staff = get_recommended_staff(
                db,
                "General"
            )

            equipment = get_recommended_equipment(
                db,
                location="General"
            )

            return {
                "patient_id": patient_id,

                "priority": emergency_level,

                "recommended_action": {
                    "type": "fallback_resource",

                    "bed_id":
                        general_bed.bed_id,

                    "ward":
                        general_bed.ward,

                    "staff_id": (
                        staff.staff_id
                        if staff
                        else None
                    ),

                    "equipment_id": (
                        equipment.equipment_id
                        if equipment
                        else None
                    )
                },

                "reason": (
                    "No ICU capacity is currently "
                    "available, so a General ward bed "
                    "is recommended as a fallback."
                    + (
                        f" ICU forecast pressure is "
                        f"{icu_pressure['status']}."
                        if icu_pressure
                        else ""
                    )
                ),

                "expected_wait_minutes": 0
            }

        return {
            "patient_id": patient_id,

            "priority": emergency_level,

            "recommended_action": None,

            "reason": (
                "No feasible bed allocation is "
                "currently available."
            ),

            "expected_wait_minutes": None
        }

    # =====================================================
    # MEDIUM / LOW PRIORITY
    # =====================================================

    general_bed = get_available_bed(
        db,
        "General"
    )

    if general_bed:

        staff = get_recommended_staff(
            db,
            "General"
        )

        equipment = get_recommended_equipment(
            db,
            location="General"
        )

        return {
            "patient_id": patient_id,

            "priority": emergency_level,

            "recommended_action": {
                "type": "immediate_resource",

                "bed_id":
                    general_bed.bed_id,

                "ward":
                    general_bed.ward,

                "staff_id": (
                    staff.staff_id
                    if staff
                    else None
                ),

                "equipment_id": (
                    equipment.equipment_id
                    if equipment
                    else None
                )
            },

            "reason": (
                "A General ward bed is currently available."
            ),

            "expected_wait_minutes": 0
        }

    # -----------------------------------------------------
    # FUTURE GENERAL BED
    # -----------------------------------------------------

    future_beds = get_future_beds(
        db,
        "General"
    )

    if future_beds:

        future_bed = future_beds[0]

        staff = get_recommended_staff(
            db,
            "General"
        )

        equipment = get_recommended_equipment(
            db,
            location="General"
        )

        wait_minutes = calculate_wait_minutes(
            future_bed.expected_release_at
        )

        return {
            "patient_id": patient_id,

            "priority": emergency_level,

            "recommended_action": {
                "type": "future_resource",

                "bed_id":
                    future_bed.bed_id,

                "ward":
                    future_bed.ward,

                "expected_release_at":
                    future_bed.expected_release_at,

                "staff_id": (
                    staff.staff_id
                    if staff
                    else None
                ),

                "equipment_id": (
                    equipment.equipment_id
                    if equipment
                    else None
                )
            },

            "reason": (
                "No General ward bed is currently "
                "available, but a bed is expected "
                "to be released."
            ),

            "expected_wait_minutes":
                wait_minutes
        }

    return {
        "patient_id": patient_id,

        "priority": emergency_level,

        "recommended_action": None,

        "reason": (
            "No feasible bed allocation is "
            "currently available."
        ),

        "expected_wait_minutes": None
    }


# =========================================================
# SAVE RECOMMENDATION
# =========================================================

def save_recommendation(
    db: Session,
    recommendation_data
):

    patient_id = recommendation_data[
        "patient_id"
    ]

    # -----------------------------------------------------
    # Prevent duplicate pending recommendation
    # -----------------------------------------------------

    existing = (
        db.query(Recommendation)
        .filter(
            Recommendation.patient_id == patient_id,
            Recommendation.status == "pending"
        )
        .first()
    )

    if existing:
        return existing

    action = recommendation_data.get(
        "recommended_action"
    )

    if not action:
        return None

    bed_id = (
        action.get("bed_id")
        or action.get("replacement_bed")
    )

    staff_id = action.get(
        "staff_id"
    )

    equipment_id = action.get(
        "equipment_id"
    )

    recommendation = Recommendation(
        patient_id=patient_id,

        recommendation_type=action.get(
            "type"
        ),

        recommended_bed_id=bed_id,

        recommended_staff_id=staff_id,

        recommended_equipment_id=equipment_id,

        reason=recommendation_data[
            "reason"
        ],

        status="pending"
    )

    db.add(recommendation)

    db.commit()

    db.refresh(recommendation)

    return recommendation


# =========================================================
# HIGHEST PRIORITY WAITING PATIENT
# =========================================================

def get_highest_priority_waiting_patient(
    db: Session
):

    priority_order = {
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4
    }

    patients = (
        db.query(Patient)
        .filter(
            Patient.status == "waiting"
        )
        .all()
    )

    eligible_patients = []

    for patient in patients:

        existing = (
            db.query(Recommendation)
            .filter(
                Recommendation.patient_id
                == patient.patient_id,

                Recommendation.status
                == "pending"
            )
            .first()
        )

        if existing:
            continue

        priority = priority_order.get(
            patient.emergency_level.lower(),
            5
        )

        eligible_patients.append(
            (
                priority,
                patient
            )
        )

    if not eligible_patients:
        return None

    eligible_patients.sort(
        key=lambda item: item[0]
    )

    return eligible_patients[0][1]


# =========================================================
# AUTOMATIC RECOMMENDATION
# =========================================================

def generate_automatic_recommendation(
    db: Session,
    released_bed_id: str
):

    patient = get_highest_priority_waiting_patient(
        db
    )

    if not patient:
        return None

    existing = (
        db.query(Recommendation)
        .filter(
            Recommendation.status == "pending",

            Recommendation.recommended_bed_id
            == released_bed_id
        )
        .first()
    )

    if existing:
        return None

    recommendation_data = generate_recommendation(
        db,
        patient.patient_id
    )

    if not recommendation_data:
        return None

    return save_recommendation(
        db,
        recommendation_data
    )


# =========================================================
# VALIDATE PENDING RECOMMENDATIONS
# =========================================================

def validate_pending_recommendations(
    db: Session
):

    pending = (
        db.query(Recommendation)
        .filter(
            Recommendation.status == "pending"
        )
        .all()
    )

    stale_ids = []

    for recommendation in pending:

        # -------------------------------------------------
        # Validate bed
        # -------------------------------------------------

        if recommendation.recommended_bed_id:

            bed = (
                db.query(Bed)
                .filter(
                    Bed.bed_id
                    == recommendation.recommended_bed_id
                )
                .first()
            )

            if not bed or bed.status != "available":

                recommendation.status = "stale"

                stale_ids.append(
                    recommendation.recommendation_id
                )

                continue

        # -------------------------------------------------
        # Validate staff
        # -------------------------------------------------

        if recommendation.recommended_staff_id:

            staff = (
                db.query(Staff)
                .filter(
                    Staff.staff_id
                    == recommendation.recommended_staff_id
                )
                .first()
            )

            if not staff or staff.status != "available":

                recommendation.status = "stale"

                stale_ids.append(
                    recommendation.recommendation_id
                )

                continue

        # -------------------------------------------------
        # Validate equipment
        # -------------------------------------------------

        if recommendation.recommended_equipment_id:

            equipment = (
                db.query(Equipment)
                .filter(
                    Equipment.equipment_id
                    == recommendation.recommended_equipment_id
                )
                .first()
            )

            if (
                not equipment
                or equipment.status != "available"
            ):

                recommendation.status = "stale"

                stale_ids.append(
                    recommendation.recommendation_id
                )

    db.commit()

    return {
        "status": "success",

        "checked":
            len(pending),

        "stale_count":
            len(stale_ids),

        "stale_recommendation_ids":
            stale_ids
    }

# =========================================================
# ML RESOURCE PRESSURE
# =========================================================

def get_resource_pressure(
    db: Session
):
    """
    Generate ML-based resource pressure signals.

    ML predicts future demand.
    It does not directly allocate resources.
    Existing recommendation and constraint logic
    remains responsible for actual allocation.
    """

    arrival_df = load_patient_arrivals(db)

    if arrival_df.empty:
        return {
            "status": "no_data",
            "pressure": []
        }

    department_hourly = prepare_department_hourly_data(
        arrival_df
    )

    if department_hourly.empty:
        return {
            "status": "no_data",
            "pressure": []
        }

    models = train_department_forecast_models(
        department_hourly
    )

    if not models:
        return {
            "status": "no_models",
            "pressure": []
        }

    last_timestamp = arrival_df["arrival_time"].max()

    department_forecast = forecast_department_next_24_hours(
        models,
        last_timestamp + pd.Timedelta(hours=1)
    )

    pressure = get_forecast_pressure(
        db,
        department_forecast
    )

    return {
        "status": "success",
        "pressure": pressure
    }


def get_department_pressure(
    db: Session,
    department: str
):
    """
    Return ML forecast pressure for one department.
    """

    result = get_resource_pressure(db)

    if result["status"] != "success":
        return None

    for item in result["pressure"]:
        if item["department"].lower() == department.lower():
            return item

    return None
