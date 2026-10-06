import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.patient import Patient

from backend.schemas.event import HospitalEvent

from backend.services.unified_recommendation_service import (
    generate_unified_recommendation
)

from backend.services.notification_service import (
    create_notification
)

from backend.services.websocket_manager import (
    connection_manager
)

from backend.utils.dependencies import (
    get_current_user
)


router = APIRouter(
    prefix="/events",
    tags=["Hospital Events"]
)


# =========================================================
# PATIENT ARRIVAL EVENT
# =========================================================

@router.post("")
async def process_event(
    event: HospitalEvent,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    # -----------------------------------------------------
    # Validate event type
    # -----------------------------------------------------

    if event.event_type != "PATIENT_ARRIVAL":

        raise HTTPException(
            status_code=400,
            detail="Unsupported event type"
        )

    patient_data = event.patient

    # -----------------------------------------------------
    # Check duplicate patient
    # -----------------------------------------------------

    existing_patient = (
        db.query(Patient)
        .filter(
            Patient.patient_id
            == patient_data.patient_id
        )
        .first()
    )

    if existing_patient:

        raise HTTPException(
            status_code=409,
            detail=(
                f"Patient "
                f"{patient_data.patient_id} "
                "already exists"
            )
        )

    # -----------------------------------------------------
    # Create patient
    # -----------------------------------------------------

    patient = Patient(
        patient_id=patient_data.patient_id,
        name=patient_data.name,
        age=patient_data.age,
        emergency_level=patient_data.emergency_level,
        status=patient_data.status
    )

    db.add(patient)

    # -----------------------------------------------------
    # Flush patient
    # -----------------------------------------------------

    db.flush()

    # -----------------------------------------------------
    # Generate resource recommendation
    #
    # IMPORTANT:
    # This does NOT allocate resources.
    #
    # Human approval is still required.
    # -----------------------------------------------------

    recommendation = (
        generate_unified_recommendation(
            db,
            patient.patient_id
        )
    )

    # -----------------------------------------------------
    # Extract recommendation information
    # -----------------------------------------------------

    recommended_resources = (
        recommendation.get(
            "recommended_resources",
            {}
        )
        if isinstance(recommendation, dict)
        else {}
    )

    resource_status = (
        recommendation.get(
            "resource_status",
            {}
        )
        if isinstance(recommendation, dict)
        else {}
    )

    recommendation_id = (
        recommendation.get(
            "recommendation_id"
        )
        if isinstance(recommendation, dict)
        else None
    )

    recommended_bed_id = (
        recommended_resources.get(
            "bed_id"
        )
    )

    recommended_ward = (
        recommended_resources.get(
            "ward"
        )
    )

    human_decision_required = (
        recommendation.get(
            "human_decision_required",
            True
        )
        if isinstance(recommendation, dict)
        else True
    )

    # -----------------------------------------------------
    # Determine notification severity
    # -----------------------------------------------------

    severity_map = {
        "critical": "CRITICAL",
        "high": "HIGH",
        "medium": "WARNING",
        "low": "INFO"
    }

    severity = severity_map.get(
        patient.emergency_level.lower(),
        "WARNING"
    )

    # -----------------------------------------------------
    # Build notification title
    # -----------------------------------------------------

    notification_title = (
        f"Patient Arrival: "
        f"{patient.name}"
    )

    # -----------------------------------------------------
    # Build notification message
    # -----------------------------------------------------

    if recommended_bed_id:

        notification_message = (
            f"{patient.name} "
            f"({patient.patient_id}) arrived "
            f"with {patient.emergency_level} "
            f"priority. "
            f"Recommended bed: "
            f"{recommended_bed_id}"
        )

        if recommended_ward:

            notification_message += (
                f" ({recommended_ward})"
            )

        if human_decision_required:

            notification_message += (
                ". Human decision required."
            )

    else:

        notification_message = (
            f"{patient.name} "
            f"({patient.patient_id}) arrived "
            f"with {patient.emergency_level} "
            f"priority. "
            f"No immediate bed allocation "
            f"was available. "
            f"Human decision required."
        )

    # -----------------------------------------------------
    # Create persistent notification
    # -----------------------------------------------------

    notification_result = create_notification(
        db=db,
        notification_type="PATIENT_ARRIVAL",
        severity=severity,
        title=notification_title,
        message=notification_message,
        department=recommended_ward,
        patient_id=patient.patient_id,
        recommendation_id=recommendation_id,
        target_role="COORDINATOR"
    )

    # -----------------------------------------------------
    # Commit patient arrival
    #
    # Resource allocation is NOT performed here.
    # -----------------------------------------------------

    db.commit()

    db.refresh(patient)

    # -----------------------------------------------------
    # Build real-time WebSocket payload
    # -----------------------------------------------------

    realtime_event = {
        "event_type": "PATIENT_ARRIVAL",
        "notification_type": "PATIENT_ARRIVAL",
        "notification_id":
            notification_result.get(
                "notification_id"
            ),
        "severity": severity,

        "title": notification_title,

        "message": notification_message,

        "patient": {
            "patient_id":
                patient.patient_id,

            "name":
                patient.name,

            "age":
                patient.age,

            "emergency_level":
                patient.emergency_level,

            "status":
                patient.status
        },

        "recommendation": {
            "recommendation_id":
                recommendation_id,

            "recommended_bed_id":
                recommended_bed_id,

            "recommended_ward":
                recommended_ward,

            "human_decision_required":
                human_decision_required,

            "resource_status":
                resource_status
        }
    }

    # -----------------------------------------------------
    # Broadcast notification to connected browsers
    # -----------------------------------------------------

    await connection_manager.broadcast(
        realtime_event
    )

    # -----------------------------------------------------
    # Final response
    # -----------------------------------------------------

    return {
        "status": "success",

        "event_type": "PATIENT_ARRIVAL",

        "message":
            "Patient arrival event processed",

        "event": {
            "patient_id":
                patient.patient_id,

            "name":
                patient.name,

            "age":
                patient.age,

            "emergency_level":
                patient.emergency_level,

            "status":
                patient.status
        },

        "resource_coordination":
            recommendation,

        "notification": {
            "notification_id":
                notification_result.get(
                    "notification_id"
                ),

            "created":
                notification_result.get(
                    "created"
                )
        },

        "next_action":
            (
                "Patient is now available for "
                "resource coordination and "
                "human decision."
            ),

        "database_modified": True,

        "realtime_broadcast": True
    }