from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.simulation import WhatIfSimulationRequest
from backend.services.simulation_service import simulate_scenario


router = APIRouter(
    prefix="/simulation",
    tags=["Simulation"]
)


@router.post("/what-if")
def run_what_if_simulation(
    simulation_data: WhatIfSimulationRequest,
    db: Session = Depends(get_db)
):
    try:
        return simulate_scenario(
            db=db,
            patients=simulation_data.patients
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )