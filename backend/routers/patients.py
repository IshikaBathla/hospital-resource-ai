from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from pydantic import BaseModel

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
# OPERATIONAL STATUS REQUEST
# =========================================================

class PatientOperationalStatusUpdate(BaseModel):

    care_status: str
    transfer_ready: bool
    expected_release_at: datetime | None = None
    staff_note: str | None = None


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
# UPDATE PATIENT OPERATIONAL STATUS
#
# STAFF / COORDINATOR / ADMIN
#
# IMPORTANT:
# This endpoint does NOT decide whether treatment is complete.
# An authorized human explicitly provides the operational status.
# =========================================================

@router.put(
    "/{patient_id}/operational-status"
)
def update_patient_operational_status(
    patient_id: str,
    status_data: PatientOperationalStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            "STAFF",
            "COORDINATOR",
            "ADMIN"
        )
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

    # -----------------------------------------------------
    # Validate care status
    # -----------------------------------------------------

    allowed_care_statuses = {
        "active",
        "transfer_ready",
        "completed"
    }

    if status_data.care_status not in allowed_care_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid care_status. Allowed values: "
                "active, transfer_ready, completed"
            )
        )

    # -----------------------------------------------------
    # Transfer-ready consistency
    # -----------------------------------------------------

    if (
        status_data.care_status == "transfer_ready"
        and not status_data.transfer_ready
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "care_status='transfer_ready' requires "
                "transfer_ready=true"
            )
        )

    if (
        status_data.care_status != "transfer_ready"
        and status_data.transfer_ready
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "transfer_ready can only be true when "
                "care_status='transfer_ready'"
            )
        )

    # -----------------------------------------------------
    # Expected release time
    # -----------------------------------------------------

    if (
        status_data.transfer_ready
        and status_data.expected_release_at is None
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "expected_release_at is required when "
                "patient is marked transfer-ready"
            )
        )

    # -----------------------------------------------------
    # Update patient operational state
    # -----------------------------------------------------

    patient.care_status = status_data.care_status

    patient.transfer_ready = (
        status_data.transfer_ready
    )

    patient.expected_release_at = (
        status_data.expected_release_at
    )

    patient.staff_note = (
        status_data.staff_note
    )

    db.commit()

    db.refresh(patient)

    return {
        "status": "success",
        "message": (
            "Patient operational status updated"
        ),
        "patient": {
            "patient_id": patient.patient_id,
            "care_status": patient.care_status,
            "transfer_ready": patient.transfer_ready,
            "expected_release_at": (
                patient.expected_release_at
            ),
            "staff_note": patient.staff_note
        },
        "human_confirmed": True
    }


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