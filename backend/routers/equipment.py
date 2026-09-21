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


router = APIRouter(
    prefix="/equipment",
    tags=["Equipment"]
)


@router.get(
    "/",
    response_model=list[EquipmentResponse]
)
def get_equipment(
    db: Session = Depends(get_db)
):

    return get_all_equipment(db)


@router.get(
    "/available",
    response_model=list[EquipmentResponse]
)
def get_available(
    equipment_type: str | None = None,
    location: str | None = None,
    db: Session = Depends(get_db)
):

    return get_available_equipment(
        db,
        equipment_type,
        location
    )


@router.get(
    "/{equipment_id}",
    response_model=EquipmentResponse
)
def get_equipment_item(
    equipment_id: str,
    db: Session = Depends(get_db)
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