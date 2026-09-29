from sqlalchemy.orm import Session

from backend.models.patient import Patient
from backend.models.bed import Bed
from backend.models.staff import Staff
from backend.models.equipment import Equipment
from backend.models.recommendation import Recommendation

from backend.services.optimization_service import (
    optimize_bed_allocation,
    optimize_staff_allocation,
    optimize_equipment_allocation,
)


def generate_unified_recommendation(
    db: Session,
    patient_id: str
):
    """
    Generate one unified resource recommendation.

    Flow:
    Patient
        ↓
    Bed Optimization
        ↓
    Staff Optimization
        ↓
    Equipment Optimization
        ↓
    Unified Recommendation

    This function does not allocate real resources.
    Human approval is required.
    """

    # ---------------------------------------------------------
    # FIND PATIENT
    # ---------------------------------------------------------

    patient = (
        db.query(Patient)
        .filter(Patient.patient_id == patient_id)
        .first()
    )

    if not patient:
        return {
            "status": "error",
            "message": "Patient not found"
        }

    if patient.status.lower() != "waiting":
        return {
            "status": "error",
            "message": "Unified recommendation requires a waiting patient"
        }

    # ---------------------------------------------------------
    # PREVENT DUPLICATE PENDING RECOMMENDATION
    # ---------------------------------------------------------

    existing = (
        db.query(Recommendation)
        .filter(
            Recommendation.patient_id == patient_id,
            Recommendation.status == "pending"
        )
        .first()
    )

    if existing:
        return {
            "status": "already_pending",
            "recommendation_id":
                existing.recommendation_id,
            "patient_id": patient_id,
            "message":
                "Pending recommendation already exists"
        }

    patient_data = {
        "patient_id": patient.patient_id,
        "emergency_level": patient.emergency_level,
        "waiting_minutes": 0
    }

    # =========================================================
    # 1. BED OPTIMIZATION
    # =========================================================

    available_beds = (
        db.query(Bed)
        .filter(
            Bed.status == "available"
        )
        .order_by(Bed.bed_id)
        .all()
    )

    bed_result = {
        "status": "no_available_beds",
        "objective_value": 0,
        "allocations": []
    }

    if available_beds:

        bed_data = [
            {
                "bed_id": bed.bed_id,
                "ward": bed.ward
            }
            for bed in available_beds
        ]

        bed_result = optimize_bed_allocation(
            patients=[patient_data],
            beds=bed_data
        )

    bed_allocations = (
        bed_result.get("allocations", [])
        if bed_result.get("status") == "optimized"
        else []
    )

    if not bed_allocations:

        return {
            "status": "no_feasible_allocation",
            "patient_id": patient_id,
            "bed_optimization": bed_result,
            "staff_optimization": {
                "status": "not_run",
                "reason":
                    "No feasible bed allocation"
            },
            "equipment_optimization": {
                "status": "not_run",
                "reason":
                    "No feasible bed allocation"
            },
            "message":
                "No feasible bed allocation is currently available"
        }

    selected_bed = bed_allocations[0]

    selected_bed_id = selected_bed["bed_id"]
    selected_ward = selected_bed["ward"]

    # =========================================================
    # 2. STAFF OPTIMIZATION
    # =========================================================

    available_staff = (
        db.query(Staff)
        .filter(
            Staff.status == "available",
            Staff.department == selected_ward
        )
        .order_by(Staff.staff_id)
        .all()
    )

    staff_result = {
        "status": "no_available_staff",
        "objective_value": 0,
        "allocations": []
    }

    if available_staff:

        staff_data = [
            {
                "staff_id": staff.staff_id,
                "name": staff.name,
                "role": staff.role,
                "department": staff.department
            }
            for staff in available_staff
        ]

        staff_patient = {
            "patient_id": patient.patient_id,
            "emergency_level":
                patient.emergency_level,
            "department": selected_ward
        }

        staff_result = optimize_staff_allocation(
            patients=[staff_patient],
            staff=staff_data
        )

    staff_allocations = (
        staff_result.get("allocations", [])
        if staff_result.get("status") == "optimized"
        else []
    )

    selected_staff_id = (
        staff_allocations[0]["staff_id"]
        if staff_allocations
        else None
    )

    # =========================================================
    # 3. EQUIPMENT OPTIMIZATION
    # =========================================================

    equipment_result = {
        "status": "not_required",
        "objective_value": 0,
        "allocations": []
    }

    selected_equipment_id = None

    if patient.required_equipment_type:

        available_equipment = (
            db.query(Equipment)
            .filter(
                Equipment.status == "available"
            )
            .order_by(Equipment.equipment_id)
            .all()
        )

        if available_equipment:

            equipment_data = [
                {
                    "equipment_id":
                        equipment.equipment_id,
                    "equipment_type":
                        equipment.equipment_type,
                    "location":
                        equipment.location
                }
                for equipment in available_equipment
            ]

            equipment_patient = {
                "patient_id":
                    patient.patient_id,
                "emergency_level":
                    patient.emergency_level,
                "required_equipment_type":
                    patient.required_equipment_type,
                "location":
                    selected_ward
            }

            equipment_result = (
                optimize_equipment_allocation(
                    patients=[equipment_patient],
                    equipment=equipment_data
                )
            )

        else:

            equipment_result = {
                "status":
                    "no_available_equipment",
                "objective_value": 0,
                "allocations": []
            }

        equipment_allocations = (
            equipment_result.get("allocations", [])
            if equipment_result.get("status")
            == "optimized"
            else []
        )

        if equipment_allocations:

            selected_equipment_id = (
                equipment_allocations[0][
                    "equipment_id"
                ]
            )

    # =========================================================
    # 4. RESOURCE STATUS
    # =========================================================

    staff_status = (
        "allocated"
        if selected_staff_id
        else "staff_required"
    )

    if not patient.required_equipment_type:

        equipment_status = "not_required"

    elif selected_equipment_id:

        equipment_status = "allocated"

    else:

        equipment_status = "equipment_required"

    # =========================================================
    # 5. BUILD UNIFIED REASON
    # =========================================================

    reason = (
        f"OR-Tools generated a unified resource "
        f"recommendation for {patient.emergency_level} "
        f"priority patient {patient.patient_id}. "
        f"Recommended bed {selected_bed_id} "
        f"in {selected_ward}. "
    )

    if selected_staff_id:

        reason += (
            f"Recommended staff "
            f"{selected_staff_id}. "
        )

    else:

        reason += (
            "No compatible available staff "
            "was found. "
        )

    if selected_equipment_id:

        reason += (
            f"Recommended equipment "
            f"{selected_equipment_id} "
            f"for required type "
            f"{patient.required_equipment_type}. "
        )

    elif patient.required_equipment_type:

        reason += (
            f"No compatible available equipment "
            f"was found for required type "
            f"{patient.required_equipment_type}. "
        )

    reason += (
        "Resources remain unchanged until "
        "a human decision is made."
    )

    # =========================================================
    # 6. SAVE PENDING RECOMMENDATION
    # =========================================================

    recommendation = Recommendation(
        patient_id=patient.patient_id,
        recommendation_type="unified_resource",
        recommended_bed_id=selected_bed_id,
        recommended_staff_id=selected_staff_id,
        recommended_equipment_id=
            selected_equipment_id,
        reason=reason,
        status="pending"
    )

    db.add(recommendation)

    db.commit()

    db.refresh(recommendation)

    # =========================================================
    # 7. RESPONSE
    # =========================================================

    return {
        "status": "success",

        "recommendation_id":
            recommendation.recommendation_id,

        "patient_id":
            patient.patient_id,

        "recommendation_type":
            "unified_resource",

        "recommended_resources": {
            "bed_id":
                selected_bed_id,

            "ward":
                selected_ward,

            "staff_id":
                selected_staff_id,

            "equipment_id":
                selected_equipment_id
        },

        "resource_status": {
            "bed":
                "allocated",

            "staff":
                staff_status,

            "equipment":
                equipment_status
        },

        "optimization": {
            "bed":
                bed_result,

            "staff":
                staff_result,

            "equipment":
                equipment_result
        },

        "reason":
            reason,

        "human_decision_required":
            True,

        "database_status":
            "pending",

        "database_modified":
            True
    }