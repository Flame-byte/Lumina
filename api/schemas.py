"""
API Data Models Module

Defines Pydantic models for FastAPI requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ChatRequest(BaseModel):
    """Chat request"""
    message: str = Field(..., description="User message content")
    files: Optional[List[str]] = Field(default=None, description="File path list (for backward compatibility, deprecated)")
    thread_id: Optional[str] = Field(default=None, description="Optional thread ID for multi-turn conversation")
    session_id: Optional[str] = Field(default=None, description="Optional session ID for database")


class ChatResponse(BaseModel):
    """Chat response"""
    thread_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Status: pending_confirmation | completed | interrupted")
    todo_list: Optional[List[Dict[str, Any]]] = Field(default=None, description="Task list")
    tool_list: Optional[List[Dict[str, Any]]] = Field(default=None, description="Tool list")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Execution result")
    interrupt_info: Optional[Dict[str, Any]] = Field(default=None, description="Interrupt information")
    messages: Optional[List[Dict[str, Any]]] = Field(default=None, description="Message list (for multi-turn conversation)")


class ConfirmRequest(BaseModel):
    """Confirm request"""
    thread_id: str = Field(..., description="Session ID")


class ConfirmResponse(BaseModel):
    """Confirm response"""
    thread_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Status: completed")
    result: Dict[str, Any] = Field(..., description="Execution result")
    messages: Optional[List[Dict[str, Any]]] = Field(default=None, description="Message list (for multi-turn conversation)")


class RejectRequest(BaseModel):
    """Reject request"""
    thread_id: str = Field(..., description="Session ID")
    feedback: str = Field(..., description="Rejection reason/feedback")


class RejectResponse(BaseModel):
    """Reject response"""
    thread_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Status: pending_confirmation | completed")
    result: Dict[str, Any] = Field(..., description="Re-planning result")


class StatusResponse(BaseModel):
    """Status response"""
    thread_id: str = Field(..., description="Session ID")
    todo_list: List[Dict[str, Any]] = Field(default=[], description="Task list")
    tool_list: List[Dict[str, Any]] = Field(default=[], description="Tool list")
    execution_results: Dict[str, Any] = Field(default={}, description="Execution results")
    has_pending_interrupt: bool = Field(default=False, description="Whether there is a pending interrupt")


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed information")


class SessionDeleteResponse(BaseModel):
    """Session delete response"""
    status: str = Field(..., description="Status")
    session_id: str = Field(..., description="Session ID")
    deleted_items: int = Field(..., description="Number of deleted items")


class SessionInfo(BaseModel):
    """Session info"""
    id: str = Field(..., description="Session ID")
    title: Optional[str] = Field(default=None, description="Session title")
    created_at: Optional[str] = Field(default=None, description="Creation time")
    updated_at: Optional[str] = Field(default=None, description="Update time")
    status: Optional[str] = Field(default=None, description="Status")


class SessionsResponse(BaseModel):
    """Sessions list response"""
    sessions: List[SessionInfo] = Field(..., description="Sessions list")


class LoadSessionRequest(BaseModel):
    """Load session request"""
    thread_id: Optional[str] = Field(default=None, description="Thread ID")


class LoadSessionResponse(BaseModel):
    """Load session response"""
    session_id: str = Field(..., description="Session ID")
    thread_id: Optional[str] = Field(default=None, description="Thread ID")
    status: str = Field(..., description="Status")


class UploadResponse(BaseModel):
    """Upload file response"""
    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Status")
    files: List[Dict[str, Any]] = Field(..., description="Uploaded file information")


class SessionFilesResponse(BaseModel):
    """Session files list response"""
    session_id: str = Field(..., description="Session ID")
    files: List[Dict[str, Any]] = Field(..., description="File list")


class DeleteSessionResponse(BaseModel):
    """Delete session response"""
    status: str = Field(..., description="Status")
    session_id: str = Field(..., description="Session ID")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Status")
    version: Optional[str] = Field(default=None, description="Version number")


class ConfigGetResponse(BaseModel):
    """Get config response"""
    llm: Dict[str, Any] = Field(..., description="LLM configuration")
    agent: Dict[str, Any] = Field(..., description="Agent configuration")


class ConfigUpdateRequest(BaseModel):
    """Update config request"""
    llm: Optional[Dict[str, Any]] = Field(default=None, description="LLM configuration update")
    agent: Optional[Dict[str, Any]] = Field(default=None, description="Agent configuration update")


class ConfigUpdateResponse(BaseModel):
    """Update config response"""
    status: str = Field(..., description="Status")
    llm: Optional[Dict[str, Any]] = Field(default=None, description="Updated LLM configuration")
    agent: Optional[Dict[str, Any]] = Field(default=None, description="Updated Agent configuration")
