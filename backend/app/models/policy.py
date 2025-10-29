from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime
from app.core.database import Base


class Policy(Base):
    """Store policies as raw JSON - no schema assumptions"""
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)  # Optional display name
    raw = Column(JSON, nullable=False)  # Full uploaded policy JSON
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserData(Base):
    """Store user data as raw JSON - no schema assumptions"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    raw = Column(JSON, nullable=False)  # Full uploaded user record
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class EvaluationResult(Base):
    """Store evaluation results"""
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    user_data = Column(JSON, nullable=False)  # Raw user data evaluated
    policy_data = Column(JSON, nullable=False)  # Raw policy used
    passed = Column(String, nullable=False)  # Boolean stored as string for SQLite compatibility
    details = Column(JSON)  # Detailed evaluation breakdown
    evaluated_at = Column(DateTime, default=datetime.utcnow)
