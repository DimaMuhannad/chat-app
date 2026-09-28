from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_INPUT = "waiting_for_input"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    DEVELOPER = "developer"
    RESEARCHER = "researcher"
    TERMINAL = "terminal"
    CUSTOM = "custom"


class AgentConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str
    agent_type: AgentType = AgentType.CUSTOM
    status: AgentStatus = AgentStatus.IDLE
    description: str = ""
    system_prompt: str = ""
    model: str = "gemini-2.5-pro"
    temperature: float = 0.7
    enabled_tools: List[str] = Field(default_factory=list)
    workspace_path: Optional[str] = None
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    session_id: Optional[str] = None
    title: str
    description: str
    status: AgentStatus = AgentStatus.IDLE
    status_detail: Optional[str] = None
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ArtifactType(str, Enum):
    FILE = "file"
    DIFF = "diff"
    MARKDOWN = "markdown"
    PLAN = "plan"
    IMAGE = "image"


class Artifact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    name: str
    artifact_type: ArtifactType
    path: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=get_utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
