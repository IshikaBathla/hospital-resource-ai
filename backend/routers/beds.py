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


router = APIRouter(
    prefix="/beds",
    tags=["Beds"]
)


@router.get(
    "/",
    response_model=list[BedResponse]
)
def get_beds(
    db: Session = Depends(get_db)
):

    return get_all_beds(db)


@router.get(
    "/available",
    response_model=list[BedResponse]
)
def get_available(
    ward: str | None = None,
    db: Session = Depends(get_db)
):

    return get_available_beds(
        db,
        ward
    )


@router.get(
    "/{bed_id}",
    response_model=BedResponse
)
def get_bed(
    bed_id: str,
    db: Session = Depends(get_db)
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


@router.put(
    "/{bed_id}",
    response_model=BedResponse
)
def update_bed_status(
    bed_id: str,
    data: BedUpdate,
    db: Session = Depends(get_db)
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