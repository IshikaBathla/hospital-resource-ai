from pydantic import BaseModel, Field


class WhatIfPatientRequest(BaseModel):
    patient_id: str
    emergency_level: str
    required_ward: str | None = None


class WhatIfSimulationRequest(BaseModel):
    patients: list[WhatIfPatientRequest] = Field(
        default_factory=list
    )