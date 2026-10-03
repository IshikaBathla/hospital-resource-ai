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

from backend.utils.dependencies import (
    get_current_user,
    require_roles
)


router = APIRouter(
    prefix="/staff",
    tags=["Staff"]
)


# =========================================================
# GET ALL STAFF
# =========================================================

@router.get(
    "/",
    response_model=list[StaffResponse]
)
def get_staff(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return get_all_staff(db)


# =========================================================
# GET AVAILABLE STAFF
# =========================================================

@router.get(
    "/available",
    response_model=list[StaffResponse]
)
def get_available(
    role: str | None = None,
    department: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return get_available_staff(
        db,
        role,
        department
    )


# =========================================================
# GET STAFF MEMBER
# =========================================================

@router.get(
    "/{staff_id}",
    response_model=StaffResponse
)
def get_staff_member(
    staff_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
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


# =========================================================
# UPDATE STAFF STATUS
# COORDINATOR / ADMIN ONLY
# =========================================================

@router.patch(
    "/{staff_id}/status",
    response_model=StaffResponse
)
def update_status(
    staff_id: str,
    status: str,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles("COORDINATOR", "ADMIN")
    )
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