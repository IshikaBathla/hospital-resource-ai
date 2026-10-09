from datetime import datetime

from pydantic import BaseModel


class PatientCreate(BaseModel):

    patient_id: str
    name: str
    age: int
    emergency_level: str
    status: str


class PatientResponse(PatientCreate):

    care_status: str
    transfer_ready: bool
    expected_release_at: datetime | None = None
    staff_note: str | None = None