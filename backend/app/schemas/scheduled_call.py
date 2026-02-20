from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ScheduledCallCreate(BaseModel):
    claim_id: int
    call_after: datetime
    reason: Optional[str] = None


class ScheduledCallResponse(BaseModel):
    id: int
    claim_id: int
    call_after: datetime
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
