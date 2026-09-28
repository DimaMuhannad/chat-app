from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ToolCallInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolResultInfo(BaseModel):
    tool_call_id: str
    tool_name: str
    output: Any
    is_error: bool = False


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: MessageRole
    content: str = ""
    thinking: Optional[str] = None
    tool_calls: Optional[List[ToolCallInfo]] = None
    tool_results: Optional[List[ToolResultInfo]] = None
    created_at: datetime = Field(default_factory=get_utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Chat"
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)
    model: str = "gemini-2.5-pro"
    agent_id: Optional[str] = None
    system_prompt: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    model: Optional[str] = None
    agent_id: Optional[str] = None
    system_prompt: Optional[str] = None
    stream: bool = True


class ChatResponseType(str, Enum):
    TOKEN = "token"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    STATUS = "status"
    ERROR = "error"
    DONE = "done"


class ChatStreamChunk(BaseModel):
    session_id: str
    message_id: str
    type: ChatResponseType
    content: Optional[str] = None
    tool_call: Optional[ToolCallInfo] = None
    tool_result: Optional[ToolResultInfo] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=get_utc_now)
