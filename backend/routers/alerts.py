from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db

from backend.services.alert_service import (
    generate_operational_alerts
)

from backend.utils.dependencies import (
    get_current_user
)


router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)


# ============================================================
# GET OPERATIONAL ALERTS
# ============================================================

@router.get("")
def get_operational_alerts(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get current operational alerts.

    Alert generation is handled by the
    alert service layer.
    """

    return generate_operational_alerts(db)