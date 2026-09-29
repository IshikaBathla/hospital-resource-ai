from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.what_if_service import run_what_if_simulation


router = APIRouter(
    prefix="/what-if",
    tags=["What-If Simulation"]
)


@router.post("/simulate")
def simulate_scenario(
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
    db: Session = Depends(get_db),
):
    return run_what_if_simulation(
        db=db,
        emergency_patients=emergency_patients,
        high_priority_patients=high_priority_patients,
        medium_priority_patients=medium_priority_patients,
        low_priority_patients=low_priority_patients,
        additional_icu_beds=additional_icu_beds,
        additional_general_beds=additional_general_beds,
        unavailable_icu_beds=unavailable_icu_beds,
        unavailable_general_beds=unavailable_general_beds,
        unavailable_icu_staff=unavailable_icu_staff,
        unavailable_general_staff=unavailable_general_staff,
        additional_icu_staff=additional_icu_staff,
        additional_general_staff=additional_general_staff,
    )
