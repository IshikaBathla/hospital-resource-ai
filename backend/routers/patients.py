from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from backend.database import get_db

from backend.models.patient import Patient
from backend.models.bed import Bed

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
# DISCHARGE PATIENT
# COORDINATOR / ADMIN ONLY
# =========================================================

@router.post(
    "/{patient_id}/discharge"
)
def discharge_patient(
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

    # Patient must currently be admitted
    if patient.status.lower() != "admitted":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Patient {patient_id} "
                "is not currently admitted"
            )
        )

    # Find the bed occupied by this patient
    bed = (
        db.query(Bed)
        .filter(
            Bed.patient_id == patient.patient_id,
            Bed.status == "occupied"
        )
        .first()
    )

    if not bed:
        raise HTTPException(
            status_code=409,
            detail=(
                f"No occupied bed found for "
                f"patient {patient_id}"
            )
        )

    # -----------------------------------------------------
    # Discharge patient
    # -----------------------------------------------------

    patient.status = "discharged"

    # -----------------------------------------------------
    # Move bed into turnover state
    # -----------------------------------------------------

    bed.status = "turnover_required"

    # Keep patient_id temporarily for traceability.
    # It will be cleared when turnover is completed.

    bed.expected_release_at = None

    db.commit()

    db.refresh(patient)
    db.refresh(bed)

    return {
        "status": "success",
        "message": (
            "Patient discharged and bed "
            "moved to turnover"
        ),
        "patient_id": patient.patient_id,
        "patient_status": patient.status,
        "bed_id": bed.bed_id,
        "bed_status": bed.status,
        "turnover_required": True
    }


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