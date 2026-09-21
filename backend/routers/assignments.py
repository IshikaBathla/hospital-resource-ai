from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

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


@router.get("/")
def get_assignments(
    db: Session = Depends(get_db)
):

    return get_all_assignments(db)


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