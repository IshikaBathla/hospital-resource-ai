from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.strategy import StrategyComparisonScenario
from backend.services.strategy_comparison_service import run_strategy_comparison


router = APIRouter(
    prefix="/strategy",
    tags=["Strategy Comparison"]
)


@router.post("/compare")
def compare_strategies(
    scenario: StrategyComparisonScenario,
    db: Session = Depends(get_db)
):
    return run_strategy_comparison(
        db=db,
        emergency_patients=scenario.emergency_patients,
        high_priority_patients=scenario.high_priority_patients,
        medium_priority_patients=scenario.medium_priority_patients,
        low_priority_patients=scenario.low_priority_patients,
        equipment_requirements=scenario.equipment_requirements,
        strategies=scenario.strategies
    )