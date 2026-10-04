from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database import get_db

from backend.utils.dependencies import (
    get_current_user,
    require_roles
)


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)


# =========================================================
# GET NOTIFICATIONS
# =========================================================

@router.get("")
def get_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get operational notifications.
    """

    notifications = db.execute(
        text("""
            SELECT
                notification_id,
                notification_type,
                severity,
                title,
                message,
                department,
                patient_id,
                recommendation_id,
                target_role,
                status,
                created_at,
                acknowledged_at,
                acknowledged_by
            FROM notifications
            ORDER BY created_at DESC
        """)
    ).mappings().all()

    return {
        "status": "success",
        "notification_count": len(notifications),
        "notifications": [
            dict(notification)
            for notification in notifications
        ]
    }


# =========================================================
# ACKNOWLEDGE NOTIFICATION
# =========================================================

@router.put(
    "/{notification_id}/acknowledge"
)
def acknowledge_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles("ADMIN", "COORDINATOR")
    )
):
    """
    Acknowledge an operational notification.

    Only ADMIN and COORDINATOR users
    can acknowledge notifications.
    """

    # -----------------------------------------------------
    # Check notification exists
    # -----------------------------------------------------

    notification = db.execute(
        text("""
            SELECT
                notification_id,
                status
            FROM notifications
            WHERE notification_id = :notification_id
        """),
        {
            "notification_id": notification_id
        }
    ).mappings().first()

    if not notification:

        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )

    # -----------------------------------------------------
    # Prevent duplicate acknowledgement
    # -----------------------------------------------------

    if notification["status"] == "ACKNOWLEDGED":

        raise HTTPException(
            status_code=400,
            detail="Notification is already acknowledged"
        )

    # -----------------------------------------------------
    # Get logged-in user's ID
    # -----------------------------------------------------

    user_id = current_user.user_id

    # -----------------------------------------------------
    # Update notification
    # -----------------------------------------------------

    db.execute(
        text("""
            UPDATE notifications
            SET
                status = 'ACKNOWLEDGED',
                acknowledged_at = CURRENT_TIMESTAMP,
                acknowledged_by = :acknowledged_by
            WHERE notification_id = :notification_id
        """),
        {
            "notification_id": notification_id,
            "acknowledged_by": user_id
        }
    )

    db.commit()

    # -----------------------------------------------------
    # Return updated notification
    # -----------------------------------------------------

    updated_notification = db.execute(
        text("""
            SELECT
                notification_id,
                notification_type,
                severity,
                title,
                message,
                department,
                patient_id,
                recommendation_id,
                target_role,
                status,
                created_at,
                acknowledged_at,
                acknowledged_by
            FROM notifications
            WHERE notification_id = :notification_id
        """),
        {
            "notification_id": notification_id
        }
    ).mappings().first()

    return {
        "status": "success",
        "message": "Notification acknowledged successfully",
        "notification": dict(updated_notification)
    }