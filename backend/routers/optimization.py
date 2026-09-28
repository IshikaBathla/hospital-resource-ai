from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db

from backend.services.optimization_service import (
    optimize_current_hospital_state,
    optimize_resource_allocation,
    generate_optimized_recommendation,
    optimize_current_equipment_state,
    generate_optimized_equipment_recommendation
)


router = APIRouter(
    prefix="/optimization",
    tags=["Optimization"]
)


# =========================================================
# BED OPTIMIZATION
# =========================================================

@router.get("/bed-allocation")
def optimize_beds(
    db: Session = Depends(get_db)
):
    return optimize_current_hospital_state(db)


# =========================================================
# BED + STAFF OPTIMIZATION
# =========================================================

@router.get("/resource-allocation")
def optimize_resources(
    db: Session = Depends(get_db)
):
    return optimize_resource_allocation(db)


# =========================================================
# BED + STAFF RECOMMENDATION
# =========================================================

@router.post("/recommendation")
def create_optimized_recommendation(
    db: Session = Depends(get_db)
):
    return generate_optimized_recommendation(db)


# =========================================================
# EQUIPMENT OPTIMIZATION
# =========================================================

@router.get("/equipment-allocation")
def optimize_equipment(
    db: Session = Depends(get_db)
):
    return optimize_current_equipment_state(db)


# =========================================================
# EQUIPMENT RECOMMENDATION
# =========================================================

@router.post("/equipment-recommendation")
def create_optimized_equipment_recommendation(
    db: Session = Depends(get_db)
):
    return generate_optimized_equipment_recommendation(db)