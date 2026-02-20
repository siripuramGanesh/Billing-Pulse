from pydantic import BaseModel


class PayerCreate(BaseModel):
    name: str
    phone: str
    ivr_notes: str | None = None
    department_code: str | None = None


class PayerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    ivr_notes: str | None = None
    department_code: str | None = None


class PayerResponse(BaseModel):
    id: int
    practice_id: int
    name: str
    phone: str
    ivr_notes: str | None
    department_code: str | None

    class Config:
        from_attributes = True
