from pydantic import BaseModel


class EquipmentCreate(BaseModel):

    equipment_id: str
    equipment_type: str
    status: str
    location: str | None = None


class EquipmentResponse(EquipmentCreate):
    pass