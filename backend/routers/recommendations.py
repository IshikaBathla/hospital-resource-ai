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
from backend.models.staff import Staff
from backend.models.equipment import Equipment

from backend.schemas.recommendation import (
    RecommendationAction
)

from backend.services.recommendation_service import (
    generate_recommendation,
    save_recommendation,
    validate_pending_recommendations
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

    recommendation = save_recommendation(
        db,
        recommendation_data
    )

    if not recommendation:
        raise HTTPException(
            status_code=400,
            detail="No feasible recommendation available"
        )

    action = recommendation_data.get(
        "action"
    )

    return {
        "status": "success",

        "recommendation_id":
            recommendation.recommendation_id,

        "patient_id":
            recommendation.patient_id,

        "recommendation_type":
            recommendation.recommendation_type,

        "recommended_action": action,

        "recommended_bed_id":
            recommendation.recommended_bed_id,

        "recommended_staff_id":
            recommendation.recommended_staff_id,

        "recommended_equipment_id":
            recommendation.recommended_equipment_id,

        "reason":
            recommendation.reason,

        "human_decision_required":
            True,

        "database_status":
            recommendation.status
    }


# =========================================================
# VALIDATE PENDING RECOMMENDATIONS
# =========================================================

@router.post(
    "/validate-pending"
)
def validate_recommendations(
    db: Session = Depends(get_db)
):

    return validate_pending_recommendations(
        db
    )


# =========================================================
# GET PENDING RECOMMENDATIONS
# =========================================================

@router.get(
    "/pending"
)
def get_pending_recommendations(
    db: Session = Depends(get_db)
):

    recommendations = (
        db.query(Recommendation)
        .filter(
            Recommendation.status == "pending"
        )
        .order_by(
            Recommendation.created_at.desc()
        )
        .all()
    )

    return [
        {
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

        for recommendation
        in recommendations
    ]


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

    if recommendation.status != "pending":

        raise HTTPException(
            status_code=400,
            detail=(
                "Recommendation has already "
                "been processed"
            )
        )

    # -----------------------------------------------------
    # Validate recommended bed
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

    if bed.status != "available":

        raise HTTPException(
            status_code=409,
            detail=(
                f"Bed {bed.bed_id} is no longer "
                "available"
            )
        )

    # -----------------------------------------------------
    # Validate patient
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
    # Validate recommended staff
    # -----------------------------------------------------

    staff = None

    if recommendation.recommended_staff_id:

        staff = (
            db.query(Staff)
            .filter(
                Staff.staff_id
                == recommendation.recommended_staff_id
            )
            .first()
        )

        if not staff:

            raise HTTPException(
                status_code=404,
                detail="Recommended staff not found"
            )

        if staff.status != "available":

            raise HTTPException(
                status_code=409,
                detail=(
                    f"Staff {staff.staff_id} "
                    "is no longer available"
                )
            )

    # -----------------------------------------------------
    # Validate recommended equipment
    # -----------------------------------------------------

    equipment = None

    if recommendation.recommended_equipment_id:

        equipment = (
            db.query(Equipment)
            .filter(
                Equipment.equipment_id
                == recommendation.recommended_equipment_id
            )
            .first()
        )

        if not equipment:

            raise HTTPException(
                status_code=404,
                detail="Recommended equipment not found"
            )

        if equipment.status != "available":

            raise HTTPException(
                status_code=409,
                detail=(
                    f"Equipment "
                    f"{equipment.equipment_id} "
                    "is no longer available"
                )
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
    # Allocate staff
    # -----------------------------------------------------

    if staff:

        staff.status = "assigned"

    # -----------------------------------------------------
    # Allocate equipment
    # -----------------------------------------------------

    if equipment:

        equipment.status = "assigned"

    # -----------------------------------------------------
    # Create assignment
    # -----------------------------------------------------

    assignment = Assignment(
        patient_id=patient.patient_id,

        bed_id=bed.bed_id,

        staff_id=(
            staff.staff_id
            if staff
            else None
        ),

        equipment_id=(
            equipment.equipment_id
            if equipment
            else None
        )
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

    db.commit()

    db.refresh(bed)
    db.refresh(patient)
    db.refresh(assignment)
    db.refresh(recommendation)

    if staff:
        db.refresh(staff)

    if equipment:
        db.refresh(equipment)

    return {
        "status": "success",

        "message":
            "Recommendation approved and "
            "resources allocated",

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

        "staff_id":
            (
                staff.staff_id
                if staff
                else None
            ),

        "staff_status":
            (
                staff.status
                if staff
                else None
            ),

        "equipment_id":
            (
                equipment.equipment_id
                if equipment
                else None
            ),

        "equipment_status":
            (
                equipment.status
                if equipment
                else None
            ),

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

    if recommendation.status != "pending":

        raise HTTPException(
            status_code=400,
            detail=(
                "Recommendation has already "
                "been processed"
            )
        )

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
                    "is not available"
                )
            )

    modified_staff = None

    if action.modified_staff_id:

        modified_staff = (
            db.query(Staff)
            .filter(
                Staff.staff_id
                == action.modified_staff_id
            )
            .first()
        )

        if not modified_staff:

            raise HTTPException(
                status_code=404,
                detail="Modified staff not found"
            )

        if modified_staff.status != "available":

            raise HTTPException(
                status_code=409,
                detail=(
                    f"Staff "
                    f"{modified_staff.staff_id} "
                    "is not available"
                )
            )

    modified_equipment = None

    if action.modified_equipment_id:

        modified_equipment = (
            db.query(Equipment)
            .filter(
                Equipment.equipment_id
                == action.modified_equipment_id
            )
            .first()
        )

        if not modified_equipment:

            raise HTTPException(
                status_code=404,
                detail="Modified equipment not found"
            )

        if modified_equipment.status != "available":

            raise HTTPException(
                status_code=409,
                detail=(
                    f"Equipment "
                    f"{modified_equipment.equipment_id} "
                    "is not available"
                )
            )

    # -----------------------------------------------------
    # Allocate modified resources
    # -----------------------------------------------------

    if modified_bed:

        modified_bed.status = "occupied"

        modified_bed.patient_id = (
            patient.patient_id
        )

        modified_bed.expected_release_at = None

        patient.status = "admitted"

    if modified_staff:

        modified_staff.status = "assigned"

    if modified_equipment:

        modified_equipment.status = "assigned"

    # -----------------------------------------------------
    # Create assignment
    # -----------------------------------------------------

    assignment = Assignment(
        patient_id=patient.patient_id,

        bed_id=(
            modified_bed.bed_id
            if modified_bed
            else None
        ),

        staff_id=(
            modified_staff.staff_id
            if modified_staff
            else None
        ),

        equipment_id=(
            modified_equipment.equipment_id
            if modified_equipment
            else None
        )
    )

    db.add(assignment)

    recommendation.status = "modified"

    # -----------------------------------------------------
    # Decision history
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
                patient.patient_id,

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
    db.refresh(patient)
    db.refresh(assignment)

    if modified_bed:
        db.refresh(modified_bed)

    if modified_staff:
        db.refresh(modified_staff)

    if modified_equipment:
        db.refresh(modified_equipment)

    return {
        "status": "success",

        "message":
            "Recommendation modified "
            "and resources allocated",

        "recommendation_id":
            recommendation.recommendation_id,

        "patient_id":
            patient.patient_id,

        "patient_status":
            patient.status,

        "modified_bed_id":
            (
                modified_bed.bed_id
                if modified_bed
                else None
            ),

        "modified_staff_id":
            (
                modified_staff.staff_id
                if modified_staff
                else None
            ),

        "modified_equipment_id":
            (
                modified_equipment.equipment_id
                if modified_equipment
                else None
            ),

        "assignment_id":
            assignment.assignment_id,

        "recommendation_status":
            recommendation.status
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

    if recommendation.status != "pending":

        raise HTTPException(
            status_code=400,
            detail=(
                "Recommendation has already "
                "been processed"
            )
        )

    recommendation.status = "rejected"

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