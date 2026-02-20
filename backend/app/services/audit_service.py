"""Audit logging for HIPAA-oriented access and action tracking."""

from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models import AuditLog


def log(
    db: Session,
    practice_id: int,
    action: str,
    resource_type: str,
    *,
    user_id: Optional[int] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Append an audit log entry. Caller should commit."""
    entry = AuditLog(
        practice_id=practice_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
