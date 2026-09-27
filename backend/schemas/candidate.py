from pydantic import BaseModel, Field


class RecommendationCandidate(BaseModel):
    action_type: str

    patient_id: str

    recommended_bed_id: str | None = None
    recommended_staff_id: str | None = None
    recommended_equipment_id: str | None = None

    current_bed_id: str | None = None
    current_staff_id: str | None = None
    current_equipment_id: str | None = None

    constraints: list[str] = Field(
        default_factory=list
    )

    score: int

    reason: str

    expected_impact: str

    feasible: bool = True