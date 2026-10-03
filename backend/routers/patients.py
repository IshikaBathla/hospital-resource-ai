from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from backend.database import get_db

from backend.models.patient import Patient

from backend.schemas.patient import (
    PatientCreate,
    PatientResponse
)

from backend.services.patient_service import (
    get_all_patients,
    get_patient_by_id,
    create_patient
)

from backend.utils.dependencies import (
    get_current_user,
    require_roles
)


router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


# =========================================================
# GET ALL PATIENTS
# =========================================================

@router.get(
    "/",
    response_model=list[PatientResponse]
)
def get_patients(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_all_patients(db)


# =========================================================
# GET PATIENT BY ID
# =========================================================

@router.get(
    "/{patient_id}",
    response_model=PatientResponse
)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
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


# =========================================================
# CREATE PATIENT
# COORDINATOR / ADMIN ONLY
# =========================================================

@router.post(
    "/",
    response_model=PatientResponse
)
def add_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles("COORDINATOR", "ADMIN")
    )
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


# =========================================================
# DELETE PATIENT
# COORDINATOR / ADMIN ONLY
# =========================================================

@router.delete("/{patient_id}")
def delete_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles("COORDINATOR", "ADMIN")
    )
):

    patient = (
        db.query(Patient)
        .filter(
            Patient.patient_id == patient_id
        )
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # Safety: admitted patients should not be deleted.
    if patient.status.lower() == "admitted":
        raise HTTPException(
            status_code=400,
            detail="Admitted patient cannot be deleted"
        )

    db.delete(patient)
    db.commit()

    return {
        "message": "Patient deleted successfully",
        "patient_id": patient_id
    }