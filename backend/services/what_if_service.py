from sqlalchemy.orm import Session

from backend.models.bed import Bed
from backend.models.patient import Patient
from backend.models.staff import Staff
from backend.models.equipment import Equipment

from backend.services.what_if_optimization_service import (
    optimize_simulated_reallocation
)

from backend.services.optimization_service import (
    optimize_staff_allocation,
    optimize_equipment_allocation
)


# =========================================================
# FIND REALLOCATION CANDIDATES
# =========================================================

def find_simulated_reallocation_candidates(
    db: Session,
    simulated_beds,
    target_department: str = "ICU"
):
    candidates = []

    for bed in simulated_beds:

        if bed["ward"] != target_department:
            continue

        if bed["status"] != "occupied":
            continue

        patient_id = bed["patient_id"]

        if not patient_id:
            continue

        patient = (
            db.query(Patient)
            .filter(Patient.patient_id == patient_id)
            .first()
        )

        if not patient:
            continue

        if patient.status.lower() != "admitted":
            continue

        # Critical patients are not considered
        # for reallocation.
        if patient.emergency_level.lower() == "critical":
            continue

        candidates.append({
            "patient_id": patient.patient_id,
            "emergency_level": patient.emergency_level,
            "current_bed_id": bed["bed_id"],
            "current_ward": bed["ward"]
        })

    return candidates


# =========================================================
# FIND GENERAL REPLACEMENT BEDS
# =========================================================

def find_simulated_replacement_beds(simulated_beds):

    return [
        bed
        for bed in simulated_beds
        if (
            bed["ward"] == "General"
            and bed["status"] == "available"
        )
    ]


# =========================================================
# CALCULATE CAPACITY
# =========================================================

def calculate_capacity(simulated_beds):

    icu_beds = [
        bed
        for bed in simulated_beds
        if bed["ward"] == "ICU"
    ]

    general_beds = [
        bed
        for bed in simulated_beds
        if bed["ward"] == "General"
    ]

    return {
        "ICU": {
            "total_beds": len(icu_beds),

            "occupied_beds": sum(
                1
                for bed in icu_beds
                if bed["status"] == "occupied"
            ),

            "available_beds": sum(
                1
                for bed in icu_beds
                if bed["status"] == "available"
            )
        },

        "General": {
            "total_beds": len(general_beds),

            "occupied_beds": sum(
                1
                for bed in general_beds
                if bed["status"] == "occupied"
            ),

            "available_beds": sum(
                1
                for bed in general_beds
                if bed["status"] == "available"
            )
        }
    }



# =========================================================
# STAFF WHAT-IF SIMULATION
# =========================================================

def copy_simulated_staff(db: Session):
    staff_members = db.query(Staff).order_by(Staff.staff_id).all()
    return [{"staff_id": s.staff_id, "name": s.name, "role": s.role, "department": s.department, "status": s.status} for s in staff_members]

def calculate_staff_capacity(simulated_staff):
    capacity = {}
    for staff in simulated_staff:
        department = staff["department"] or "Unassigned"
        capacity.setdefault(department, {"total_staff": 0, "available_staff": 0, "occupied_staff": 0, "simulated_unavailable_staff": 0})
        capacity[department]["total_staff"] += 1
        status = staff["status"].lower()
        if status == "available": capacity[department]["available_staff"] += 1
        elif status in ("assigned", "busy", "occupied", "simulated_assigned"): capacity[department]["occupied_staff"] += 1
        elif status == "simulated_unavailable": capacity[department]["simulated_unavailable_staff"] += 1
    return capacity

def simulate_staff_unavailability(simulated_staff, unavailable_icu_staff, unavailable_general_staff):
    icu_count = general_count = 0
    for staff in simulated_staff:
        department = (staff["department"] or "").lower()
        if department == "icu" and staff["status"].lower() == "available" and icu_count < unavailable_icu_staff:
            staff["status"] = "simulated_unavailable"; icu_count += 1
        elif department == "general" and staff["status"].lower() == "available" and general_count < unavailable_general_staff:
            staff["status"] = "simulated_unavailable"; general_count += 1
    return simulated_staff

def get_available_staff_for_department(simulated_staff, department):
    return [s for s in simulated_staff if s["status"].lower() == "available" and s["department"] and s["department"].lower() == department.lower()]

def assign_simulated_staff(simulated_staff, simulated_patients):
    recommendations=[]
    for patient in simulated_patients:
        level=patient["emergency_level"].lower()
        department="ICU" if level in ("critical","high") else "General"
        preferred_roles=["doctor","nurse"] if department=="ICU" else ["nurse","doctor"]
        candidates=get_available_staff_for_department(simulated_staff, department)
        selected=None
        for role in preferred_roles:
            selected=next((s for s in candidates if s["role"].lower()==role),None)
            if selected: break
        if selected is None and candidates: selected=candidates[0]
        if selected:
            selected["status"]="simulated_assigned"
            recommendations.append({
                "patient_id":patient["patient_id"], "emergency_level":patient["emergency_level"], "department":department,
                "recommended_action":"assign_staff", "recommended_staff_id":selected["staff_id"],
                "staff_name":selected["name"], "staff_role":selected["role"],
                "reason":f"{patient['emergency_level'].capitalize()} priority patient requires operational staff support in {department}. Staff {selected['staff_id']} is available and department-compatible.",
                "constraints":["Staff must be available in the simulated state.","Staff department must match the patient department.","One staff member can be assigned to only one simulated patient."],
                "expected_impact":f"{selected['staff_id']} is assigned to {patient['patient_id']} in {department}.",
                "human_decision_required":True
            })
        else:
            recommendations.append({
                "patient_id":patient["patient_id"], "emergency_level":patient["emergency_level"], "department":department,
                "recommended_action":"staff_required", "recommended_staff_id":None, "staff_name":None, "staff_role":None,
                "reason":f"No compatible available staff exists for {patient['emergency_level']} priority patient {patient['patient_id']} in {department}.",
                "constraints":["Staff must be available in the simulated state.","Staff department must match the patient department.","One staff member can be assigned to only one simulated patient."],
                "expected_impact":"Additional staff capacity or another feasible operational action is required.",
                "human_decision_required":True
            })
    return recommendations

# =========================================================
# BUILD UNIFIED PATIENT-LEVEL RECOMMENDATIONS
# =========================================================

def build_unified_recommendations(
    simulated_patients,
    personalized_recommendations,
    staff_recommendations,
    equipment_recommendations
):
    """
    Combine bed, staff and equipment recommendations
    into one patient-level operational recommendation.

    This function only combines simulation results.
    It does not modify the database.
    """

    bed_map = {r["patient_id"]: r for r in personalized_recommendations}
    staff_map = {r["patient_id"]: r for r in staff_recommendations}
    equipment_map = {r["patient_id"]: r for r in equipment_recommendations}

    unified_recommendations = []

    for patient in simulated_patients:
        patient_id = patient["patient_id"]
        emergency_level = patient["emergency_level"]
        department = patient["department"]

        bed = bed_map.get(patient_id)
        staff = staff_map.get(patient_id)
        equipment = equipment_map.get(patient_id)

        bed_action = bed.get("recommended_action") if bed else None
        staff_action = staff.get("recommended_action") if staff else None
        equipment_action = equipment.get("recommended_action") if equipment else None

        primary_bottleneck = None

        if bed_action == "reallocation_required":
            primary_bottleneck = f"{department} bed capacity"
        elif staff_action == "staff_required":
            primary_bottleneck = f"{department} staff capacity"
        elif equipment_action == "equipment_required":
            primary_bottleneck = "Equipment capacity"

        if bed_action == "reallocation_required":
            overall_action = "reallocation_required"
        elif staff_action == "staff_required":
            overall_action = "allocate_with_staff_required"
        elif equipment_action == "equipment_required":
            overall_action = "allocate_with_equipment_required"
        elif (
            bed_action == "allocate"
            and staff_action in ("assign_staff", None)
            and equipment_action in ("assign_equipment", None)
        ):
            overall_action = "fully_allocated"
        elif bed_action == "allocate":
            overall_action = "allocate"
        else:
            overall_action = "resource_shortage"

        bed_summary = {
            "status": "allocated" if bed and bed.get("recommended_bed_id") else "unavailable",
            "recommended_bed_id": bed.get("recommended_bed_id") if bed else None,
            "action": bed_action
        }

        staff_summary = {
            "status": "allocated" if staff and staff.get("recommended_staff_id") else "unavailable",
            "recommended_staff_id": staff.get("recommended_staff_id") if staff else None,
            "action": staff_action
        }

        equipment_summary = {
            "status": "allocated" if equipment and equipment.get("recommended_equipment_id") else "unavailable",
            "recommended_equipment_id": equipment.get("recommended_equipment_id") if equipment else None,
            "action": equipment_action
        }

        reasons = []
        for label, recommendation in (("Bed", bed), ("Staff", staff), ("Equipment", equipment)):
            if recommendation and recommendation.get("reason"):
                reasons.append(f"{label}: {recommendation['reason']}")

        impacts = []
        for label, recommendation in (("Bed", bed), ("Staff", staff), ("Equipment", equipment)):
            if recommendation and recommendation.get("expected_impact"):
                impacts.append(f"{label}: {recommendation['expected_impact']}")

        unified_recommendations.append({
            "patient_id": patient_id,
            "emergency_level": emergency_level,
            "department": department,
            "resources": {
                "bed": bed_summary,
                "staff": staff_summary,
                "equipment": equipment_summary
            },
            "primary_bottleneck": primary_bottleneck,
            "recommended_action": overall_action,
            "reason": " ".join(reasons),
            "expected_impact": " ".join(impacts),
            "human_decision_required": True
        })

    return unified_recommendations


# MAIN WHAT-IF SIMULATION
# =========================================================

def run_what_if_simulation(
    db: Session,

    emergency_patients: int = 0,

    high_priority_patients: int = 0,

    medium_priority_patients: int = 0,

    low_priority_patients: int = 0,

    additional_icu_beds: int = 0,

    additional_general_beds: int = 0,

    unavailable_icu_beds: int = 0,

    unavailable_general_beds: int = 0,
    unavailable_icu_staff: int = 0,
    unavailable_general_staff: int = 0,
    additional_icu_staff: int = 0,
    additional_general_staff: int = 0,
    equipment_requirements: dict | None = None
):

    # =====================================================
    # 1. COPY CURRENT DATABASE BED STATE
    # =====================================================

    beds = (
        db.query(Bed)
        .order_by(Bed.bed_id)
        .all()
    )

    simulated_beds = []

    for bed in beds:

        simulated_beds.append({

            "bed_id": bed.bed_id,

            "ward": bed.ward,

            "status": bed.status,

            "patient_id": bed.patient_id,

            "expected_release_at":
                bed.expected_release_at
        })

    # =====================================================
    # 2. SIMULATE UNAVAILABLE ICU BEDS
    # =====================================================

    unavailable_icu_count = 0

    unavailable_general_count = 0

    for bed in simulated_beds:

        if (
            bed["ward"] == "ICU"
            and bed["status"] == "available"
            and unavailable_icu_count
            < unavailable_icu_beds
        ):

            bed["status"] = "simulated_unavailable"

            unavailable_icu_count += 1

        elif (
            bed["ward"] == "General"
            and bed["status"] == "available"
            and unavailable_general_count
            < unavailable_general_beds
        ):

            bed["status"] = "simulated_unavailable"

            unavailable_general_count += 1

    # =====================================================
    # 3. ADD SIMULATED ICU BEDS
    # =====================================================

    for index in range(additional_icu_beds):

        simulated_beds.append({

            "bed_id":
                f"SIM-ICU-{index + 1:03d}",

            "ward":
                "ICU",

            "status":
                "available",

            "patient_id":
                None,

            "expected_release_at":
                None
        })

    # =====================================================
    # 4. ADD SIMULATED GENERAL BEDS
    # =====================================================

    for index in range(additional_general_beds):

        simulated_beds.append({

            "bed_id":
                f"SIM-GEN-{index + 1:03d}",

            "ward":
                "General",

            "status":
                "available",

            "patient_id":
                None,

            "expected_release_at":
                None
        })

    # =====================================================
    # 5. INITIAL CAPACITY
    # =====================================================

    initial_capacity = calculate_capacity(
        simulated_beds
    )

    # =====================================================
    # 5A. SIMULATED STAFF STATE
    # =====================================================

    simulated_staff = copy_simulated_staff(db)

    # Add temporary simulated staff without modifying the real database.
    for index in range(additional_icu_staff):
        simulated_staff.append({
            "staff_id": f"SIM-ICU-STAFF-{index + 1:03d}",
            "name": f"Simulated ICU Staff {index + 1}",
            "role": "nurse",
            "department": "ICU",
            "status": "available"
        })

    for index in range(additional_general_staff):
        simulated_staff.append({
            "staff_id": f"SIM-GEN-STAFF-{index + 1:03d}",
            "name": f"Simulated General Staff {index + 1}",
            "role": "nurse",
            "department": "General",
            "status": "available"
        })

    simulated_staff = simulate_staff_unavailability(
        simulated_staff, unavailable_icu_staff, unavailable_general_staff
    )
    initial_staff_capacity = calculate_staff_capacity(simulated_staff)

    # =====================================================
    # 5B. SIMULATED EQUIPMENT STATE
    # =====================================================

    # Copy the current equipment state into memory.
    # This is used only by the What-If simulation.
    # The real database is never modified.
    equipment = (
        db.query(Equipment)
        .order_by(Equipment.equipment_id)
        .all()
    )

    simulated_equipment = []

    for item in equipment:
        simulated_equipment.append({
            "equipment_id": item.equipment_id,
            "equipment_type": item.equipment_type,
            "status": item.status,
            "location": item.location
        })

    # =====================================================
    # 6. DEMAND
    # =====================================================

    total_new_patients = (
        emergency_patients
        + high_priority_patients
        + medium_priority_patients
        + low_priority_patients
    )

    # Operational simulation rule:
    #
    # Emergency + High -> ICU
    # Medium + Low -> General

    icu_demand = (
        emergency_patients
        + high_priority_patients
    )

    general_demand = (
        medium_priority_patients
        + low_priority_patients
    )

    # =====================================================
    # 7. BOTTLENECK DETECTION
    # =====================================================

    bottlenecks = []

    if (
        icu_demand
        > initial_capacity["ICU"]["available_beds"]
    ):

        bottlenecks.append({

            "department":
                "ICU",

            "type":
                "capacity_shortage",

            "required":
                icu_demand,

            "available":
                initial_capacity["ICU"]["available_beds"],

            "shortage":
                (
                    icu_demand
                    - initial_capacity["ICU"]["available_beds"]
                )
        })

    if (
        general_demand
        > initial_capacity["General"]["available_beds"]
    ):

        bottlenecks.append({

            "department":
                "General",

            "type":
                "capacity_shortage",

            "required":
                general_demand,

            "available":
                initial_capacity["General"]["available_beds"],

            "shortage":
                (
                    general_demand
                    - initial_capacity["General"]["available_beds"]
                )
        })

    # =====================================================
    # 8. CREATE SIMULATED PATIENTS
    # =====================================================

    equipment_requirements = equipment_requirements or {}

    simulated_patients = []

    patient_counter = 1

    priority_groups = [

        (
            "critical",
            emergency_patients
        ),

        (
            "high",
            high_priority_patients
        ),

        (
            "medium",
            medium_priority_patients
        ),

        (
            "low",
            low_priority_patients
        )
    ]

    for emergency_level, count in priority_groups:

        for _ in range(count):

            required_equipment_type = None

            # Explicitly map equipment demand from the scenario.
            # We do not infer equipment requirements from priority.
            for equipment_type, required_count in equipment_requirements.items():
                assigned_count = sum(
                    1
                    for existing_patient in simulated_patients
                    if existing_patient.get("required_equipment_type") == equipment_type
                )

                if assigned_count < required_count:
                    required_equipment_type = equipment_type
                    break

            simulated_patients.append({

                "patient_id":
                    f"SIM-P{patient_counter:03d}",

                "emergency_level":
                    emergency_level,

                "department":
                    (
                        "ICU"
                        if emergency_level in ("critical", "high")
                        else "General"
                    ),

                "current_bed_id":
                    None,

                "required_equipment_type":
                    required_equipment_type
            })

            patient_counter += 1

    # =====================================================
    # 8A. EQUIPMENT OPTIMIZATION
    # =====================================================
    # Use the existing OR-Tools equipment optimizer on the
    # simulated equipment state. No database rows are changed.
    # =====================================================

    equipment_patients = [
        {
            "patient_id": patient["patient_id"],
            "emergency_level": patient["emergency_level"],
            "required_equipment_type": patient.get("required_equipment_type"),
            "location": patient["department"]
        }
        for patient in simulated_patients
        if patient.get("required_equipment_type")
    ]

    available_simulated_equipment = [
        item.copy()
        for item in simulated_equipment
        if item["status"].lower() == "available"
    ]

    if not equipment_patients:
        equipment_optimization = {
            "status": "not_required",
            "objective_value": 0,
            "allocations": []
        }
    elif not available_simulated_equipment:
        equipment_optimization = {
            "status": "no_available_equipment",
            "objective_value": 0,
            "allocations": []
        }
    else:
        equipment_optimization = optimize_equipment_allocation(
            patients=equipment_patients,
            equipment=available_simulated_equipment
        )

    equipment_allocation_map = {
        allocation["patient_id"]: allocation
        for allocation in equipment_optimization.get("allocations", [])
    }

    equipment_recommendations = []

    for patient in equipment_patients:
        patient_id = patient["patient_id"]
        required_type = patient["required_equipment_type"]
        allocation = equipment_allocation_map.get(patient_id)

        if allocation:
            equipment_id = allocation["equipment_id"]

            for simulated_item in simulated_equipment:
                if simulated_item["equipment_id"] == equipment_id:
                    simulated_item["status"] = "simulated_assigned"
                    break

            equipment_recommendations.append({
                "patient_id": patient_id,
                "emergency_level": patient["emergency_level"],
                "department": patient["location"],
                "required_equipment_type": required_type,
                "recommended_action": "assign_equipment",
                "recommended_equipment_id": equipment_id,
                "equipment_location": allocation.get("location"),
                "reason": (
                    f"OR-Tools selected equipment {equipment_id} "
                    f"for patient {patient_id} because its type "
                    f"matches the required {required_type} equipment "
                    "and the equipment is compatible with the simulated location."
                ),
                "constraints": [
                    "Equipment type must match the patient requirement.",
                    "Equipment must be available in the simulated state.",
                    "One equipment unit can be assigned to only one simulated patient.",
                    "Equipment location must match the patient location when both are known."
                ],
                "expected_impact": (
                    f"{equipment_id} is reserved for {patient_id} "
                    f"in the simulated {patient['location']} state."
                ),
                "human_decision_required": True
            })
        else:
            equipment_recommendations.append({
                "patient_id": patient_id,
                "emergency_level": patient["emergency_level"],
                "department": patient["location"],
                "required_equipment_type": required_type,
                "recommended_action": "equipment_required",
                "recommended_equipment_id": None,
                "equipment_location": None,
                "reason": (
                    f"No compatible available {required_type} equipment "
                    f"was found for patient {patient_id} in the simulated state."
                ),
                "constraints": [
                    "Equipment type must match the patient requirement.",
                    "Equipment must be available in the simulated state.",
                    "One equipment unit can be assigned to only one simulated patient.",
                    "Equipment location must match the patient location when both are known."
                ],
                "expected_impact": (
                    f"Additional {required_type} capacity or another feasible "
                    "operational action is required."
                ),
                "human_decision_required": True
            })

    # =====================================================
    # 8B. STAFF OPTIMIZATION
    # =====================================================
    #
    # The existing greedy assign_simulated_staff() logic is
    # replaced here by the existing OR-Tools optimizer.
    #
    # Only simulated/real staff that are AVAILABLE in the
    # simulated state are passed to the optimizer.
    #
    # ICU and General patients are optimized separately so
    # department compatibility remains a hard operational
    # constraint rather than only a scoring preference.
    #
    # This is still a What-If simulation:
    # the real database is never modified.
    # =====================================================

    available_simulated_staff = [
        staff_member.copy()
        for staff_member in simulated_staff
        if staff_member["status"].lower() == "available"
    ]

    staff_optimization_allocations = []

    staff_optimization_results = {}

    for department in ("ICU", "General"):

        department_patients = [
            patient
            for patient in simulated_patients
            if patient["department"].lower() == department.lower()
        ]

        department_staff = [
            staff_member
            for staff_member in available_simulated_staff
            if (
                staff_member.get("department")
                and staff_member["department"].lower()
                == department.lower()
            )
        ]

        if not department_patients:
            staff_optimization_results[department] = {
                "status": "not_required",
                "objective_value": 0,
                "allocations": []
            }
            continue

        if not department_staff:
            staff_optimization_results[department] = {
                "status": "no_available_staff",
                "objective_value": 0,
                "allocations": []
            }
            continue

        result = optimize_staff_allocation(
            department_patients,
            department_staff
        )

        staff_optimization_results[department] = result

        staff_optimization_allocations.extend(
            result.get("allocations", [])
        )

    allocation_map = {
        allocation["patient_id"]: allocation
        for allocation in staff_optimization_allocations
    }

    staff_recommendations = []

    for patient in simulated_patients:

        patient_id = patient["patient_id"]
        emergency_level = patient["emergency_level"]
        department = patient["department"]

        allocation = allocation_map.get(patient_id)

        if allocation:

            selected_staff = next(
                (
                    staff_member
                    for staff_member in available_simulated_staff
                    if staff_member["staff_id"]
                    == allocation["staff_id"]
                ),
                None
            )

            if selected_staff:

                staff_recommendations.append({
                    "patient_id": patient_id,
                    "emergency_level": emergency_level,
                    "department": department,
                    "recommended_action": "assign_staff",
                    "recommended_staff_id":
                        selected_staff["staff_id"],
                    "staff_name":
                        selected_staff["name"],
                    "staff_role":
                        selected_staff["role"],
                    "reason": (
                        f"{emergency_level.capitalize()} priority "
                        f"patient requires operational staff support "
                        f"in {department}. OR-Tools selected staff "
                        f"{selected_staff['staff_id']} based on "
                        "emergency priority, department compatibility "
                        "and role compatibility."
                    ),
                    "constraints": [
                        "Staff must be available in the simulated state.",
                        "Staff department must match the patient department.",
                        "One staff member can be assigned to only one simulated patient.",
                        "One patient can receive at most one staff member."
                    ],
                    "expected_impact": (
                        f"{selected_staff['staff_id']} is assigned "
                        f"to {patient_id} in {department}."
                    ),
                    "optimization_score":
                        allocation.get("score"),
                    "human_decision_required": True
                })

                # Update simulated state only.
                for staff_member in simulated_staff:
                    if (
                        staff_member["staff_id"]
                        == selected_staff["staff_id"]
                    ):
                        staff_member["status"] = "simulated_assigned"
                        break

                continue

        staff_recommendations.append({
            "patient_id": patient_id,
            "emergency_level": emergency_level,
            "department": department,
            "recommended_action": "staff_required",
            "recommended_staff_id": None,
            "staff_name": None,
            "staff_role": None,
            "reason": (
                f"No compatible available staff exists for "
                f"{emergency_level} priority patient "
                f"{patient_id} in {department}."
            ),
            "constraints": [
                "Staff must be available in the simulated state.",
                "Staff department must match the patient department.",
                "One staff member can be assigned to only one simulated patient.",
                "One patient can receive at most one staff member."
            ],
            "expected_impact": (
                "Additional staff capacity or another feasible "
                "operational action is required."
            ),
            "human_decision_required": True
        })

    final_staff_capacity = calculate_staff_capacity(
        simulated_staff
    )

    # =====================================================
    # 9. DIRECTLY AVAILABLE ICU BEDS
    # =====================================================

    available_icu_beds = [

        bed

        for bed in simulated_beds

        if (
            bed["ward"] == "ICU"
            and bed["status"] == "available"
        )
    ]

    # =====================================================
    # 10. DIRECTLY AVAILABLE GENERAL BEDS
    # =====================================================

    available_general_beds = [

        bed

        for bed in simulated_beds

        if (
            bed["ward"] == "General"
            and bed["status"] == "available"
        )
    ]

    # =====================================================
    # 11. REALLOCATION CANDIDATES
    # =====================================================

    reallocation_candidates = (
        find_simulated_reallocation_candidates(

            db=db,

            simulated_beds=simulated_beds,

            target_department="ICU"
        )
    )

    # Keep original candidates for reporting
    original_reallocation_candidates = list(
        reallocation_candidates
    )

    # =====================================================
    # 12. REPLACEMENT BEDS
    # =====================================================

    replacement_beds = (
        find_simulated_replacement_beds(
            simulated_beds
        )
    )

    # Keep original replacement beds for optimizer
    original_replacement_beds = [

        {
            "bed_id": bed["bed_id"],
            "ward": bed["ward"],
            "status": bed["status"]
        }

        for bed in replacement_beds
    ]

    # =====================================================
    # 13. PERSONALIZED RECOMMENDATIONS
    # =====================================================

    personalized_recommendations = []

    # =====================================================
    # 14. HANDLE ICU PATIENTS
    # =====================================================

    for patient in simulated_patients:

        if patient["emergency_level"] not in (
            "critical",
            "high"
        ):
            continue

        # -------------------------------------------------
        # DIRECT ICU BED
        # -------------------------------------------------

        if available_icu_beds:

            selected_bed = available_icu_beds.pop(0)

            selected_bed["status"] = "occupied"

            selected_bed["patient_id"] = (
                patient["patient_id"]
            )

            personalized_recommendations.append({

                "patient_id":
                    patient["patient_id"],

                "emergency_level":
                    patient["emergency_level"],

                "current_assignment":
                    None,

                "recommended_action":
                    "allocate",

                "recommended_bed_id":
                    selected_bed["bed_id"],

                "affected_patient_id":
                    None,

                "affected_patient_current_bed":
                    None,

                "affected_patient_replacement_bed":
                    None,

                "department":
                    "ICU",

                "reason":
                    (
                        f"{patient['emergency_level'].capitalize()} "
                        "priority patient requires ICU capacity "
                        "and an ICU bed is available."
                    ),

                "expected_impact":
                    (
                        "Patient receives ICU capacity without "
                        "reallocating an existing patient."
                    ),

                "human_decision_required":
                    True
            })

            continue

        # -------------------------------------------------
        # REALLOCATION
        # -------------------------------------------------

        if (
            reallocation_candidates
            and replacement_beds
        ):

            affected_patient = (
                reallocation_candidates.pop(0)
            )

            replacement_bed = (
                replacement_beds.pop(0)
            )

            old_icu_bed_id = (
                affected_patient["current_bed_id"]
            )

            replacement_bed_id = (
                replacement_bed["bed_id"]
            )

            affected_patient_id = (
                affected_patient["patient_id"]
            )

            # =============================================
            # SIMULATED STATE UPDATE
            # =============================================

            for simulated_bed in simulated_beds:

                # Existing ICU bed -> new patient

                if (
                    simulated_bed["bed_id"]
                    == old_icu_bed_id
                ):

                    simulated_bed["status"] = (
                        "occupied"
                    )

                    simulated_bed["patient_id"] = (
                        patient["patient_id"]
                    )

                # General replacement bed ->
                # existing patient

                elif (
                    simulated_bed["bed_id"]
                    == replacement_bed_id
                ):

                    simulated_bed["status"] = (
                        "occupied"
                    )

                    simulated_bed["patient_id"] = (
                        affected_patient_id
                    )

            personalized_recommendations.append({

                "patient_id":
                    patient["patient_id"],

                "emergency_level":
                    patient["emergency_level"],

                "current_assignment":
                    None,

                "recommended_action":
                    "reallocate_existing_patient",

                "recommended_bed_id":
                    old_icu_bed_id,

                "affected_patient_id":
                    affected_patient_id,

                "affected_patient_current_bed":
                    old_icu_bed_id,

                "affected_patient_replacement_bed":
                    replacement_bed_id,

                "department":
                    "ICU",

                "reason":
                    (
                        f"ICU capacity is unavailable for "
                        f"the {patient['emergency_level']} "
                        "priority patient. An eligible "
                        "existing ICU patient can be moved "
                        "to available General capacity."
                    ),

                "expected_impact":
                    (
                        f"{affected_patient_id} moves from "
                        f"{old_icu_bed_id} to "
                        f"{replacement_bed_id}, creating "
                        f"{old_icu_bed_id} for "
                        f"{patient['patient_id']}."
                    ),

                "human_decision_required":
                    True
            })

            continue

        # -------------------------------------------------
        # NO FEASIBLE REALLOCATION
        # -------------------------------------------------

        personalized_recommendations.append({

            "patient_id":
                patient["patient_id"],

            "emergency_level":
                patient["emergency_level"],

            "current_assignment":
                None,

            "recommended_action":
                "reallocation_required",

            "recommended_bed_id":
                None,

            "affected_patient_id":
                None,

            "affected_patient_current_bed":
                None,

            "affected_patient_replacement_bed":
                None,

            "department":
                "ICU",

            "reason":
                (
                    f"No ICU bed is available for this "
                    f"{patient['emergency_level']} priority "
                    "patient, and no feasible reallocation "
                    "is currently available."
                ),

            "expected_impact":
                (
                    "Additional ICU capacity or another "
                    "feasible operational action is required."
                ),

            "human_decision_required":
                True
        })

    # =====================================================
    # 15. HANDLE GENERAL PATIENTS
    # =====================================================

    for patient in simulated_patients:

        if patient["emergency_level"] not in (
            "medium",
            "low"
        ):
            continue

        if available_general_beds:

            selected_bed = (
                available_general_beds.pop(0)
            )

            selected_bed["status"] = (
                "occupied"
            )

            selected_bed["patient_id"] = (
                patient["patient_id"]
            )

            personalized_recommendations.append({

                "patient_id":
                    patient["patient_id"],

                "emergency_level":
                    patient["emergency_level"],

                "current_assignment":
                    None,

                "recommended_action":
                    "allocate",

                "recommended_bed_id":
                    selected_bed["bed_id"],

                "affected_patient_id":
                    None,

                "affected_patient_current_bed":
                    None,

                "affected_patient_replacement_bed":
                    None,

                "department":
                    "General",

                "reason":
                    (
                        f"{patient['emergency_level'].capitalize()} "
                        "priority patient can use available "
                        "General ward capacity."
                    ),

                "expected_impact":
                    (
                        "Patient receives an available General "
                        "ward bed in the simulated scenario."
                    ),

                "human_decision_required":
                    True
            })

        else:

            personalized_recommendations.append({

                "patient_id":
                    patient["patient_id"],

                "emergency_level":
                    patient["emergency_level"],

                "current_assignment":
                    None,

                "recommended_action":
                    "reallocation_required",

                "recommended_bed_id":
                    None,

                "affected_patient_id":
                    None,

                "affected_patient_current_bed":
                    None,

                "affected_patient_replacement_bed":
                    None,

                "department":
                    "General",

                "reason":
                    (
                        f"No General bed is available for "
                        f"this {patient['emergency_level']} "
                        "priority patient."
                    ),

                "expected_impact":
                    (
                        "An existing patient/resource allocation "
                        "must be evaluated to create General capacity."
                    ),

                "human_decision_required":
                    True
            })

    # =====================================================
    # 16. OR-TOOLS OPTIMIZATION
    # =====================================================

    optimization_result = {
        "status": "success",
        "optimized": False,
        "reason": "Optimization not required.",
        "selected_actions": [],
        "optimized_recommendations": [],
        "reallocations_selected": 0
    }

    if (
        icu_demand
        > initial_capacity["ICU"]["available_beds"]
    ):

        icu_shortage = (
            icu_demand
            - initial_capacity["ICU"]["available_beds"]
        )

        optimization_result = (
            optimize_simulated_reallocation(
                simulated_patients=simulated_patients,
                reallocation_candidates=original_reallocation_candidates,
                replacement_beds=original_replacement_beds,
                required_icu_slots=icu_shortage
            )
        )

        # -----------------------------------------------------
        # Apply the OR-Tools decision to the simulated state.
        #
        # The real database is still NOT modified.
        # Manual reallocation decisions are first restored,
        # then the OR-Tools-selected reallocations are applied.
        # -----------------------------------------------------

        if optimization_result.get("optimized"):

            # Restore manual reallocation decisions.
            for recommendation in personalized_recommendations:

                if (
                    recommendation.get("recommended_action")
                    != "reallocate_existing_patient"
                ):
                    continue

                old_bed_id = recommendation.get(
                    "affected_patient_current_bed"
                )

                replacement_bed_id = recommendation.get(
                    "affected_patient_replacement_bed"
                )

                affected_patient_id = recommendation.get(
                    "affected_patient_id"
                )

                for simulated_bed in simulated_beds:

                    if simulated_bed["bed_id"] == old_bed_id:
                        simulated_bed["status"] = "occupied"
                        simulated_bed["patient_id"] = (
                            affected_patient_id
                        )

                    elif (
                        simulated_bed["bed_id"]
                        == replacement_bed_id
                    ):
                        simulated_bed["status"] = "available"
                        simulated_bed["patient_id"] = None

            # Remove the manual reallocation recommendations.
            personalized_recommendations = [
                recommendation
                for recommendation in personalized_recommendations
                if recommendation.get("recommended_action")
                != "reallocate_existing_patient"
            ]

            # Directly allocated ICU patients do not need
            # another reallocation recommendation.
            allocated_patient_ids = {
                recommendation.get("patient_id")
                for recommendation in personalized_recommendations
                if (
                    recommendation.get("department") == "ICU"
                    and recommendation.get("recommended_action")
                    == "allocate"
                )
            }

            pending_icu_patients = [
                patient
                for patient in simulated_patients
                if (
                    patient["emergency_level"]
                    in ("critical", "high")
                    and patient["patient_id"]
                    not in allocated_patient_ids
                )
            ]

            optimized_recommendations = []

            for index, action in enumerate(
                optimization_result.get(
                    "selected_actions",
                    []
                )
            ):

                if index >= len(pending_icu_patients):
                    break

                target_patient = pending_icu_patients[index]

                affected_patient_id = action[
                    "affected_patient_id"
                ]

                old_icu_bed_id = action["from_bed"]

                replacement_bed_id = action["to_bed"]

                # ---------------------------------------------
                # Apply optimized simulated state
                # ---------------------------------------------

                for simulated_bed in simulated_beds:

                    if (
                        simulated_bed["bed_id"]
                        == old_icu_bed_id
                    ):
                        simulated_bed["status"] = "occupied"
                        simulated_bed["patient_id"] = (
                            target_patient["patient_id"]
                        )

                    elif (
                        simulated_bed["bed_id"]
                        == replacement_bed_id
                    ):
                        simulated_bed["status"] = "occupied"
                        simulated_bed["patient_id"] = (
                            affected_patient_id
                        )

                # ---------------------------------------------
                # Transparent numeric optimization score
                # ---------------------------------------------

                affected_level = (
                    action[
                        "affected_patient_emergency_level"
                    ].lower()
                )

                if affected_level == "low":
                    optimization_score = 120

                elif affected_level == "medium":
                    optimization_score = 100

                elif affected_level == "high":
                    optimization_score = 60

                else:
                    optimization_score = 20

                optimized_recommendations.append({

                    "patient_id":
                        target_patient["patient_id"],

                    "emergency_level":
                        target_patient["emergency_level"],

                    "current_assignment":
                        None,

                    "recommended_action":
                        "reallocate_existing_patient",

                    "recommended_bed_id":
                        old_icu_bed_id,

                    "affected_patient_id":
                        affected_patient_id,

                    "affected_patient_current_bed":
                        old_icu_bed_id,

                    "affected_patient_replacement_bed":
                        replacement_bed_id,

                    "department":
                        "ICU",

                    "reason": (
                        f"OR-Tools selected patient "
                        f"{affected_patient_id} for reallocation "
                        f"from {old_icu_bed_id} to "
                        f"{replacement_bed_id} so that "
                        f"{target_patient['patient_id']} can use "
                        f"the freed ICU capacity."
                    ),

                    "constraints": [
                        "Critical patients are not selected "
                        "for reallocation.",
                        "One affected patient can use only "
                        "one replacement bed.",
                        "One replacement bed can be assigned "
                        "to only one affected patient.",
                        "The replacement bed must be available "
                        "in the simulated scenario."
                    ],

                    "expected_impact": (
                        f"{affected_patient_id} moves from "
                        f"{old_icu_bed_id} to "
                        f"{replacement_bed_id}, creating "
                        f"{old_icu_bed_id} for "
                        f"{target_patient['patient_id']}."
                    ),

                    "optimization_score":
                        optimization_score,

                    "human_decision_required":
                        True
                })

            personalized_recommendations.extend(
                optimized_recommendations
            )

            # Keep optimizer output synchronized with the
            # recommendations actually returned to the user.
            optimization_result[
                "optimized_recommendations"
            ] = optimized_recommendations

    # =====================================================
    # 17. FINAL SIMULATED CAPACITY
    # =====================================================


    final_capacity = calculate_capacity(
        simulated_beds
    )

    # =====================================================
    # 18. UNIFIED PATIENT-LEVEL RECOMMENDATIONS
    # =====================================================

    unified_recommendations = build_unified_recommendations(
        simulated_patients=simulated_patients,
        personalized_recommendations=personalized_recommendations,
        staff_recommendations=staff_recommendations,
        equipment_recommendations=equipment_recommendations
    )

    # =====================================================
    # 19. FINAL RESPONSE
    # =====================================================

    return {

        "status":
            "success",

        "scenario": {

            "emergency_patients":
                emergency_patients,

            "high_priority_patients":
                high_priority_patients,

            "medium_priority_patients":
                medium_priority_patients,

            "low_priority_patients":
                low_priority_patients,

            "additional_icu_beds":
                additional_icu_beds,

            "additional_general_beds":
                additional_general_beds,

            "unavailable_icu_beds":
                unavailable_icu_beds,

            "unavailable_general_beds":
                unavailable_general_beds,

            "unavailable_icu_staff": unavailable_icu_staff,

            "unavailable_general_staff":
                unavailable_general_staff,

            "additional_icu_staff":
                additional_icu_staff,

            "additional_general_staff":
                additional_general_staff,

            "equipment_requirements":
                equipment_requirements
        },

        "simulated_beds":
            simulated_beds,

        "simulated_staff": simulated_staff,

        "simulated_equipment":
            simulated_equipment,

        "initial_staff_capacity":
            initial_staff_capacity,

        "final_staff_capacity":
            final_staff_capacity,

        "staff_recommendations":
            staff_recommendations,

        "equipment_recommendations":
            equipment_recommendations,

        "equipment_optimization":
            equipment_optimization,

        "staff_optimization": {
            "status": "success",
            "allocations":
                staff_optimization_allocations,
            "by_department":
                staff_optimization_results
        },

        "initial_capacity":
            initial_capacity,

        "final_capacity":
            final_capacity,

        "simulated_demand": {

            "total_new_patients":
                total_new_patients,

            "ICU_demand":
                icu_demand,

            "General_demand":
                general_demand
        },

        "bottlenecks":
            bottlenecks,

        "reallocation_candidates":
            original_reallocation_candidates,

        "replacement_beds":
            original_replacement_beds,

        "personalized_recommendations":
            personalized_recommendations,

        "unified_recommendations":
            unified_recommendations,

        "optimization":
            optimization_result,

        "database_modified":
            False
    }