from datetime import datetime

from ortools.linear_solver import pywraplp
from sqlalchemy.orm import Session

from backend.models.patient import Patient
from backend.models.bed import Bed
from backend.models.staff import Staff
from backend.models.equipment import Equipment
from backend.models.recommendation import Recommendation


# ============================================================
# BED OPTIMIZATION
# ============================================================

def optimize_bed_allocation(patients, beds):
    """
    Optimize patient-to-bed allocation using OR-Tools.

    Hard constraints:
    1. A patient can receive at most one bed.
    2. A bed can be assigned to at most one patient.
    3. Critical/High patients can only be assigned to ICU beds.

    Objective:
    - Emergency priority
    - Waiting-time bonus
    - ICU bonus for Critical/High patients
    """

    solver = pywraplp.Solver.CreateSolver("SCIP")

    if not solver:
        raise RuntimeError("SCIP solver could not be created")

    x = {}

    for patient in patients:
        for bed in beds:
            x[
                (
                    patient["patient_id"],
                    bed["bed_id"]
                )
            ] = solver.IntVar(
                0,
                1,
                f"x_{patient['patient_id']}_{bed['bed_id']}"
            )

    # One bed maximum per patient
    for patient in patients:
        solver.Add(
            sum(
                x[
                    (
                        patient["patient_id"],
                        bed["bed_id"]
                    )
                ]
                for bed in beds
            ) <= 1
        )

    # One patient maximum per bed
    for bed in beds:
        solver.Add(
            sum(
                x[
                    (
                        patient["patient_id"],
                        bed["bed_id"]
                    )
                ]
                for patient in patients
            ) <= 1
        )

    # Critical / High patients -> ICU only
    for patient in patients:
        emergency_level = (
            patient["emergency_level"].lower()
        )

        if emergency_level in {"critical", "high"}:
            for bed in beds:
                if bed["ward"].lower() != "icu":
                    solver.Add(
                        x[
                            (
                                patient["patient_id"],
                                bed["bed_id"]
                            )
                        ] == 0
                    )

    # Objective
    objective = solver.Objective()

    priority = {
        "critical": 100,
        "high": 70,
        "medium": 40,
        "low": 20
    }

    for patient in patients:

        emergency_level = (
            patient["emergency_level"].lower()
        )

        patient_priority = priority.get(
            emergency_level,
            10
        )

        waiting_minutes = patient.get(
            "waiting_minutes",
            0
        )

        waiting_bonus = waiting_minutes / 10

        for bed in beds:

            score = (
                patient_priority
                + waiting_bonus
            )

            if (
                emergency_level in {"critical", "high"}
                and bed["ward"].lower() == "icu"
            ):
                score += 50

            objective.SetCoefficient(
                x[
                    (
                        patient["patient_id"],
                        bed["bed_id"]
                    )
                ],
                score
            )

    objective.SetMaximization()

    status = solver.Solve()

    if status not in (
        pywraplp.Solver.OPTIMAL,
        pywraplp.Solver.FEASIBLE
    ):
        return {
            "status": "no_solution",
            "objective_value": 0,
            "allocations": []
        }

    allocations = []

    for patient in patients:
        for bed in beds:

            variable = x[
                (
                    patient["patient_id"],
                    bed["bed_id"]
                )
            ]

            if variable.solution_value() > 0.5:

                allocations.append(
                    {
                        "patient_id":
                            patient["patient_id"],

                        "bed_id":
                            bed["bed_id"],

                        "ward":
                            bed["ward"],

                        "waiting_minutes":
                            patient.get(
                                "waiting_minutes",
                                0
                            )
                    }
                )

    return {
        "status": "optimized",
        "objective_value": objective.Value(),
        "allocations": allocations
    }


def get_optimization_input(db: Session):
    """
    Fetch waiting patients and available beds
    from PostgreSQL.

    waiting_minutes is calculated from waiting_since.
    """

    patients = (
        db.query(Patient)
        .filter(
            Patient.status == "waiting"
        )
        .order_by(
            Patient.patient_id
        )
        .all()
    )

    beds = (
        db.query(Bed)
        .filter(
            Bed.status == "available"
        )
        .order_by(
            Bed.bed_id
        )
        .all()
    )

    patient_data = []

    for patient in patients:

        waiting_minutes = 0

        if patient.waiting_since:

            waiting_minutes = max(
                0,
                int(
                    (
                        datetime.now()
                        - patient.waiting_since
                    ).total_seconds() / 60
                )
            )

        patient_data.append(
            {
                "patient_id":
                    patient.patient_id,

                "emergency_level":
                    patient.emergency_level,

                "waiting_minutes":
                    waiting_minutes
            }
        )

    bed_data = [
        {
            "bed_id": bed.bed_id,
            "ward": bed.ward
        }
        for bed in beds
    ]

    return patient_data, bed_data


def optimize_current_hospital_state(db: Session):
    """
    Run OR-Tools bed optimization using
    current PostgreSQL hospital state.

    Read-only operation.
    """

    patients, beds = get_optimization_input(db)

    if not patients:
        return {
            "status": "no_waiting_patients",
            "objective_value": 0,
            "allocations": []
        }

    if not beds:
        return {
            "status": "no_available_beds",
            "objective_value": 0,
            "allocations": []
        }

    return optimize_bed_allocation(
        patients=patients,
        beds=beds
    )


# ============================================================
# STAFF OPTIMIZATION
# ============================================================

def optimize_staff_allocation(patients, staff):
    """
    Optimize patient-to-staff allocation using OR-Tools.

    Hard constraints:
    1. A patient can receive at most one staff member.
    2. A staff member can be assigned to at most one patient.

    Objective:
    - Emergency priority
    - Department compatibility
    - Role compatibility
    """

    solver = pywraplp.Solver.CreateSolver("SCIP")

    if not solver:
        raise RuntimeError("SCIP solver could not be created")

    x = {}

    for patient in patients:
        for staff_member in staff:

            x[
                (
                    patient["patient_id"],
                    staff_member["staff_id"]
                )
            ] = solver.IntVar(
                0,
                1,
                f"staff_"
                f"{patient['patient_id']}_"
                f"{staff_member['staff_id']}"
            )

    # One staff maximum per patient
    for patient in patients:

        solver.Add(
            sum(
                x[
                    (
                        patient["patient_id"],
                        staff_member["staff_id"]
                    )
                ]
                for staff_member in staff
            ) <= 1
        )

    # One patient maximum per staff
    for staff_member in staff:

        solver.Add(
            sum(
                x[
                    (
                        patient["patient_id"],
                        staff_member["staff_id"]
                    )
                ]
                for patient in patients
            ) <= 1
        )

    objective = solver.Objective()

    priority = {
        "critical": 100,
        "high": 70,
        "medium": 40,
        "low": 20
    }

    for patient in patients:

        emergency_level = (
            patient["emergency_level"].lower()
        )

        patient_priority = priority.get(
            emergency_level,
            10
        )

        for staff_member in staff:

            score = patient_priority

            patient_department = (
                patient.get("department") or ""
            ).lower()

            staff_department = (
                staff_member.get("department") or ""
            ).lower()

            if (
                patient_department
                and staff_department
                and patient_department
                == staff_department
            ):
                score += 30

            if emergency_level in {
                "critical",
                "high"
            }:

                if (
                    staff_member
                    .get("role", "")
                    .lower()
                    in {"doctor", "nurse"}
                ):
                    score += 10

            objective.SetCoefficient(
                x[
                    (
                        patient["patient_id"],
                        staff_member["staff_id"]
                    )
                ],
                score
            )

    objective.SetMaximization()

    status = solver.Solve()

    if status not in (
        pywraplp.Solver.OPTIMAL,
        pywraplp.Solver.FEASIBLE
    ):
        return {
            "status": "no_solution",
            "objective_value": 0,
            "allocations": []
        }

    allocations = []

    for patient in patients:
        for staff_member in staff:

            variable = x[
                (
                    patient["patient_id"],
                    staff_member["staff_id"]
                )
            ]

            if variable.solution_value() > 0.5:

                allocations.append(
                    {
                        "patient_id":
                            patient["patient_id"],

                        "staff_id":
                            staff_member["staff_id"],

                        "staff_name":
                            staff_member["name"],

                        "role":
                            staff_member["role"],

                        "department":
                            staff_member["department"],

                        "score": objective.GetCoefficient(
                            x[
                                (
                                    patient["patient_id"],
                                    staff_member["staff_id"]
                                )
                            ]
                        )
                    }
                )

    return {
        "status": "optimized",
        "objective_value": objective.Value(),
        "allocations": allocations
    }


def get_staff_optimization_input(db: Session):
    """
    Fetch waiting patients and available staff.
    """

    patients = (
        db.query(Patient)
        .filter(
            Patient.status == "waiting"
        )
        .order_by(
            Patient.patient_id
        )
        .all()
    )

    staff_members = (
        db.query(Staff)
        .filter(
            Staff.status == "available"
        )
        .order_by(
            Staff.staff_id
        )
        .all()
    )

    patient_data = [
        {
            "patient_id":
                patient.patient_id,

            "emergency_level":
                patient.emergency_level,

            "department":
                None
        }
        for patient in patients
    ]

    staff_data = [
        {
            "staff_id":
                staff.staff_id,

            "name":
                staff.name,

            "role":
                staff.role,

            "department":
                staff.department
        }
        for staff in staff_members
    ]

    return patient_data, staff_data


def optimize_resource_allocation(db: Session):
    """
    Optimize waiting patients across:

    Patient -> Bed
    Patient -> Staff

    Read-only operation.
    """

    patients, beds = get_optimization_input(db)

    if not patients:
        return {
            "status": "no_waiting_patients",
            "bed_allocations": [],
            "staff_allocations": []
        }

    if not beds:
        return {
            "status": "no_available_beds",
            "bed_allocations": [],
            "staff_allocations": []
        }

    bed_result = optimize_bed_allocation(
        patients=patients,
        beds=beds
    )

    bed_allocations = bed_result["allocations"]

    if not bed_allocations:
        return {
            "status": "no_feasible_bed_allocation",
            "bed_allocations": [],
            "staff_allocations": []
        }

    _, available_staff = get_staff_optimization_input(db)

    patient_ward_map = {
        allocation["patient_id"]:
            allocation["ward"]
        for allocation in bed_allocations
    }

    staff_patients = []

    for patient in patients:

        patient_id = patient["patient_id"]

        if patient_id not in patient_ward_map:
            continue

        staff_patients.append(
            {
                "patient_id":
                    patient_id,

                "emergency_level":
                    patient["emergency_level"],

                "department":
                    patient_ward_map[patient_id]
            }
        )

    if not available_staff:

        return {
            "status":
                "bed_optimized_staff_unavailable",

            "bed_allocations":
                bed_allocations,

            "staff_allocations":
                []
        }

    staff_result = optimize_staff_allocation(
        patients=staff_patients,
        staff=available_staff
    )

    return {
        "status":
            "optimized",

        "bed_allocations":
            bed_allocations,

        "staff_allocations":
            staff_result["allocations"],

        "bed_objective_value":
            bed_result["objective_value"],

        "staff_objective_value":
            staff_result["objective_value"]
    }


# ============================================================
# OPTIMIZED BED + STAFF RECOMMENDATION
# ============================================================

def generate_optimized_recommendation(db: Session):
    """
    Generate a pending recommendation using
    OR-Tools bed + staff optimization.

    Does NOT allocate resources.
    Human approval is required.
    """

    result = optimize_resource_allocation(db)

    if result["status"] != "optimized":

        return {
            "status":
                result["status"],

            "recommendation_id":
                None,

            "message":
                "No optimized allocation available"
        }

    bed_allocations = result.get(
        "bed_allocations",
        []
    )

    staff_allocations = result.get(
        "staff_allocations",
        []
    )

    if not bed_allocations:

        return {
            "status":
                "no_bed_allocation",

            "recommendation_id":
                None,

            "message":
                "No optimized bed allocation available"
        }

    for bed_allocation in bed_allocations:

        patient_id = (
            bed_allocation["patient_id"]
        )

        bed_id = (
            bed_allocation["bed_id"]
        )

        staff_id = None

        for staff_allocation in staff_allocations:

            if (
                staff_allocation["patient_id"]
                == patient_id
            ):
                staff_id = (
                    staff_allocation["staff_id"]
                )
                break

        existing = (
            db.query(Recommendation)
            .filter(
                Recommendation.patient_id
                == patient_id,

                Recommendation.status
                == "pending"
            )
            .first()
        )

        if existing:
            continue

        reason = (
            f"OR-Tools optimized allocation "
            f"selected bed {bed_id}"
        )

        if staff_id:

            reason += (
                f" and staff {staff_id}"
            )

        reason += (
            " based on emergency priority, "
            "waiting time, resource availability, "
            "and allocation constraints."
        )

        recommendation = Recommendation(
            patient_id=patient_id,
            recommendation_type=
                "optimized_resource",

            recommended_bed_id=
                bed_id,

            recommended_staff_id=
                staff_id,

            recommended_equipment_id=
                None,

            reason=reason,

            status="pending"
        )

        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)

        return {
            "status":
                "success",

            "recommendation_id":
                recommendation.recommendation_id,

            "patient_id":
                patient_id,

            "recommended_bed_id":
                bed_id,

            "recommended_staff_id":
                staff_id,

            "reason":
                reason,

            "human_decision_required":
                True,

            "database_status":
                "pending"
        }

    return {
        "status":
            "no_new_recommendation",

        "recommendation_id":
            None,

        "message":
            "Pending recommendation already exists"
    }


# ============================================================
# EQUIPMENT OPTIMIZATION
# ============================================================

def optimize_equipment_allocation(
    patients,
    equipment
):
    """
    Optimize patient-to-equipment allocation
    using OR-Tools.

    Hard constraints:
    1. A patient can receive at most one equipment.
    2. Equipment can be assigned to at most one patient.
    3. Equipment type must match requirement.
    4. Location must match when both locations exist.

    Objective:
    - Emergency priority
    - Location compatibility
    """

    solver = pywraplp.Solver.CreateSolver("SCIP")

    if not solver:
        raise RuntimeError(
            "SCIP solver could not be created"
        )

    x = {}

    for patient in patients:

        for equipment_item in equipment:

            x[
                (
                    patient["patient_id"],
                    equipment_item["equipment_id"]
                )
            ] = solver.IntVar(
                0,
                1,
                f"equipment_"
                f"{patient['patient_id']}_"
                f"{equipment_item['equipment_id']}"
            )

    # One equipment maximum per patient
    for patient in patients:

        solver.Add(
            sum(
                x[
                    (
                        patient["patient_id"],
                        equipment_item["equipment_id"]
                    )
                ]
                for equipment_item in equipment
            ) <= 1
        )

    # One patient maximum per equipment
    for equipment_item in equipment:

        solver.Add(
            sum(
                x[
                    (
                        patient["patient_id"],
                        equipment_item["equipment_id"]
                    )
                ]
                for patient in patients
            ) <= 1
        )

    # Compatibility constraints
    for patient in patients:

        required_type = (
            patient.get(
                "required_equipment_type"
            ) or ""
        ).lower()

        patient_location = (
            patient.get("location")
            or ""
        ).lower()

        for equipment_item in equipment:

            equipment_type = (
                equipment_item.get(
                    "equipment_type"
                ) or ""
            ).lower()

            equipment_location = (
                equipment_item.get(
                    "location"
                ) or ""
            ).lower()

            # Equipment type must match
            if required_type != equipment_type:

                solver.Add(
                    x[
                        (
                            patient["patient_id"],
                            equipment_item[
                                "equipment_id"
                            ]
                        )
                    ] == 0
                )

            # Location must match when known
            if (
                patient_location
                and equipment_location
                and patient_location
                != equipment_location
            ):

                solver.Add(
                    x[
                        (
                            patient["patient_id"],
                            equipment_item[
                                "equipment_id"
                            ]
                        )
                    ] == 0
                )

    # Objective
    objective = solver.Objective()

    priority = {
        "critical": 100,
        "high": 70,
        "medium": 40,
        "low": 20
    }

    for patient in patients:

        emergency_level = (
            patient["emergency_level"].lower()
        )

        patient_priority = priority.get(
            emergency_level,
            10
        )

        for equipment_item in equipment:

            score = patient_priority

            if (
                patient.get("location")
                and equipment_item.get("location")
                and patient["location"].lower()
                == equipment_item["location"].lower()
            ):
                score += 30

            objective.SetCoefficient(
                x[
                    (
                        patient["patient_id"],
                        equipment_item["equipment_id"]
                    )
                ],
                score
            )

    objective.SetMaximization()

    status = solver.Solve()

    if status not in (
        pywraplp.Solver.OPTIMAL,
        pywraplp.Solver.FEASIBLE
    ):

        return {
            "status":
                "no_solution",

            "objective_value":
                0,

            "allocations":
                []
        }

    allocations = []

    for patient in patients:

        for equipment_item in equipment:

            variable = x[
                (
                    patient["patient_id"],
                    equipment_item["equipment_id"]
                )
            ]

            if variable.solution_value() > 0.5:

                allocations.append(
                    {
                        "patient_id":
                            patient["patient_id"],

                        "equipment_id":
                            equipment_item[
                                "equipment_id"
                            ],

                        "equipment_type":
                            equipment_item[
                                "equipment_type"
                            ],

                        "location":
                            equipment_item[
                                "location"
                            ]
                    }
                )

    return {
        "status":
            "optimized",

        "objective_value":
            objective.Value(),

        "allocations":
            allocations
    }


def get_equipment_optimization_input(
    db: Session
):
    """
    Fetch waiting patients that require
    equipment and currently available equipment.
    """

    patients = (
        db.query(Patient)
        .filter(
            Patient.status == "waiting",

            Patient.required_equipment_type
            .isnot(None)
        )
        .order_by(
            Patient.patient_id
        )
        .all()
    )

    equipment_items = (
        db.query(Equipment)
        .filter(
            Equipment.status == "available"
        )
        .order_by(
            Equipment.equipment_id
        )
        .all()
    )

    patient_data = [
        {
            "patient_id":
                patient.patient_id,

            "emergency_level":
                patient.emergency_level,

            "required_equipment_type":
                patient.required_equipment_type,

            "location":
                None
        }
        for patient in patients
    ]

    equipment_data = [
        {
            "equipment_id":
                equipment.equipment_id,

            "equipment_type":
                equipment.equipment_type,

            "location":
                equipment.location
        }
        for equipment in equipment_items
    ]

    return patient_data, equipment_data


def optimize_current_equipment_state(
    db: Session
):
    """
    Run OR-Tools equipment optimization
    using current PostgreSQL state.

    Read-only operation.
    """

    patients, equipment = (
        get_equipment_optimization_input(db)
    )

    if not patients:

        return {
            "status":
                "no_equipment_required_patients",

            "objective_value":
                0,

            "allocations":
                []
        }

    if not equipment:

        return {
            "status":
                "no_available_equipment",

            "objective_value":
                0,

            "allocations":
                []
        }

    return optimize_equipment_allocation(
        patients=patients,
        equipment=equipment
    )
def generate_optimized_equipment_recommendation(
    db: Session
):
    """
    Generate a pending recommendation using
    OR-Tools equipment optimization.

    This function does NOT allocate equipment.
    Human approval is required.
    """

    result = optimize_current_equipment_state(db)

    if result["status"] != "optimized":
        return {
            "status": result["status"],
            "recommendation_id": None,
            "message": "No optimized equipment allocation available"
        }

    allocations = result.get(
        "allocations",
        []
    )

    if not allocations:
        return {
            "status": "no_equipment_allocation",
            "recommendation_id": None,
            "message": "No optimized equipment allocation available"
        }

    for allocation in allocations:

        patient_id = allocation["patient_id"]
        equipment_id = allocation["equipment_id"]

        # Prevent duplicate pending recommendations
        existing = (
            db.query(Recommendation)
            .filter(
                Recommendation.patient_id == patient_id,
                Recommendation.status == "pending"
            )
            .first()
        )

        if existing:
            continue

        reason = (
            f"OR-Tools optimized equipment allocation "
            f"selected equipment {equipment_id} "
            f"({allocation['equipment_type']}) "
            f"for patient {patient_id} "
            f"based on emergency priority, "
            f"equipment availability, type compatibility, "
            f"and allocation constraints."
        )

        recommendation = Recommendation(
            patient_id=patient_id,
            recommendation_type="optimized_equipment",
            recommended_bed_id=None,
            recommended_staff_id=None,
            recommended_equipment_id=equipment_id,
            reason=reason,
            status="pending"
        )

        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)

        return {
            "status": "success",
            "recommendation_id":
                recommendation.recommendation_id,
            "patient_id":
                patient_id,
            "recommended_equipment_id":
                equipment_id,
            "reason":
                reason,
            "human_decision_required": True,
            "database_status": "pending"
        }

    return {
        "status": "no_new_recommendation",
        "recommendation_id": None,
        "message": "Pending equipment recommendation already exists"
    }