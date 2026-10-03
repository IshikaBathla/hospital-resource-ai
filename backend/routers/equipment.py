from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from backend.database import get_db

from backend.schemas.equipment import (
    EquipmentResponse
)

from backend.services.equipment_service import (
    get_all_equipment,
    get_equipment_by_id,
    get_available_equipment
)

from backend.services.optimization_service import (
    optimize_current_equipment_state,
    generate_optimized_equipment_recommendation
)

from backend.utils.dependencies import (
    get_current_user,
    require_roles
)


router = APIRouter(
    prefix="/equipment",
    tags=["Equipment"]
)


# =========================================================
# GET ALL EQUIPMENT
# =========================================================

@router.get(
    "/",
    response_model=list[EquipmentResponse]
)
def get_equipment(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return get_all_equipment(db)


# =========================================================
# GET AVAILABLE EQUIPMENT
# =========================================================

@router.get(
    "/available",
    response_model=list[EquipmentResponse]
)
def get_available(
    equipment_type: str | None = None,
    location: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return get_available_equipment(
        db,
        equipment_type,
        location
    )


# =========================================================
# OPTIMIZE EQUIPMENT STATE
# READ / ANALYSIS OPERATION
# =========================================================

@router.get(
    "/optimize"
)
def optimize_equipment(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return optimize_current_equipment_state(db)


# =========================================================
# GENERATE EQUIPMENT RECOMMENDATION
# COORDINATOR / ADMIN ONLY
# =========================================================

@router.post(
    "/recommend"
)
def recommend_equipment(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles("COORDINATOR", "ADMIN")
    )
):

    return generate_optimized_equipment_recommendation(db)


# =========================================================
# GET EQUIPMENT BY ID
# =========================================================

@router.get(
    "/{equipment_id}",
    response_model=EquipmentResponse
)
def get_equipment_item(
    equipment_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    equipment = get_equipment_by_id(
        db,
        equipment_id
    )

    if not equipment:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found"
        )

    return equipment