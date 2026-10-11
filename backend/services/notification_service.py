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
    target_role: str | None = None,
):
    """
    Create an operational notification.

    If a matching unread notification already exists,
    refresh its details instead of creating a duplicate.

    This function does not allocate hospital resources.
    """

    try:
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
                "title": title,
            },
        ).fetchone()

        if existing:
            notification_id = existing.notification_id

            # Refresh the existing notification.
            # This also repairs a missing recommendation link
            # if a valid recommendation is now available.
            db.execute(
                text("""
                    UPDATE notifications
                    SET severity = :severity,
                        message = :message,
                        patient_id = :patient_id,
                        recommendation_id = COALESCE(
                            :recommendation_id,
                            recommendation_id
                        ),
                        target_role = :target_role
                    WHERE notification_id = :notification_id
                """),
                {
                    "severity": severity,
                    "message": message,
                    "patient_id": patient_id,
                    "recommendation_id": recommendation_id,
                    "target_role": target_role,
                    "notification_id": notification_id,
                },
            )

            db.commit()

            return {
                "created": False,
                "notification_id": notification_id,
            }

        result = db.execute(
            text("""
                INSERT INTO notifications (
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
                VALUES (
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
                "target_role": target_role,
            },
        )

        notification_id = result.scalar_one()
        db.commit()

        return {
            "created": True,
            "notification_id": notification_id,
        }

    except Exception:
        db.rollback()
        raise


def create_notifications_from_alerts(
    db: Session,
    alerts: list,
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
                "SYSTEM_ALERT",
            ),
            severity=alert.get(
                "severity",
                "WARNING",
            ),
            title=alert.get(
                "title",
                "Hospital operational alert",
            ),
            message=alert.get("message", ""),
            department=alert.get("department"),
            patient_id=alert.get("patient_id"),
            recommendation_id=alert.get(
                "recommendation_id"
            ),
            target_role="COORDINATOR",
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
        "created_count": len(created_notifications),
        "skipped_count": len(skipped_notifications),
        "created_notification_ids": created_notifications,
        "skipped_notification_ids": skipped_notifications,
    }