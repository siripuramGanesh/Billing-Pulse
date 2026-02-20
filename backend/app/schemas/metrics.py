from pydantic import BaseModel
from typing import Optional


class MetricsResponse(BaseModel):
    total_claims: int
    pending_claims: int
    in_progress_claims: int
    resolved_claims: int
    total_calls: int
    calls_today: int
    calls_this_week: int
    resolution_rate: float  # % of calls that resulted in resolved
    revenue_recovered: Optional[float] = None  # sum of amounts from resolved claims
    calls_by_day: list[dict]  # [{date, count}, ...]
    in_progress_calls: list[dict]  # [{id, claim_id, status}, ...]
