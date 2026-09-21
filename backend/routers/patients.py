from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from backend.database import get_db

from backend.schemas.patient import (
    PatientCreate,
    PatientResponse
)

from backend.services.patient_service import (
    get_all_patients,
    get_patient_by_id,
    create_patient
)


router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


@router.get(
    "/",
    response_model=list[PatientResponse]
)
def get_patients(
    db: Session = Depends(get_db)
):
    return get_all_patients(db)


@router.get(
    "/{patient_id}",
    response_model=PatientResponse
)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db)
):

    patient = get_patient_by_id(
        db,
        patient_id
    )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return patient


@router.post(
    "/",
    response_model=PatientResponse
)
def add_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db)
):

    existing_patient = get_patient_by_id(
        db,
        patient_data.patient_id
    )

    if existing_patient:
        raise HTTPException(
            status_code=400,
            detail="Patient already exists"
        )

    return create_patient(
        db,
        patient_data
    )