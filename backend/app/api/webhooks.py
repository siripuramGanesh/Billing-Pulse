"""
Webhook endpoints for external services (Vapi, etc.).
These are called by external services - no auth required.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Call, Claim
from ..services.claim_outcome import apply_extracted_to_claim, apply_ended_reason_to_claim
from ..workflows import run_post_call_workflow

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/vapi")
async def vapi_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Vapi server URL webhook. Receives call events.
    Configure this URL in Vapi dashboard: https://your-domain/api/webhooks/vapi
    Enable: end-of-call-report, status-update
    """
    try:
        body = await request.json()
    except Exception:
        return {"ok": True}

    msg = body.get("message") or body
    msg_type = msg.get("type", "")

    call_obj = msg.get("call") or {}
    external_id = call_obj.get("id") or call_obj.get("callId")
    if isinstance(external_id, dict):
        external_id = external_id.get("id")

    if not external_id:
        return {"ok": True}

    # Find our Call record
    call_record = db.query(Call).filter(Call.external_id == str(external_id)).first()
    if not call_record:
        return {"ok": True}

    if msg_type == "status-update":
        status = msg.get("status", "")
        if status == "ended":
            call_record.status = "ended"
            db.commit()
        elif status == "in-progress":
            call_record.status = "in_progress"
            db.commit()
        return {"ok": True}

    if msg_type == "end-of-call-report":
        artifact = msg.get("artifact") or {}
        transcript = artifact.get("transcript", "")
        ended_reason = msg.get("endedReason", "unknown")

        call_record.status = "ended"
        call_record.transcript = transcript or None
        call_record.outcome = _map_ended_reason(ended_reason)

        # Try to get duration from call object
        duration = call_obj.get("duration") or call_obj.get("durationSeconds")
        if duration is not None:
            call_record.duration_seconds = int(duration)

        # Post-call workflow: extract → apply to claim → optionally schedule follow-up
        claim = db.get(Claim, call_record.claim_id)
        payer = claim.payer if claim else None
        run_post_call_workflow(
            db=db,
            call_record=call_record,
            transcript=transcript or "",
            ended_reason=ended_reason,
            denial_code=claim.denial_code if claim else None,
            payer_name=payer.name if payer else None,
        )
        db.commit()

    return {"ok": True}


def _map_ended_reason(reason: str) -> str:
    """Map Vapi endedReason to our CallOutcome."""
    reason = (reason or "").lower()
    if "hangup" in reason or "completed" in reason:
        return "resolved"
    if "no-answer" in reason or "no_answer" in reason or "busy" in reason:
        return "no_answer"
    if "failed" in reason or "error" in reason:
        return "failed"
    return "resolved"


