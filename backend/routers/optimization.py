from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db

from backend.services.optimization_service import (
    optimize_current_hospital_state,
    optimize_resource_allocation,
    generate_optimized_recommendation,
    optimize_current_equipment_state,
    generate_optimized_equipment_recommendation,
    optimize_current_transfer_ready_reallocation,
    generate_transfer_ready_reallocation_recommendation
)


router = APIRouter(
    prefix="/optimization",
    tags=["Optimization"]
)


# ============================================================
# BED ALLOCATION OPTIMIZATION
# ============================================================

@router.get("/bed-allocation")
def optimize_beds(
    db: Session = Depends(get_db)
):
    return optimize_current_hospital_state(db)


# ============================================================
# RESOURCE ALLOCATION OPTIMIZATION
# ============================================================

@router.get("/resource-allocation")
def optimize_resources(
    db: Session = Depends(get_db)
):
    return optimize_resource_allocation(db)


# ============================================================
# CREATE OPTIMIZED BED RECOMMENDATION
# ============================================================

@router.post("/recommendation")
def create_optimized_recommendation(
    db: Session = Depends(get_db)
):
    return generate_optimized_recommendation(db)


# ============================================================
# EQUIPMENT ALLOCATION OPTIMIZATION
# ============================================================

@router.get("/equipment-allocation")
def optimize_equipment(
    db: Session = Depends(get_db)
):
    return optimize_current_equipment_state(db)


# ============================================================
# CREATE OPTIMIZED EQUIPMENT RECOMMENDATION
# ============================================================

@router.post("/equipment-recommendation")
def create_optimized_equipment_recommendation(
    db: Session = Depends(get_db)
):
    return generate_optimized_equipment_recommendation(db)


# ============================================================
# TRANSFER-READY REALLOCATION OPTIMIZATION
# ============================================================

@router.get("/transfer-ready-reallocation")
def optimize_transfer_ready_reallocation(
    db: Session = Depends(get_db)
):
    """
    Run OR-Tools transfer-ready reallocation optimization.

    This endpoint is READ-ONLY.

    It does not:
    - move patients
    - allocate beds
    - modify assignments
    - create recommendations
    """

    return optimize_current_transfer_ready_reallocation(db)


# ============================================================
# CREATE TRANSFER-READY REALLOCATION RECOMMENDATION
# ============================================================

@router.post("/transfer-ready-reallocation/recommendation")
def create_transfer_ready_reallocation_recommendation(
    db: Session = Depends(get_db)
):
    """
    Generate and save the best transfer-ready reallocation
    as a pending Recommendation.

    This endpoint does NOT move any patient or bed.

    Human approval is required before the actual reallocation.
    """

    return generate_transfer_ready_reallocation_recommendation(db)