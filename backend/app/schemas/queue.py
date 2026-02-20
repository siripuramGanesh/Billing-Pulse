from pydantic import BaseModel


class QueueClaimRequest(BaseModel):
    claim_id: int


class QueueBulkRequest(BaseModel):
    claim_ids: list[int]


class QueueResponse(BaseModel):
    queued: int
    task_ids: list[str]
    message: str
