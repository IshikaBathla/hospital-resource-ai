from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from backend.database import get_db

from backend.schemas.what_if import WhatIfScenario

from backend.services.what_if_service import run_what_if_simulation


router = APIRouter(
    prefix="/what-if",
    tags=["What-If Simulation"]
)


# =========================================================
# WHAT-IF SIMULATION
# =========================================================

@router.post("/simulate")
def simulate_scenario(
    scenario: WhatIfScenario,
    db: Session = Depends(get_db)
):

    return run_what_if_simulation(
        db=db,

        emergency_patients=scenario.emergency_patients,
        high_priority_patients=scenario.high_priority_patients,
        medium_priority_patients=scenario.medium_priority_patients,
        low_priority_patients=scenario.low_priority_patients,

        additional_icu_beds=scenario.additional_icu_beds,
        additional_general_beds=scenario.additional_general_beds,

        unavailable_icu_beds=scenario.unavailable_icu_beds,
        unavailable_general_beds=scenario.unavailable_general_beds,

        unavailable_icu_staff=scenario.unavailable_icu_staff,
        unavailable_general_staff=scenario.unavailable_general_staff,

        additional_icu_staff=scenario.additional_icu_staff,
        additional_general_staff=scenario.additional_general_staff,

        equipment_requirements=scenario.equipment_requirements,
    )