from typing import Literal

from pydantic import BaseModel, Field


class PatientArrivalData(BaseModel):
    patient_id: str
    name: str
    age: int = Field(gt=0)
    emergency_level: Literal[
        "critical",
        "high",
        "medium",
        "low"
    ]
    status: Literal["waiting", "admitted"] = "waiting"


class HospitalEvent(BaseModel):
    event_type: Literal["PATIENT_ARRIVAL"]
    patient: PatientArrivalData