"""
Pydantic Data Model Module

For API request/response validation and data serialization
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SessionStatusEnum(str, Enum):
    """Session status enum"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ToolExecutionStatusEnum(str, Enum):
    """Tool execution status enum"""
    SUCCESS = "success"
    FAILED = "failed"


# ========== Session Related Models ==========

class SessionCreate(BaseModel):
    """Create session request"""
    title: Optional[str] = Field(default=None, description="Session title")


class SessionResponse(BaseModel):
    """Session response"""
    id: str = Field(..., description="Session ID")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: Optional[datetime] = Field(default=None, description="Update time")
    status: str = Field(..., description="Session status")
    title: Optional[str] = Field(default=None, description="Session title")

    class Config:
        from_attributes = True


# ========== Message Related Models ==========

class MessageCreate(BaseModel):
    """Create message request"""
    thread_id: str = Field(..., description="Thread ID")
    role: str = Field(..., description="Role (human/ai/system/tool)")
    content: str = Field(..., description="Message content")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="Tool call list")
    tool_call_id: Optional[str] = Field(default=None, description="Tool call ID")


class MessageResponse(BaseModel):
    """Message response"""
    id: str = Field(..., description="Message ID")
    session_id: str = Field(..., description="Session ID")
    thread_id: str = Field(..., description="Thread ID")
    role: str = Field(..., description="Role")
    content: str = Field(..., description="Message content")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="Tool call list")
    tool_call_id: Optional[str] = Field(default=None, description="Tool call ID")
    created_at: datetime = Field(..., description="Creation time")

    class Config:
        from_attributes = True


# ========== Tool Execution Log Related Models ==========

class ToolExecutionLogCreate(BaseModel):
    """Create tool execution log request"""
    tool_name: str = Field(..., description="Tool name")
    input_args: Optional[Dict[str, Any]] = Field(default=None, description="Input parameters")
    output_result: Optional[Dict[str, Any]] = Field(default=None, description="Output result")
    status: str = Field(..., description="Status (success/failed)")
    error_message: Optional[str] = Field(default=None, description="Error message")
    execution_time_ms: Optional[int] = Field(default=None, description="Execution time (milliseconds)")


class ToolExecutionLogResponse(BaseModel):
    """Tool execution log response"""
    id: str = Field(..., description="Log ID")
    session_id: str = Field(..., description="Session ID")
    tool_name: str = Field(..., description="Tool name")
    input_args: Optional[Dict[str, Any]] = Field(default=None, description="Input parameters")
    output_result: Optional[Dict[str, Any]] = Field(default=None, description="Output result")
    status: str = Field(..., description="Status")
    error_message: Optional[str] = Field(default=None, description="Error message")
    execution_time_ms: Optional[int] = Field(default=None, description="Execution time")
    created_at: datetime = Field(..., description="Creation time")

    class Config:
        from_attributes = True


# ========== List Response Models ==========

class SessionListResponse(BaseModel):
    """Session list response"""
    sessions: List[SessionResponse]
    total: int


class MessageListResponse(BaseModel):
    """Message list response"""
    messages: List[MessageResponse]
    total: int


class ToolExecutionLogListResponse(BaseModel):
    """Tool execution log list response"""
    logs: List[ToolExecutionLogResponse]
    total: int
