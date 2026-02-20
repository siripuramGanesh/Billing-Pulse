from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..core.dependencies import get_current_user
from ..models import User, Claim, Payer, Call
from ..schemas import CallInitiateRequest, CallInitiateResponse, CallResponse
from ..schemas.queue import QueueBulkRequest, QueueResponse
from ..services.vapi_service import create_outbound_call
from ..agents.call_context import build_call_system_prompt, build_first_message
from ..tasks.call_tasks import initiate_call_for_claim
from ..services.audit_service import log as audit_log

router = APIRouter(prefix="/calls", tags=["calls"])


def require_practice(current_user: User) -> int:
    if not current_user.practice_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create a practice first",
        )
    return current_user.practice_id


@router.post("/initiate", response_model=CallInitiateResponse)
async def initiate_call(
    data: CallInitiateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initiate an outbound call for a claim. Calls the payer's phone number."""
    practice_id = require_practice(current_user)

    claim = (
        db.query(Claim)
        .filter(Claim.id == data.claim_id, Claim.practice_id == practice_id)
        .first()
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    payer = db.get(Payer, claim.payer_id)
    if not payer or not payer.phone:
        raise HTTPException(
            status_code=400,
            detail="Payer has no phone number configured",
        )

    claim_context = {
        "system_prompt": build_call_system_prompt(claim, payer),
        "first_message": build_first_message(claim, payer),
    }

    try:
        result = await create_outbound_call(
            customer_phone=payer.phone,
            claim_context=claim_context,
            metadata={
                "claim_id": str(claim.id),
                "claim_number": claim.claim_number,
                "practice_id": str(practice_id),
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to initiate call: {str(e)}",
        )

    external_id = result.get("id") or result.get("callId") or str(result)
    if isinstance(external_id, dict):
        external_id = external_id.get("id", str(external_id))

    call = Call(
        claim_id=claim.id,
        status="initiated",
        external_id=str(external_id),
    )
    db.add(call)
    claim.status = "in_progress"
    db.flush()
    audit_log(db, practice_id, "call.initiate", "call", user_id=current_user.id, resource_id=str(call.id), details={"claim_id": claim.id})
    db.commit()
    db.refresh(call)

    return CallInitiateResponse(
        call_id=call.id,
        external_id=str(external_id),
    )


@router.post("/queue", response_model=QueueResponse)
def queue_call(
    data: CallInitiateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Queue a claim for background call. Returns immediately."""
    practice_id = require_practice(current_user)
    claim = (
        db.query(Claim)
        .filter(Claim.id == data.claim_id, Claim.practice_id == practice_id)
        .first()
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status == "in_progress":
        raise HTTPException(status_code=400, detail="Claim already has call in progress")
    payer = db.get(Payer, claim.payer_id)
    if not payer or not payer.phone:
        raise HTTPException(status_code=400, detail="Payer has no phone number")
    task = initiate_call_for_claim.delay(claim.id)
    return QueueResponse(queued=1, task_ids=[task.id], message="Claim queued for call")


@router.post("/queue/bulk", response_model=QueueResponse)
def queue_calls_bulk(
    data: QueueBulkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Queue multiple claims for background calls. Claims are processed with rate limiting."""
    practice_id = require_practice(current_user)
    claims = (
        db.query(Claim)
        .filter(Claim.id.in_(data.claim_ids), Claim.practice_id == practice_id)
        .all()
    )
    task_ids = []
    for claim in claims:
        if claim.status == "in_progress":
            continue
        payer = db.get(Payer, claim.payer_id)
        if not payer or not payer.phone:
            continue
        task = initiate_call_for_claim.delay(claim.id)
        task_ids.append(task.id)
    return QueueResponse(
        queued=len(task_ids),
        task_ids=task_ids,
        message=f"Queued {len(task_ids)} claims for calls",
    )


@router.get("", response_model=list[CallResponse])
def list_calls(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    claim_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List calls. Filter by claim_id or return recent calls for the practice."""
    practice_id = require_practice(current_user)

    q = (
        db.query(Call)
        .join(Claim)
        .filter(Claim.practice_id == practice_id)
    )
    if claim_id:
        q = q.filter(Call.claim_id == claim_id)
    calls = q.order_by(Call.created_at.desc()).offset(skip).limit(limit).all()
    return calls


@router.get("/{call_id}", response_model=CallResponse)
def get_call(
    call_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    practice_id = require_practice(current_user)
    call = (
        db.query(Call)
        .join(Claim)
        .filter(Call.id == call_id, Claim.practice_id == practice_id)
        .first()
    )
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call
