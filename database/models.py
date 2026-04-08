"""
SQLAlchemy Model Definition Module

Defines ORM models for database tables
"""

from sqlalchemy import (
    create_engine, Column, String, Text, Integer, DateTime, ForeignKey,
    Enum, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import enum

Base = declarative_base()


class SessionStatus(enum.Enum):
    """Session status enum"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ToolExecutionStatus(enum.Enum):
    """Tool execution status enum"""
    SUCCESS = "success"
    FAILED = "failed"


class Session(Base):
    """Session table model"""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    status = Column(String, default="active")
    title = Column(Text, nullable=True)

    # Relationships
    processed_data = relationship(
        "ProcessedData",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    tool_logs = relationship(
        "ToolExecutionLog",
        back_populates="session",
        cascade="all, delete-orphan"
    )


class ProcessedData(Base):
    """Processed data table model"""
    __tablename__ = "processed_data"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    original_filename = Column(Text, nullable=False)
    file_type = Column(String, nullable=False)
    processed_type = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    data_metadata = Column("metadata", Text, nullable=True)  # Use metadata column name, but attribute name is data_metadata
    storage_path = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="processed_data")


class Message(Base):
    """Message history table model"""
    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    thread_id = Column(String, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    tool_calls = Column(Text, nullable=True)
    tool_call_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="messages")


class ToolExecutionLog(Base):
    """Tool execution log table model"""
    __tablename__ = "tool_execution_logs"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    tool_name = Column(String, nullable=False)
    input_args = Column(Text, nullable=True)
    output_result = Column(Text, nullable=True)
    status = Column(String, nullable=False)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="tool_logs")


def create_tables(engine_url: str):
    """
    Create all tables

    Args:
        engine_url: SQLite database URL
    """
    engine = create_engine(engine_url)
    Base.metadata.create_all(engine)


def drop_tables(engine_url: str):
    """
    Drop all tables

    Args:
        engine_url: SQLite database URL
    """
    engine = create_engine(engine_url)
    Base.metadata.drop_all(engine)
