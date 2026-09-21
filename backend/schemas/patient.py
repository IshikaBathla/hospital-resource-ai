from pydantic import BaseModel


class PatientCreate(BaseModel):

    patient_id: str
    name: str
    age: int
    emergency_level: str
    status: str


class PatientResponse(PatientCreate):
    pass