from ortools.sat.python import cp_model


def get_patient_priority_score(emergency_level):
    level = emergency_level.lower()

    if level == "critical":
        return 100
    elif level == "high":
        return 70
    elif level == "medium":
        return 40
    elif level == "low":
        return 20

    return 0


def get_reallocation_score(emergency_level):
    """
    Score used specifically for selecting an existing ICU patient
    for reallocation.

    Lower-priority patients are preferred for moving out of ICU.

    Therefore:
        low > medium > high > critical
    """

    level = emergency_level.lower()

    if level == "low":
        return 100
    elif level == "medium":
        return 70
    elif level == "high":
        return 30
    elif level == "critical":
        return 0

    return 0


def optimize_simulated_reallocation(
    simulated_patients,
    reallocation_candidates,
    replacement_beds,
    required_icu_slots
):
    # ---------------------------------------------------------
    # 1. Basic feasibility checks
    # ---------------------------------------------------------

    if required_icu_slots <= 0:
        return {
            "status": "success",
            "optimized": False,
            "reason": "No ICU reallocation is required.",
            "selected_actions": [],
            "optimized_recommendations": [],
            "reallocations_selected": 0
        }

    if not reallocation_candidates:
        return {
            "status": "success",
            "optimized": False,
            "reason": "No eligible ICU reallocation candidates.",
            "selected_actions": [],
            "optimized_recommendations": [],
            "reallocations_selected": 0
        }

    if not replacement_beds:
        return {
            "status": "success",
            "optimized": False,
            "reason": "No replacement beds are available.",
            "selected_actions": [],
            "optimized_recommendations": [],
            "reallocations_selected": 0
        }

    max_possible = min(
        len(reallocation_candidates),
        len(replacement_beds),
        required_icu_slots
    )

    if max_possible <= 0:
        return {
            "status": "success",
            "optimized": False,
            "reason": "No feasible reallocation combination exists.",
            "selected_actions": [],
            "optimized_recommendations": [],
            "reallocations_selected": 0
        }

    # ---------------------------------------------------------
    # 2. Create OR-Tools model
    # ---------------------------------------------------------

    model = cp_model.CpModel()

    x = {}

    for i in range(len(reallocation_candidates)):
        for j in range(len(replacement_beds)):

            x[i, j] = model.NewBoolVar(
                f"reallocate_{i}_{j}"
            )

    # ---------------------------------------------------------
    # 3. Constraints
    # ---------------------------------------------------------

    # One existing patient can move to at most one replacement bed.
    for i in range(len(reallocation_candidates)):

        model.Add(
            sum(
                x[i, j]
                for j in range(len(replacement_beds))
            ) <= 1
        )

    # One replacement bed can receive at most one patient.
    for j in range(len(replacement_beds)):

        model.Add(
            sum(
                x[i, j]
                for i in range(len(reallocation_candidates))
            ) <= 1
        )

    # Do not perform more reallocations than required.
    all_assignments = [
        x[i, j]
        for i in range(len(reallocation_candidates))
        for j in range(len(replacement_beds))
    ]

    model.Add(
        sum(all_assignments) <= max_possible
    )

    # ---------------------------------------------------------
    # 4. Objective function
    # ---------------------------------------------------------

    objective_terms = []

    for i, candidate in enumerate(
        reallocation_candidates
    ):

        emergency_level = candidate[
            "emergency_level"
        ].lower()

        # Lower priority patients are better
        # candidates for moving out of ICU.
        #
        # Therefore:
        # low > medium > high > critical
        #
        # Critical patients should normally never
        # be selected as reallocation candidates.

        patient_score = get_reallocation_score(
            emergency_level
        )

        for j, replacement_bed in enumerate(
            replacement_beds
        ):

            bed_score = 0

            # General ward is preferred as replacement
            # for this simulation.
            if replacement_bed["ward"].lower() == "general":
                bed_score += 20

            total_score = (
                patient_score
                + bed_score
            )

            objective_terms.append(
                total_score * x[i, j]
            )

    model.Maximize(
        sum(objective_terms)
    )

    # ---------------------------------------------------------
    # 5. Solve
    # ---------------------------------------------------------

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 5

    status = solver.Solve(model)

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE
    ):
        return {
            "status": "success",
            "optimized": False,
            "reason": (
                "OR-Tools could not find "
                "a feasible solution."
            ),
            "selected_actions": [],
            "optimized_recommendations": [],
            "reallocations_selected": 0
        }

    # ---------------------------------------------------------
    # 6. Extract selected actions
    # ---------------------------------------------------------

    selected_actions = []

    for i, candidate in enumerate(
        reallocation_candidates
    ):

        for j, replacement_bed in enumerate(
            replacement_beds
        ):

            if solver.Value(x[i, j]) == 1:

                # IMPORTANT:
                # Use the SAME score used by the
                # optimization objective.
                patient_score = get_reallocation_score(
                    candidate["emergency_level"]
                )

                bed_score = 0

                if replacement_bed[
                    "ward"
                ].lower() == "general":
                    bed_score = 20

                total_score = (
                    patient_score
                    + bed_score
                )

                selected_actions.append({

                    "affected_patient_id":
                        candidate["patient_id"],

                    "affected_patient_emergency_level":
                        candidate[
                            "emergency_level"
                        ],

                    "from_bed":
                        candidate[
                            "current_bed_id"
                        ],

                    "to_bed":
                        replacement_bed[
                            "bed_id"
                        ],

                    "replacement_ward":
                        replacement_bed[
                            "ward"
                        ],

                    "optimization_score":
                        total_score
                })

    # ---------------------------------------------------------
    # 7. Find target emergency patients
    # ---------------------------------------------------------

    target_patients = [
        patient
        for patient in simulated_patients
        if patient["emergency_level"].lower()
        in ("critical", "high")
    ]

    # Stable deterministic ordering:
    # critical first, then high.
    priority_order = {
        "critical": 0,
        "high": 1
    }

    target_patients.sort(
        key=lambda patient: (
            priority_order.get(
                patient["emergency_level"].lower(),
                99
            ),
            patient["patient_id"]
        )
    )

    # ---------------------------------------------------------
    # 8. Create one-to-one optimized recommendations
    # ---------------------------------------------------------

    optimized_recommendations = []

    number_of_recommendations = min(
        len(selected_actions),
        len(target_patients)
    )

    for index in range(
        number_of_recommendations
    ):

        action = selected_actions[index]

        target_patient = target_patients[index]

        optimized_recommendations.append({

            "patient_id":
                target_patient[
                    "patient_id"
                ],

            "emergency_level":
                target_patient[
                    "emergency_level"
                ],

            "recommended_action":
                "reallocate_existing_patient",

            "recommended_bed_id":
                action[
                    "from_bed"
                ],

            "affected_patient_id":
                action[
                    "affected_patient_id"
                ],

            "affected_patient_current_bed":
                action[
                    "from_bed"
                ],

            "affected_patient_replacement_bed":
                action[
                    "to_bed"
                ],

            "department":
                "ICU",

            "reason":
                (
                    f"OR-Tools selected reallocation "
                    f"of {action['affected_patient_id']} "
                    f"from {action['from_bed']} to "
                    f"{action['to_bed']} to create ICU "
                    f"capacity for "
                    f"{target_patient['patient_id']}."
                ),

            "expected_impact":
                (
                    f"ICU bed {action['from_bed']} "
                    f"becomes available for "
                    f"{target_patient['patient_id']} "
                    f"while "
                    f"{action['affected_patient_id']} "
                    f"moves to "
                    f"{action['to_bed']}."
                ),

            "optimization_score":
                action[
                    "optimization_score"
                ],

            "human_decision_required":
                True
        })

    # ---------------------------------------------------------
    # 9. Final optimization result
    # ---------------------------------------------------------

    return {

        "status":
            "success",

        "optimized":
            True,

        "solver_status":
            (
                "optimal"
                if status == cp_model.OPTIMAL
                else "feasible"
            ),

        "required_icu_slots":
            required_icu_slots,

        "reallocations_selected":
            len(selected_actions),

        "selected_actions":
            selected_actions,

        "optimized_recommendations":
            optimized_recommendations
    }