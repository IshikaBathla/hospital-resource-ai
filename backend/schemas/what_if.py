from typing import Dict
from pydantic import BaseModel, Field, field_validator


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

    equipment_requirements: Dict[str, int] = Field(
        default_factory=dict
    )

    @field_validator("equipment_requirements")
    @classmethod
    def validate_equipment_requirements(cls, value):
        for equipment, quantity in value.items():
            if not equipment.strip():
                raise ValueError("Equipment name cannot be empty.")

            if quantity < 0:
                raise ValueError(
                    f"Quantity for {equipment} cannot be negative."
                )

        return value