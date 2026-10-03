from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.simulation import WhatIfSimulationRequest
from backend.services.simulation_service import simulate_scenario
from backend.utils.dependencies import get_current_user, require_roles


router = APIRouter(
    prefix="/simulation",
    tags=["Simulation"]
)


@router.post(
    "/what-if",
    dependencies=[
        Depends(require_roles("ADMIN", "COORDINATOR"))
    ]
)
def run_what_if_simulation(
    simulation_data: WhatIfSimulationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        return simulate_scenario(
            db=db,
            patients=simulation_data.patients
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="What-if simulation failed"
        )