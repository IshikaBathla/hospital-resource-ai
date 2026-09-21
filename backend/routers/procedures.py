from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from backend.database import get_db

from backend.schemas.procedure import (
    ProcedureCreate,
    ProcedureResponse
)

from backend.services.procedure_service import (
    create_procedure,
    get_all_procedures,
    get_procedure_by_id
)


router = APIRouter(
    prefix="/procedures",
    tags=["Procedures"]
)


# =========================================================
# CREATE PROCEDURE
# =========================================================

@router.post(
    "/",
    response_model=ProcedureResponse
)
def add_procedure(
    procedure_data: ProcedureCreate,
    db: Session = Depends(get_db)
):

    try:

        return create_procedure(
            db,
            procedure_data
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
# =========================================================
# GET ALL PROCEDURES
# =========================================================

@router.get(
    "/",
    response_model=list[ProcedureResponse]
)
def get_procedures(
    db: Session = Depends(get_db)
):

    return get_all_procedures(db)


# =========================================================
# GET PROCEDURE BY ID
# =========================================================

@router.get(
    "/{procedure_id}",
    response_model=ProcedureResponse
)
def get_procedure(
    procedure_id: int,
    db: Session = Depends(get_db)
):

    procedure = get_procedure_by_id(
        db,
        procedure_id
    )

    if not procedure:

        raise HTTPException(
            status_code=404,
            detail="Procedure not found"
        )

    return procedure