from pydantic import BaseModel, Field


class WhatIfScenario(BaseModel):
    emergency_patients: int = Field(default=0, ge=0)
    high_priority_patients: int = Field(default=0, ge=0)
    medium_priority_patients: int = Field(default=0, ge=0)
    low_priority_patients: int = Field(default=0, ge=0)

    additional_icu_beds: int = Field(default=0, ge=0)
    additional_general_beds: int = Field(default=0, ge=0)

    unavailable_icu_beds: int = Field(default=0, ge=0)
    unavailable_general_beds: int = Field(default=0, ge=0)

    unavailable_icu_staff: int = Field(default=0, ge=0)
    unavailable_general_staff: int = Field(default=0, ge=0)

    additional_icu_staff: int = Field(default=0, ge=0)
additional_general_staff: int = Field(default=0, ge=0)