from sqlalchemy import text
from sqlalchemy.orm import Session


def create_notification(
    db: Session,
    notification_type: str,
    severity: str,
    title: str,
    message: str,
    department: str | None = None,
    patient_id: str | None = None,
    recommendation_id: int | None = None,
    target_role: str | None = None
):
    """
    Create an operational notification.

    Duplicate unread notifications with the same
    type, department and title are not created.
    """

    existing = db.execute(
        text("""
            SELECT notification_id
            FROM notifications
            WHERE notification_type = :notification_type
              AND department IS NOT DISTINCT FROM :department
              AND title = :title
              AND status = 'UNREAD'
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {
            "notification_type": notification_type,
            "department": department,
            "title": title
        }
    ).fetchone()

    if existing:
        return {
            "created": False,
            "notification_id": existing.notification_id
        }

    result = db.execute(
        text("""
            INSERT INTO notifications
            (
                notification_type,
                severity,
                title,
                message,
                department,
                patient_id,
                recommendation_id,
                target_role,
                status
            )
            VALUES
            (
                :notification_type,
                :severity,
                :title,
                :message,
                :department,
                :patient_id,
                :recommendation_id,
                :target_role,
                'UNREAD'
            )
            RETURNING notification_id
        """),
        {
            "notification_type": notification_type,
            "severity": severity,
            "title": title,
            "message": message,
            "department": department,
            "patient_id": patient_id,
            "recommendation_id": recommendation_id,
            "target_role": target_role
        }
    )

    notification_id = result.scalar()

    db.commit()

    return {
        "created": True,
        "notification_id": notification_id
    }


def create_notifications_from_alerts(
    db: Session,
    alerts: list
):
    """
    Convert operational alerts into persistent notifications.
    """

    created_notifications = []
    skipped_notifications = []

    for alert in alerts:

        result = create_notification(
            db=db,

            notification_type=alert.get(
                "alert_type",
                "SYSTEM_ALERT"
            ),

            severity=alert.get(
                "severity",
                "WARNING"
            ),

            title=alert.get(
                "title",
                "Hospital operational alert"
            ),

            message=alert.get(
                "message",
                ""
            ),

            department=alert.get(
                "department"
            ),

            target_role="COORDINATOR"
        )

        if result["created"]:

            created_notifications.append(
                result["notification_id"]
            )

        else:

            skipped_notifications.append(
                result["notification_id"]
            )

    return {
        "created_count":
            len(created_notifications),

        "skipped_count":
            len(skipped_notifications),

        "created_notification_ids":
            created_notifications,

        "skipped_notification_ids":
            skipped_notifications
    }