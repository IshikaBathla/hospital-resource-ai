from sqlalchemy.orm import Session

from backend.services.what_if_service import run_what_if_simulation


def run_strategy_comparison(
    db: Session,
    emergency_patients: int,
    high_priority_patients: int,
    medium_priority_patients: int,
    low_priority_patients: int,
    equipment_requirements: dict[str, int],
    strategies: list[str]
):
    results = []

    for strategy in strategies:

        additional_icu_beds = 0
        additional_icu_staff = 0

        if strategy == "baseline":
            pass

        elif strategy == "add_icu_beds":
            additional_icu_beds = emergency_patients + high_priority_patients

        elif strategy == "add_icu_staff":
            additional_icu_staff = emergency_patients + high_priority_patients

        elif strategy == "add_icu_beds_and_staff":
            additional_icu_beds = emergency_patients + high_priority_patients
            additional_icu_staff = emergency_patients + high_priority_patients

        elif strategy == "reallocation":
            pass

        else:
            continue

        result = run_what_if_simulation(
            db=db,
            emergency_patients=emergency_patients,
            high_priority_patients=high_priority_patients,
            medium_priority_patients=medium_priority_patients,
            low_priority_patients=low_priority_patients,
            additional_icu_beds=additional_icu_beds,
            additional_general_beds=0,
            unavailable_icu_beds=0,
            unavailable_general_beds=0,
            unavailable_icu_staff=0,
            unavailable_general_staff=0,
            additional_icu_staff=additional_icu_staff,
            additional_general_staff=0,
            equipment_requirements=equipment_requirements,
        )

        results.append({
            "strategy": strategy,
            "icu_capacity": result["final_capacity"]["ICU"],
            "general_capacity": result["final_capacity"]["General"],
            "bottlenecks": result["bottlenecks"],
            "personalized_recommendations": result[
                "personalized_recommendations"
            ],
            "unified_recommendations": result[
                "unified_recommendations"
            ],
            "optimization": result["optimization"],
            "database_modified": result["database_modified"]
        })

    return {
        "status": "success",
        "strategies_compared": len(results),
        "results": results,
        "database_modified": False
    }