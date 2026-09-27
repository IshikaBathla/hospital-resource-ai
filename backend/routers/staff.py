from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from backend.database import get_db

from backend.schemas.staff import StaffResponse

from backend.services.staff_service import (
    get_all_staff,
    get_staff_by_id,
    get_available_staff,
    update_staff_status
)


router = APIRouter(
    prefix="/staff",
    tags=["Staff"]
)


@router.get(
    "/",
    response_model=list[StaffResponse]
)
def get_staff(
    db: Session = Depends(get_db)
):

    return get_all_staff(db)


@router.get(
    "/available",
    response_model=list[StaffResponse]
)
def get_available(
    role: str | None = None,
    department: str | None = None,
    db: Session = Depends(get_db)
):

    return get_available_staff(
        db,
        role,
        department
    )


@router.get(
    "/{staff_id}",
    response_model=StaffResponse
)
def get_staff_member(
    staff_id: str,
    db: Session = Depends(get_db)
):

    staff = get_staff_by_id(
        db,
        staff_id
    )

    if not staff:
        raise HTTPException(
            status_code=404,
            detail="Staff member not found"
        )

    return staff


@router.patch(
    "/{staff_id}/status",
    response_model=StaffResponse
)
def update_status(
    staff_id: str,
    status: str,
    db: Session = Depends(get_db)
):

    try:

        return update_staff_status(
            db,
            staff_id,
            status
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )