"""
LLM-based extraction of structured claim outcome from call transcript.
Uses RAG (denial codes + payer policies) when available to improve extraction.
"""

from typing import Optional
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser

from ..core.config import get_settings
from ..services.rag_service import query_denial_codes, query_payer_policies


class ExtractedOutcome(BaseModel):
    """Structured outcome extracted from call transcript."""

    claim_status: str = Field(
        description="Current status of the claim: pending, paid, denied, reprocessing, appeal_required, or unknown"
    )
    denial_reason: Optional[str] = Field(
        default=None,
        description="Reason for denial if denied, otherwise null",
    )
    denial_code: Optional[str] = Field(
        default=None,
        description="Denial/error code if mentioned, e.g. CO-16, PR-1",
    )
    action_taken: Optional[str] = Field(
        default=None,
        description="What action was taken: reprocess_requested, appeal_escalated, info_gathered, none, etc.",
    )
    next_steps: Optional[str] = Field(
        default=None,
        description="Recommended next steps or follow-up needed",
    )
    amount_paid: Optional[str] = Field(
        default=None,
        description="Amount paid or approved if mentioned",
    )
    summary: str = Field(
        description="Brief 1-2 sentence summary of the call outcome",
    )


EXTRACTION_PROMPT = """You are an expert medical billing analyst. Extract structured information from this insurance claim status call transcript.

The call was made to check on a medical billing claim. Extract the key outcomes and update the claim accordingly.
{rag_context}

Transcript:
---
{transcript}
---

If the transcript is empty, very short, or indicates the call was not answered, return claim_status="unknown" and summary describing what happened.

Extract the following in JSON format:"""


def _build_rag_context(
    transcript: str,
    denial_code: Optional[str] = None,
    payer_name: Optional[str] = None,
) -> str:
    """Query RAG for denial codes and payer policies; return a string to inject into the prompt."""
    parts = []
    query_denial = (denial_code or "").strip() or transcript[:500].strip()
    if query_denial:
        denial_snippets = query_denial_codes(query_denial, k=3)
        if denial_snippets:
            parts.append(
                "## Relevant denial code / remedy reference\n"
                + "\n".join(f"- {s}" for s in denial_snippets)
            )
    query_payer = transcript[:500].strip() or (payer_name or "").strip()
    if query_payer:
        policy_snippets = query_payer_policies(query_payer, payer_name=payer_name, k=3)
        if policy_snippets:
            parts.append(
                "## Relevant payer policy\n"
                + "\n".join(f"- {s}" for s in policy_snippets)
            )
    if not parts:
        return ""
    return "\n\n".join(parts) + "\n\n"


def extract_outcome_from_transcript(
    transcript: str,
    denial_code: Optional[str] = None,
    payer_name: Optional[str] = None,
) -> Optional[ExtractedOutcome]:
    """
    Use LLM to extract structured outcome from call transcript.
    Optionally uses RAG (denial_code, payer_name) to inject reference context.
    Returns None if OPENAI_API_KEY is not configured or extraction fails.
    """
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        return None

    if not transcript or not transcript.strip():
        return ExtractedOutcome(
            claim_status="unknown",
            summary="No transcript available",
        )

    rag_context = _build_rag_context(transcript, denial_code=denial_code, payer_name=payer_name)
    if rag_context:
        rag_context = "Use the following reference context to interpret codes and policies mentioned in the call.\n\n" + rag_context
    else:
        rag_context = ""

    try:
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )
        parser = PydanticOutputParser(pydantic_object=ExtractedOutcome)
        format_instructions = parser.get_format_instructions()

        messages = [
            SystemMessage(
                content="You extract structured data from medical billing call transcripts. "
                "Respond only with valid JSON matching the schema. "
                "Be concise and accurate."
            ),
            HumanMessage(
                content=EXTRACTION_PROMPT.format(transcript=transcript[:8000], rag_context=rag_context)
                + "\n\n"
                + format_instructions
            ),
        ]

        response = llm.invoke(messages)
        return parser.parse(response.content)
    except Exception:
        return None
