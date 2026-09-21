from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database import get_db

from backend.models.recommendation import Recommendation
from backend.models.bed import Bed
from backend.models.patient import Patient
from backend.models.assignment import Assignment

from backend.schemas.recommendation import (
    RecommendationAction
)

from backend.services.recommendation_service import (
    generate_recommendation,
    save_recommendation
)


router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"]
)


# =========================================================
# GENERATE RECOMMENDATION
# =========================================================

@router.get(
    "/patient/{patient_id}"
)
def get_patient_recommendation(
    patient_id: str,
    db: Session = Depends(get_db)
):

    recommendation_data = generate_recommendation(
        db,
        patient_id
    )

    if recommendation_data.get("status") == "error":

        raise HTTPException(
            status_code=404,
            detail=recommendation_data["message"]
        )

    # Save generated recommendation
    recommendation = save_recommendation(
        db,
        recommendation_data
    )

    return {
        "status": "success",

        "recommendation_id":
            recommendation.recommendation_id,

        "patient_id":
            recommendation.patient_id,

        "recommendation_type":
            recommendation.recommendation_type,

        "recommended_action":
            recommendation_data[
                "recommended_action"
            ],

        "reason":
            recommendation.reason,

        "human_decision_required":
            True,

        "database_status":
            recommendation.status
    }


# =========================================================
# APPROVE RECOMMENDATION
# =========================================================

@router.post(
    "/{recommendation_id}/approve"
)
def approve_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Get recommendation
    # -----------------------------------------------------

    recommendation = (
        db.query(Recommendation)
        .filter(
            Recommendation.recommendation_id
            == recommendation_id
        )
        .first()
    )

    if not recommendation:

        raise HTTPException(
            status_code=404,
            detail="Recommendation not found"
        )

    # -----------------------------------------------------
    # Check recommendation status
    # -----------------------------------------------------

    if recommendation.status != "pending":

        raise HTTPException(
            status_code=400,
            detail=(
                "Recommendation has already "
                "been processed"
            )
        )

    # -----------------------------------------------------
    # Check recommended bed
    # -----------------------------------------------------

    if not recommendation.recommended_bed_id:

        raise HTTPException(
            status_code=400,
            detail=(
                "Recommendation does not contain "
                "a bed allocation"
            )
        )

    bed = (
        db.query(Bed)
        .filter(
            Bed.bed_id
            == recommendation.recommended_bed_id
        )
        .first()
    )

    if not bed:

        raise HTTPException(
            status_code=404,
            detail="Recommended bed not found"
        )

    # -----------------------------------------------------
    # IMPORTANT:
    # Check current live DB state
    # -----------------------------------------------------

    if bed.status != "available":

        raise HTTPException(
            status_code=409,
            detail=(
                f"Bed {bed.bed_id} is no longer "
                f"available"
            )
        )

    # -----------------------------------------------------
    # Get patient
    # -----------------------------------------------------

    patient = (
        db.query(Patient)
        .filter(
            Patient.patient_id
            == recommendation.patient_id
        )
        .first()
    )

    if not patient:

        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # -----------------------------------------------------
    # Allocate bed
    # -----------------------------------------------------

    bed.status = "occupied"

    bed.patient_id = patient.patient_id

    bed.expected_release_at = None

    # -----------------------------------------------------
    # Update patient
    # -----------------------------------------------------

    patient.status = "admitted"

    # -----------------------------------------------------
    # Create assignment
    # -----------------------------------------------------

    assignment = Assignment(
        patient_id=patient.patient_id,
        bed_id=bed.bed_id
    )

    db.add(assignment)

    # -----------------------------------------------------
    # Update recommendation
    # -----------------------------------------------------

    recommendation.status = "approved"

    # -----------------------------------------------------
    # Save decision history
    # -----------------------------------------------------

    db.execute(
        text("""
            INSERT INTO recommendation_decisions
            (
                patient_id,
                recommendation_id,
                decision,
                recommended_bed_id,
                reason
            )
            VALUES
            (
                :patient_id,
                :recommendation_id,
                'approved',
                :recommended_bed_id,
                :reason
            )
        """),
        {
            "patient_id":
                patient.patient_id,

            "recommendation_id":
                recommendation_id,

            "recommended_bed_id":
                bed.bed_id,

            "reason":
                recommendation.reason
        }
    )

    # -----------------------------------------------------
    # Commit transaction
    # -----------------------------------------------------

    db.commit()

    db.refresh(bed)
    db.refresh(patient)
    db.refresh(assignment)
    db.refresh(recommendation)

    return {
        "status": "success",

        "message":
            "Recommendation approved and "
            "resource allocated",

        "recommendation_id":
            recommendation.recommendation_id,

        "patient_id":
            patient.patient_id,

        "patient_status":
            patient.status,

        "bed_id":
            bed.bed_id,

        "bed_status":
            bed.status,

        "assignment_id":
            assignment.assignment_id,

        "recommendation_status":
            recommendation.status
    }


# =========================================================
# MODIFY RECOMMENDATION
# =========================================================

@router.post(
    "/{recommendation_id}/modify"
)
def modify_recommendation(
    recommendation_id: int,
    action: RecommendationAction,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Get recommendation
    # -----------------------------------------------------

    recommendation = (
        db.query(Recommendation)
        .filter(
            Recommendation.recommendation_id
            == recommendation_id
        )
        .first()
    )

    if not recommendation:

        raise HTTPException(
            status_code=404,
            detail="Recommendation not found"
        )

    # -----------------------------------------------------
    # Check status
    # -----------------------------------------------------

    if recommendation.status != "pending":

        raise HTTPException(
            status_code=400,
            detail=(
                "Recommendation has already "
                "been processed"
            )
        )

    # -----------------------------------------------------
    # At least one modification required
    # -----------------------------------------------------

    if not (
        action.modified_bed_id
        or action.modified_staff_id
        or action.modified_equipment_id
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Provide at least one modified "
                "resource"
            )
        )

    # -----------------------------------------------------
    # If modified bed is provided,
    # verify that it exists and is available
    # -----------------------------------------------------

    modified_bed = None

    if action.modified_bed_id:

        modified_bed = (
            db.query(Bed)
            .filter(
                Bed.bed_id
                == action.modified_bed_id
            )
            .first()
        )

        if not modified_bed:

            raise HTTPException(
                status_code=404,
                detail="Modified bed not found"
            )

        if modified_bed.status != "available":

            raise HTTPException(
                status_code=409,
                detail=(
                    f"Modified bed "
                    f"{modified_bed.bed_id} "
                    f"is not available"
                )
            )

    # -----------------------------------------------------
    # Update recommendation
    # -----------------------------------------------------

    recommendation.status = "modified"

    # -----------------------------------------------------
    # Save decision
    # -----------------------------------------------------

    db.execute(
        text("""
            INSERT INTO recommendation_decisions
            (
                patient_id,
                recommendation_id,
                decision,
                recommended_bed_id,
                modified_bed_id,
                modified_staff_id,
                modified_equipment_id,
                reason
            )
            VALUES
            (
                :patient_id,
                :recommendation_id,
                'modified',
                :recommended_bed_id,
                :modified_bed_id,
                :modified_staff_id,
                :modified_equipment_id,
                :reason
            )
        """),
        {
            "patient_id":
                recommendation.patient_id,

            "recommendation_id":
                recommendation_id,

            "recommended_bed_id":
                recommendation.recommended_bed_id,

            "modified_bed_id":
                action.modified_bed_id,

            "modified_staff_id":
                action.modified_staff_id,

            "modified_equipment_id":
                action.modified_equipment_id,

            "reason":
                action.reason
        }
    )

    db.commit()

    db.refresh(recommendation)

    return {
        "status": "success",

        "message":
            "Recommendation modified",

        "recommendation_id":
            recommendation.recommendation_id,

        "recommendation_status":
            recommendation.status,

        "modified_action":
            action.model_dump()
    }


# =========================================================
# REJECT RECOMMENDATION
# =========================================================

@router.post(
    "/{recommendation_id}/reject"
)
def reject_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Get recommendation
    # -----------------------------------------------------

    recommendation = (
        db.query(Recommendation)
        .filter(
            Recommendation.recommendation_id
            == recommendation_id
        )
        .first()
    )

    if not recommendation:

        raise HTTPException(
            status_code=404,
            detail="Recommendation not found"
        )

    # -----------------------------------------------------
    # Check status
    # -----------------------------------------------------

    if recommendation.status != "pending":

        raise HTTPException(
            status_code=400,
            detail=(
                "Recommendation has already "
                "been processed"
            )
        )

    # -----------------------------------------------------
    # Update recommendation
    # -----------------------------------------------------

    recommendation.status = "rejected"

    # -----------------------------------------------------
    # Save decision history
    # -----------------------------------------------------

    db.execute(
        text("""
            INSERT INTO recommendation_decisions
            (
                patient_id,
                recommendation_id,
                decision,
                recommended_bed_id,
                reason
            )
            VALUES
            (
                :patient_id,
                :recommendation_id,
                'rejected',
                :recommended_bed_id,
                :reason
            )
        """),
        {
            "patient_id":
                recommendation.patient_id,

            "recommendation_id":
                recommendation_id,

            "recommended_bed_id":
                recommendation.recommended_bed_id,

            "reason":
                recommendation.reason
        }
    )

    db.commit()

    db.refresh(recommendation)

    return {
        "status": "success",

        "message":
            "Recommendation rejected",

        "recommendation_id":
            recommendation.recommendation_id,

        "recommendation_status":
            recommendation.status
    }


# =========================================================
# GET SINGLE RECOMMENDATION
# =========================================================

@router.get(
    "/{recommendation_id}"
)
def get_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db)
):

    recommendation = (
        db.query(Recommendation)
        .filter(
            Recommendation.recommendation_id
            == recommendation_id
        )
        .first()
    )

    if not recommendation:

        raise HTTPException(
            status_code=404,
            detail="Recommendation not found"
        )

    return {
        "recommendation_id":
            recommendation.recommendation_id,

        "patient_id":
            recommendation.patient_id,

        "recommendation_type":
            recommendation.recommendation_type,

        "recommended_bed_id":
            recommendation.recommended_bed_id,

        "recommended_staff_id":
            recommendation.recommended_staff_id,

        "recommended_equipment_id":
            recommendation.recommended_equipment_id,

        "reason":
            recommendation.reason,

        "status":
            recommendation.status,

        "created_at":
            recommendation.created_at
    }


# =========================================================
# DECISION HISTORY
# =========================================================

@router.get(
    "/patient/{patient_id}/decision-history"
)
def get_decision_history(
    patient_id: str,
    db: Session = Depends(get_db)
):

    decisions = db.execute(
        text("""
            SELECT *
            FROM recommendation_decisions
            WHERE patient_id = :patient_id
            ORDER BY created_at DESC
        """),
        {
            "patient_id":
                patient_id
        }
    ).mappings().all()

    return [
        dict(decision)
        for decision in decisions
    ]