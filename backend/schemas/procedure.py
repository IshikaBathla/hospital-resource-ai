from datetime import datetime

from pydantic import BaseModel


class ProcedureCreate(BaseModel):

    patient_id: str

    bed_id: str | None = None

    procedure_name: str

    duration_minutes: int


class ProcedureResponse(BaseModel):

    procedure_id: int

    patient_id: str | None

    bed_id: str | None

    procedure_name: str

    status: str

    expected_end_at: datetime | None