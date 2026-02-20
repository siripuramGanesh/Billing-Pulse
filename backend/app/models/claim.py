from sqlalchemy import String, ForeignKey, Column, Integer, Text, Numeric, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, TimestampMixin


class ClaimStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DENIED = "denied"
    APPEAL_REQUIRED = "appeal_required"


class Claim(Base, TimestampMixin):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    practice_id = Column(Integer, ForeignKey("practices.id"), nullable=False)
    payer_id = Column(Integer, ForeignKey("payers.id"), nullable=False)

    claim_number = Column(String(100), nullable=False, index=True)
    patient_name = Column(String(255))
    patient_dob = Column(String(20))
    date_of_service = Column(String(50))
    amount = Column(Numeric(12, 2))
    status = Column(String(50), default=ClaimStatus.PENDING, index=True)
    denial_reason = Column(Text)
    denial_code = Column(String(50))
    notes = Column(Text)
    claimer_notified_at = Column(DateTime(timezone=True))  # when we last emailed the practice about this claim

    practice = relationship("Practice", back_populates="claims")
    payer = relationship("Payer", back_populates="claims")
    calls = relationship("Call", back_populates="claim", order_by="Call.created_at")
    scheduled_calls = relationship("ScheduledCall", back_populates="claim")
