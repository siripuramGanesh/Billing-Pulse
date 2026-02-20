"""Phase 7: Reporting & analytics - denial trends, payer performance, export."""

import io
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..core.dependencies import get_current_user
from ..models import User, Claim, Call, Payer
from ..services.encryption_service import decrypt_value

router = APIRouter(prefix="/reports", tags=["reports"])


def require_practice(current_user: User) -> int:
    if not current_user.practice_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Create a practice first")
    return current_user.practice_id


@router.get("/denial-trends")
def get_denial_trends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(90, ge=1, le=365),
):
    """Denial code counts and trends for the practice."""
    practice_id = require_practice(current_user)
    start = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        db.query(Claim.denial_code, func.count(Claim.id).label("count"))
        .filter(Claim.practice_id == practice_id, Claim.denial_code.isnot(None), Claim.denial_code != "")
        .filter(Claim.updated_at >= start)
        .group_by(Claim.denial_code)
        .order_by(func.count(Claim.id).desc())
    )
    rows = q.all()
    return {"denial_codes": [{"code": r.denial_code, "count": r.count} for r in rows], "days": days}


@router.get("/payer-performance")
def get_payer_performance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(90, ge=1, le=365),
):
    """Per-payer: total claims, resolved, resolution rate, total calls."""
    practice_id = require_practice(current_user)
    start = datetime.now(timezone.utc) - timedelta(days=days)
    payers = db.query(Payer).filter(Payer.practice_id == practice_id).all()
    result = []
    for p in payers:
        total = (
            db.query(func.count(Claim.id))
            .filter(Claim.payer_id == p.id, Claim.updated_at >= start)
            .scalar()
            or 0
        )
        resolved = (
            db.query(func.count(Claim.id))
            .filter(Claim.payer_id == p.id, Claim.updated_at >= start, Claim.status == "resolved")
            .scalar()
            or 0
        )
        rate = (resolved / total * 100) if total else 0.0
        calls = (
            db.query(func.count(Call.id))
            .join(Claim)
            .filter(Claim.payer_id == p.id, Call.created_at >= start)
            .scalar()
            or 0
        )
        result.append({
            "payer_id": p.id,
            "payer_name": p.name,
            "total_claims": total,
            "resolved_claims": resolved,
            "resolution_rate_pct": round(rate, 1),
            "calls_count": calls,
        })
    return {"payers": result, "days": days}


@router.get("/export/claims")
def export_claims(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    status_filter: str | None = Query(None, alias="status"),
):
    """Export claims to CSV or Excel. Respects practice scope."""
    practice_id = require_practice(current_user)
    q = db.query(Claim).filter(Claim.practice_id == practice_id).order_by(Claim.id)
    if status_filter:
        q = q.filter(Claim.status == status_filter)
    claims = q.all()
    rows = []
    for c in claims:
        rows.append({
            "id": c.id,
            "claim_number": c.claim_number,
            "patient_name": c.patient_name,
            "patient_dob": c.patient_dob,
            "date_of_service": c.date_of_service,
            "amount": float(c.amount) if c.amount else None,
            "status": c.status,
            "denial_reason": decrypt_value(c.denial_reason),
            "denial_code": c.denial_code,
            "notes": decrypt_value(c.notes),
            "payer_id": c.payer_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    df = pd.DataFrame(rows)
    if format == "csv":
        buf = io.BytesIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=claims_export.csv"},
        )
    else:
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=claims_export.xlsx"},
        )
