from sqlalchemy.orm import Session

from backend.models.recommendation import Recommendation
from backend.models.recommendation_outcome import RecommendationOutcome
from backend.models.assignment import Assignment


def record_recommendation_outcome(
    db: Session,
    recommendation_id: int,
    outcome_status: str,
    notes: str | None = None
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
        raise ValueError(
            "Recommendation not found"
        )

    # -----------------------------------------------------
    # Prevent duplicate outcome
    # -----------------------------------------------------

    existing = (
        db.query(RecommendationOutcome)
        .filter(
            RecommendationOutcome.recommendation_id
            == recommendation_id
        )
        .first()
    )

    if existing:
        raise ValueError(
            "Outcome already recorded for this recommendation"
        )

    # -----------------------------------------------------
    # Get latest assignment for patient
    # -----------------------------------------------------

    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.patient_id
            == recommendation.patient_id
        )
        .order_by(
            Assignment.assignment_id.desc()
        )
        .first()
    )

    # -----------------------------------------------------
    # Recommended resources
    # -----------------------------------------------------

    recommended_bed_id = (
        recommendation.recommended_bed_id
    )

    recommended_staff_id = (
        recommendation.recommended_staff_id
    )

    recommended_equipment_id = (
        recommendation.recommended_equipment_id
    )

    # -----------------------------------------------------
    # Actual resources
    # -----------------------------------------------------

    actual_bed_id = None
    actual_staff_id = None
    actual_equipment_id = None

    if assignment:
        actual_bed_id = assignment.bed_id
        actual_staff_id = assignment.staff_id
        actual_equipment_id = assignment.equipment_id

    # -----------------------------------------------------
    # Create outcome
    # -----------------------------------------------------

    outcome = RecommendationOutcome(
        recommendation_id=recommendation.recommendation_id,
        patient_id=recommendation.patient_id,

        decision=recommendation.status,

        recommended_bed_id=recommended_bed_id,
        actual_bed_id=actual_bed_id,

        recommended_staff_id=recommended_staff_id,
        actual_staff_id=actual_staff_id,

        recommended_equipment_id=recommended_equipment_id,
        actual_equipment_id=actual_equipment_id,

        outcome_status=outcome_status,

        notes=notes
    )

    db.add(outcome)
    db.commit()
    db.refresh(outcome)

    return outcome


def get_outcome_by_recommendation(
    db: Session,
    recommendation_id: int
):
    outcome = (
        db.query(RecommendationOutcome)
        .filter(
            RecommendationOutcome.recommendation_id
            == recommendation_id
        )
        .first()
    )

    return outcome


def get_all_outcomes(
    db: Session
):
    return (
        db.query(RecommendationOutcome)
        .order_by(
            RecommendationOutcome.outcome_id.desc()
        )
        .all()
    )