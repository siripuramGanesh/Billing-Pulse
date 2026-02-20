from sqlalchemy import String, ForeignKey, Column, Integer, Text, JSON
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class CallOutcome:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REPROCESS_REQUESTED = "reprocess_requested"
    APPEAL_ESCALATED = "appeal_escalated"
    NO_ANSWER = "no_answer"
    FAILED = "failed"


class Call(Base, TimestampMixin):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)

    status = Column(String(50), default="pending", index=True)
    outcome = Column(String(50))
    duration_seconds = Column(Integer)
    transcript = Column(Text)
    external_id = Column(String(100), index=True)  # Vapi/Bland call ID
    extracted_data = Column(JSON)  # LLM-extracted outcome (Phase 3)

    claim = relationship("Claim", back_populates="calls")
