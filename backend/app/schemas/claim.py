from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class ClaimCreate(BaseModel):
    payer_id: int
    claim_number: str
    patient_name: str | None = None
    patient_dob: str | None = None
    date_of_service: str | None = None
    amount: Decimal | None = None
    denial_reason: str | None = None
    denial_code: str | None = None
    notes: str | None = None


class ClaimUpdate(BaseModel):
    status: str | None = None
    denial_reason: str | None = None
    denial_code: str | None = None
    notes: str | None = None


class ClaimResponse(BaseModel):
    id: int
    practice_id: int
    payer_id: int
    claim_number: str
    patient_name: str | None
    patient_dob: str | None
    date_of_service: str | None
    amount: Decimal | None
    status: str
    denial_reason: str | None
    denial_code: str | None
    notes: str | None
    claimer_notified_at: datetime | None

    class Config:
        from_attributes = True


class ClaimBulkCreate(BaseModel):
    claims: list[ClaimCreate]
