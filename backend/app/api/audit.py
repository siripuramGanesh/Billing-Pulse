"""Audit log API (Phase 7). Admin or staff can list practice audit logs."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..core.dependencies import get_current_user
from ..models import User, AuditLog
from ..schemas.audit_log import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List audit logs for the current user's practice. Scoped by practice_id."""
    if not current_user.practice_id:
        raise HTTPException(status_code=400, detail="No practice associated")
    q = db.query(AuditLog).filter(AuditLog.practice_id == current_user.practice_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if resource_type:
        q = q.filter(AuditLog.resource_type == resource_type)
    logs = q.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    return logs
