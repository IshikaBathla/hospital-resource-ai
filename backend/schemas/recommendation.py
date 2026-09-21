from pydantic import BaseModel


class RecommendationAction(BaseModel):

    modified_bed_id: str | None = None

    modified_staff_id: str | None = None

    modified_equipment_id: str | None = None

    reason: str | None = None