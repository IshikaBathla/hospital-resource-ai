from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db

from backend.services.outcome_service import (
    record_recommendation_outcome,
    get_outcome_by_recommendation,
    get_all_outcomes
)


router = APIRouter(
    prefix="/outcomes",
    tags=["Recommendation Outcomes"]
)


# =========================================================
# CREATE OUTCOME
# =========================================================

@router.post("/{recommendation_id}")
def create_outcome(
    recommendation_id: int,
    outcome_status: str,
    notes: str | None = None,
    db: Session = Depends(get_db)
):

    try:

        outcome = record_recommendation_outcome(
            db=db,
            recommendation_id=recommendation_id,
            outcome_status=outcome_status,
            notes=notes
        )

        return {
            "status": "success",
            "outcome_id": outcome.outcome_id,
            "recommendation_id": outcome.recommendation_id,
            "patient_id": outcome.patient_id,
            "decision": outcome.decision,

            "recommended_bed_id":
                outcome.recommended_bed_id,

            "actual_bed_id":
                outcome.actual_bed_id,

            "recommended_staff_id":
                outcome.recommended_staff_id,

            "actual_staff_id":
                outcome.actual_staff_id,

            "recommended_equipment_id":
                outcome.recommended_equipment_id,

            "actual_equipment_id":
                outcome.actual_equipment_id,

            "outcome_status":
                outcome.outcome_status,

            "notes":
                outcome.notes,

            "created_at":
                outcome.created_at
        }

    except ValueError as error:

        return {
            "status": "error",
            "message": str(error)
        }


# =========================================================
# GET OUTCOME BY RECOMMENDATION
# =========================================================

@router.get("/recommendation/{recommendation_id}")
def get_recommendation_outcome(
    recommendation_id: int,
    db: Session = Depends(get_db)
):

    outcome = get_outcome_by_recommendation(
        db,
        recommendation_id
    )

    if not outcome:
        return {
            "status": "not_found",
            "message": "Outcome not found"
        }

    return {
        "outcome_id":
            outcome.outcome_id,

        "recommendation_id":
            outcome.recommendation_id,

        "patient_id":
            outcome.patient_id,

        "decision":
            outcome.decision,

        "recommended_bed_id":
            outcome.recommended_bed_id,

        "actual_bed_id":
            outcome.actual_bed_id,

        "recommended_staff_id":
            outcome.recommended_staff_id,

        "actual_staff_id":
            outcome.actual_staff_id,

        "recommended_equipment_id":
            outcome.recommended_equipment_id,

        "actual_equipment_id":
            outcome.actual_equipment_id,

        "outcome_status":
            outcome.outcome_status,

        "notes":
            outcome.notes,

        "created_at":
            outcome.created_at
    }


# =========================================================
# GET ALL OUTCOMES
# =========================================================

@router.get("/")
def get_outcomes(
    db: Session = Depends(get_db)
):

    outcomes = get_all_outcomes(db)

    return [
        {
            "outcome_id":
                outcome.outcome_id,

            "recommendation_id":
                outcome.recommendation_id,

            "patient_id":
                outcome.patient_id,

            "decision":
                outcome.decision,

            "recommended_bed_id":
                outcome.recommended_bed_id,

            "actual_bed_id":
                outcome.actual_bed_id,

            "recommended_staff_id":
                outcome.recommended_staff_id,

            "actual_staff_id":
                outcome.actual_staff_id,

            "recommended_equipment_id":
                outcome.recommended_equipment_id,

            "actual_equipment_id":
                outcome.actual_equipment_id,

            "outcome_status":
                outcome.outcome_status,

            "notes":
                outcome.notes,

            "created_at":
                outcome.created_at
        }

        for outcome in outcomes
    ]