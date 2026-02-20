"""
Post-call workflow: extract outcome → apply to claim → optionally schedule follow-up.
Implemented as a LangGraph state graph for clarity and future extension.
"""

import re
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

# Context for passing db/call_record into nodes (LangGraph may not pass config to plain functions)
_workflow_context: ContextVar[dict] = ContextVar("workflow_context", default={})

from ..agents.outcome_extractor import (
    ExtractedOutcome,
    extract_outcome_from_transcript,
)
from ..models import Claim, ScheduledCall
from ..services.claim_outcome import apply_extracted_to_claim, apply_ended_reason_to_claim
from ..services.email_service import send_claim_call_notification


class PostCallState(TypedDict, total=False):
    """State for the post-call workflow."""

    transcript: str
    ended_reason: str
    claim_id: int
    call_id: int
    denial_code: Optional[str]
    payer_name: Optional[str]
    extracted: Optional[dict]
    claim_updated: bool
    schedule_after: Optional[datetime]
    schedule_reason: Optional[str]
    claimer_notified: bool
    error: Optional[str]


# Keywords that suggest a follow-up call
FOLLOW_UP_KEYWORDS = re.compile(
    r"call\s*back|callback|follow\s*up|followup|call\s*again|"
    r"in\s+\d+\s+days?|next\s+week|recheck|call\s+in",
    re.I,
)


def _extract_node(state: PostCallState, config: Optional[dict] = None) -> dict:
    """Run LLM extraction; write result into state."""
    ctx = _workflow_context.get() or (config or {}).get("configurable", {})
    db: Session = ctx.get("db")
    if not db:
        return {"error": "No db in context"}
    transcript = (state.get("transcript") or "").strip()
    if not transcript:
        return {"extracted": None}
    extracted = extract_outcome_from_transcript(
        transcript,
        denial_code=state.get("denial_code"),
        payer_name=state.get("payer_name"),
    )
    if extracted:
        return {"extracted": extracted.model_dump(), "error": None}
    return {"extracted": None}


def _apply_node(state: PostCallState, config: Optional[dict] = None) -> dict:
    """Apply extracted outcome to claim and call record."""
    ctx = _workflow_context.get() or (config or {}).get("configurable", {})
    db: Session = ctx.get("db")
    call_record = ctx.get("call_record")
    if not db or not call_record:
        return {"claim_updated": False, "error": "Missing db or call_record"}
    extracted_data = state.get("extracted")
    claim_id = state.get("claim_id")
    ended_reason = state.get("ended_reason") or "unknown"
    if not claim_id:
        return {"claim_updated": False}
    if extracted_data:
        extracted = ExtractedOutcome.model_validate(extracted_data)
        call_record.extracted_data = extracted_data
        apply_extracted_to_claim(db, claim_id, extracted, ended_reason)
        return {"claim_updated": True, "error": None}
    else:
        apply_ended_reason_to_claim(db, claim_id, getattr(call_record, "outcome", None) or "resolved")
        return {"claim_updated": True}


def _notify_claimer_node(state: PostCallState, config: Optional[dict] = None) -> dict:
    """Email the practice (claimer) with call outcome and set claim.claimer_notified_at."""
    ctx = _workflow_context.get() or (config or {}).get("configurable", {})
    db: Session = ctx.get("db")
    call_record = ctx.get("call_record")
    if not db or not call_record:
        return {"claimer_notified": False}
    claim_id = state.get("claim_id")
    if not claim_id:
        return {"claimer_notified": False}
    claim = db.get(Claim, claim_id)
    if not claim or not claim.payer:
        return {"claimer_notified": False}
    payer_name = getattr(claim.payer, "name", "") or "Payer"
    duration = getattr(call_record, "duration_seconds", None)
    ok = send_claim_call_notification(
        db,
        claim_id=claim_id,
        payer_name=payer_name,
        extracted=state.get("extracted"),
        call_duration_seconds=duration,
    )
    return {"claimer_notified": ok}


def _decide_follow_up_node(state: PostCallState, config: Optional[dict] = None) -> dict:
    """Set schedule_after and schedule_reason if follow-up is suggested."""
    extracted = state.get("extracted")
    if not extracted or not isinstance(extracted, dict):
        return {}
    next_steps = (extracted.get("next_steps") or "").strip()
    summary = (extracted.get("summary") or "").strip()
    text = f"{next_steps} {summary}"
    if not text or not FOLLOW_UP_KEYWORDS.search(text):
        return {}
    days = 5
    match = re.search(r"in\s+(\d+)\s+days?", text, re.I)
    if match:
        try:
            days = min(30, max(1, int(match.group(1))))
        except ValueError:
            pass
    now = datetime.now(timezone.utc)
    schedule_after = now + timedelta(days=days)
    reason = (next_steps or summary)[:255]
    return {"schedule_after": schedule_after, "schedule_reason": reason or "Follow-up per call outcome"}


def _schedule_node(state: PostCallState, config: Optional[dict] = None) -> dict:
    """Create ScheduledCall if schedule_after is set."""
    ctx = _workflow_context.get() or (config or {}).get("configurable", {})
    db: Session = ctx.get("db")
    if not db:
        return {}
    claim_id = state.get("claim_id")
    schedule_after = state.get("schedule_after")
    schedule_reason = state.get("schedule_reason")
    if not claim_id or not schedule_after:
        return {}
    scheduled = ScheduledCall(
        claim_id=claim_id,
        call_after=schedule_after,
        reason=schedule_reason,
    )
    db.add(scheduled)
    return {}


def _route_after_decide(state: PostCallState) -> Literal["schedule", "__end__"]:
    if state.get("schedule_after"):
        return "schedule"
    return "__end__"


def _build_post_call_graph() -> Any:
    """Build and compile the post-call workflow graph."""
    graph = StateGraph(PostCallState)
    graph.add_node("extract", _extract_node)
    graph.add_node("apply", _apply_node)
    graph.add_node("notify_claimer", _notify_claimer_node)
    graph.add_node("decide_follow_up", _decide_follow_up_node)
    graph.add_node("schedule", _schedule_node)

    graph.add_edge("extract", "apply")
    graph.add_edge("apply", "notify_claimer")
    graph.add_edge("notify_claimer", "decide_follow_up")
    graph.add_conditional_edges("decide_follow_up", _route_after_decide, {"schedule": "schedule", "__end__": END})
    graph.add_edge("schedule", END)

    graph.set_entry_point("extract")
    return graph.compile()


_compiled_graph = None


def _get_graph() -> Any:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_post_call_graph()
    return _compiled_graph


def run_post_call_workflow(
    db: Session,
    call_record: Any,
    transcript: str,
    ended_reason: str,
    denial_code: Optional[str] = None,
    payer_name: Optional[str] = None,
) -> PostCallState:
    """
    Run the post-call workflow: extract outcome, apply to claim, optionally schedule follow-up.
    Uses the same db session; caller should commit after.
    """
    initial: PostCallState = {
        "transcript": transcript or "",
        "ended_reason": ended_reason or "unknown",
        "claim_id": call_record.claim_id,
        "call_id": getattr(call_record, "id", 0),
        "denial_code": denial_code,
        "payer_name": payer_name,
    }
    token = _workflow_context.set({"db": db, "call_record": call_record})
    try:
        result = _get_graph().invoke(initial, config={"configurable": {"db": db, "call_record": call_record}})
        return result
    finally:
        _workflow_context.reset(token)
