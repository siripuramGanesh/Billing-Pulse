"""Metrics API for dashboard."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..core.dependencies import get_current_user
from ..models import User, Claim, Call
from ..schemas.metrics import MetricsResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


def require_practice(current_user: User) -> int:
    if not current_user.practice_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Create a practice first")
    return current_user.practice_id


@router.get("", response_model=MetricsResponse)
def get_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=90),
):
    """Get dashboard metrics for the practice."""
    practice_id = require_practice(current_user)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Claim counts by status
    claim_counts = (
        db.query(Claim.status, func.count(Claim.id))
        .filter(Claim.practice_id == practice_id)
        .group_by(Claim.status)
        .all()
    )
    status_map = {s: c for s, c in claim_counts}
    total_claims = sum(status_map.values())
    pending_claims = status_map.get("pending", 0)
    in_progress_claims = status_map.get("in_progress", 0)
    resolved_claims = status_map.get("resolved", 0)

    # Call counts
    total_calls = (
        db.query(func.count(Call.id))
        .join(Claim)
        .filter(Claim.practice_id == practice_id)
        .scalar()
        or 0
    )
    calls_today = (
        db.query(func.count(Call.id))
        .join(Claim)
        .filter(Claim.practice_id == practice_id, Call.created_at >= today_start)
        .scalar()
        or 0
    )
    calls_this_week = (
        db.query(func.count(Call.id))
        .join(Claim)
        .filter(Claim.practice_id == practice_id, Call.created_at >= week_start)
        .scalar()
        or 0
    )

    # Resolution rate: ended calls with outcome resolved / total ended
    ended_calls = (
        db.query(func.count(Call.id))
        .join(Claim)
        .filter(
            Claim.practice_id == practice_id,
            Call.status == "ended",
        )
        .scalar()
        or 0
    )
    resolved_calls = (
        db.query(func.count(Call.id))
        .join(Claim)
        .filter(
            Claim.practice_id == practice_id,
            Call.status == "ended",
            Call.outcome.in_(["resolved", "reprocess_requested"]),
        )
        .scalar()
        or 0
    )
    resolution_rate = (resolved_calls / ended_calls * 100) if ended_calls > 0 else 0.0

    # Revenue recovered (resolved claims amount sum)
    revenue_result = (
        db.query(func.coalesce(func.sum(Claim.amount), 0))
        .filter(Claim.practice_id == practice_id, Claim.status == "resolved")
        .scalar()
    )
    revenue_recovered = float(revenue_result) if revenue_result else 0.0

    # Calls by day (last N days)
    start_date = today_start - timedelta(days=days)
    try:
        calls_by_day_raw = (
            db.query(func.date(Call.created_at).label("date"), func.count(Call.id).label("count"))
            .join(Claim)
            .filter(
                Claim.practice_id == practice_id,
                Call.created_at >= start_date,
            )
            .group_by(func.date(Call.created_at))
            .order_by(func.date(Call.created_at))
            .all()
        )
        calls_by_day = [{"date": str(d), "count": c} for d, c in calls_by_day_raw]
    except Exception:
        calls_by_day = []

    # In-progress calls
    in_progress = (
        db.query(Call)
        .join(Claim)
        .filter(
            Claim.practice_id == practice_id,
            Call.status.in_(["initiated", "in_progress"]),
        )
        .order_by(Call.created_at.desc())
        .limit(20)
        .all()
    )
    in_progress_calls = [
        {"id": c.id, "claim_id": c.claim_id, "status": c.status}
        for c in in_progress
    ]

    return MetricsResponse(
        total_claims=total_claims,
        pending_claims=pending_claims,
        in_progress_claims=in_progress_claims,
        resolved_claims=resolved_claims,
        total_calls=total_calls,
        calls_today=calls_today,
        calls_this_week=calls_this_week,
        resolution_rate=round(resolution_rate, 1),
        revenue_recovered=revenue_recovered,
        calls_by_day=calls_by_day,
        in_progress_calls=in_progress_calls,
    )
