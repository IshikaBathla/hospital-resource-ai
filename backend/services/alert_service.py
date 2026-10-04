from backend.services.recommendation_service import (
    get_resource_pressure
)

from backend.services.notification_service import (
    create_notifications_from_alerts
)


def generate_operational_alerts(db):
    """
    Convert resource-pressure information
    into operational alerts.

    Operational alerts are also converted into
    persistent notifications.

    This function does not allocate resources
    or modify hospital resource state.
    """

    pressure_result = get_resource_pressure(db)

    pressure = pressure_result.get(
        "pressure",
        []
    )

    alerts = []

    for department in pressure:

        status = department.get(
            "status"
        )

        department_name = department.get(
            "department"
        )

        predicted_arrivals = department.get(
            "predicted_24h_arrivals",
            0
        )

        available_beds = department.get(
            "available_beds",
            0
        )

        total_beds = department.get(
            "total_beds",
            0
        )

        # =====================================================
        # CRITICAL PRESSURE
        # =====================================================

        if status == "critical_pressure":

            alerts.append({
                "alert_type": "RESOURCE_PRESSURE",

                "severity": "CRITICAL",

                "department": department_name,

                "title": (
                    f"{department_name} capacity "
                    f"under critical pressure"
                ),

                "message": (
                    f"{department_name} has "
                    f"{available_beds} available beds "
                    f"out of {total_beds}. "
                    f"Predicted arrivals in the next "
                    f"24 hours: "
                    f"{predicted_arrivals:.2f}."
                ),

                "recommended_action": (
                    "Review bed availability, "
                    "staff capacity and pending "
                    "resource recommendations."
                )
            })

        # =====================================================
        # HIGH PRESSURE
        # =====================================================

        elif status == "high_pressure":

            alerts.append({
                "alert_type": "RESOURCE_PRESSURE",

                "severity": "HIGH",

                "department": department_name,

                "title": (
                    f"{department_name} capacity "
                    f"under high pressure"
                ),

                "message": (
                    f"{department_name} has "
                    f"{available_beds} available beds "
                    f"out of {total_beds}. "
                    f"Predicted arrivals in the next "
                    f"24 hours: "
                    f"{predicted_arrivals:.2f}."
                ),

                "recommended_action": (
                    "Review resource availability "
                    "and upcoming demand."
                )
            })

        # =====================================================
        # MODERATE PRESSURE
        # =====================================================

        elif status == "moderate_pressure":

            alerts.append({
                "alert_type": "RESOURCE_PRESSURE",

                "severity": "WARNING",

                "department": department_name,

                "title": (
                    f"{department_name} capacity "
                    f"requires attention"
                ),

                "message": (
                    f"{department_name} has "
                    f"{available_beds} available beds "
                    f"out of {total_beds}. "
                    f"Predicted arrivals in the next "
                    f"24 hours: "
                    f"{predicted_arrivals:.2f}."
                ),

                "recommended_action": (
                    "Monitor capacity and "
                    "forecasted demand."
                )
            })

    # =========================================================
    # CREATE PERSISTENT NOTIFICATIONS
    # =========================================================

    notification_result = (
        create_notifications_from_alerts(
            db,
            alerts
        )
    )

    # =========================================================
    # FINAL RESPONSE
    # =========================================================

    return {
        "status": "success",

        "alert_count": len(alerts),

        "alerts": alerts,

        "notifications": notification_result,

        "database_modified": True
        if notification_result["created_count"] > 0
        else False
    }