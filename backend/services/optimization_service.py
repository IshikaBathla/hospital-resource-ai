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

            (patient.get("emergency_level") or "low").lower()

        )



        if emergency_level in {"critical", "high"}:

            for bed in beds:

                if (bed.get("ward") or "").lower() != "icu":

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

            (patient.get("emergency_level") or "low").lower()

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

                and (bed.get("ward") or "").lower() == "icu"

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

            (patient.get("emergency_level") or "low").lower()

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

                getattr(staff, "name", getattr(staff, "full_name", None)),



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

            (patient.get("emergency_level") or "low").lower()

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

                and (patient.get("location") or "").lower()

                == (equipment_item.get("location") or "").lower()

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

# ============================================================

# TRANSFER-READY REALLOCATION OPTIMIZATION

# ============================================================





def optimize_transfer_ready_reallocation(

    waiting_patients,

    transfer_ready_patients,

    replacement_beds

):

    """

    Optimize reallocation of currently admitted patients who have

    been explicitly marked transfer-ready by staff.



    This function is READ-ONLY. It produces a recommendation only;

    it does not modify patients, beds, assignments, or any other DB state.



    A valid reallocation has three parts:

    1. A waiting patient receives the currently occupied bed of a

       transfer-ready patient.

    2. The transfer-ready patient moves to an available replacement bed.

    3. Both bed assignments must satisfy the existing ICU compatibility rule.



    Human approval is required before any DB mutation.

    """



    if not waiting_patients:

        return {

            "status": "no_waiting_patients",

            "objective_value": 0,

            "reallocations": [],

            "optimized_recommendations": []

        }



    if not transfer_ready_patients:

        return {

            "status": "no_transfer_ready_patients",

            "objective_value": 0,

            "reallocations": [],

            "optimized_recommendations": []

        }



    if not replacement_beds:

        return {

            "status": "no_replacement_beds",

            "objective_value": 0,

            "reallocations": [],

            "optimized_recommendations": []

        }



    solver = pywraplp.Solver.CreateSolver("SCIP")



    if not solver:

        raise RuntimeError("SCIP solver could not be created")



    priority = {

        "critical": 100,

        "high": 70,

        "medium": 40,

        "low": 20

    }



    variables = {}



    def is_bed_compatible(patient, ward):

        emergency_level = (

            patient.get("emergency_level") or ""

        ).lower()



        return not (

            emergency_level in {"critical", "high"}

            and (ward or "").lower() != "icu"

        )



    for waiting in waiting_patients:



        waiting_id = waiting.get("patient_id")



        if not waiting_id:

            continue



        for affected in transfer_ready_patients:



            affected_id = affected.get("patient_id")

            current_bed_id = affected.get("current_bed_id")

            current_ward = affected.get("current_ward") or ""



            if not affected_id or not current_bed_id:

                continue



            # Waiting patient must be compatible with freed bed.

            if not is_bed_compatible(

                waiting,

                current_ward

            ):

                continue



            for replacement in replacement_beds:



                replacement_bed_id = replacement.get("bed_id")

                replacement_ward = (

                    replacement.get("ward") or ""

                )



                if not replacement_bed_id:

                    continue



                # Transfer-ready patient must be compatible

                # with replacement bed.

                if not is_bed_compatible(

                    affected,

                    replacement_ward

                ):

                    continue



                key = (

                    waiting_id,

                    affected_id,

                    replacement_bed_id

                )



                variables[key] = solver.IntVar(

                    0,

                    1,

                    f"reallocation_{waiting_id}_"

                    f"{affected_id}_{replacement_bed_id}"

                )



    if not variables:

        return {

            "status": "no_feasible_reallocation",

            "objective_value": 0,

            "reallocations": [],

            "optimized_recommendations": []

        }



    # One reallocation maximum per waiting patient.

    for waiting in waiting_patients:



        waiting_id = waiting.get("patient_id")



        related = [

            variable

            for key, variable in variables.items()

            if key[0] == waiting_id

        ]



        if related:

            solver.Add(

                sum(related) <= 1

            )



    # A transfer-ready patient can be moved at most once.

    for affected in transfer_ready_patients:



        affected_id = affected.get("patient_id")



        related = [

            variable

            for key, variable in variables.items()

            if key[1] == affected_id

        ]



        if related:

            solver.Add(

                sum(related) <= 1

            )



    # A replacement bed can be used at most once.

    for replacement in replacement_beds:



        replacement_bed_id = replacement.get("bed_id")



        related = [

            variable

            for key, variable in variables.items()

            if key[2] == replacement_bed_id

        ]



        if related:

            solver.Add(

                sum(related) <= 1

            )



    objective = solver.Objective()



    for key, variable in variables.items():



        waiting_id, affected_id, replacement_bed_id = key



        waiting = next(

            patient

            for patient in waiting_patients

            if patient.get("patient_id") == waiting_id

        )



        affected = next(

            patient

            for patient in transfer_ready_patients

            if patient.get("patient_id") == affected_id

        )



        replacement = next(

            bed

            for bed in replacement_beds

            if bed.get("bed_id") == replacement_bed_id

        )



        waiting_level = (

            waiting.get("emergency_level") or ""

        ).lower()



        affected_level = (

            affected.get("emergency_level") or ""

        ).lower()



        score = (

            priority.get(waiting_level, 10)

            * 100

        )



        score += priority.get(

            affected_level,

            10

        )



        # Prefer same ward for the transfer-ready patient

        # when possible.

        if (

            (affected.get("current_ward") or "").lower()

            ==

            (replacement.get("ward") or "").lower()

        ):

            score += 10



        objective.SetCoefficient(

            variable,

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

            "reallocations": [],

            "optimized_recommendations": []

        }



    reallocations = []

    optimized_recommendations = []



    waiting_lookup = {

        patient.get("patient_id"): patient

        for patient in waiting_patients

    }



    affected_lookup = {

        patient.get("patient_id"): patient

        for patient in transfer_ready_patients

    }



    replacement_lookup = {

        bed.get("bed_id"): bed

        for bed in replacement_beds

    }



    for key, variable in variables.items():



        if variable.solution_value() <= 0.5:

            continue



        waiting_id, affected_id, replacement_bed_id = key



        waiting = waiting_lookup[waiting_id]

        affected = affected_lookup[affected_id]

        replacement = replacement_lookup[

            replacement_bed_id

        ]



        current_bed_id = affected.get(

            "current_bed_id"

        )



        current_ward = affected.get(

            "current_ward"

        )



        replacement_ward = replacement.get(

            "ward"

        )



        score = objective.GetCoefficient(

            variable

        )



        reason = (

            f"Staff confirmed patient {affected_id} "

            f"as transfer-ready. OR-Tools selected "

            f"reallocation of {affected_id} from "

            f"{current_bed_id} to "

            f"{replacement_bed_id}, freeing "

            f"{current_bed_id} for waiting patient "

            f"{waiting_id}."

        )



        expected_impact = (

            f"Frees bed {current_bed_id} for "

            f"waiting patient {waiting_id} while "

            f"moving the staff-confirmed transfer-ready "

            f"patient {affected_id} to compatible "

            f"replacement bed {replacement_bed_id}."

        )



        reallocation = {

            "waiting_patient_id": waiting_id,

            "affected_patient_id": affected_id,

            "from_bed": current_bed_id,

            "to_bed": replacement_bed_id,

            "from_ward": current_ward,

            "replacement_ward": replacement_ward,

            "optimization_score": score,

            "reason": reason,

            "expected_impact": expected_impact,

            "human_decision_required": True

        }



        reallocations.append(

            reallocation

        )



        optimized_recommendations.append({

            "patient_id": waiting_id,

            "emergency_level": waiting.get(

                "emergency_level"

            ),

            "recommended_action":

                "reallocate_existing_patient",



            "recommended_bed_id":

                current_bed_id,



            "affected_patient_id":

                affected_id,



            "affected_patient_current_bed":

                current_bed_id,



            "affected_patient_replacement_bed":

                replacement_bed_id,



            "affected_patient_replacement_ward":

                replacement_ward,



            "affected_patient_transfer_ready":

                True,



            "staff_note":

                affected.get("staff_note"),



            "reason":

                reason,



            "constraints": [

                "Only staff-confirmed transfer-ready patients are eligible.",

                "Critical/High patients can only use ICU beds.",

                "One waiting patient can participate in at most one reallocation.",

                "One transfer-ready patient can be moved at most once.",

                "One replacement bed can be used at most once.",

                "Database remains unchanged until human approval."

            ],



            "expected_impact":

                expected_impact,



            "optimization_score":

                score,



            "human_decision_required":

                True,



            "database_modified":

                False

        })



    return {

        "status":

            "optimized"

            if reallocations

            else "no_feasible_reallocation",



        "objective_value":

            objective.Value(),



        "reallocations":

            reallocations,



        "optimized_recommendations":

            optimized_recommendations

    }





def get_transfer_ready_reallocation_input(

    db: Session

):

    """

    Build read-only OR-Tools input from the current

    PostgreSQL hospital state.



    Waiting patients are patients whose status is waiting.



    Transfer-ready patients must be admitted and explicitly

    confirmed transfer-ready by staff.



    Replacement beds must currently be available.

    """



    waiting = (

        db.query(Patient)

        .filter(

            Patient.status == "waiting"

        )

        .order_by(

            Patient.patient_id

        )

        .all()

    )



    transfer_ready = (

        db.query(Patient)

        .filter(

            Patient.status == "admitted",

            Patient.transfer_ready.is_(True)

        )

        .order_by(

            Patient.patient_id

        )

        .all()

    )



    available_beds = (

        db.query(Bed)

        .filter(

            Bed.status == "available"

        )

        .order_by(

            Bed.bed_id

        )

        .all()

    )



    waiting_data = [

        {

            "patient_id":

                patient.patient_id,



            "emergency_level":

                patient.emergency_level

        }

        for patient in waiting

    ]



    occupied_beds = (

        db.query(Bed)

        .filter(

            Bed.status == "occupied"

        )

        .all()

    )



    occupied_by_patient = {

        bed.patient_id: bed

        for bed in occupied_beds

        if bed.patient_id

    }



    transfer_ready_data = []



    for patient in transfer_ready:



        current_bed = occupied_by_patient.get(

            patient.patient_id

        )



        if not current_bed:

            continue



        transfer_ready_data.append({

            "patient_id":

                patient.patient_id,



            "emergency_level":

                patient.emergency_level,



            "current_bed_id":

                current_bed.bed_id,



            "current_ward":

                current_bed.ward,



            "staff_note":

                patient.staff_note,



            "expected_release_at":

                (

                    patient.expected_release_at.isoformat()

                    if patient.expected_release_at

                    else None

                )

        })



    replacement_bed_data = [

        {

            "bed_id":

                bed.bed_id,



            "ward":

                bed.ward

        }

        for bed in available_beds

    ]



    return (

        waiting_data,

        transfer_ready_data,

        replacement_bed_data

    )





def optimize_current_transfer_ready_reallocation(

    db: Session

):

    """

    Run transfer-ready reallocation optimization

    against the current PostgreSQL hospital state.



    This is strictly read-only.



    No patient, bed, assignment, or recommendation

    record is modified by this function.

    """



    (

        waiting_patients,

        transfer_ready_patients,

        replacement_beds

    ) = get_transfer_ready_reallocation_input(

        db

    )



    return optimize_transfer_ready_reallocation(

        waiting_patients=

            waiting_patients,



        transfer_ready_patients=

            transfer_ready_patients,



        replacement_beds=

            replacement_beds

    )
# ============================================================
# SAVE TRANSFER-READY REALLOCATION RECOMMENDATION
# ============================================================

def generate_transfer_ready_reallocation_recommendation(db: Session):
    """
    Generate and persist the best transfer-ready reallocation
    as a pending Recommendation.

    This function does NOT allocate or move any resource.
    It only creates a pending recommendation for human approval.
    """

    result = optimize_current_transfer_ready_reallocation(db)

    if result.get("status") != "optimized":
        return {
            "status": result.get("status"),
            "recommendation_id": None,
            "message": (
                "No feasible transfer-ready reallocation "
                "recommendation is currently available."
            ),
            "reallocations": result.get("reallocations", []),
            "optimized_recommendations": result.get(
                "optimized_recommendations", []
            ),
        }

    optimized_recommendations = result.get(
        "optimized_recommendations", []
    )

    for optimized in optimized_recommendations:
        waiting_patient_id = optimized.get("patient_id")
        affected_patient_id = optimized.get("affected_patient_id")
        current_bed_id = optimized.get("affected_patient_current_bed")
        replacement_bed_id = optimized.get("affected_patient_replacement_bed")

        if not all([
            waiting_patient_id,
            affected_patient_id,
            current_bed_id,
            replacement_bed_id,
        ]):
            continue

        existing = (
            db.query(Recommendation)
            .filter(
                Recommendation.patient_id == waiting_patient_id,
                Recommendation.status == "pending",
                Recommendation.recommendation_type == "reallocation",
            )
            .first()
        )

        if existing:
            return {
                "status": "existing_pending_recommendation",
                "recommendation_id": existing.recommendation_id,
                "patient_id": existing.patient_id,
                "message": (
                    "A pending transfer-ready reallocation "
                    "recommendation already exists."
                ),
                "human_decision_required": True,
                "database_status": "pending",
            }

        recommendation = Recommendation(
            patient_id=waiting_patient_id,
            recommendation_type="reallocation",
            recommended_bed_id=current_bed_id,
            recommended_staff_id=None,
            recommended_equipment_id=None,
            affected_patient_id=affected_patient_id,
            affected_patient_current_bed_id=current_bed_id,
            affected_patient_replacement_bed_id=replacement_bed_id,
            reason=optimized.get(
                "reason",
                "OR-Tools selected a transfer-ready patient reallocation.",
            ),
            status="pending",
        )

        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)

        return {
            "status": "success",
            "recommendation_id": recommendation.recommendation_id,
            "patient_id": waiting_patient_id,
            "recommendation_type": recommendation.recommendation_type,
            "recommended_bed_id": current_bed_id,
            "affected_patient_id": affected_patient_id,
            "affected_patient_current_bed": current_bed_id,
            "affected_patient_replacement_bed": replacement_bed_id,
            "reason": recommendation.reason,
            "expected_impact": optimized.get("expected_impact"),
            "optimization_score": optimized.get("optimization_score"),
            "human_decision_required": True,
            "database_status": "pending",
            "database_modified": True,
            "resources_allocated": False,
        }

    return {
        "status": "no_new_recommendation",
        "recommendation_id": None,
        "message": (
            "No new transfer-ready reallocation recommendation "
            "was created."
        ),
        "human_decision_required": True,
        "database_status": "unchanged",
    }
