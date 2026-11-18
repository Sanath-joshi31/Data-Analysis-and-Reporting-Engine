"""Database persistence models for sessions, dataset metadata, and execution traces."""

from datetime import datetime
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class DatasetModel(Base):
    """Stored metadata and profile for an uploaded or sample dataset."""
    __tablename__ = "datasets"

    id = Column(String(64), primary_key=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    health_score = Column(Float, default=100.0)
    profile_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("AnalysisSessionModel", back_populates="dataset", cascade="all, delete-orphan")


class AnalysisSessionModel(Base):
    """An analytical session associated with a dataset and conversation history."""
    __tablename__ = "analysis_sessions"

    id = Column(String(64), primary_key=True)
    dataset_id = Column(String(64), ForeignKey("datasets.id"), nullable=False)
    title = Column(String(255), default="New Analysis")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dataset = relationship("DatasetModel", back_populates="sessions")
    messages = relationship("ChatMessageModel", back_populates="session", cascade="all, delete-orphan")
    traces = relationship("ExecutionTraceModel", back_populates="session", cascade="all, delete-orphan")


class ChatMessageModel(Base):
    """Conversation history message between user and autonomous analyst."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("analysis_sessions.id"), nullable=False)
    role = Column(String(32), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    code_generated = Column(Text, nullable=True)
    execution_success = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("AnalysisSessionModel", back_populates="messages")


class ExecutionTraceModel(Base):
    """Audit log of code generation and sandbox execution attempts."""
    __tablename__ = "execution_traces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("analysis_sessions.id"), nullable=False)
    attempt_number = Column(Integer, default=1)
    code_executed = Column(Text, nullable=False)
    success = Column(Boolean, default=False)
    return_code = Column(Integer, default=0)
    execution_time_seconds = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("AnalysisSessionModel", back_populates="traces")
