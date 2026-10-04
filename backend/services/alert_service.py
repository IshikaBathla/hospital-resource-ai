from backend.services.recommendation_service import (
    get_resource_pressure
)


def generate_operational_alerts(db):
    """
    Convert resource-pressure information
    into operational alerts.

    This function does not modify the database.
    """

    pressure_result = get_resource_pressure(db)

    pressure = pressure_result.get(
        "pressure",
        []
    )

    alerts = []

    for department in pressure:

        status = department.get("status")

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
                    "under critical pressure"
                ),
                "message": (
                    f"{department_name} has "
                    f"{available_beds} available beds "
                    f"out of {total_beds}. "
                    f"Predicted arrivals in the next "
                    f"24 hours: {predicted_arrivals:.2f}."
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
                    "under high pressure"
                ),
                "message": (
                    f"{department_name} has "
                    f"{available_beds} available beds "
                    f"out of {total_beds}. "
                    f"Predicted arrivals in the next "
                    f"24 hours: {predicted_arrivals:.2f}."
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
                    "requires attention"
                ),
                "message": (
                    f"{department_name} has "
                    f"{available_beds} available beds "
                    f"out of {total_beds}. "
                    f"Predicted arrivals in the next "
                    f"24 hours: {predicted_arrivals:.2f}."
                ),
                "recommended_action": (
                    "Monitor capacity and forecasted demand."
                )
            })

    return {
        "status": "success",
        "alert_count": len(alerts),
        "alerts": alerts,
        "database_modified": False
    }