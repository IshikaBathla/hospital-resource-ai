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

        # -----------------------------------------------------
        # BED BOTTLENECK / ELIGIBILITY ANALYSIS
        # -----------------------------------------------------
        # Distinguish between: 
        # 1. No beds are physically available.
        # 2. Beds are available, but none are eligible under the
        #    current allocation constraints.

        all_beds = (
            db.query(Bed)
            .order_by(Bed.bed_id)
            .all()
        )

        bed_status_counts = {}
        available_beds_info = []
        eligible_beds = []
        ineligible_available_beds = []
        occupied_beds = []
        turnover_candidates = []
        maintenance_beds = []

        emergency_level = (
            patient.emergency_level or ""
        ).lower()

        for bed in all_beds:

            status = (bed.status or "unknown").lower()

            bed_status_counts[status] = (
                bed_status_counts.get(status, 0) + 1
            )

            if status == "available":

                available_beds_info.append({
                    "bed_id": bed.bed_id,
                    "ward": bed.ward,
                    "status": bed.status
                })

                # Current optimization rule: Critical/High patients
                # can only be assigned to ICU beds.
                if (
                    emergency_level in {"critical", "high"}
                    and (bed.ward or "").lower() != "icu"
                ):
                    ineligible_available_beds.append({
                        "bed_id": bed.bed_id,
                        "ward": bed.ward,
                        "status": bed.status,
                        "reason":
                            "High-priority patient requires ICU "
                            "under current allocation constraints"
                    })
                else:
                    eligible_beds.append({
                        "bed_id": bed.bed_id,
                        "ward": bed.ward,
                        "status": bed.status
                    })

            elif status == "occupied":
                occupied_beds.append({
                    "bed_id": bed.bed_id,
                    "ward": bed.ward,
                    "patient_id": bed.patient_id,
                    "expected_release_at": bed.expected_release_at
                })

                if bed.expected_release_at:
                    turnover_candidates.append({
                        "bed_id": bed.bed_id,
                        "ward": bed.ward,
                        "patient_id": bed.patient_id,
                        "expected_release_at":
                            bed.expected_release_at
                    })

            elif status in {"maintenance", "under_maintenance"}:
                maintenance_beds.append({
                    "bed_id": bed.bed_id,
                    "ward": bed.ward,
                    "status": bed.status
                })

        if available_beds_info and not eligible_beds:
            bottleneck_type = "bed_eligibility"
            bottleneck_message = (
                "Available bed(s) exist, but no eligible bed is "
                "currently available for this patient under the "
                "current allocation constraints"
            )
            reason = (
                f"Patient {patient.patient_id} has available bed(s) "
                f"in the hospital, but none are eligible under the "
                f"current allocation constraints. The coordinator "
                f"should review the available bed options and other "
                f"operational alternatives before making the next decision."
            )
        elif not available_beds_info:
            bottleneck_type = "bed_capacity"
            bottleneck_message = (
                "No immediately available bed is currently available"
            )
            reason = (
                f"No immediately available bed was found for "
                f"waiting patient {patient.patient_id}. "
                f"This is an operational bed-capacity bottleneck. "
                f"The coordinator should review eligible bed turnover, "
                f"maintenance release, or other operational alternatives "
                f"before making the next decision."
            )
        else:
            bottleneck_type = "bed_optimization"
            bottleneck_message = (
                "Available bed(s) exist, but no feasible allocation "
                "was produced by the optimization model"
            )
            reason = (
                f"Available bed(s) were found for patient "
                f"{patient.patient_id}, but the optimization model "
                f"did not produce a feasible allocation. The coordinator "
                f"should review the current operational constraints."
            )

        recommended_actions = [
            "Review beds with an expected release time",
            "Review beds currently under maintenance",
            "Review operational alternatives with the coordinator"
        ]

        if ineligible_available_beds:
            recommended_actions.insert(
                0,
                "Review available beds that are not eligible under the current allocation constraints"
            )

        # ---------------------------------------------------------
        # INDEPENDENT STAFF FEASIBILITY
        # ---------------------------------------------------------
        # Staff assessment must not depend on a successful bed
        # allocation. We first determine the patient's operational
        # department using the same current allocation rule:
        # Critical/High -> ICU, otherwise General.
        target_department = (
            "ICU"
            if emergency_level in {"critical", "high"}
            else "General"
        )

        available_staff = (
            db.query(Staff)
            .filter(Staff.status == "available")
            .order_by(Staff.staff_id)
            .all()
        )

        compatible_staff = [
            {
                "staff_id": staff.staff_id,
                "name": staff.name,
                "role": staff.role,
                "department": staff.department
            }
            for staff in available_staff
            if (staff.department or "").lower()
            == target_department.lower()
        ]

        if compatible_staff:
            staff_patient = {
                "patient_id": patient.patient_id,
                "emergency_level": patient.emergency_level,
                "department": target_department
            }

            staff_result = optimize_staff_allocation(
                patients=[staff_patient],
                staff=compatible_staff
            )
        else:
            staff_result = {
                "status": "no_available_staff",
                "objective_value": 0,
                "allocations": []
            }

        staff_allocations = (
            staff_result.get("allocations", [])
            if staff_result.get("status") == "optimized"
            else []
        )

        selected_staff_id = (
            staff_allocations[0].get("staff_id")
            if staff_allocations
            else None
        )

        # ---------------------------------------------------------
        # INDEPENDENT EQUIPMENT FEASIBILITY
        # ---------------------------------------------------------
        # Equipment assessment also runs independently of bed
        # allocation. The target location is the patient's
        # operational department.
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
                        "equipment_id": equipment.equipment_id,
                        "equipment_type": equipment.equipment_type,
                        "location": equipment.location
                    }
                    for equipment in available_equipment
                ]

                equipment_patient = {
                    "patient_id": patient.patient_id,
                    "emergency_level": patient.emergency_level,
                    "required_equipment_type":
                        patient.required_equipment_type,
                    "location": target_department
                }

                equipment_result = (
                    optimize_equipment_allocation(
                        patients=[equipment_patient],
                        equipment=equipment_data
                    )
                )
            else:
                equipment_result = {
                    "status": "no_available_equipment",
                    "objective_value": 0,
                    "allocations": []
                }

            equipment_allocations = (
                equipment_result.get("allocations", [])
                if equipment_result.get("status") == "optimized"
                else []
            )

            if equipment_allocations:
                selected_equipment_id = (
                    equipment_allocations[0].get("equipment_id")
                )

        # ---------------------------------------------------------
        # COMBINED COORDINATION RESPONSE
        # ---------------------------------------------------------
        # No resource is allocated here. The response only reports
        # the independent operational feasibility of each resource.
        independent_resource_status = {
            "bed": "blocked",
            "staff": (
                "feasible"
                if selected_staff_id
                else "blocked"
            ),
            "equipment": (
                "not_required"
                if not patient.required_equipment_type
                else (
                    "feasible"
                    if selected_equipment_id
                    else "blocked"
                )
            )
        }

        coordination_actions = list(recommended_actions)

        if not selected_staff_id:
            coordination_actions.insert(
                0,
                f"Review available {target_department} staff "
                "and current staff availability"
            )

        if (
            patient.required_equipment_type
            and not selected_equipment_id
        ):
            coordination_actions.insert(
                0,
                f"Review availability of required equipment "
                f"{patient.required_equipment_type}"
            )

        return {
            "status": "coordination_required",
            "patient_id": patient_id,
            "bottleneck": {
                "type": bottleneck_type,
                "message": bottleneck_message,
                "bed_status_counts": bed_status_counts,
                "available_beds": available_beds_info,
                "eligible_beds": eligible_beds,
                "ineligible_available_beds":
                    ineligible_available_beds,
                "occupied_beds": occupied_beds,
                "turnover_candidates": turnover_candidates,
                "maintenance_beds": maintenance_beds
            },
            "resource_feasibility": {
                "bed": {
                    "status": "blocked",
                    "reason": bottleneck_message
                },
                "staff": {
                    "status": independent_resource_status["staff"],
                    "target_department": target_department,
                    "available_compatible_count":
                        len(compatible_staff),
                    "optimization": staff_result,
                    "recommended_staff_id":
                        selected_staff_id
                },
                "equipment": {
                    "status":
                        independent_resource_status["equipment"],
                    "required_type":
                        patient.required_equipment_type,
                    "optimization": equipment_result,
                    "recommended_equipment_id":
                        selected_equipment_id
                }
            },
            "bed_optimization": bed_result,
            "staff_optimization": staff_result,
            "equipment_optimization": equipment_result,
            "recommended_actions": coordination_actions,
            "reason": (
                reason
                + " Staff and equipment were assessed independently "
                "of the blocked bed allocation."
            ),
            "human_decision_required": True,
            "database_status": "not_modified",
            "database_modified": False
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