"""Scheduled follow-up calls."""

from sqlalchemy import Integer, ForeignKey, Column, DateTime, String
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class ScheduledCall(Base, TimestampMixin):
    __tablename__ = "scheduled_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    call_after = Column(DateTime(timezone=True), nullable=False)
    reason = Column(String(255), nullable=True)

    claim = relationship("Claim", back_populates="scheduled_calls")
