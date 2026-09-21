from datetime import datetime

from pydantic import BaseModel


class BedCreate(BaseModel):

    bed_id: str
    ward: str
    status: str
    patient_id: str | None = None
    expected_release_at: datetime | None = None


class BedUpdate(BaseModel):

    status: str
    patient_id: str | None = None
    expected_release_at: datetime | None = None


class BedResponse(BedCreate):
    pass