from sqlalchemy import String, ForeignKey, Column, Integer, Text, JSON
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class Payer(Base, TimestampMixin):
    __tablename__ = "payers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    practice_id = Column(Integer, ForeignKey("practices.id"), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    ivr_notes = Column(Text)  # IVR navigation hints (legacy)
    ivr_config = Column(JSON)  # Structured: {"steps": [{"prompt": "...", "options": {"1": "claims", "2": "..."}}]}
    department_code = Column(String(50))  # e.g., "2" for claims dept

    practice = relationship("Practice", back_populates="payers")
    claims = relationship("Claim", back_populates="payer")
