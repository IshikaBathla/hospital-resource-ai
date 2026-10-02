from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database import get_db

from backend.schemas.assignment import (
    AssignmentCreate
)

from backend.services.assignment_service import (
    get_all_assignments,
    get_assignment_by_id,
    create_assignment,
    delete_assignment
)


router = APIRouter(
    prefix="/assignments",
    tags=["Assignments"]
)


# =========================================================
# GET ALL ASSIGNMENTS
# =========================================================

@router.get("/")
def get_assignments(
    db: Session = Depends(get_db)
):

    return get_all_assignments(db)


# =========================================================
# GET CURRENT ASSIGNMENT FOR ALL PATIENTS
# =========================================================

@router.get("/current")
def get_current_assignments(
    db: Session = Depends(get_db)
):

    result = db.execute(
        text("""
            SELECT DISTINCT ON (patient_id)
                assignment_id,
                patient_id,
                bed_id,
                staff_id,
                equipment_id,
                assigned_at
            FROM assignments
            ORDER BY patient_id, assigned_at DESC, assignment_id DESC
        """)
    )

    assignments = result.mappings().all()

    return [
        dict(assignment)
        for assignment in assignments
    ]


# =========================================================
# GET CURRENT ASSIGNMENT FOR A PATIENT
# =========================================================

@router.get("/patient/{patient_id}")
def get_patient_assignment(
    patient_id: str,
    db: Session = Depends(get_db)
):

    result = db.execute(
        text("""
            SELECT
                assignment_id,
                patient_id,
                bed_id,
                staff_id,
                equipment_id,
                assigned_at
            FROM assignments
            WHERE patient_id = :patient_id
            ORDER BY assigned_at DESC, assignment_id DESC
            LIMIT 1
        """),
        {
            "patient_id": patient_id
        }
    )

    assignment = result.mappings().first()

    if assignment is None:

        return {
            "patient_id": patient_id,
            "assignment": None
        }

    return {
        "patient_id": patient_id,
        "assignment": dict(assignment)
    }


# =========================================================
# GET ASSIGNMENT BY ID
# =========================================================

@router.get("/{assignment_id}")
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db)
):

    assignment = get_assignment_by_id(
        db,
        assignment_id
    )

    if not assignment:

        raise HTTPException(
            status_code=404,
            detail="Assignment not found"
        )

    return assignment


# =========================================================
# CREATE ASSIGNMENT
# =========================================================

@router.post("/")
def add_assignment(
    assignment_data: AssignmentCreate,
    db: Session = Depends(get_db)
):

    try:

        return create_assignment(
            db,
            assignment_data
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


# =========================================================
# DELETE ASSIGNMENT
# =========================================================

@router.delete("/{assignment_id}")
def remove_assignment(
    assignment_id: int,
    db: Session = Depends(get_db)
):

    try:

        return delete_assignment(
            db,
            assignment_id
        )

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )