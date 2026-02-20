"""API for RAG ingestion: denial codes and payer policies."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..core.dependencies import get_current_user
from ..models import User
from ..services.rag_service import add_denial_codes, add_payer_policies

router = APIRouter(prefix="/rag", tags=["rag"])


class DenialCodeEntry(BaseModel):
    code: str | None = None
    description: str | None = None
    remedy: str | None = None
    payer: str | None = None


class DenialCodesIngestRequest(BaseModel):
    entries: list[DenialCodeEntry] = Field(..., min_length=1)


class PayerPolicyEntry(BaseModel):
    payer_name: str | None = None
    text: str = ""


class PayerPoliciesIngestRequest(BaseModel):
    entries: list[PayerPolicyEntry] = Field(..., min_length=1)


class IngestResponse(BaseModel):
    added: int


@router.post("/denial-codes", response_model=IngestResponse)
def ingest_denial_codes(
    data: DenialCodesIngestRequest,
    current_user: User = Depends(get_current_user),
):
    """Ingest denial code entries into the RAG vector store. Requires OPENAI_API_KEY."""
    dicts = [e.model_dump() for e in data.entries]
    added = add_denial_codes(dicts)
    return IngestResponse(added=added)


@router.post("/payer-policies", response_model=IngestResponse)
def ingest_payer_policies(
    data: PayerPoliciesIngestRequest,
    current_user: User = Depends(get_current_user),
):
    """Ingest payer policy text into the RAG vector store. Requires OPENAI_API_KEY."""
    dicts = [{"payer_name": e.payer_name, "text": e.text} for e in data.entries]
    added = add_payer_policies(dicts)
    return IngestResponse(added=added)
