from pydantic import BaseModel


class StaffCreate(BaseModel):

    staff_id: str
    name: str
    role: str
    department: str | None = None
    status: str


class StaffResponse(StaffCreate):
    pass