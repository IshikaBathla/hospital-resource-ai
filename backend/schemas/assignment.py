from pydantic import BaseModel


class AssignmentCreate(BaseModel):

    patient_id: str
    bed_id: str | None = None
    staff_id: str | None = None
    equipment_id: str | None = None