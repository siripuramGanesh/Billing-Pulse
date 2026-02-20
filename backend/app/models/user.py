from sqlalchemy import String, ForeignKey, Boolean, Column, Integer
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class Practice(Base, TimestampMixin):
    __tablename__ = "practices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    npi = Column(String(20), unique=True)
    tax_id = Column(String(20))
    address = Column(String(500))
    phone = Column(String(20))
    notification_email = Column(String(255))  # optional; if set, call notifications go here instead of user emails

    users = relationship("User", back_populates="practice")
    payers = relationship("Payer", back_populates="practice")
    claims = relationship("Claim", back_populates="practice")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    practice_id = Column(Integer, ForeignKey("practices.id"))
    role = Column(String(32), default="staff", nullable=False)  # staff | admin (admin can view audit logs, manage practice)

    practice = relationship("Practice", back_populates="users")
