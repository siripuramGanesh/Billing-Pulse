"""Audit log for HIPAA-oriented tracking of who did what and when."""

from sqlalchemy import String, ForeignKey, Column, Integer, Text, JSON, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    practice_id = Column(Integer, ForeignKey("practices.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # null for system/webhook
    action = Column(String(64), nullable=False, index=True)  # login, claim.view, claim.update, call.initiate, etc.
    resource_type = Column(String(32), nullable=False, index=True)  # claim, call, payer, practice, user
    resource_id = Column(String(64), nullable=True, index=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    practice = relationship("Practice", foreign_keys=[practice_id])
    user = relationship("User", foreign_keys=[user_id])
