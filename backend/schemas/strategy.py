from pydantic import BaseModel, Field


class StrategyComparisonScenario(BaseModel):
    emergency_patients: int = Field(default=0, ge=0)
    high_priority_patients: int = Field(default=0, ge=0)
    medium_priority_patients: int = Field(default=0, ge=0)
    low_priority_patients: int = Field(default=0, ge=0)

    equipment_requirements: dict[str, int] = Field(default_factory=dict)

    strategies: list[str] = Field(
        default=[
            "baseline",
            "add_icu_beds",
            "add_icu_staff",
            "add_icu_beds_and_staff",
            "reallocation"
        ]
    )