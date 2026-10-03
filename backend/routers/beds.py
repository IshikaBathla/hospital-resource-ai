from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from backend.database import get_db

from backend.schemas.bed import (
    BedUpdate,
    BedResponse
)

from backend.services.bed_service import (
    get_all_beds,
    get_bed_by_id,
    get_available_beds,
    update_bed
)

from backend.utils.dependencies import (
    get_current_user,
    require_roles
)


router = APIRouter(
    prefix="/beds",
    tags=["Beds"]
)


# =========================================================
# GET ALL BEDS
# =========================================================

@router.get(
    "/",
    response_model=list[BedResponse]
)
def get_beds(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return get_all_beds(db)


# =========================================================
# GET AVAILABLE BEDS
# =========================================================

@router.get(
    "/available",
    response_model=list[BedResponse]
)
def get_available(
    ward: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return get_available_beds(
        db,
        ward
    )


# =========================================================
# GET BED BY ID
# =========================================================

@router.get(
    "/{bed_id}",
    response_model=BedResponse
)
def get_bed(
    bed_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    bed = get_bed_by_id(
        db,
        bed_id
    )

    if not bed:
        raise HTTPException(
            status_code=404,
            detail="Bed not found"
        )

    return bed


# =========================================================
# UPDATE BED
# COORDINATOR / ADMIN ONLY
# =========================================================

@router.put(
    "/{bed_id}",
    response_model=BedResponse
)
def update_bed_status(
    bed_id: str,
    data: BedUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles("COORDINATOR", "ADMIN")
    )
):

    bed = update_bed(
        db,
        bed_id,
        data.status,
        data.patient_id,
        data.expected_release_at
    )

    if not bed:
        raise HTTPException(
            status_code=404,
            detail="Bed not found"
        )

    return bed


# =========================================================
# COMPLETE BED TURNOVER
# COORDINATOR / ADMIN ONLY
# =========================================================

@router.put(
    "/{bed_id}/turnover-complete",
    response_model=BedResponse
)
def complete_bed_turnover(
    bed_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles("COORDINATOR", "ADMIN")
    )
):

    bed = get_bed_by_id(
        db,
        bed_id
    )

    if not bed:
        raise HTTPException(
            status_code=404,
            detail="Bed not found"
        )

    # Bed must actually be waiting for turnover
    if bed.status != "turnover_required":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Bed {bed_id} is not "
                "awaiting turnover"
            )
        )

    # -----------------------------------------------------
    # Bed is now clean and available
    # -----------------------------------------------------

    bed.status = "available"
    bed.patient_id = None
    bed.expected_release_at = None

    db.commit()

    db.refresh(bed)

    return bed