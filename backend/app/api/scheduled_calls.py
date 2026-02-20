"""API for scheduling follow-up calls."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..core.dependencies import get_current_user
from ..models import User, Claim, ScheduledCall
from ..schemas.scheduled_call import ScheduledCallCreate, ScheduledCallResponse
from ..tasks.call_tasks import initiate_call_for_claim

router = APIRouter(prefix="/scheduled-calls", tags=["scheduled-calls"])


def require_practice(current_user: User) -> int:
    if not current_user.practice_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create a practice first",
        )
    return current_user.practice_id


@router.post("", response_model=ScheduledCallResponse)
def create_scheduled_call(
    data: ScheduledCallCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Schedule a follow-up call for a claim. Call will be queued when call_after is reached (processed by Celery)."""
    practice_id = require_practice(current_user)
    claim = (
        db.query(Claim)
        .filter(Claim.id == data.claim_id, Claim.practice_id == practice_id)
        .first()
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    # Normalize to UTC if naive
    call_after = data.call_after
    if call_after.tzinfo is None:
        call_after = call_after.replace(tzinfo=timezone.utc)
    if call_after <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="call_after must be in the future",
        )
    scheduled = ScheduledCall(
        claim_id=data.claim_id,
        call_after=call_after,
        reason=data.reason,
    )
    db.add(scheduled)
    db.commit()
    db.refresh(scheduled)
    return scheduled


@router.get("", response_model=list[ScheduledCallResponse])
def list_scheduled_calls(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    claim_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List scheduled calls for the practice. Optionally filter by claim_id."""
    practice_id = require_practice(current_user)
    q = (
        db.query(ScheduledCall)
        .join(Claim)
        .filter(Claim.practice_id == practice_id)
    )
    if claim_id is not None:
        q = q.filter(ScheduledCall.claim_id == claim_id)
    rows = q.order_by(ScheduledCall.call_after.asc()).offset(skip).limit(limit).all()
    return rows


@router.delete("/{scheduled_call_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_scheduled_call(
    scheduled_call_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a scheduled call."""
    practice_id = require_practice(current_user)
    scheduled = (
        db.query(ScheduledCall)
        .join(Claim)
        .filter(
            ScheduledCall.id == scheduled_call_id,
            Claim.practice_id == practice_id,
        )
        .first()
    )
    if not scheduled:
        raise HTTPException(status_code=404, detail="Scheduled call not found")
    db.delete(scheduled)
    db.commit()
    return None
