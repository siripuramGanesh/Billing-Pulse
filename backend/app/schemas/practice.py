from pydantic import BaseModel


class PracticeCreate(BaseModel):
    name: str
    npi: str | None = None
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None
    notification_email: str | None = None


class PracticeUpdate(BaseModel):
    name: str | None = None
    npi: str | None = None
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None
    notification_email: str | None = None


class PracticeResponse(BaseModel):
    id: int
    name: str
    npi: str | None
    tax_id: str | None
    address: str | None
    phone: str | None
    notification_email: str | None

    class Config:
        from_attributes = True
