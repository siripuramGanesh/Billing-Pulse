from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CallInitiateRequest(BaseModel):
    claim_id: int


class CallResponse(BaseModel):
    id: int
    claim_id: int
    status: str
    outcome: Optional[str] = None
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    external_id: Optional[str] = None
    extracted_data: Optional[dict] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CallInitiateResponse(BaseModel):
    call_id: int
    external_id: str
    message: str = "Call initiated"
